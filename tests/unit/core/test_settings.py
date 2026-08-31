from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from packages.core.settings import RuntimeConfigurationError, validate_runtime_policy


def test_test_bypass_allows_isolated_sqlite_database():
    policy = validate_runtime_policy("test", "sqlite+pysqlite:////tmp/agora-test.db", True, None)

    assert policy.environment == "test"
    assert policy.auth_bypass is True


def test_production_rejects_auth_bypass():
    with pytest.raises(RuntimeConfigurationError) as exc:
        validate_runtime_policy("production", "postgresql+psycopg://agora@db/agora", True, None)

    assert exc.value.code == "AGORA_TEST_AUTH_BYPASS_FORBIDDEN"
    assert exc.value.field == "AGORA_TEST_AUTH_BYPASS"


def test_development_rejects_auth_bypass():
    with pytest.raises(RuntimeConfigurationError) as exc:
        validate_runtime_policy("development", "sqlite+pysqlite:////tmp/agora-test.db", True, None)

    assert exc.value.code == "AGORA_TEST_AUTH_BYPASS_FORBIDDEN"
    assert exc.value.field == "AGORA_TEST_AUTH_BYPASS"


@pytest.mark.parametrize("local_init_root", ["/srv/repos", ".", "/", ""])
def test_production_rejects_any_local_init_root(local_init_root):
    with pytest.raises(RuntimeConfigurationError) as exc:
        validate_runtime_policy(
            "production",
            "postgresql+psycopg://agora@db/agora",
            False,
            local_init_root,
        )

    assert exc.value.code == "AGORA_LOCAL_INIT_ROOT_FORBIDDEN"
    assert exc.value.field == "AGORA_LOCAL_INIT_ROOT"


@pytest.mark.parametrize("environment", ["local", "production-like"])
def test_unknown_environment_values_return_stable_secret_free_diagnostic(environment):
    secret_database_url = "postgresql+psycopg://agora:top-secret@db/agora"

    with pytest.raises(RuntimeConfigurationError) as exc:
        validate_runtime_policy(environment, secret_database_url, False, None)

    assert exc.value.diagnostic == {
        "code": "AGORA_ENV_INVALID",
        "message": "AGORA_ENV must be one of: test, development, production",
        "field": "AGORA_ENV",
    }
    assert "top-secret" not in str(exc.value)
    assert secret_database_url not in str(exc.value.diagnostic)


@pytest.mark.parametrize("environment", ["test", "development", "production"])
def test_accepts_exact_supported_environment_values(environment):
    policy = validate_runtime_policy(
        environment,
        "postgresql+psycopg://agora@db/agora_test"
        if environment == "test"
        else "postgresql+psycopg://agora@db/agora",
        False,
        None,
    )

    assert policy.environment == environment


def test_missing_environment_defaults_to_development():
    policy = validate_runtime_policy(None, "sqlite+pysqlite:////tmp/agora.db", False, None)

    assert policy.environment == "development"


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite+pysqlite:////tmp/agora-test.db",
        "sqlite+pysqlite:////tmp/contest.sqlite3",
        "postgresql+psycopg://agora@db/agora_test",
    ],
)
def test_test_bypass_accepts_isolated_test_database_names(database_url):
    policy = validate_runtime_policy("test", database_url, True, None)

    assert policy.auth_bypass is True


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite+pysqlite:////tmp/test-fixtures/agora.db",
        "postgresql+psycopg://agora@db/test_agora",
        "postgresql+psycopg://agora@db/agora_test_copy",
    ],
)
def test_test_bypass_rejects_non_isolated_database_names(database_url):
    with pytest.raises(RuntimeConfigurationError) as exc:
        validate_runtime_policy("test", database_url, True, None)

    assert exc.value.code == "AGORA_TEST_DATABASE_NOT_ISOLATED"
    assert exc.value.field == "AGORA_DATABASE_URL"


@pytest.mark.parametrize("environment", ["test", "development"])
def test_non_production_resolves_explicit_local_init_root(environment, tmp_path):
    configured_root = tmp_path / "repos" / ".." / "repos"

    policy = validate_runtime_policy(
        environment,
        "sqlite+pysqlite:////tmp/agora-test.db",
        False,
        str(configured_root),
    )

    assert policy.local_init_root == Path(configured_root).resolve()


@pytest.mark.parametrize("local_init_root", [None, "", "   "])
def test_missing_local_init_root_is_not_inferred(local_init_root):
    policy = validate_runtime_policy("development", "sqlite+pysqlite:////tmp/agora.db", False, local_init_root)

    assert policy.local_init_root is None


def test_runtime_policy_is_immutable():
    policy = validate_runtime_policy("development", "sqlite+pysqlite:////tmp/agora.db", False, None)

    with pytest.raises(FrozenInstanceError):
        policy.environment = "production"
