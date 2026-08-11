BUILT_IN_SKILLS = {
    "task-context-summary": {"name": "Task Context Summary"},
    "impact-analysis": {"name": "Impact Analysis"},
    "test-case-generation": {"name": "Test Case Generation"},
    "risk-check": {"name": "Risk Check"},
    "knowledge-writeback": {"name": "Knowledge Writeback"},
}


def get_builtin_skill(slug: str) -> dict | None:
    return BUILT_IN_SKILLS.get(slug)
