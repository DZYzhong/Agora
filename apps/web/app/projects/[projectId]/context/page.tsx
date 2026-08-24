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

type ContextStream = {
  id: string;
  name: string;
  branch: string;
  head_revision_id: string | null;
  status: string;
  updated_at: string;
};

type ContextProposal = {
  id: string;
  type: string;
  status: string;
  title: string;
  summary: string;
  target_branch: string;
  expected_head_revision_id: string | null;
  accepted_revision_id: string | null;
  updated_at: string;
};

function healthLabel(state: ContextState | null): string {
  if (!state) return "missing";
  return state.provisional ? "provisional" : "accepted";
}

export default async function ContextStatePage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const project = await apiGet<Project>(`/projects/${projectId}`);
  let workItems: WorkItem[] = [];
  let streams: ContextStream[] = [];
  let proposals: ContextProposal[] = [];
  try {
    workItems = await apiGet<WorkItem[]>(`/projects/${projectId}/work-items`);
  } catch {
    workItems = [];
  }
  try {
    [streams, proposals] = await Promise.all([
      apiGet<ContextStream[]>(`/projects/${projectId}/context/streams`),
      apiGet<ContextProposal[]>(`/projects/${projectId}/context/proposals`),
    ]);
  } catch {
    streams = [];
    proposals = [];
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

      <section className="panel">
        <h2>Context streams</h2>
        {streams.length ? (
          <div className="event-list">
            {streams.map((stream) => (
              <article className="event-row" key={stream.id}>
                <div className="session-header">
                  <div>
                    <strong>{stream.name} · {stream.branch}</strong>
                    <p className="asset-uri">{stream.head_revision_id ?? "No accepted head"}</p>
                  </div>
                  <span className="asset-type">{stream.status}</span>
                </div>
                <p className="muted">Updated {new Date(stream.updated_at).toLocaleString()}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">No ContextStream exists yet. An AI tool can submit an initial ContextProposal for review.</p>
        )}
      </section>

      <section className="panel">
        <h2>Context proposals</h2>
        {proposals.length ? (
          <div className="event-list">
            {proposals.map((proposal) => (
              <article className="event-row" key={proposal.id}>
                <div className="session-header">
                  <div>
                    <strong>{proposal.title}</strong>
                    <p className="asset-uri">{proposal.type} · {proposal.target_branch}</p>
                  </div>
                  <span className="asset-type">{proposal.status}</span>
                </div>
                <p>{proposal.summary}</p>
                <dl className="status-metrics">
                  <div>
                    <dt>Expected head</dt>
                    <dd>{proposal.expected_head_revision_id ?? "None"}</dd>
                  </div>
                  <div>
                    <dt>Accepted revision</dt>
                    <dd>{proposal.accepted_revision_id ?? "Not accepted"}</dd>
                  </div>
                  <div>
                    <dt>Updated</dt>
                    <dd>{new Date(proposal.updated_at).toLocaleString()}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">No ContextProposal has been uploaded for review.</p>
        )}
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
