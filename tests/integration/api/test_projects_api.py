from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from apps.api import dependencies
from apps.api.main import app
from packages.core.models import AssetModel, ContextStreamModel, QualityEvidenceModel, SkillModel, WorkItemModel
from packages.core.uow import SqlAlchemyUnitOfWork


def test_create_project_api():
    client = TestClient(app)

    response = client.post(
        "/projects",
        json={
            "org_id": "org_1",
            "name": "Payment",
            "slug": "payment",
            "git_remotes": ["git@example.com:payment.git"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["name"] == "Payment"


def test_archive_project_hides_it_from_default_project_list():
    client = TestClient(app)
    keep = client.post(
        "/projects",
        json={
            "org_id": "org_1",
            "name": "Keep",
            "slug": "keep",
            "git_remotes": ["git@example.com:keep.git"],
        },
    ).json()
    archived = client.post(
        "/projects",
        json={
            "org_id": "org_1",
            "name": "Archive",
            "slug": "archive",
            "git_remotes": ["git@example.com:archive.git"],
        },
    ).json()

    archive_response = client.post(f"/projects/{archived['id']}/archive")

    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"
    active_projects = client.get("/projects").json()
    assert [project["id"] for project in active_projects] == [keep["id"]]
    all_projects = client.get("/projects?include_archived=true").json()
    assert {project["id"] for project in all_projects} == {keep["id"], archived["id"]}


def test_project_operations_summary_api_reports_project_governance_state():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_1",
            "name": "研发协作中台",
            "slug": "rd-collaboration-platform",
            "git_remotes": ["git@example.com:rd-collaboration-platform.git"],
        },
    ).json()
    session = sessionmaker(bind=dependencies.get_engine())()
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            work_item = WorkItemModel(
                id="work-item-operations-summary",
                org_id="org_1",
                project_id=project["id"],
                external_key="AG-9301",
                title="补齐项目治理摘要",
                source="jira",
            )
            session.add(work_item)
            session.add(
                AssetModel(
                    org_id="org_1",
                    project_id=project["id"],
                    type="code_file",
                    source="local_scan",
                    source_uri="src/summary.py",
                    title="summary.py",
                    content="summary",
                )
            )
            session.add(
                ContextStreamModel(
                    org_id="org_1",
                    project_id=project["id"],
                    name="main",
                    branch="main",
                    repository_identity={"remote": "git@example.com:rd-collaboration-platform.git"},
                )
            )
            session.add(
                QualityEvidenceModel(
                    org_id="org_1",
                    project_id=project["id"],
                    work_item_id=work_item.id,
                    session_id=None,
                    evidence_type="test",
                    source="pytest",
                    status="passed",
                    conclusion="项目治理摘要 API 回归通过。",
                )
            )
            session.add(
                SkillModel(
                    org_id="org_1",
                    project_id=project["id"],
                    slug="risk-review",
                    name="风险评审",
                    status="candidate",
                    definition={"summary": "检查变更风险。"},
                )
            )
            uow.commit()
    finally:
        session.close()

    response = client.get(f"/projects/{project['id']}/operations-summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["format"] == "agora-project-summary/v1"
    assert summary["project"]["id"] == project["id"]
    assert summary["assets"]["by_type"] == {"code_file": 1}
    assert summary["work_items"]["by_stage"] == {"backlog": 1}
    assert summary["context"]["streams"] == 1
    assert summary["quality"]["evidence_by_status"] == {"passed": 1}
    assert summary["skills"]["skills_by_status"] == {"candidate": 1}
