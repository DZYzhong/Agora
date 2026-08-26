import { apiPost } from "../../../../lib/api";

type ProjectStatus = {
  project: {
    id: string;
    name: string;
    slug: string;
    status: string;
  };
  work_item_counts: {
    total: number;
    active: number;
    completed: number;
  };
  delivery_readiness: {
    state: string;
    reason: string;
  };
  quality_counts: Record<string, number>;
  quality_dimensions: Record<string, Record<string, number>>;
  pending_approvals: {
    context_proposals: number;
    skill_candidates: number;
  };
  blockers: {
    code: string;
    severity: string;
    work_item_id: string;
    work_item_title: string;
    reason: string;
  }[];
  work_items: {
    id: string;
    external_key: string | null;
    title: string;
    status: string;
    stage: string;
    owner_id: string | null;
    quality_state: string;
    quality_counts: Record<string, number>;
    quality_gaps: { code: string; message: string }[];
    quality_evidence: {
      id: string;
      evidence_type: string;
      source: string;
      status: string;
      conclusion: string;
      command: string | null;
      output_summary: string | null;
      classification: string;
    }[];
  }[];
};

export default async function ProjectStatusPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  let status: ProjectStatus | null = null;
  try {
    status = await apiPost<ProjectStatus>("/harness/get-project-status", { project_id: projectId });
  } catch {
    status = null;
  }

  if (!status) {
    return (
      <main className="page">
        <h1>Project status</h1>
        <p className="alert">Unable to load project status.</p>
      </main>
    );
  }

  return (
    <main className="page">
      <h1>Project status</h1>
      <p className="muted">
        {status.project.name} · {status.project.slug}
      </p>
      <section className="panel status-panel">
        <p className="eyebrow">Project management</p>
        <dl className="status-metrics">
          <div>
            <dt>Work items</dt>
            <dd>{status.work_item_counts.total}</dd>
          </div>
          <div>
            <dt>Active</dt>
            <dd>{status.work_item_counts.active}</dd>
          </div>
          <div>
            <dt>Completed</dt>
            <dd>{status.work_item_counts.completed}</dd>
          </div>
        </dl>
      </section>
      <section className="panel status-panel">
        <p className="eyebrow">Delivery readiness</p>
        <dl className="status-metrics">
          <div>
            <dt>State</dt>
            <dd>{status.delivery_readiness.state}</dd>
          </div>
          <div>
            <dt>Reason</dt>
            <dd>{status.delivery_readiness.reason}</dd>
          </div>
        </dl>
      </section>
      <section className="panel status-panel">
        <p className="eyebrow">Quality evidence</p>
        <dl className="status-metrics">
          {Object.entries(status.quality_counts).map(([quality_state, count]) => (
            <div key={quality_state}>
              <dt>{quality_state}</dt>
              <dd>{count}</dd>
            </div>
          ))}
        </dl>
      </section>
      <section className="panel status-panel">
        <p className="eyebrow">Quality dimensions</p>
        <dl className="status-metrics">
          {Object.entries(status.quality_dimensions).map(([dimension, counts]) => (
            <div key={dimension}>
              <dt>{dimension}</dt>
              <dd>
                passed {counts.passed ?? 0} · failed {counts.failed ?? 0} · warning {counts.warning ?? 0}
              </dd>
            </div>
          ))}
        </dl>
      </section>
      <section className="panel status-panel">
        <p className="eyebrow">Pending approvals</p>
        <dl className="status-metrics">
          <div>
            <dt>Context proposals</dt>
            <dd>{status.pending_approvals.context_proposals}</dd>
          </div>
          <div>
            <dt>Skill candidates</dt>
            <dd>{status.pending_approvals.skill_candidates}</dd>
          </div>
        </dl>
      </section>
      <section className="panel">
        <h2>Blockers</h2>
        {status.blockers.length ? (
          <div className="history-list">
            <div className="history-row history-header">
              <span>Severity</span>
              <span>Work item</span>
              <span>Reason</span>
            </div>
            {status.blockers.map((blocker) => (
              <div className="history-row" key={`${blocker.code}-${blocker.work_item_id}`}>
                <span>{blocker.severity}</span>
                <span>{blocker.work_item_title}</span>
                <span>{blocker.reason}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No blockers recorded.</p>
        )}
      </section>
      <section className="panel">
        <h2>Work item quality</h2>
        <div className="history-list">
          <div className="history-row history-header">
            <span>Work item</span>
            <span>Stage</span>
            <span>Status</span>
            <span>Quality</span>
            <span>Gaps</span>
          </div>
          {status.work_items.map((item) => (
            <div className="history-row" key={item.id}>
              <span>{item.external_key ? `${item.external_key} · ${item.title}` : item.title}</span>
              <span>{item.stage}</span>
              <span>{item.status}</span>
              <span>{item.quality_state}</span>
              <span>{item.quality_gaps.map((gap) => gap.code).join(", ") || "None"}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="panel">
        <h2>Latest evidence</h2>
        <div className="history-list">
          <div className="history-row history-header">
            <span>Work item</span>
            <span>Type</span>
            <span>Status</span>
            <span>Conclusion</span>
            <span>Command</span>
          </div>
          {status.work_items.flatMap((item) =>
            item.quality_evidence.map((evidence) => (
              <div className="history-row" key={evidence.id}>
                <span>{item.external_key ? `${item.external_key} · ${item.title}` : item.title}</span>
                <span>{evidence.evidence_type}</span>
                <span>{evidence.status}</span>
                <span>{evidence.conclusion}</span>
                <span>{evidence.command ?? evidence.output_summary ?? "None"}</span>
              </div>
            )),
          )}
        </div>
      </section>
    </main>
  );
}
