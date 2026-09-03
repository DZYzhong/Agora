import Link from "next/link";
import { apiPost } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { Badge, Card, EmptyState, Page, PageHeader, SectionLabel, Table } from "../../../../components/ui";

type ProjectStatus = {
  project: { id: string; name: string; slug: string; status: string };
  work_item_counts: { total: number; active: number; completed: number };
  delivery_readiness: { state: string; reason: string };
  quality_counts: Record<string, number>;
  quality_dimensions: Record<string, Record<string, number>>;
  pending_approvals: { context_proposals: number; skill_candidates: number };
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
    task_links: {
      id: string;
      provider: string;
      external_key: string;
      external_url: string | null;
      title: string | null;
      status: string;
    }[];
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

function severityTone(severity: string) {
  if (severity === "critical" || severity === "high") return "red" as const;
  if (severity === "medium") return "amber" as const;
  return "slate" as const;
}

export default async function ProjectStatusPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const lang = await currentLang();
  const zh = lang === "zh";

  let status: ProjectStatus | null = null;
  try {
    status = await apiPost<ProjectStatus>("/harness/get-project-status", {
      project_id: projectId,
    });
  } catch {
    status = null;
  }

  if (!status) {
    return (
      <Page>
        <PageHeader title={zh ? "项目状态" : "Project status"} />
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {zh ? "无法加载项目状态。" : "Unable to load project status."}
        </div>
      </Page>
    );
  }

  const readinessTone =
    status.delivery_readiness.state === "ready"
      ? ("green" as const)
      : status.delivery_readiness.state === "blocked"
        ? ("red" as const)
        : ("amber" as const);

  return (
    <Page>
      <PageHeader
        title={zh ? "项目状态" : "Project status"}
        subtitle={`${status.project.name} · ${status.project.slug}`}
        actions={
          <Link
            href={`/projects/${projectId}/pending`}
            className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm hover:bg-canvas"
          >
            {zh ? "打开待办队列" : "Open pending queue"} →
          </Link>
        }
      />

      <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-3">
            {zh ? "工作项" : "Work items"}
          </p>
          <p className="mt-1 text-3xl font-semibold tracking-tight text-ink">
            {status.work_item_counts.total}
          </p>
          <p className="mt-1 text-xs text-ink-3">
            {zh ? "进行中" : "Active"} {status.work_item_counts.active} ·{" "}
            {zh ? "完成" : "Completed"} {status.work_item_counts.completed}
          </p>
        </Card>
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-3">
              {zh ? "交付就绪" : "Delivery readiness"}
            </p>
            <Badge tone={readinessTone}>{status.delivery_readiness.state}</Badge>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-ink-2">
            {status.delivery_readiness.reason}
          </p>
        </Card>
        <Card className="p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-3">
            {zh ? "质量证据" : "Quality evidence"}
          </p>
          <dl className="mt-2 space-y-1">
            {Object.entries(status.quality_counts).map(([qualityState, count]) => (
              <div key={qualityState} className="flex items-center justify-between text-sm">
                <dt className="text-ink-2">{qualityState}</dt>
                <dd className="font-semibold text-ink">{count}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card className="p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-3">
            {zh ? "待批审批" : "Pending approvals"}
          </p>
          <div className="mt-2 space-y-1 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-ink-2">{zh ? "上下文提案" : "Context proposals"}</span>
              <span className="font-semibold text-amber-600">
                {status.pending_approvals.context_proposals}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-ink-2">{zh ? "技能候选" : "Skill candidates"}</span>
              <span className="font-semibold text-amber-600">
                {status.pending_approvals.skill_candidates}
              </span>
            </div>
          </div>
        </Card>
      </section>

      {Object.keys(status.quality_dimensions).length ? (
        <>
          <SectionLabel>{zh ? "质量维度" : "Quality dimensions"}</SectionLabel>
          <Card className="mt-3">
            <dl className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(status.quality_dimensions).map(([dimension, counts]) => (
                <div key={dimension}>
                  <dt className="text-sm font-semibold text-ink">{dimension}</dt>
                  <dd className="mt-1 text-xs text-ink-2">
                    {zh ? "通过" : "passed"} {counts.passed ?? 0} ·{" "}
                    {zh ? "失败" : "failed"} {counts.failed ?? 0} ·{" "}
                    {zh ? "警告" : "warning"} {counts.warning ?? 0}
                  </dd>
                </div>
              ))}
            </dl>
          </Card>
        </>
      ) : null}

      <SectionLabel>{zh ? "阻塞项" : "Blockers"}</SectionLabel>
      {status.blockers.length ? (
        <Card className="mt-3">
          <Table headers={[zh ? "严重度" : "Severity", zh ? "工作项" : "Work item", zh ? "原因" : "Reason"]}>
            {status.blockers.map((blocker) => (
              <tr key={`${blocker.code}-${blocker.work_item_id}`}>
                <td className="px-5 py-3">
                  <Badge tone={severityTone(blocker.severity)}>{blocker.severity}</Badge>
                </td>
                <td className="px-5 py-3">
                  <Link
                    href={`/projects/${projectId}/work-items/${blocker.work_item_id}`}
                    className="font-medium text-ink hover:text-blue-700"
                  >
                    {blocker.work_item_title}
                  </Link>
                </td>
                <td className="px-5 py-3 text-sm text-ink-2">{blocker.reason}</td>
              </tr>
            ))}
          </Table>
        </Card>
      ) : (
        <Card className="mt-3 p-5 text-sm text-ink-3">
          {zh ? "暂无阻塞项。" : "No blockers recorded."}
        </Card>
      )}

      <SectionLabel>{zh ? "工作项质量" : "Work item quality"}</SectionLabel>
      {status.work_items.length ? (
        <Card className="mt-3">
          <Table
            headers={[
              zh ? "工作项" : "Work item",
              zh ? "阶段" : "Stage",
              zh ? "状态" : "Status",
              zh ? "质量" : "Quality",
              zh ? "任务链接" : "Task links",
              zh ? "缺口" : "Gaps",
            ]}
          >
            {status.work_items.map((item) => (
              <tr key={item.id} className="align-top">
                <td className="px-5 py-3">
                  <Link
                    href={`/projects/${projectId}/work-items/${item.id}`}
                    className="block max-w-xs font-medium text-ink hover:text-blue-700"
                  >
                    {item.external_key ? `${item.external_key} · ${item.title}` : item.title}
                  </Link>
                </td>
                <td className="px-5 py-3 text-xs text-ink-2">{item.stage}</td>
                <td className="px-5 py-3">
                  <Badge tone="slate" dot={false}>
                    {item.status}
                  </Badge>
                </td>
                <td className="px-5 py-3">
                  <Badge tone={item.quality_state === "passed" ? "green" : item.quality_state === "failed" ? "red" : "amber"} dot={false}>
                    {item.quality_state}
                  </Badge>
                </td>
                <td className="px-5 py-3 text-xs">
                  {item.task_links.length ? (
                    <div className="space-y-1">
                      {item.task_links.map((link) =>
                        link.external_url ? (
                          <a
                            key={link.id}
                            href={link.external_url}
                            className="block truncate font-mono text-blue-600 hover:underline"
                            target="_blank"
                            rel="noreferrer"
                          >
                            {link.provider}:{link.external_key}
                          </a>
                        ) : (
                          <span key={link.id} className="block truncate font-mono text-ink-2">
                            {link.provider}:{link.external_key}
                          </span>
                        ),
                      )}
                    </div>
                  ) : (
                    <span className="text-ink-3">—</span>
                  )}
                </td>
                <td className="max-w-[10rem] px-5 py-3 font-mono text-xs text-ink-2">
                  {item.quality_gaps.map((gap) => gap.code).join(", ") || "—"}
                </td>
              </tr>
            ))}
          </Table>
        </Card>
      ) : (
        <EmptyState title={zh ? "暂无工作项" : "No work items"} />
      )}

      <SectionLabel>{zh ? "最新证据" : "Latest evidence"}</SectionLabel>
      <Card className="mt-3">
        <Table
          headers={[
            zh ? "工作项" : "Work item",
            zh ? "类型" : "Type",
            zh ? "状态" : "Status",
            zh ? "结论" : "Conclusion",
            zh ? "命令" : "Command",
          ]}
        >
          {status.work_items.flatMap((item) =>
            item.quality_evidence.map((evidence) => (
              <tr key={evidence.id} className="align-top">
                <td className="px-5 py-3 text-sm font-medium text-ink">
                  {item.external_key ? `${item.external_key} · ${item.title}` : item.title}
                </td>
                <td className="px-5 py-3 text-xs text-ink-2">{evidence.evidence_type}</td>
                <td className="px-5 py-3">
                  <Badge tone={evidence.status === "passed" ? "green" : evidence.status === "failed" ? "red" : "amber"} dot={false}>
                    {evidence.status}
                  </Badge>
                </td>
                <td className="max-w-xs px-5 py-3 text-sm text-ink-2">{evidence.conclusion}</td>
                <td className="max-w-xs px-5 py-3">
                  <span className="block truncate font-mono text-xs text-ink-3">
                    {evidence.command ?? evidence.output_summary ?? "—"}
                  </span>
                </td>
              </tr>
            )),
          )}
        </Table>
      </Card>
    </Page>
  );
}
