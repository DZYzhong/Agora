import Link from "next/link";
import { apiGet } from "../../../../lib/api";

type Project = {
  id: string;
  name: string;
  slug: string;
};

type ContextState = {
  session_id: string;
  event_type: string;
  context_pack_id: string | null;
  provisional: boolean;
  freshness: {
    repository_relation?: string;
    workspace_state?: string;
    context_coverage?: string;
    proposal_state?: string;
    accepted_revision_id?: string | null;
    observed_commit_sha?: string | null;
    recommended_action?: string;
  };
  budget: {
    estimated_tokens?: number;
    token_budget?: number;
    included_assets?: number;
  } | null;
  created_at: string;
};

type WorkItem = {
  id: string;
  external_key: string | null;
  title: string;
  status: string;
  stage: string;
  session_count: number;
  participants: string[];
  latest_context_state: ContextState | null;
};

function healthLabel(state: ContextState | null): string {
  if (!state) return "missing";
  return state.provisional ? "provisional" : "accepted";
}

export default async function ContextStatePage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const project = await apiGet<Project>(`/projects/${projectId}`);
  let workItems: WorkItem[] = [];
  try {
    workItems = await apiGet<WorkItem[]>(`/projects/${projectId}/work-items`);
  } catch {
    workItems = [];
  }
  const withContext = workItems.filter((item) => item.latest_context_state);
  const latest = withContext
    .map((item) => item.latest_context_state)
    .filter((state): state is ContextState => state !== null)
    .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())[0];

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <h1>Context state</h1>
          <p className="muted">{project.name} / {project.slug}</p>
        </div>
        <Link className="button-link secondary-link" href={`/projects/${project.id}`}>
          Back to project
        </Link>
      </div>

      <section className="panel status-panel">
        <div className="session-header">
          <div>
            <p className="eyebrow">Project context</p>
            <h2>{latest ? healthLabel(latest) : "No uploaded context"}</h2>
            <p className="muted">P1 indexed material is treated as provisional until a reviewed context revision is accepted.</p>
          </div>
          <span className="asset-type">{withContext.length}/{workItems.length} tasks</span>
        </div>
        <dl className="status-metrics">
          <div>
            <dt>Latest update</dt>
            <dd>{latest ? new Date(latest.created_at).toLocaleString() : "None"}</dd>
          </div>
          <div>
            <dt>Coverage</dt>
            <dd>{latest?.freshness.context_coverage ?? "unknown"}</dd>
          </div>
          <div>
            <dt>Recommended action</dt>
            <dd>{latest?.freshness.recommended_action ?? "ai_tool_upload_context"}</dd>
          </div>
          <div>
            <dt>Estimated tokens</dt>
            <dd>{latest?.budget?.estimated_tokens ?? "Unknown"}</dd>
          </div>
        </dl>
      </section>

      <section className="work-table" aria-label="Context state by work item">
        <div className="work-row work-header">
          <span>Task</span>
          <span>State</span>
          <span>Coverage</span>
          <span>Updated</span>
          <span>Action</span>
        </div>
        {workItems.map((item) => {
          const state = item.latest_context_state;
          return (
            <Link className="work-row" href={`/projects/${project.id}/work-items/${item.id}`} key={item.id}>
              <span>
                <strong>{item.external_key ? `${item.external_key} · ${item.title}` : item.title}</strong>
                <small>{item.session_count} sessions · {item.participants.length || "no"} participants</small>
              </span>
              <span>
                <span className="asset-type">{healthLabel(state)}</span>
              </span>
              <span>{state?.freshness.context_coverage ?? "unknown"}</span>
              <span>{state ? new Date(state.created_at).toLocaleString() : "Not uploaded"}</span>
              <span>{state?.freshness.recommended_action ?? "ai_tool_upload_context"}</span>
            </Link>
          );
        })}
      </section>

      {workItems.length === 0 ? (
        <section className="panel">
          <h2>No task context yet</h2>
          <p className="muted">When an AI tool starts work and uploads a context bundle, Agora will show the task-level state here.</p>
        </section>
      ) : null}
    </main>
  );
}
