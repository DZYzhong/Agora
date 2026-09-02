import pytest

from packages.core.passwords import (
    PasswordHashError,
    hash_password,
    password_hash_digest,
    verify_and_upgrade,
    verify_password,
)


def test_hash_verify_round_trip():
    password_hash = hash_password("correct horse battery staple")
    assert password_hash.startswith("$argon2id$")
    assert verify_password("correct horse battery staple", password_hash) is True


def test_wrong_password_fails():
    password_hash = hash_password("correct horse battery staple")
    assert verify_password("wrong password", password_hash) is False


def test_hash_parameters_embedded_in_phc_string():
    password_hash = hash_password("secret")
    assert "$argon2id$v=19$" in password_hash
    assert "m=" in password_hash
    assert "t=" in password_hash
    assert "p=" in password_hash


def test_verify_upgrade_returns_new_hash_when_parameters_drift():
    password_hash = hash_password("secret")
    ok, upgraded = verify_and_upgrade("secret", password_hash)
    assert ok is True
    assert upgraded is None  # current policy parameters already match


def test_verify_upgrade_rejects_wrong_password():
    password_hash = hash_password("secret")
    ok, upgraded = verify_and_upgrade("wrong", password_hash)
    assert ok is False
    assert upgraded is None


def test_blank_password_rejected():
    with pytest.raises(PasswordHashError):
        hash_password("")
    with pytest.raises(PasswordHashError):
        hash_password(None)  # type: ignore[arg-type]


def test_verify_against_missing_hash_fails_through_dummy():
    assert verify_password("anything", None) is False
    assert verify_password("", "some-hash") is False


def test_verify_against_corrupt_hash_returns_false():
    assert verify_password("secret", "not-a-valid-hash") is False


def test_plaintext_never_retained_in_hash_string():
    password = "super-secret-value-xyz"
    password_hash = hash_password(password)
    assert password not in password_hash
    assert password not in password_hash_digest(password_hash)
