"""Generic protocol-aware idempotency executor for Harness write operations.

Under protocol 1.1 every create/complete/submit/close Harness operation must
carry an ``Idempotency-Key`` header. The executor owns request hashing,
pending/completed replay, deterministic conflicts and response status/body;
endpoints supply the operation name and a transaction-safe callback that runs
inside the unit of work.

The protocol version is part of both the operation scope (record lookup) and
the request hash, so reusing one key across protocol versions cannot replay a
response from the other version and instead returns a deterministic
``IDEMPOTENCY_CONFLICT``.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import timedelta
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from packages.core.auth import Principal
from packages.core.models import utc_now
from packages.core.services.protocol import ProtocolContext
from packages.core.services.runtime import CoreRuntime
from packages.core.uow import SqlAlchemyUnitOfWork

REPLAY_WINDOW = timedelta(hours=24)
MAX_ATTEMPTS = 10
RETRY_DELAY_SECONDS = 0.05

IDEMPOTENCY_REQUIRED_OPERATIONS = frozenset(
    {
        "harness.start_work",
        "harness.prepare_context",
        "harness.submit_context_proposal",
        "harness.complete_workflow_step",
        "harness.submit_skill_candidate",
        "harness.record_evidence",
        "harness.close_work",
    }
)


def idempotency_required(operation: str, protocol: ProtocolContext) -> bool:
    return operation in IDEMPOTENCY_REQUIRED_OPERATIONS and not protocol.legacy


def require_idempotency_key(
    operation: str,
    protocol: ProtocolContext,
    idempotency_key: str | None,
) -> None:
    if idempotency_required(operation, protocol) and not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail={
                "protocol_version": protocol.protocol_version,
                "code": "IDEMPOTENCY_KEY_REQUIRED",
                "message": f"Protocol {protocol.protocol_version} requires an Idempotency-Key header for this operation",
            },
        )


def request_hash_of(request_payload: dict[str, Any], *, protocol: ProtocolContext) -> str:
    encoded = json.dumps(
        {
            "payload": request_payload,
            "protocol_version": protocol.protocol_version,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def json_safe(value: Any) -> Any:
    """Normalize a response to a JSON-storable structure (datetimes to ISO strings)."""
    return json.loads(json.dumps(value, default=str))


def execute_idempotent(
    *,
    session: Session,
    principal: Principal,
    protocol: ProtocolContext,
    operation: str,
    idempotency_key: str | None,
    request_payload: dict[str, Any],
    callback: Callable[[str | None], dict[str, Any]],
) -> dict[str, Any]:
    """Run ``callback`` exactly once per (credential, operation, key, payload, protocol).

    - Protocol 1.1 write operations without a key are rejected up front.
    - A completed record with a matching hash replays the stored response.
    - A completed record with a different hash or protocol returns a conflict.
    - Pending/expired records follow the same deterministic rules as start-work.

    The callback receives the idempotency record id (``None`` without a key) so
    callers can bind created entities to the record for tracing.
    """
    require_idempotency_key(operation, protocol, idempotency_key)
    if idempotency_key is None:
        with SqlAlchemyUnitOfWork(session) as uow:
            response = json_safe(callback(None))
            uow.commit()
        return response

    request_hash = request_hash_of(request_payload, protocol=protocol)
    pending_error: HTTPException | None = None
    for _ in range(MAX_ATTEMPTS):
        pending = False
        try:
            with SqlAlchemyUnitOfWork(session) as uow:
                runtime = CoreRuntime(session)
                record = runtime.get_idempotency_record(
                    credential_id=principal.credential_id,
                    operation=operation,
                    idempotency_key=idempotency_key,
                )
                if record is not None:
                    if record.status == "expired" or _replay_expired(record.replay_expires_at):
                        record.status = "expired"
                        uow.commit()
                        pending_error = _idempotency_error(
                            "IDEMPOTENCY_KEY_EXPIRED",
                            "Idempotency key has expired",
                            protocol=protocol,
                        )
                    elif record.request_hash != request_hash:
                        pending_error = _idempotency_error(
                            "IDEMPOTENCY_CONFLICT",
                            "Idempotency key payload changed",
                            protocol=protocol,
                        )
                    elif record.status == "completed" and record.response_json is not None:
                        uow.commit()
                        return dict(record.response_json)
                    else:
                        pending = True
                else:
                    record = runtime.create_idempotency_record(
                        user_id=principal.user_id,
                        credential_id=principal.credential_id,
                        operation=operation,
                        idempotency_key=idempotency_key,
                        request_hash=request_hash,
                        replay_window=REPLAY_WINDOW,
                    )
                    response = json_safe(callback(record.id))
                    runtime.complete_idempotency_record(record, response_json=response)
                    uow.commit()
                    return response
        except (IntegrityError, OperationalError):
            if session.in_transaction():
                session.rollback()
            time.sleep(RETRY_DELAY_SECONDS)
            continue

        if pending_error is not None:
            raise pending_error
        if pending:
            time.sleep(RETRY_DELAY_SECONDS)
            continue
    raise _idempotency_error(
        "IDEMPOTENCY_REPLAY_PENDING",
        "Idempotency replay is still pending",
        protocol=protocol,
    )


def _replay_expired(replay_expires_at) -> bool:
    now = utc_now()
    if replay_expires_at.tzinfo is None:
        return replay_expires_at <= now.replace(tzinfo=None)
    return replay_expires_at <= now


def _idempotency_error(code: str, message: str, *, protocol: ProtocolContext | None = None) -> HTTPException:
    protocol_version = protocol.protocol_version if protocol is not None else "1.0"
    return HTTPException(
        status_code=409,
        detail={
            "protocol_version": protocol_version,
            "request_id": None,
            "code": code,
            "message": message,
            "error": {"code": code, "message": message},
            "next_actions": [{"type": "retry", "reason": message}],
            "deprecation": {"legacy_error_fields": ["code", "message"], "remove_after": "P2"},
        },
    )
