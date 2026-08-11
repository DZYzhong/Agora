class ContextPlanner:
    def __init__(self, *, core, context_engine):
        self.core = core
        self.context_engine = context_engine

    def plan(self, *, session_id: str, query: str, token_budget: int = 4000):
        session = self.core.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        return self.context_engine.plan_context(
            org_id=session.org_id,
            project_id=session.project_id,
            intent=session.intent,
            query=query,
            token_budget=token_budget,
        )
