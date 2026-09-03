import Link from "next/link";
import { notFound } from "next/navigation";
import { apiGet } from "../../../../../../lib/api";
import { currentLang } from "../../../../../../lib/i18n";
import { Badge, Card, Page, PageHeader, SectionLabel } from "../../../../../../components/ui";

type Project = { id: string; name: string; slug: string };

type ContextProposal = {
  id: string;
  type: string;
  status: string;
  title: string;
  summary: string;
  target_branch: string;
  expected_head_revision_id: string | null;
  from_commit_sha: string | null;
  to_commit_sha: string | null;
  accepted_revision_id: string | null;
  content: Record<string, unknown>;
  source_anchors: Record<string, unknown>[];
  provenance: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  stream: { id: string; branch: string; head_revision_id: string | null } | null;
};

function pretty(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-surface px-3 py-2 text-sm shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";
const labelClass = "mb-1 block text-xs font-medium text-ink-2";
const dt = "text-xs text-ink-3";
const dd = "font-mono text-xs text-ink-2 break-all";

function statusTone(status: string) {
  if (status === "approved" || status === "accepted") return "green" as const;
  if (status === "submitted") return "amber" as const;
  if (status === "rejected" || status === "superseded") return "red" as const;
  return "slate" as const;
}

export default async function ContextProposalPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string; proposalId: string }>;
  searchParams?: Promise<{ error?: string }>;
}) {
  const { projectId, proposalId } = await params;
  const query = searchParams ? await searchParams : {};
  const lang = await currentLang();
  const zh = lang === "zh";

  const project = await apiGet<Project>(`/projects/${projectId}`);
  const proposals = await apiGet<ContextProposal[]>(`/projects/${projectId}/context/proposals`);
  const proposal = proposals.find((item) => item.id === proposalId);
  if (!proposal) {
    notFound();
  }

  return (
    <Page>
      <PageHeader
        title={zh ? "上下文提案" : "Context proposal"}
        subtitle={`${project.name} / ${project.slug}`}
        meta={<Badge tone={statusTone(proposal.status)}>{proposal.status}</Badge>}
        actions={
          <Link
            href={`/projects/${project.id}/context`}
            className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm hover:bg-canvas"
          >
            ← {zh ? "返回上下文" : "Back to context"}
          </Link>
        }
      />

      {query.error ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {query.error}
        </div>
      ) : null}

      <Card className="mt-6 p-5">
        <h2 className="text-lg font-semibold text-ink">{proposal.title}</h2>
        <p className="mt-1 text-sm text-ink-2">{proposal.summary}</p>
        <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-3 border-t border-edge-1 pt-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className={dt}>{zh ? "类型" : "Type"}</dt>
            <dd className="text-ink">{proposal.type}</dd>
          </div>
          <div>
            <dt className={dt}>{zh ? "目标分支" : "Target branch"}</dt>
            <dd className={dd}>{proposal.target_branch}</dd>
          </div>
          <div>
            <dt className={dt}>{zh ? "期望 head" : "Expected head"}</dt>
            <dd className={dd}>{proposal.expected_head_revision_id ?? "—"}</dd>
          </div>
          <div>
            <dt className={dt}>{zh ? "当前 head" : "Current head"}</dt>
            <dd className={dd}>{proposal.stream?.head_revision_id ?? "—"}</dd>
          </div>
          <div>
            <dt className={dt}>{zh ? "目标提交" : "Target commit"}</dt>
            <dd className={dd}>{proposal.to_commit_sha ?? "—"}</dd>
          </div>
          <div>
            <dt className={dt}>{zh ? "已接受修订" : "Accepted revision"}</dt>
            <dd className={dd}>{proposal.accepted_revision_id ?? (zh ? "未接受" : "Not accepted")}</dd>
          </div>
        </dl>
      </Card>

      {proposal.status !== "approved" ? (
        <Card className="mt-4 p-5">
          <h2 className="text-sm font-semibold text-ink">{zh ? "人工审阅" : "Human review"}</h2>
          <p className="mt-1 text-xs text-ink-3">
            {zh ? "修订信号（revision signal）" : "Revision signal"}
          </p>
          <form
            action={`/projects/${project.id}/context/proposals/${proposal.id}/approve`}
            method="post"
            className="mt-4 grid gap-3 sm:grid-cols-2"
          >
            <input type="hidden" name="target_branch" value={proposal.target_branch} />
            <label className="block">
              <span className={labelClass}>{zh ? "期望 head" : "Expected head"}</span>
              <input
                name="expected_head_revision_id"
                defaultValue={proposal.expected_head_revision_id ?? ""}
                className={inputClass}
              />
            </label>
            <label className="block">
              <span className={labelClass}>{zh ? "观察到的 head SHA" : "Observed head SHA"}</span>
              <input name="observed_head_sha" defaultValue={proposal.to_commit_sha ?? ""} className={inputClass} />
            </label>
            <label className="flex items-center gap-2 text-sm text-ink-2 sm:col-span-2">
              <input
                type="checkbox"
                name="contains_to_commit"
                defaultChecked={Boolean(proposal.to_commit_sha)}
                className="h-4 w-4 rounded border-slate-300"
              />
              {zh ? "包含目标提交" : "Contains target commit"}
            </label>
            <label className="block">
              <span className={labelClass}>{zh ? "合并目标分支" : "Merge target branch"}</span>
              <input name="merge_target_branch" defaultValue="" className={inputClass} />
            </label>
            <label className="flex items-center gap-2 self-end text-sm text-ink-2">
              <input type="checkbox" name="merged_to_target" className="h-4 w-4 rounded border-slate-300" />
              {zh ? "已合并到目标分支" : "Merged to target branch"}
            </label>
            <label className="block sm:col-span-2">
              <span className={labelClass}>{zh ? "评论" : "Comment"}</span>
              <textarea name="comment" rows={2} defaultValue="" className={inputClass} />
            </label>
            <button
              type="submit"
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700 sm:col-span-2"
            >
              {zh ? "批准提案" : "Approve proposal"}
            </button>
          </form>
        </Card>
      ) : null}

      <SectionLabel>{zh ? "上下文内容" : "Context content"}</SectionLabel>
      <Card className="mt-3">
        <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap px-5 py-4 font-sans text-sm text-ink-2">
          {pretty(proposal.content)}
        </pre>
      </Card>

      <SectionLabel>{zh ? "来源锚点" : "Source anchors"}</SectionLabel>
      <Card className="mt-3">
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap px-5 py-4 font-sans text-sm text-ink-2">
          {pretty(proposal.source_anchors)}
        </pre>
      </Card>

      <SectionLabel>{zh ? "来源追踪" : "Provenance"}</SectionLabel>
      <Card className="mt-3">
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap px-5 py-4 font-sans text-sm text-ink-2">
          {pretty(proposal.provenance)}
        </pre>
      </Card>
    </Page>
  );
}
