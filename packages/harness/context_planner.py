class ContextPlanner:
    def __init__(self, *, core, context_engine):
        self.core = core
        self.context_engine = context_engine

    def plan(self, *, session_id: str, query: str, token_budget: int = 4000):
        session = self.core.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        context = self.context_engine.plan_context(
            org_id=session.org_id,
            project_id=session.project_id,
            intent=session.intent,
            query=query,
            token_budget=token_budget,
        )
        if hasattr(self.core, "create_context_pack"):
            self.core.create_context_pack(
                id=context.id,
                org_id=context.org_id,
                project_id=context.project_id,
                level=context.level,
                summary=context.summary,
                key_facts=context.key_facts,
                source_refs=context.source_refs,
            )
        if hasattr(self.core, "record_event"):
            self.core.record_event(
                session_id=session_id,
                event_type="context_planned",
                payload={
                    "context_pack_id": context.id,
                    "level": context.level,
                    "source_count": len(context.source_refs),
                },
            )
        return context
