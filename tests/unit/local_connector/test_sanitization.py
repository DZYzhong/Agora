from pydantic import ValidationError
import pytest

from packages.domain.local_workspace import LocalWorkspaceObservation
from packages.local_connector.sanitization import normalize_repository_identity


def test_normalizes_https_remote_without_credentials():
    identity = normalize_repository_identity("https://alice:s3cr3t@example.com/team/payment-service.git")

    assert identity.host == "example.com"
    assert identity.path == "team/payment-service"
    assert identity.normalized == "example.com/team/payment-service"
    assert "alice" not in identity.model_dump_json()
    assert "s3cr3t" not in identity.model_dump_json()


def test_normalizes_scp_ssh_remote_without_username():
    identity = normalize_repository_identity("git@example.com:team/payment-service.git")

    assert identity.host == "example.com"
    assert identity.path == "team/payment-service"
    assert identity.normalized == "example.com/team/payment-service"
    assert "git@" not in identity.model_dump_json()


def test_local_observation_rejects_local_path_fields():
    with pytest.raises(ValidationError, match="local workspace paths"):
        LocalWorkspaceObservation.model_validate(
            {
                "workspace_root": "/Users/daniel/Documents/payment",
                "dirty": False,
            }
        )
