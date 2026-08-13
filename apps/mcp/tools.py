class AgoraMcpTools:
    def __init__(self, *, harness):
        self.harness = harness

    def agora_start_work(self, *, user_message: str, repo_remote: str | None = None, agent_type: str) -> dict:
        result = self.harness.start_work(user_message=user_message, repo_remote=repo_remote, agent_type=agent_type)
        return _object_to_dict(result)

    def agora_plan_context(self, *, session_id: str, query: str | None = None, token_budget: int = 4000) -> dict:
        result = self.harness.plan_context(session_id=session_id, query=query, token_budget=token_budget)
        return _object_to_dict(result)

    def agora_fetch_context_ref(self, *, session_id: str, asset_id: str, max_tokens: int = 2000) -> dict:
        if not hasattr(self.harness, "fetch_context_ref"):
            return {"session_id": session_id, "asset_id": asset_id, "max_tokens": max_tokens, "status": "not_implemented"}
        return _object_to_dict(self.harness.fetch_context_ref(session_id=session_id, asset_id=asset_id, max_tokens=max_tokens))

    def agora_run_skill(self, *, session_id: str, skill_slug: str, input: dict) -> dict:
        if not hasattr(self.harness, "run_skill"):
            return {"session_id": session_id, "skill_slug": skill_slug, "input": input, "status": "not_implemented"}
        return _object_to_dict(self.harness.run_skill(session_id=session_id, skill_slug=skill_slug, input=input))

    def agora_record_event(self, *, session_id: str, event_type: str, payload: dict) -> dict:
        self.harness.record_event(session_id=session_id, event_type=event_type, payload=payload)
        return {"ok": True}

    def agora_prepare_writeback(self, *, session_id: str, agent_summary: str, diff_summary: str | None = None, test_result: str | None = None) -> dict:
        if not hasattr(self.harness, "prepare_writeback"):
            return {
                "session_id": session_id,
                "agent_summary": agent_summary,
                "diff_summary": diff_summary,
                "test_result": test_result,
                "status": "not_implemented",
            }
        return _object_to_dict(
            self.harness.prepare_writeback(
                session_id=session_id,
                agent_summary=agent_summary,
                diff_summary=diff_summary,
                test_result=test_result,
            )
        )

    def agora_close_work(
        self,
        *,
        session_id: str,
        status: str = "closed",
        repo_path: str | None = None,
        base_ref: str = "HEAD",
        head_ref: str | None = None,
        agent_summary: str | None = None,
        test_result: str | None = None,
    ) -> dict:
        return _object_to_dict(
            self.harness.close_work(
                session_id=session_id,
                status=status,
                repo_path=repo_path,
                base_ref=base_ref,
                head_ref=head_ref,
                agent_summary=agent_summary,
                test_result=test_result,
            )
        )

    def agora_search_knowledge(self, *, session_id: str, query: str, max_results: int = 10) -> dict:
        return {"session_id": session_id, "query": query, "max_results": max_results, "results": []}


def _object_to_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "__dict__"):
        data = value.__dict__
        if data:
            return data
    public_attrs = {
        key: getattr(value, key)
        for key in dir(value)
        if not key.startswith("_") and not callable(getattr(value, key))
    }
    if public_attrs:
        return public_attrs
    raise TypeError(f"Cannot convert {type(value)!r} to dict")
