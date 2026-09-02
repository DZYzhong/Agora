"""Argon2id password hashing with PHC strings and on-login parameter upgrade.

Design: `docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md`
§5.2 — passwords are stored as Argon2id PHC strings only; the database never
holds plaintext or reversible material. Parameters are embedded in the hash
string, so hashes can be upgraded on successful verification when the cost
parameters drift from the current policy.
"""

from __future__ import annotations

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from packages.core.auth import hash_token

_HASHER = PasswordHasher(type=Type.ID)

# A fake hash used to keep login timing uniform when the account has no
# password set (activation-only users). Verification always fails against it.
_DUMMY_HASH = _HASHER.hash("agora-dummy-password-for-timing")


class PasswordHashError(ValueError):
    pass


def hash_password(password: str) -> str:
    if password is None or not password:
        raise PasswordHashError("password must not be empty")
    return _HASHER.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Return True only when the password matches the stored Argon2id hash.

    Accounts without a password hash (activation-only) always fail through a
    dummy hash so the response time does not reveal whether a user exists or
    has a password set.
    """
    if password is None or not password:
        return False
    candidate = password_hash if password_hash else _DUMMY_HASH
    try:
        return _HASHER.verify(candidate, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def verify_and_upgrade(password: str, password_hash: str | None) -> tuple[bool, str | None]:
    """Verify and return (ok, upgraded_hash) when cost parameters drifted.

    The caller persists the upgraded hash when it is not None and the
    verification succeeded.
    """
    if password is None or not password:
        return False, None
    candidate = password_hash if password_hash else _DUMMY_HASH
    try:
        ok = _HASHER.verify(candidate, password)
    except (VerifyMismatchError, InvalidHashError):
        return False, None
    if not ok:
        return False, None
    try:
        if _HASHER.check_needs_rehash(candidate):
            return True, hash_password(password)
    except InvalidHashError:
        return False, None
    return True, None


def password_hash_digest(password_hash: str) -> str:
    """Deterministic digest of a hash string for audit equality checks."""
    return hash_token(password_hash)
