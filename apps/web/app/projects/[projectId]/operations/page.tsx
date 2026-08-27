import { apiGet } from "../../../../lib/api";

type CountMap = Record<string, number>;

type ProjectOperationsSummary = {
  format: string;
  generated_at: string;
  schema_revision: string;
  project: {
    id: string;
    name: string;
    slug: string;
    status: string;
    git_remotes: string[];
    default_branch: string | null;
  };
  assets: {
    total: number;
    by_type: CountMap;
    by_source: CountMap;
  };
  work_items: {
    total: number;
    by_status: CountMap;
    by_stage: CountMap;
    by_source: CountMap;
  };
  context: {
    streams: number;
    revisions: number;
    proposals_by_status: CountMap;
  };
  quality: {
    evidence_by_status: CountMap;
    evidence_by_type: CountMap;
  };
  skills: {
    skills_by_status: CountMap;
    versions_by_status: CountMap;
    runs_by_status: CountMap;
  };
  approvals: {
    decisions: CountMap;
  };
  security: {
    decisions: CountMap;
    actions: CountMap;
  };
  repository_signals: {
    by_status: CountMap;
    by_type: CountMap;
  };
  pull_request_signals: {
    by_status: CountMap;
    by_action: CountMap;
  };
};

export default async function ProjectOperationsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  let summary: ProjectOperationsSummary | null = null;
  try {
    summary = await apiGet<ProjectOperationsSummary>(`/projects/${projectId}/operations-summary`);
  } catch {
    summary = null;
  }

  if (!summary) {
    return (
      <main className="page">
        <h1>Operations summary</h1>
        <p className="alert">Unable to load operations summary.</p>
      </main>
    );
  }

  return (
    <main className="page">
      <h1>Operations summary</h1>
      <p className="muted">
        {summary.project.name} · {summary.project.slug} · {summary.schema_revision}
      </p>
      <section className="panel status-panel">
        <p className="eyebrow">Project</p>
        <dl className="status-metrics">
          <div>
            <dt>Status</dt>
            <dd>{summary.project.status}</dd>
          </div>
          <div>
            <dt>Default branch</dt>
            <dd>{summary.project.default_branch ?? "Not set"}</dd>
          </div>
          <div>
            <dt>Generated</dt>
            <dd>{new Date(summary.generated_at).toLocaleString()}</dd>
          </div>
        </dl>
      </section>
      <section className="grid">
        <SummaryPanel title="Assets" total={summary.assets.total} maps={[["Types", summary.assets.by_type], ["Sources", summary.assets.by_source]]} />
        <SummaryPanel
          title="Work items"
          total={summary.work_items.total}
          maps={[
            ["Status", summary.work_items.by_status],
            ["Stages", summary.work_items.by_stage],
            ["Sources", summary.work_items.by_source],
          ]}
        />
        <SummaryPanel
          title="Context governance"
          total={summary.context.streams + summary.context.revisions}
          maps={[
            ["Streams", { total: summary.context.streams }],
            ["Revisions", { total: summary.context.revisions }],
            ["Proposals", summary.context.proposals_by_status],
          ]}
        />
        <SummaryPanel
          title="Quality evidence"
          maps={[
            ["Status", summary.quality.evidence_by_status],
            ["Types", summary.quality.evidence_by_type],
          ]}
        />
        <SummaryPanel
          title="Skills"
          maps={[
            ["Skills", summary.skills.skills_by_status],
            ["Versions", summary.skills.versions_by_status],
            ["Runs", summary.skills.runs_by_status],
          ]}
        />
        <SummaryPanel title="Approvals" maps={[["Decisions", summary.approvals.decisions]]} />
        <SummaryPanel
          title="Security audit"
          maps={[
            ["Decisions", summary.security.decisions],
            ["Actions", summary.security.actions],
          ]}
        />
        <SummaryPanel
          title="Repository signals"
          maps={[
            ["Status", summary.repository_signals.by_status],
            ["Types", summary.repository_signals.by_type],
            ["PR/MR", summary.pull_request_signals.by_status],
          ]}
        />
      </section>
    </main>
  );
}

function SummaryPanel({ title, total, maps }: { title: string; total?: number; maps: [string, CountMap][] }) {
  return (
    <section className="panel status-panel">
      <div>
        <p className="eyebrow">{title}</p>
        {typeof total === "number" ? <h2>{total}</h2> : null}
      </div>
      {maps.map(([label, values]) => (
        <div key={label}>
          <h3>{label}</h3>
          <dl className="status-metrics compact-metrics">
            {Object.keys(values).length ? (
              Object.entries(values).map(([key, count]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{count}</dd>
                </div>
              ))
            ) : (
              <div>
                <dt>None</dt>
                <dd>0</dd>
              </div>
            )}
          </dl>
        </div>
      ))}
    </section>
  );
}
