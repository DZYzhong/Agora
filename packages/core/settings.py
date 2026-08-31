from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

RuntimeEnvironment = Literal["test", "development", "production"]
SUPPORTED_ENVIRONMENTS: tuple[RuntimeEnvironment, ...] = ("test", "development", "production")
SQLITE_TEST_TOKEN = re.compile(r"(?:^|[^a-z0-9])test(?:[^a-z0-9]|$)", re.IGNORECASE)


class RuntimeConfigurationError(ValueError):
    def __init__(self, *, code: str, message: str, field: str):
        self.code = code
        self.message = message
        self.field = field
        super().__init__(message)

    @property
    def diagnostic(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "field": self.field}


@dataclass(frozen=True)
class RuntimePolicy:
    environment: RuntimeEnvironment
    database_url: str = field(repr=False)
    auth_bypass: bool
    local_init_root: Path | None


def validate_runtime_policy(
    environment: str | None,
    database_url: str,
    auth_bypass: bool,
    local_init_root: str | None,
) -> RuntimePolicy:
    requested_environment = environment if environment is not None else "development"
    if requested_environment not in SUPPORTED_ENVIRONMENTS:
        raise RuntimeConfigurationError(
            code="AGORA_ENV_INVALID",
            message="AGORA_ENV must be one of: test, development, production",
            field="AGORA_ENV",
        )
    normalized_environment = cast(RuntimeEnvironment, requested_environment)

    if normalized_environment != "test" and auth_bypass:
        raise RuntimeConfigurationError(
            code="AGORA_TEST_AUTH_BYPASS_FORBIDDEN",
            message="AGORA_TEST_AUTH_BYPASS is only allowed in an isolated test environment",
            field="AGORA_TEST_AUTH_BYPASS",
        )

    configured_local_init_root = (
        local_init_root if local_init_root and local_init_root.strip() else None
    )
    if normalized_environment == "production" and configured_local_init_root is not None:
        raise RuntimeConfigurationError(
            code="AGORA_LOCAL_INIT_ROOT_FORBIDDEN",
            message="AGORA_LOCAL_INIT_ROOT is not allowed in production",
            field="AGORA_LOCAL_INIT_ROOT",
        )

    if auth_bypass and not _is_isolated_test_database(database_url):
        raise RuntimeConfigurationError(
            code="AGORA_TEST_DATABASE_NOT_ISOLATED",
            message="AGORA_TEST_AUTH_BYPASS requires an isolated test database",
            field="AGORA_DATABASE_URL",
        )

    resolved_local_init_root = (
        _resolve_local_init_root(configured_local_init_root)
        if configured_local_init_root is not None
        else None
    )

    return RuntimePolicy(
        environment=normalized_environment,
        database_url=database_url,
        auth_bypass=auth_bypass,
        local_init_root=resolved_local_init_root,
    )


def _is_isolated_test_database(database_url: str) -> bool:
    try:
        url = make_url(database_url)
    except ArgumentError:
        return False

    database_name = url.database or ""
    if url.get_backend_name() == "sqlite":
        database_path = Path(database_name)
        if not database_path.is_absolute() or SQLITE_TEST_TOKEN.search(database_path.name) is None:
            return False
        if database_path.is_symlink():
            return False
        return True
    if url.get_backend_name() == "postgresql":
        return database_name.lower().endswith("_test")
    return False


def _resolve_local_init_root(local_init_root: str) -> Path:
    raw_path = Path(local_init_root)
    if not raw_path.is_absolute():
        raise _invalid_local_init_root()

    resolved_path = raw_path.resolve()
    unsafe_paths = {Path("/").resolve(), Path.cwd().resolve(), Path.home().resolve()}
    if resolved_path in unsafe_paths:
        raise _invalid_local_init_root()
    return resolved_path


def _invalid_local_init_root() -> RuntimeConfigurationError:
    return RuntimeConfigurationError(
        code="AGORA_LOCAL_INIT_ROOT_INVALID",
        message="AGORA_LOCAL_INIT_ROOT must be an explicit safe absolute path",
        field="AGORA_LOCAL_INIT_ROOT",
    )
