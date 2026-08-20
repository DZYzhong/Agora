import { apiGet } from "../../../../lib/api";
import Link from "next/link";

type SessionEvent = {
  id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};

type TaskSession = {
  id: string;
  project_id: string;
  task_id: string | null;
  work_item: {
    id: string;
    external_key: string | null;
    title: string;
    status: string;
    stage: string;
    source: string;
  } | null;
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
  };
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

type SearchParams = {
  intent?: string;
  status?: string;
  q?: string;
};

function queryString(searchParams: SearchParams): string {
  const params = new URLSearchParams();
  if (searchParams.intent) params.set("intent", searchParams.intent);
  if (searchParams.status) params.set("status", searchParams.status);
  if (searchParams.q) params.set("q", searchParams.q);
  const value = params.toString();
  return value ? `?${value}` : "";
}

export default async function SessionsPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { projectId } = await params;
  const filters = await searchParams;
  let sessions: TaskSession[] = [];
  try {
    sessions = await apiGet<TaskSession[]>(`/projects/${projectId}/sessions${queryString(filters)}`);
  } catch {
    sessions = [];
  }

  return (
    <main className="page">
      <h1>Sessions</h1>
      <p className="muted">Project {projectId}</p>
      <section className="panel form">
        <h2>Filters</h2>
        <form className="filter-form" action={`/projects/${projectId}/sessions`} method="get">
          <label>
            Intent
            <select name="intent" defaultValue={filters.intent ?? ""}>
              <option value="">All intents</option>
              <option value="analysis">analysis</option>
              <option value="implementation">implementation</option>
              <option value="review">review</option>
              <option value="test_generation">test_generation</option>
            </select>
          </label>
          <label>
            Status
            <select name="status" defaultValue={filters.status ?? ""}>
              <option value="">All statuses</option>
              <option value="started">started</option>
              <option value="closed">closed</option>
              <option value="failed">failed</option>
            </select>
          </label>
          <label>
            Search
            <input name="q" defaultValue={filters.q ?? ""} placeholder="context, skill, writeback, event" />
          </label>
          <button type="submit">Apply filters</button>
          <Link className="button-link secondary-link" href={`/projects/${projectId}/sessions`}>Clear</Link>
        </form>
      </section>
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
                <dt>Work item</dt>
                <dd>{session.work_item ? session.work_item.title : session.task_id ?? "Not set"}</dd>
              </div>
              <div>
                <dt>Task key</dt>
                <dd>{session.work_item?.external_key ?? session.task_id ?? "Not set"}</dd>
              </div>
              <div>
                <dt>Started</dt>
                <dd>{new Date(session.created_at).toLocaleString()}</dd>
              </div>
              <div>
                <dt>Closed</dt>
                <dd>{session.closed_at ? new Date(session.closed_at).toLocaleString() : "Open"}</dd>
              </div>
              <div>
                <dt>Context</dt>
                <dd>{session.audit_counts.context_packs}</dd>
              </div>
              <div>
                <dt>Skill runs</dt>
                <dd>{session.audit_counts.skill_runs}</dd>
              </div>
              <div>
                <dt>Writebacks</dt>
                <dd>{session.audit_counts.writebacks}</dd>
              </div>
              <div>
                <dt>Events</dt>
                <dd>{session.audit_counts.events}</dd>
              </div>
            </dl>
            <div className="actions">
              <Link className="button-link" href={`/projects/${projectId}/sessions/${session.id}`}>View audit</Link>
            </div>
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
