import Link from "next/link";
import { apiGet } from "../../../../../lib/api";

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

type WorkSession = {
  id: string;
  task_id: string | null;
  agent_type: string;
  intent: string;
  status: string;
  created_at: string;
  closed_at: string | null;
  audit_counts: {
    events: number;
    context_states: number;
    development_updates: number;
  };
};

type WorkArtifact = {
  id: string;
  session_id: string;
  step_key: string;
  type: string;
  title: string;
  content: string;
  metadata: Record<string, unknown>;
  created_by_user_id: string;
  created_at: string;
};

type HumanConfirmation = {
  id: string;
  session_id: string;
  step_key: string;
  confirmation_type: string;
  decision: string;
  comment: string | null;
  confirmed_by_user_id: string;
  created_at: string;
};

type WorkflowStep = {
  id: string;
  step_key: string;
  title: string;
  order_index: number;
  status: string;
  required_artifacts: Array<{ type?: string }>;
  artifacts: WorkArtifact[];
  human_confirmations: HumanConfirmation[];
};

type WorkflowExecution = {
  id: string;
  workflow_version_id: string;
  status: string;
  current_step_key: string | null;
  steps: WorkflowStep[];
};

type WorkItemDetail = {
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
  workflow_execution: WorkflowExecution | null;
  sessions: WorkSession[];
};

function formatPin(value: string | null): string {
  return value ?? "Not pinned";
}

function metadataLabel(metadata: Record<string, unknown>): string {
  const path = metadata.path;
  if (typeof path === "string" && path.length > 0) return path;
  const keys = Object.keys(metadata);
  return keys.length ? keys.join(", ") : "No metadata";
}

export default async function WorkItemDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; workItemId: string }>;
}) {
  const { projectId, workItemId } = await params;
  let item: WorkItemDetail | null = null;
  try {
    item = await apiGet<WorkItemDetail>(`/projects/${projectId}/work-items/${workItemId}`);
  } catch {
    item = null;
  }

  if (!item) {
    return (
      <main className="page">
        <h1>Work item</h1>
        <p className="muted">Work item not found.</p>
        <Link className="button-link secondary-link" href={`/projects/${projectId}/work-items`}>
          Back to work items
        </Link>
      </main>
    );
  }

  const context = item.latest_context_state;

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Work item</p>
          <h1>{item.external_key ? `${item.external_key} · ${item.title}` : item.title}</h1>
          <p className="muted">{item.description ?? "Tracked from AI tool work sessions."}</p>
        </div>
        <Link className="button-link secondary-link" href={`/projects/${projectId}/work-items`}>
          Back to work items
        </Link>
      </div>

      <section className="panel status-panel">
        <div className="session-header">
          <div>
            <h2>Task state</h2>
            <p className="muted">{item.source}</p>
          </div>
          <span className="asset-type">{item.status}</span>
        </div>
        <dl className="status-metrics">
          <div>
            <dt>Stage</dt>
            <dd>{item.stage}</dd>
          </div>
          <div>
            <dt>Sessions</dt>
            <dd>{item.session_count}</dd>
          </div>
          <div>
            <dt>Participants</dt>
            <dd>{item.participants.length ? item.participants.join(", ") : "None"}</dd>
          </div>
        </dl>
      </section>

      <section className="panel">
        <h2>Latest context state</h2>
        {context ? (
          <>
            <div className="session-header">
              <div>
                <p className="eyebrow">{context.event_type}</p>
                <p className="asset-uri">{context.context_pack_id ?? "No context pack id"}</p>
              </div>
              <span className="asset-type">{context.provisional ? "provisional" : "accepted"}</span>
            </div>
            <dl className="status-metrics">
              <div>
                <dt>Coverage</dt>
                <dd>{context.freshness.context_coverage ?? "unknown"}</dd>
              </div>
              <div>
                <dt>Recommended action</dt>
                <dd>{context.freshness.recommended_action ?? "review_context"}</dd>
              </div>
              <div>
                <dt>Observed commit</dt>
                <dd>{context.freshness.observed_commit_sha ?? "Not recorded"}</dd>
              </div>
              <div>
                <dt>Estimated tokens</dt>
                <dd>{context.budget?.estimated_tokens ?? "Unknown"}</dd>
              </div>
              <div>
                <dt>Budget</dt>
                <dd>{context.budget?.token_budget ?? "Unknown"}</dd>
              </div>
              <div>
                <dt>Updated</dt>
                <dd>{new Date(context.created_at).toLocaleString()}</dd>
              </div>
            </dl>
          </>
        ) : (
          <p className="muted">No AI tool has uploaded context for this work item yet.</p>
        )}
      </section>

      <section className="panel">
        <h2>Capability pins</h2>
        <dl className="status-metrics">
          <div>
            <dt>Context revision</dt>
            <dd>{formatPin(item.capability_pins.context_revision_id)}</dd>
          </div>
          <div>
            <dt>Workflow version</dt>
            <dd>{formatPin(item.capability_pins.workflow_version_id)}</dd>
          </div>
          <div>
            <dt>Skill version</dt>
            <dd>{formatPin(item.capability_pins.skill_version_id)}</dd>
          </div>
        </dl>
      </section>

      <section className="panel">
        <div className="session-header">
          <div>
            <h2>Workflow audit</h2>
            <p className="muted">Step state, required outputs, AI-submitted evidence and human confirmations.</p>
          </div>
          {item.workflow_execution ? <span className="asset-type">{item.workflow_execution.status}</span> : null}
        </div>
        {item.workflow_execution ? (
          <div className="event-list">
            {item.workflow_execution.steps.map((step) => (
              <article className="event-row" key={step.id}>
                <div className="session-header">
                  <div>
                    <strong>{step.title}</strong>
                    <p className="asset-uri">{step.step_key}</p>
                  </div>
                  <span className="asset-type">{step.status}</span>
                </div>
                <dl className="status-metrics">
                  <div>
                    <dt>Required outputs</dt>
                    <dd>{step.required_artifacts.map((artifact) => artifact.type ?? "artifact").join(", ") || "None"}</dd>
                  </div>
                  <div>
                    <dt>Step outputs</dt>
                    <dd>{step.artifacts.length}</dd>
                  </div>
                  <div>
                    <dt>Human confirmations</dt>
                    <dd>{step.human_confirmations.length}</dd>
                  </div>
                </dl>

                {step.artifacts.length ? (
                  <div className="evidence-list" aria-label={`${step.title} Step outputs`}>
                    <p className="eyebrow">Step outputs</p>
                    {step.artifacts.map((artifact) => (
                      <div className="evidence-row" key={artifact.id}>
                        <div className="session-header">
                          <div>
                            <strong>{artifact.title}</strong>
                            <p className="asset-uri">{artifact.type} · {metadataLabel(artifact.metadata)}</p>
                          </div>
                          <span className="asset-type">{new Date(artifact.created_at).toLocaleString()}</span>
                        </div>
                        <p>{artifact.content}</p>
                      </div>
                    ))}
                  </div>
                ) : null}

                {step.human_confirmations.length ? (
                  <div className="evidence-list" aria-label={`${step.title} Human confirmations`}>
                    <p className="eyebrow">Human confirmations</p>
                    {step.human_confirmations.map((confirmation) => (
                      <div className="evidence-row" key={confirmation.id}>
                        <div className="session-header">
                          <div>
                            <strong>{confirmation.decision}</strong>
                            <p className="asset-uri">{confirmation.confirmation_type} · {confirmation.confirmed_by_user_id}</p>
                          </div>
                          <span className="asset-type">{new Date(confirmation.created_at).toLocaleString()}</span>
                        </div>
                        <p>{confirmation.comment ?? "No comment"}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">No workflow execution has been created for this work item.</p>
        )}
      </section>

      <section className="panel">
        <h2>Work sessions</h2>
        {item.sessions.length ? (
          <div className="event-list">
            {item.sessions.map((session) => (
              <article className="event-row" key={session.id}>
                <div className="session-header">
                  <div>
                    <strong>{session.intent}</strong>
                    <p className="asset-uri">{session.agent_type} · {session.id}</p>
                  </div>
                  <span className="asset-type">{session.status}</span>
                </div>
                <dl className="status-metrics">
                  <div>
                    <dt>Started</dt>
                    <dd>{new Date(session.created_at).toLocaleString()}</dd>
                  </div>
                  <div>
                    <dt>Closed</dt>
                    <dd>{session.closed_at ? new Date(session.closed_at).toLocaleString() : "Open"}</dd>
                  </div>
                  <div>
                    <dt>Context states</dt>
                    <dd>{session.audit_counts.context_states}</dd>
                  </div>
                  <div>
                    <dt>Events</dt>
                    <dd>{session.audit_counts.events}</dd>
                  </div>
                </dl>
                <div className="actions">
                  <Link className="button-link secondary-link" href={`/projects/${projectId}/sessions/${session.id}`}>
                    View session audit
                  </Link>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">No sessions recorded for this work item.</p>
        )}
      </section>
    </main>
  );
}
