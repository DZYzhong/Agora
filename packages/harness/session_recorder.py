class SessionRecorder:
    def __init__(self, core):
        self.core = core

    def start(self, *, org_id: str, project_id: str, agent_type: str, intent: str, task_id: str | None):
        return self.core.create_session(
            org_id=org_id,
            project_id=project_id,
            agent_type=agent_type,
            intent=intent,
            task_id=task_id,
        )

    def record_event(self, *, session_id: str, event_type: str, payload: dict):
        return self.core.record_event(session_id=session_id, event_type=event_type, payload=payload)
