class SessionRecorder:
    def __init__(self, core):
        self.core = core

    def start(
        self,
        *,
        work_item_id: str,
        user_id: str,
        credential_id: str,
        agent_type: str,
        intent: str,
        initial_request_id: str | None = None,
    ):
        return self.core.create_work_session(
            work_item_id=work_item_id,
            user_id=user_id,
            credential_id=credential_id,
            agent_type=agent_type,
            intent=intent,
            initial_request_id=initial_request_id,
        )

    def record_event(self, *, session_id: str, event_type: str, payload: dict):
        return self.core.record_event(session_id=session_id, event_type=event_type, payload=payload)
