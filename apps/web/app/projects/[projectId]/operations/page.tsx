import { apiGet } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { Card, Page, PageHeader } from "../../../../components/ui";

type CountMap = Record<string, number>;

type Summary = {
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
  assets: { total: number; by_type: CountMap; by_source: CountMap };
  work_items: { total: number; by_status: CountMap; by_stage: CountMap; by_source: CountMap };
  context: { streams: number; revisions: number; proposals_by_status: CountMap };
  quality: { evidence_by_status: CountMap; evidence_by_type: CountMap };
  skills: { skills_by_status: CountMap; versions_by_status: CountMap; runs_by_status: CountMap };
  approvals: { decisions: CountMap };
  security: { decisions: CountMap; actions: CountMap };
  repository_signals: { by_status: CountMap; by_type: CountMap };
  pull_request_signals: { by_status: CountMap; by_action: CountMap };
};

function MiniStats({ values }: { values: CountMap }) {
  const entries = Object.keys(values).length ? Object.entries(values) : [["—", 0]];
  return (
    <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
      {entries.map(([key, count]) => (
        <div key={key} className="flex items-center justify-between gap-2 text-sm">
          <dt className="truncate font-mono text-xs text-ink-3">{key}</dt>
          <dd className="font-semibold text-ink">{count}</dd>
        </div>
      ))}
    </dl>
  );
}

function SummaryPanel({
  title,
  total,
  maps,
}: {
  title: string;
  total?: number;
  maps: [string, CountMap][];
}) {
  return (
    <Card className="p-5">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {typeof total === "number" ? (
          <span className="text-2xl font-semibold tracking-tight text-ink">{total}</span>
        ) : null}
      </div>
      <div className="mt-3 space-y-3 border-t border-edge-1 pt-3">
        {maps.map(([label, values]) => (
          <div key={label}>
            <p className="text-xs font-medium uppercase tracking-wide text-ink-3">{label}</p>
            <MiniStats values={values} />
          </div>
        ))}
      </div>
    </Card>
  );
}

export default async function ProjectOperationsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const lang = await currentLang();
  const zh = lang === "zh";

  let summary: Summary | null = null;
  try {
    summary = await apiGet<Summary>(`/projects/${projectId}/operations-summary`);
  } catch {
    summary = null;
  }

  if (!summary) {
    return (
      <Page>
        <PageHeader title={zh ? "运营摘要" : "Operations summary"} />
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {zh ? "无法加载运营摘要。" : "Unable to load operations summary."}
        </div>
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader
        title={zh ? "运营摘要" : "Operations summary"}
        subtitle={`${summary.project.name} · ${summary.project.slug}`}
        meta={
          <span className="rounded-full bg-surface px-3 py-1 font-mono text-xs text-ink-3 ring-1 ring-inset ring-edge">
            {summary.schema_revision}
          </span>
        }
      />

      <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryPanel
          title="Assets"
          total={summary.assets.total}
          maps={[
            [zh ? "类型" : "Types", summary.assets.by_type],
            [zh ? "来源" : "Sources", summary.assets.by_source],
          ]}
        />
        <SummaryPanel
          title={zh ? "工作项" : "Work items"}
          total={summary.work_items.total}
          maps={[
            ["Status", summary.work_items.by_status],
            ["Stages", summary.work_items.by_stage],
            ["Sources", summary.work_items.by_source],
          ]}
        />
        <SummaryPanel
          title={zh ? "上下文治理" : "Context governance"}
          total={summary.context.streams + summary.context.revisions}
          maps={[
            ["Streams", { total: summary.context.streams }],
            ["Revisions", { total: summary.context.revisions }],
            ["Proposals", summary.context.proposals_by_status],
          ]}
        />
        <SummaryPanel
          title={zh ? "质量证据" : "Quality evidence"}
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
          title={zh ? "安全审计" : "Security audit"}
          maps={[
            ["Decisions", summary.security.decisions],
            ["Actions", summary.security.actions],
          ]}
        />
        <SummaryPanel
          title={zh ? "仓库信号" : "Repository signals"}
          maps={[
            ["Status", summary.repository_signals.by_status],
            ["Types", summary.repository_signals.by_type],
            ["PR/MR", summary.pull_request_signals.by_status],
          ]}
        />
      </section>
    </Page>
  );
}
