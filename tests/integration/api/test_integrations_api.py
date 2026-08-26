from fastapi.testclient import TestClient

from apps.api.main import app

HUMAN_TOKEN = "integrations-human-token"
AGENT_TOKEN = "integrations-agent-token"
CI_TOKEN = "integrations-ci-token"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _production_auth(monkeypatch) -> None:
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", HUMAN_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", AGENT_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_CI_TOKEN", CI_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_ORG_ID", "local-org")


def test_ci_quality_signal_records_evidence_and_updates_project_status(monkeypatch):
    _production_auth(monkeypatch)

    with TestClient(app) as client:
        project = client.post(
            "/projects",
            headers=_headers(HUMAN_TOKEN),
            json={
                "org_id": "ignored-org",
                "name": "CI Quality Signal",
                "slug": "ci-quality-signal",
                "git_remotes": ["git@example.com:team/payment-service.git"],
                "default_branch": "main",
            },
        ).json()

        response = client.post(
            "/integrations/ci/quality-signal",
            headers=_headers(CI_TOKEN),
            json={
                "project_id": project["id"],
                "work_item_key": "AG-1101",
                "work_item_title": "修复支付回调重试幂等",
                "status": "failed",
                "conclusion": "CI 中支付回调重试幂等测试失败。",
                "command": "pytest tests/payment/test_callback_retry.py",
                "output_summary": "1 failed, 42 passed",
                "provider": "gitlab-ci",
                "run_id": "pipeline-8848",
                "commit_sha": "abc1234",
                "branch": "feature/AG-1101-payment-callback",
                "raw_ref": "https://gitlab.example.com/team/payment-service/-/pipelines/8848",
            },
        )

        body = response.json()
        project_status = client.post(
            "/harness/get-project-status",
            headers=_headers(AGENT_TOKEN),
            json={"project_id": project["id"]},
        ).json()

    assert response.status_code == 201
    assert body["operation"] == "ingest_ci_quality_signal"
    assert body["work_item"]["external_key"] == "AG-1101"
    assert body["evidence"]["source"] == "ci"
    assert body["evidence"]["status"] == "failed"
    assert body["evidence"]["metadata"]["provider"] == "gitlab-ci"
    assert body["evidence"]["metadata"]["run_id"] == "pipeline-8848"
    assert body["project_status"]["delivery_readiness"]["state"] == "blocked"
    assert project_status["quality_counts"]["failing"] == 1
    assert project_status["quality_dimensions"]["ci"]["failed"] == 1


def test_ci_quality_signal_rejects_non_ci_credentials(monkeypatch):
    _production_auth(monkeypatch)

    with TestClient(app) as client:
        project = client.post(
            "/projects",
            headers=_headers(HUMAN_TOKEN),
            json={
                "org_id": "ignored-org",
                "name": "CI Credential Required",
                "slug": "ci-credential-required",
                "git_remotes": [],
            },
        ).json()
        human_response = client.post(
            "/integrations/ci/quality-signal",
            headers=_headers(HUMAN_TOKEN),
            json={
                "project_id": project["id"],
                "work_item_key": "AG-1102",
                "status": "passed",
                "conclusion": "不应由 human token 上报 CI。",
            },
        )
        agent_response = client.post(
            "/integrations/ci/quality-signal",
            headers=_headers(AGENT_TOKEN),
            json={
                "project_id": project["id"],
                "work_item_key": "AG-1102",
                "status": "passed",
                "conclusion": "不应由 agent token 上报 CI。",
            },
        )

    assert human_response.status_code == 403
    assert human_response.json()["detail"]["code"] == "CI_CREDENTIAL_REQUIRED"
    assert agent_response.status_code == 403
    assert agent_response.json()["detail"]["code"] == "CI_CREDENTIAL_REQUIRED"
