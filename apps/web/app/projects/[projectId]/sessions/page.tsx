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
  context_packs: Array<{
    id: string;
    level: string;
    summary: string;
    key_facts: Array<{
      fact: string;
      source_refs: string[];
    }>;
    source_refs: Array<{
      asset_id: string;
      title: string;
      chunk_id: string;
    }>;
    created_at: string;
  }>;
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
            {session.context_packs.length ? (
              <div className="context-pack-list">
                {session.context_packs.map((contextPack) => (
                  <section className="context-pack-row" key={contextPack.id}>
                    <div className="session-header">
                      <div>
                        <p className="eyebrow">ContextPack</p>
                        <h3>{contextPack.level}</h3>
                        <p className="asset-uri">{contextPack.id}</p>
                      </div>
                      <span className="asset-type">{contextPack.source_refs.length} sources</span>
                    </div>
                    <pre className="context-summary">{contextPack.summary}</pre>
                    {contextPack.key_facts.length ? (
                      <ul className="fact-list">
                        {contextPack.key_facts.map((fact) => (
                          <li key={`${contextPack.id}-${fact.source_refs.join("-")}`}>
                            <span>{fact.fact}</span>
                            <code>{fact.source_refs.join(", ")}</code>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </section>
                ))}
              </div>
            ) : null}
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
