import Link from "next/link";
import { apiGet } from "../../../../lib/api";

type ContextState = {
  session_id: string;
  event_type: string;
  context_pack_id: string | null;
  provisional: boolean;
  freshness: {
    context_coverage?: string;
    recommended_action?: string;
    observed_commit_sha?: string | null;
  };
  budget: {
    estimated_tokens?: number;
    token_budget?: number;
  } | null;
  created_at: string;
};

type WorkItem = {
  id: string;
  external_key: string | null;
  title: string;
  description: string | null;
  status: string;
  stage: string;
  source: string;
  session_count: number;
  participants: string[];
  latest_context_state: ContextState | null;
  capability_pins: {
    context_revision_id: string | null;
    workflow_version_id: string | null;
    skill_version_id: string | null;
  };
};

function contextLabel(state: ContextState | null): string {
  if (!state) return "No context";
  const coverage = state.freshness.context_coverage ?? "unknown";
  return state.provisional ? `Provisional · ${coverage}` : coverage;
}

function participantLabel(participants: string[]): string {
  if (participants.length === 0) return "None";
  if (participants.length === 1) return "1 participant";
  return `${participants.length} participants`;
}

export default async function WorkItemsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  let workItems: WorkItem[] = [];
  try {
    workItems = await apiGet<WorkItem[]>(`/projects/${projectId}/work-items`);
  } catch {
    workItems = [];
  }

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <h1>Work items</h1>
          <p className="muted">Team tasks detected from AI tool sessions and project workflow activity.</p>
        </div>
        <Link className="button-link secondary-link" href={`/projects/${projectId}`}>
          Back to project
        </Link>
      </div>

      <section className="work-table" aria-label="Work item state">
        <div className="work-row work-header">
          <span>Task</span>
          <span>Status</span>
          <span>Sessions</span>
          <span>Context</span>
          <span>Participants</span>
        </div>
        {workItems.map((item) => (
          <Link className="work-row" href={`/projects/${projectId}/work-items/${item.id}`} key={item.id}>
            <span>
              <strong>{item.external_key ? `${item.external_key} · ${item.title}` : item.title}</strong>
              <small>{item.description ?? item.source}</small>
            </span>
            <span>
              <span className="asset-type">{item.status}</span>
              <small>{item.stage}</small>
            </span>
            <span>{item.session_count}</span>
            <span>
              <strong>{contextLabel(item.latest_context_state)}</strong>
              <small>{item.latest_context_state ? new Date(item.latest_context_state.created_at).toLocaleString() : "AI tool has not uploaded context yet"}</small>
            </span>
            <span>{participantLabel(item.participants)}</span>
          </Link>
        ))}
      </section>

      {workItems.length === 0 ? (
        <section className="panel">
          <h2>No work items</h2>
          <p className="muted">When an AI tool starts work for this project, Agora will identify the task and show it here.</p>
        </section>
      ) : null}
    </main>
  );
}
