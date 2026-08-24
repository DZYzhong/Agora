from packages.harness.context_bundle import build_context_bundle


class ContextPlanner:
    def __init__(self, *, core, context_engine):
        self.core = core
        self.context_engine = context_engine

    def plan(self, *, session_id: str, query: str, token_budget: int = 4000):
        return self._plan_context_pack(session_id=session_id, query=query, token_budget=token_budget)

    def prepare(self, *, session_id: str, query: str, token_budget: int = 4000, event_type: str = "context_prepared"):
        context = self._plan_context_pack(session_id=session_id, query=query, token_budget=token_budget, record_event=False)
        bundle = build_context_bundle(
            session_id=session_id,
            query=query,
            token_budget=token_budget,
            context_pack=context,
        )
        if hasattr(self.core, "record_event"):
            self.core.record_event(
                session_id=session_id,
                event_type=event_type,
                payload={
                    "context_pack_id": context.id,
                    "level": context.level,
                    "source_count": len(context.source_refs),
                    "budget": bundle["budget"],
                    "freshness": bundle["freshness"],
                },
            )
        return bundle

    def _plan_context_pack(self, *, session_id: str, query: str, token_budget: int = 4000, record_event: bool = True):
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
        if record_event and hasattr(self.core, "record_event"):
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
