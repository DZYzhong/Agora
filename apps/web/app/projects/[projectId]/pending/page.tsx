import Link from "next/link";
import { apiGet } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { Badge, Card, EmptyState, Page, PageHeader, Table } from "../../../../components/ui";

type Proposal = {
  id: string;
  title: string;
  type: string;
  status: string;
  target_branch: string;
  updated_at: string | null;
};

type Skill = {
  id: string;
  slug: string;
  name: string;
  status: string;
  updated_at?: string | null;
  created_at?: string | null;
};

type PendingQueue = {
  proposals: Proposal[];
  skillCandidates: Skill[];
  activeWorkItems: Array<{
    id: string;
    external_key: string | null;
    title: string;
    stage: string;
    status: string;
  }>;
};

export default async function PendingPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const base = `/projects/${projectId}`;
  const lang = await currentLang();
  const zh = lang === "zh";

  let queue: PendingQueue = { proposals: [], skillCandidates: [], activeWorkItems: [] };
  try {
    const [proposals, skills, workItems] = await Promise.all([
      apiGet<Proposal[]>(`/projects/${projectId}/context/proposals`),
      apiGet<Skill[]>(`/projects/${projectId}/skills`),
      apiGet<Array<{ id: string; external_key: string | null; title: string; stage: string; status: string }>>(
        `/projects/${projectId}/work-items`
      ),
    ]);
    queue = {
      proposals: proposals.filter((proposal) => proposal.status === "submitted"),
      skillCandidates: skills.filter((skill) => skill.status === "candidate"),
      activeWorkItems: workItems.filter(
        (item) => item.status === "active" || item.status === "in_progress"
      ),
    };
  } catch {
    return (
      <Page>
        <PageHeader title={zh ? "待办" : "Pending"} />
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {zh ? "无法加载待办队列。" : "Unable to load the pending queue."}
        </div>
      </Page>
    );
  }

  const totalPending = queue.proposals.length + queue.skillCandidates.length;

  return (
    <Page>
      <PageHeader
        title={zh ? "待办审批" : "Pending actions"}
        subtitle={
          zh
            ? `${totalPending} 项等待审阅或批准。`
            : `${totalPending} item(s) waiting for review or approval.`
        }
        actions={
          <Link
            href={`${base}/status`}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
          >
            ← {zh ? "返回项目状态" : "Back to project status"}
          </Link>
        }
      />

      <Card className="mt-6">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-900">
            {zh ? "待批准的上下文提案" : "Context proposals awaiting approval"}
          </h2>
          <Badge tone={queue.proposals.length ? "amber" : "green"}>
            {queue.proposals.length}
          </Badge>
        </div>
        {queue.proposals.length ? (
          <Table headers={[zh ? "标题" : "Title", zh ? "分支" : "Branch", zh ? "更新" : "Updated"]}>
            {queue.proposals.map((proposal) => (
              <tr key={proposal.id} className="transition hover:bg-slate-50">
                <td className="px-5 py-3.5">
                  <Link
                    href={`${base}/context/proposals/${proposal.id}`}
                    className="font-medium text-slate-900 hover:text-blue-700"
                  >
                    {proposal.title}
                  </Link>
                </td>
                <td className="px-5 py-3.5 font-mono text-xs text-slate-500">
                  {proposal.target_branch}
                </td>
                <td className="px-5 py-3.5 text-sm text-slate-400">
                  {proposal.updated_at
                    ? new Date(proposal.updated_at).toLocaleString()
                    : zh
                      ? "未知"
                      : "Unknown"}
                </td>
              </tr>
            ))}
          </Table>
        ) : (
          <p className="px-5 py-8 text-center text-sm text-slate-400">
            {zh ? "暂无待批提案。" : "No context proposals waiting."}
          </p>
        )}
      </Card>

      <Card className="mt-4">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-900">
            {zh ? "待批准的技能候选" : "Skill candidates awaiting approval"}
          </h2>
          <Badge tone={queue.skillCandidates.length ? "amber" : "green"}>
            {queue.skillCandidates.length}
          </Badge>
        </div>
        {queue.skillCandidates.length ? (
          <Table headers={[zh ? "名称" : "Name", "Slug"]}>
            {queue.skillCandidates.map((skill) => (
              <tr key={skill.id} className="transition hover:bg-slate-50">
                <td className="px-5 py-3.5">
                  <Link href={`${base}/skills`} className="font-medium text-slate-900 hover:text-blue-700">
                    {skill.name}
                  </Link>
                </td>
                <td className="px-5 py-3.5 font-mono text-xs text-slate-500">{skill.slug}</td>
              </tr>
            ))}
          </Table>
        ) : (
          <p className="px-5 py-8 text-center text-sm text-slate-400">
            {zh ? "暂无技能候选。" : "No skill candidates waiting."}
          </p>
        )}
      </Card>

      <Card className="mt-4">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-900">
            {zh ? "进行中的工作项" : "Active work items"}
          </h2>
          <Badge tone={queue.activeWorkItems.length ? "blue" : "green"}>
            {queue.activeWorkItems.length}
          </Badge>
        </div>
        {queue.activeWorkItems.length ? (
          <Table headers={[zh ? "工作项" : "Work item", zh ? "阶段" : "Stage"]}>
            {queue.activeWorkItems.map((item) => (
              <tr key={item.id} className="transition hover:bg-slate-50">
                <td className="px-5 py-3.5">
                  <Link
                    href={`${base}/work-items/${item.id}`}
                    className="font-medium text-slate-900 hover:text-blue-700"
                  >
                    {item.external_key ? `${item.external_key} · ${item.title}` : item.title}
                  </Link>
                </td>
                <td className="px-5 py-3.5">
                  <Badge tone="slate" dot={false}>
                    {item.stage}
                  </Badge>
                </td>
              </tr>
            ))}
          </Table>
        ) : (
          <p className="px-5 py-8 text-center text-sm text-slate-400">
            {zh
              ? "没有进行中的工作项。人工确认发生在 AI 工具内部，工作项详情页展示工作流审计。"
              : "No active work items. Human confirmations happen inside the AI tool; the work item detail page shows the workflow audit."}
          </p>
        )}
      </Card>
    </Page>
  );
}
