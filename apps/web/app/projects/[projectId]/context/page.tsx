import Link from "next/link";
import { apiGet } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { relativeTime } from "../../../../lib/format";
import { Badge, Card, Page, PageHeader, SectionLabel } from "../../../../components/ui";

type Project = { id: string; name: string; slug: string };

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
  budget: { estimated_tokens?: number; token_budget?: number; included_assets?: number } | null;
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

function healthLabel(state: ContextState | null, zh: boolean): { text: string; tone: "green" | "amber" | "slate" } {
  if (!state) return { text: zh ? "缺失" : "missing", tone: "slate" };
  if (state.provisional) return { text: zh ? "临时" : "provisional", tone: "amber" };
  return { text: zh ? "已接受" : "accepted", tone: "green" };
}

export default async function ContextStatePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const lang = await currentLang();
  const zh = lang === "zh";

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
  const health = healthLabel(latest ?? null, zh);

  return (
    <Page>
      <PageHeader
        title={zh ? "上下文状态" : "Context state"}
        subtitle={`${project.name} / ${project.slug}`}
        actions={
          <Link
            href={`/projects/${project.id}`}
            className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm hover:bg-canvas"
          >
            ← {zh ? "返回项目" : "Back to project"}
          </Link>
        }
      />

      <Card className="mt-6 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-ink-3">
              {zh ? "项目上下文" : "Project context"}
            </p>
            <div className="mt-1 flex items-center gap-3">
              <h2 className="text-lg font-semibold text-ink">
                {latest ? health.text : zh ? "暂无上传上下文" : "No uploaded context"}
              </h2>
              <Badge tone={health.tone}>{health.text}</Badge>
            </div>
            <p className="mt-1 text-xs text-ink-3">
              {zh
                ? "P1 已索引材料在被审阅的上下文修订接受前视为临时内容。"
                : "P1 indexed material is treated as provisional until a reviewed context revision is accepted."}
            </p>
          </div>
          <span className="rounded-full bg-fill px-3 py-1 text-xs font-medium text-ink-2">
            {withContext.length}/{workItems.length} {zh ? "任务" : "tasks"}
          </span>
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-edge-1 pt-4 text-sm lg:grid-cols-4">
          <div>
            <dt className="text-xs text-ink-3">{zh ? "最近更新" : "Latest update"}</dt>
            <dd className="text-ink">
              {latest ? relativeTime(latest.created_at, lang) : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-ink-3">{zh ? "覆盖度" : "Coverage"}</dt>
            <dd className="text-ink">{latest?.freshness.context_coverage ?? "unknown"}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-3">{zh ? "建议动作" : "Recommended action"}</dt>
            <dd className="truncate font-mono text-xs text-ink-2">
              {latest?.freshness.recommended_action ?? "ai_tool_upload_context"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-ink-3">{zh ? "估算 tokens" : "Estimated tokens"}</dt>
            <dd className="text-ink">
              {latest?.budget?.estimated_tokens ?? (zh ? "未知" : "Unknown")}
            </dd>
          </div>
        </dl>
      </Card>

      {workItems.length ? (
        <>
          <SectionLabel>{zh ? "按工作项查看上下文" : "Context state by work item"}</SectionLabel>
          <Card className="mt-3 divide-y divide-edge-1">
            {workItems.map((item) => {
              const state = item.latest_context_state;
              const itemHealth = healthLabel(state ?? null, zh);
              return (
                <Link
                  href={`/projects/${project.id}/work-items/${item.id}`}
                  key={item.id}
                  className="flex flex-wrap items-center gap-x-6 gap-y-1 px-5 py-3.5 transition hover:bg-canvas"
                >
                  <span className="min-w-0 flex-1">
                    <span className="font-medium text-ink">
                      {item.external_key ? `${item.external_key} · ${item.title}` : item.title}
                    </span>
                    <span className="mt-0.5 block text-xs text-ink-3">
                      {item.session_count} sessions ·{" "}
                      {item.participants.length || (zh ? "无" : "no")}{" "}
                      {zh ? "参与者" : "participants"}
                    </span>
                  </span>
                  <Badge tone={itemHealth.tone}>{itemHealth.text}</Badge>
                  <span className="w-24 truncate font-mono text-xs text-ink-2">
                    {state?.freshness.context_coverage ?? "unknown"}
                  </span>
                  <span className="w-28 text-xs text-ink-3">
                    {state ? relativeTime(state.created_at, lang) : zh ? "未上传" : "Not uploaded"}
                  </span>
                </Link>
              );
            })}
          </Card>
        </>
      ) : null}

      <SectionLabel>{zh ? "上下文流" : "Context streams"}</SectionLabel>
      {streams.length ? (
        <div className="mt-3 grid gap-4 lg:grid-cols-2">
          {streams.map((stream) => (
            <Card key={stream.id} className="flex items-start justify-between gap-3 p-5">
              <div className="min-w-0">
                <h3 className="truncate text-[15px] font-semibold text-ink">
                  {stream.name} · <span className="font-mono text-sm">{stream.branch}</span>
                </h3>
                <p className="mt-0.5 text-xs text-ink-3">
                  {stream.head_revision_id
                    ? zh
                      ? "已存在 head 修订"
                      : "Head revision present"
                    : zh
                      ? "暂无已接受 head"
                      : "No accepted head"}
                </p>
                <p className="mt-2 text-xs text-ink-3">
                  {zh ? "更新于" : "Updated"}{" "}
                  <time dateTime={stream.updated_at}>{relativeTime(stream.updated_at, lang)}</time>
                </p>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-2">
                <Badge tone={stream.status === "active" ? "green" : "slate"}>{stream.status}</Badge>
                <Link
                  href={`/projects/${project.id}/context/streams/${stream.id}`}
                  className="text-xs font-medium text-blue-600 hover:text-blue-700"
                >
                  {zh ? "查看版本历史" : "View revision history"} →
                </Link>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="mt-3 p-5 text-sm text-ink-3">
          {zh
            ? "暂无 ContextStream。AI 工具可提交初始 ContextProposal 供审阅。"
            : "No ContextStream exists yet. An AI tool can submit an initial ContextProposal for review."}
        </Card>
      )}

      <SectionLabel>{zh ? "上下文提案" : "Context proposals"}</SectionLabel>
      {proposals.length ? (
        <div className="mt-3 grid gap-4 lg:grid-cols-2">
          {proposals.map((proposal) => (
            <Card key={proposal.id} className="flex flex-col p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-[15px] font-semibold text-ink">
                    {proposal.title}
                  </h3>
                  <p className="mt-0.5 font-mono text-xs text-ink-3">
                    {proposal.type} · {proposal.target_branch}
                  </p>
                </div>
                <Badge
                  tone={
                    proposal.status === "accepted"
                      ? "green"
                      : proposal.status === "submitted"
                        ? "amber"
                        : "slate"
                  }
                >
                  {proposal.status}
                </Badge>
              </div>
              <p className="mt-2 line-clamp-2 text-sm text-ink-2">{proposal.summary}</p>
              <dl className="mt-3 grid grid-cols-2 gap-2 border-t border-edge-1 pt-3 text-sm">
                <div>
                  <dt className="text-xs text-ink-3">{zh ? "期望 head" : "Expected head"}</dt>
                  <dd className="truncate font-mono text-[11px] text-ink-2">
                    {proposal.expected_head_revision_id ?? "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-3">{zh ? "已接受修订" : "Accepted revision"}</dt>
                  <dd className="truncate font-mono text-[11px] text-ink-2">
                    {proposal.accepted_revision_id ?? (zh ? "未接受" : "Not accepted")}
                  </dd>
                </div>
              </dl>
              <Link
                href={`/projects/${project.id}/context/proposals/${proposal.id}`}
                className="mt-3 text-sm font-medium text-blue-600 hover:text-blue-700"
              >
                {zh ? "查看提案" : "View proposal"} →
              </Link>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="mt-3 p-5 text-sm text-ink-3">
          {zh ? "暂无待审提案。" : "No ContextProposal has been uploaded for review."}
        </Card>
      )}
    </Page>
  );
}
