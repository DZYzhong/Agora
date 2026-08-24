from pathlib import Path


def test_next_dev_and_build_use_separate_dist_dirs():
    config_path = Path("apps/web/next.config.mjs")
    config = config_path.read_text()

    assert "process.env.NODE_ENV === \"development\"" in config
    assert "\".next-dev\"" in config
    assert "\".next\"" in config


def test_server_fetches_attach_configured_human_token():
    api_path = Path("apps/web/lib/api.ts")
    api = api_path.read_text()

    assert "AGORA_WEB_HUMAN_TOKEN" in api
    assert "Authorization" in api
    assert "Bearer" in api


def test_session_pages_render_work_item_details():
    list_page = Path("apps/web/app/projects/[projectId]/sessions/page.tsx").read_text()
    detail_page = Path("apps/web/app/projects/[projectId]/sessions/[sessionId]/page.tsx").read_text()

    assert "work_item" in list_page
    assert "Work item" in list_page
    assert "work_item" in detail_page
    assert "Work item" in detail_page


def test_product_context_page_is_read_only_audit_view():
    context_page = Path("apps/web/app/projects/[projectId]/context/page.tsx").read_text()

    assert "Context state" in context_page
    assert "Context streams" in context_page
    assert "Context proposals" in context_page
    assert "/context/proposals/" in context_page
    assert "Context Tester" not in context_page
    assert "Run context query" not in context_page
    assert "/harness/plan-context" not in context_page
    assert "/harness/start-work" not in context_page


def test_context_proposal_review_pages_are_available():
    detail_page = Path("apps/web/app/projects/[projectId]/context/proposals/[proposalId]/page.tsx")
    approve_route = Path("apps/web/app/projects/[projectId]/context/proposals/[proposalId]/approve/route.ts")

    assert detail_page.exists()
    assert approve_route.exists()

    detail = detail_page.read_text()
    route = approve_route.read_text()
    assert "Revision signal" in detail
    assert "observed_head_sha" in detail
    assert "contains_to_commit" in detail
    assert "source_anchors" in detail
    assert "/approve" in detail
    assert "/context/proposals" in route
    assert "/approve" in route


def test_web_does_not_ship_agent_simulation_routes():
    assert not Path("apps/web/app/projects/[projectId]/context/submit/route.ts").exists()
    assert not Path("apps/web/app/projects/[projectId]/development-capture/route.ts").exists()


def test_work_item_pages_are_available_and_linked_from_project_home():
    list_page = Path("apps/web/app/projects/[projectId]/work-items/page.tsx")
    detail_page = Path("apps/web/app/projects/[projectId]/work-items/[workItemId]/page.tsx")
    project_page = Path("apps/web/app/projects/[projectId]/page.tsx").read_text()

    assert list_page.exists()
    assert detail_page.exists()
    assert "/work-items" in project_page
