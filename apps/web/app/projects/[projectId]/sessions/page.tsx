import { apiGet } from "../../../../lib/api";

type SessionEvent = {
  id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};

type TaskSession = {
  id: string;
  task_id: string | null;
  agent_type: string;
  intent: string;
  status: string;
  created_at: string;
  closed_at: string | null;
  events: SessionEvent[];
};

export default async function SessionsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  let sessions: TaskSession[] = [];
  try {
    sessions = await apiGet<TaskSession[]>(`/projects/${projectId}/sessions`);
  } catch {
    sessions = [];
  }

  return (
    <main className="page">
      <h1>Sessions</h1>
      <p className="muted">Project {projectId}</p>
      <section className="session-list">
        {sessions.map((session) => (
          <article className="panel" key={session.id}>
            <div className="session-header">
              <div>
                <p className="eyebrow">{session.agent_type}</p>
                <h2>{session.intent}</h2>
                <p className="asset-uri">{session.id}</p>
              </div>
              <span className="asset-type">{session.status}</span>
            </div>
            <dl className="status-metrics">
              <div>
                <dt>Task</dt>
                <dd>{session.task_id ?? "Not set"}</dd>
              </div>
              <div>
                <dt>Started</dt>
                <dd>{new Date(session.created_at).toLocaleString()}</dd>
              </div>
              <div>
                <dt>Closed</dt>
                <dd>{session.closed_at ? new Date(session.closed_at).toLocaleString() : "Open"}</dd>
              </div>
            </dl>
            {session.events.length ? (
              <div className="event-list">
                {session.events.map((event) => (
                  <div className="event-row" key={event.id}>
                    <strong>{event.event_type}</strong>
                    <pre>{JSON.stringify(event.payload, null, 2)}</pre>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted">No events recorded.</p>
            )}
          </article>
        ))}
        {sessions.length === 0 ? (
          <div className="panel">
            <h2>Agent work sessions</h2>
            <p className="muted">Harness sessions created by MCP/API calls will be listed here.</p>
          </div>
        ) : null}
      </section>
    </main>
  );
}
