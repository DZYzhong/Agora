import Link from "next/link";
import { apiGet } from "../../../../../lib/api";

type SessionAudit = {
  id: string;
  project_id: string;
  task_id: string | null;
  agent_type: string;
  intent: string;
  status: string;
  created_at: string;
  closed_at: string | null;
  audit_counts: {
    events: number;
    context_packs: number;
    skill_runs: number;
    writebacks: number;
    development_updates: number;
  };
  development_updates: Array<{
    writeback_id: string;
    writeback_type: string | null;
    writeback_status: string | null;
    accepted_asset_id: string | null;
    summary: string;
    changed_files: Array<{
      path: string;
      status: string;
      category: string;
    }>;
    tests: Array<{
      command: string;
      status: string;
      raw: string;
    }>;
    risks: string[];
    follow_ups: string[];
    created_at: string;
  }>;
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
      asset_type?: string;
      title: string;
      source_uri?: string;
      chunk_id: string;
      preview?: string;
    }>;
    created_at: string;
  }>;
  skill_runs: Array<{
    id: string;
    skill_id: string;
    skill_name: string;
    input: Record<string, unknown>;
    output: Record<string, unknown>;
    warnings: string[];
    status: string;
    created_at: string;
  }>;
  writebacks: Array<{
    id: string;
    type: string;
    title: string;
    content: string;
    asset_refs: string[];
    status: string;
    accepted_asset_id: string | null;
    created_at: string;
  }>;
  events: Array<{
    id: string;
    event_type: string;
    payload: Record<string, unknown>;
    created_at: string;
  }>;
};

export default async function SessionAuditPage({
  params,
}: {
  params: Promise<{ projectId: string; sessionId: string }>;
}) {
  const { projectId, sessionId } = await params;
  let audit: SessionAudit | null = null;
  try {
    audit = await apiGet<SessionAudit>(`/projects/${projectId}/sessions/${sessionId}`);
  } catch {
    audit = null;
  }

  if (!audit) {
    return (
      <main className="page">
        <h1>Session audit</h1>
        <p className="muted">Session not found.</p>
        <Link className="button-link secondary-link" href={`/projects/${projectId}/sessions`}>Back to sessions</Link>
      </main>
    );
  }

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <h1>Session audit</h1>
          <p className="muted">Project {projectId}</p>
        </div>
        <Link className="button-link secondary-link" href={`/projects/${projectId}/sessions`}>Back to sessions</Link>
      </div>
      <section className="panel">
        <div className="session-header">
          <div>
            <p className="eyebrow">{audit.agent_type}</p>
            <h2>{audit.intent}</h2>
            <p className="asset-uri">{audit.id}</p>
          </div>
          <span className="asset-type">{audit.status}</span>
        </div>
        <dl className="status-metrics">
          <div>
            <dt>Task</dt>
            <dd>{audit.task_id ?? "Not set"}</dd>
          </div>
          <div>
            <dt>Started</dt>
            <dd>{new Date(audit.created_at).toLocaleString()}</dd>
          </div>
          <div>
            <dt>Closed</dt>
            <dd>{audit.closed_at ? new Date(audit.closed_at).toLocaleString() : "Open"}</dd>
          </div>
          <div>
            <dt>Context</dt>
            <dd>{audit.audit_counts.context_packs}</dd>
          </div>
          <div>
            <dt>Skill runs</dt>
            <dd>{audit.audit_counts.skill_runs}</dd>
          </div>
          <div>
            <dt>Writebacks</dt>
            <dd>{audit.audit_counts.writebacks}</dd>
          </div>
          <div>
            <dt>Events</dt>
            <dd>{audit.audit_counts.events}</dd>
          </div>
          <div>
            <dt>Dev updates</dt>
            <dd>{audit.audit_counts.development_updates}</dd>
          </div>
        </dl>
      </section>

      <section className="panel">
        <h2>Development updates</h2>
        {audit.development_updates.length ? (
          <div className="event-list">
            {audit.development_updates.map((update) => (
              <article className="event-row" key={`${update.writeback_id}-${update.created_at}`}>
                <div className="session-header">
                  <div>
                    <strong>{update.summary}</strong>
                    <p className="asset-uri">
                      {update.writeback_type ?? "development_update"} · {update.writeback_status ?? "unknown"}
                    </p>
                  </div>
                  {update.accepted_asset_id ? <span className="asset-type">accepted</span> : <span className="asset-type">draft</span>}
                </div>
                {update.changed_files.length ? (
                  <div className="audit-grid">
                    <section>
                      <p className="eyebrow">Changed files</p>
                      <ul className="compact-list">
                        {update.changed_files.map((file) => (
                          <li key={`${update.writeback_id}-${file.path}`}>
                            <code>{file.path}</code>
                            <span>{file.category} · {file.status}</span>
                          </li>
                        ))}
                      </ul>
                    </section>
                    <section>
                      <p className="eyebrow">Tests</p>
                      {update.tests.length ? (
                        <ul className="compact-list">
                          {update.tests.map((test) => (
                            <li key={`${update.writeback_id}-${test.raw}`}>
                              <code>{test.command}</code>
                              <span>{test.status}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="muted">No tests recorded.</p>
                      )}
                    </section>
                  </div>
                ) : null}
                <div className="audit-grid">
                  <section>
                    <p className="eyebrow">Risks</p>
                    <ul className="compact-list">
                      {update.risks.map((risk) => (
                        <li key={`${update.writeback_id}-${risk}`}>{risk}</li>
                      ))}
                    </ul>
                  </section>
                  <section>
                    <p className="eyebrow">Follow-ups</p>
                    <ul className="compact-list">
                      {update.follow_ups.map((followUp) => (
                        <li key={`${update.writeback_id}-${followUp}`}>{followUp}</li>
                      ))}
                    </ul>
                  </section>
                </div>
                {update.writeback_id ? <p className="asset-uri">Writeback: {update.writeback_id}</p> : null}
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">No structured development updates recorded.</p>
        )}
      </section>

      <section className="panel">
        <h2>Context packs</h2>
        {audit.context_packs.length ? (
          <div className="context-pack-list">
            {audit.context_packs.map((contextPack) => (
              <article className="context-pack-row" key={contextPack.id}>
                <div className="session-header">
                  <div>
                    <p className="eyebrow">ContextPack</p>
                    <h3>{contextPack.level}</h3>
                    <p className="asset-uri">{contextPack.id}</p>
                  </div>
                  <span className="asset-type">{contextPack.source_refs.length} sources</span>
                </div>
                <pre className="context-summary">{contextPack.summary}</pre>
                {contextPack.source_refs.length ? (
                  <div className="event-list">
                    {contextPack.source_refs.map((source) => (
                      <div className="event-row" key={source.chunk_id}>
                        <strong>{source.title}</strong>
                        <p className="asset-uri">{source.asset_type ?? "source"} · {source.source_uri ?? source.asset_id}</p>
                        {source.preview ? <p>{source.preview}</p> : null}
                      </div>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">No context packs recorded.</p>
        )}
      </section>

      <section className="panel">
        <h2>Skill runs</h2>
        {audit.skill_runs.length ? (
          <div className="event-list">
            {audit.skill_runs.map((run) => (
              <div className="event-row" key={run.id}>
                <strong>{run.skill_name}</strong>
                <p className="asset-uri">{run.status} · {new Date(run.created_at).toLocaleString()}</p>
                <pre>{JSON.stringify({ input: run.input, output: run.output, warnings: run.warnings }, null, 2)}</pre>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No skill runs recorded.</p>
        )}
      </section>

      <section className="panel">
        <h2>Writebacks</h2>
        {audit.writebacks.length ? (
          <div className="event-list">
            {audit.writebacks.map((writeback) => (
              <div className="event-row" key={writeback.id}>
                <strong>{writeback.title}</strong>
                <p className="asset-uri">{writeback.type} · {writeback.status}</p>
                <pre>{writeback.content}</pre>
                {writeback.accepted_asset_id ? <p className="asset-uri">Accepted asset: {writeback.accepted_asset_id}</p> : null}
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No writebacks recorded.</p>
        )}
      </section>

      <section className="panel">
        <h2>Timeline</h2>
        {audit.events.length ? (
          <div className="event-list">
            {audit.events.map((event) => (
              <div className="event-row" key={event.id}>
                <strong>{event.event_type}</strong>
                <p className="asset-uri">{new Date(event.created_at).toLocaleString()}</p>
                <pre>{JSON.stringify(event.payload, null, 2)}</pre>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No events recorded.</p>
        )}
      </section>
    </main>
  );
}
