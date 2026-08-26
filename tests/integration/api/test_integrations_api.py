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
                "task_provider": "jira",
                "task_url": "https://jira.example.com/browse/AG-1101",
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
    assert body["task_link"]["provider"] == "jira"
    assert body["task_link"]["external_key"] == "AG-1101"
    assert body["task_link"]["external_url"] == "https://jira.example.com/browse/AG-1101"
    assert body["project_status"]["delivery_readiness"]["state"] == "blocked"
    assert project_status["quality_counts"]["failing"] == 1
    assert project_status["quality_dimensions"]["ci"]["failed"] == 1
    assert project_status["work_items"][0]["task_links"][0]["external_url"] == "https://jira.example.com/browse/AG-1101"


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


def test_repository_revision_signal_marks_context_stale_and_creates_refresh_proposal(monkeypatch):
    _production_auth(monkeypatch)

    with TestClient(app) as client:
        project = client.post(
            "/projects",
            headers=_headers(HUMAN_TOKEN),
            json={
                "org_id": "ignored-org",
                "name": "Repository Revision Signal",
                "slug": "repository-revision-signal",
                "git_remotes": ["git@example.com:team/order-service.git"],
                "default_branch": "main",
            },
        ).json()
        initial = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json={
                "type": "initial",
                "title": "Initial order context",
                "summary": "订单服务上下文初始版本。",
                "target_branch": "main",
                "expected_head_revision_id": None,
                "to_commit_sha": "old123",
                "content": {"project_overview": "订单服务负责订单状态流转。"},
                "source_anchors": [],
                "provenance": {"generating_tool": "codex", "schema_version": "context-revision/v1"},
            },
        ).json()
        client.post(
            f"/projects/{project['id']}/context/proposals/{initial['id']}/approve",
            headers=_headers(HUMAN_TOKEN),
            json={
                "expected_head_revision_id": None,
                "comment": "批准初始上下文。",
                "revision_signal": {
                    "target_branch": "main",
                    "observed_head_sha": "old123",
                    "contains_to_commit": True,
                },
            },
        )

        response = client.post(
            "/integrations/repository/revision-signal",
            headers=_headers(CI_TOKEN),
            json={
                "project_id": project["id"],
                "provider": "gitlab",
                "repository_identity": "git@example.com:team/order-service.git",
                "branch": "main",
                "observed_head_sha": "new999",
                "previous_head_sha": "old123",
                "signal_type": "push",
                "work_item_key": "AG-1202",
                "work_item_title": "订单状态机合并",
                "raw_ref": "https://gitlab.example.com/team/order-service/-/commit/new999",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["operation"] == "ingest_repository_revision_signal"
    assert body["signal"]["status"] == "stale_context"
    assert body["context_freshness"]["state"] == "stale"
    assert body["context_freshness"]["head_commit_sha"] == "old123"
    assert body["context_freshness"]["observed_head_sha"] == "new999"
    assert body["context_proposal"]["type"] == "refresh"
    assert body["context_proposal"]["status"] == "submitted"
    assert body["context_proposal"]["from_commit_sha"] == "old123"
    assert body["context_proposal"]["to_commit_sha"] == "new999"


def test_repository_revision_signal_reuses_existing_task_link_work_item(monkeypatch):
    _production_auth(monkeypatch)

    with TestClient(app) as client:
        project = client.post(
            "/projects",
            headers=_headers(HUMAN_TOKEN),
            json={
                "org_id": "ignored-org",
                "name": "Task Link Reuse",
                "slug": "task-link-reuse",
                "git_remotes": ["git@example.com:team/profile-service.git"],
                "default_branch": "main",
            },
        ).json()

        ci_response = client.post(
            "/integrations/ci/quality-signal",
            headers=_headers(CI_TOKEN),
            json={
                "project_id": project["id"],
                "work_item_key": "AG-1301",
                "work_item_title": "用户资料脱敏展示",
                "status": "passed",
                "conclusion": "资料脱敏单测与接口契约测试通过。",
                "provider": "github-actions",
                "run_id": "run-1301",
                "task_provider": "jira",
                "task_url": "https://jira.example.com/browse/AG-1301",
            },
        )
        repo_response = client.post(
            "/integrations/repository/revision-signal",
            headers=_headers(CI_TOKEN),
            json={
                "project_id": project["id"],
                "provider": "github",
                "repository_identity": "git@example.com:team/profile-service.git",
                "branch": "main",
                "observed_head_sha": "profile1301",
                "signal_type": "push",
                "work_item_key": "AG-1301",
                "work_item_title": "用户资料脱敏展示",
                "raw_ref": "https://github.example.com/team/profile-service/commit/profile1301",
                "task_provider": "jira",
                "task_url": "https://jira.example.com/browse/AG-1301",
            },
        )

    ci_body = ci_response.json()
    repo_body = repo_response.json()
    assert ci_response.status_code == 201
    assert repo_response.status_code == 201
    assert repo_body["work_item"]["id"] == ci_body["work_item"]["id"]
    assert repo_body["task_link"]["id"] == ci_body["task_link"]["id"]
    assert repo_body["task_link"]["provider"] == "jira"
    assert repo_body["task_link"]["external_url"] == "https://jira.example.com/browse/AG-1301"
