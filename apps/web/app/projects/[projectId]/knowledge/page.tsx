import Link from "next/link";
import { apiGet } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { relativeTime } from "../../../../lib/format";
import { Card, EmptyState, Page, PageHeader, SectionLabel, Table } from "../../../../components/ui";

type Asset = { id: string; type: string; title: string; created_at: string | null };
type Skill = { id: string; slug: string; name: string; status: string; created_at: string | null };
type Writeback = {
  id: string;
  type: string;
  title: string;
  status: string;
  accepted_asset_id: string | null;
  created_at: string | null;
};
type Proposal = {
  id: string;
  title: string;
  status: string;
  accepted_revision_id: string | null;
  updated_at: string | null;
};
type ContextState = {
  streams: Array<{
    id: string;
    name: string;
    branch: string;
    status: string;
    head_revision_id: string | null;
    updated_at: string | null;
  }>;
  proposals: Proposal[];
};

type KnowledgeItem = { kind: string; title: string; at: string | null; href: string };

const kindLabel: Record<string, { zh: string; en: string }> = {
  Asset: { zh: "资产", en: "Asset" },
  Context: { zh: "上下文", en: "Context" },
  "Context revision": { zh: "上下文修订", en: "Context revision" },
  Skill: { zh: "技能", en: "Skill" },
  Experience: { zh: "经验", en: "Experience" },
};

export default async function KnowledgePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const base = `/projects/${projectId}`;
  const lang = await currentLang();
  const zh = lang === "zh";

  let assets: Asset[] = [];
  let skills: Skill[] = [];
  let writebacks: Writeback[] = [];
  let context: ContextState = { streams: [], proposals: [] };
  try {
    [assets, skills, writebacks, context] = await Promise.all([
      apiGet<Asset[]>(`/projects/${projectId}/assets`),
      apiGet<Skill[]>(`/projects/${projectId}/skills`),
      apiGet<Writeback[]>(`/projects/${projectId}/writebacks`),
      apiGet<ContextState>(`/projects/${projectId}/context`),
    ]);
  } catch {
    return (
      <Page>
        <PageHeader title={zh ? "知识" : "Knowledge"} />
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {zh ? "无法加载项目知识。" : "Unable to load project knowledge."}
        </div>
      </Page>
    );
  }

  const acceptedProposals = context.proposals.filter((proposal) => proposal.accepted_revision_id);
  const approvedSkills = skills.filter((skill) => skill.status === "approved");
  const acceptedWritebacks = writebacks.filter((writeback) => writeback.status === "accepted");

  const typeCounts: Record<string, number> = {};
  for (const asset of assets) {
    typeCounts[asset.type] = (typeCounts[asset.type] ?? 0) + 1;
  }

  const timeline: KnowledgeItem[] = [
    ...assets.map((asset) => ({
      kind: "Asset",
      title: asset.title,
      at: asset.created_at,
      href: `${base}/assets`,
    })),
    ...context.streams.map((stream) => ({
      kind: "Context",
      title: `${stream.name} · ${stream.branch}${stream.head_revision_id ? (zh ? "（已接受 head）" : " (accepted head)") : ""}`,
      at: stream.updated_at,
      href: `${base}/context`,
    })),
    ...acceptedProposals.map((proposal) => ({
      kind: "Context revision",
      title: proposal.title,
      at: proposal.updated_at,
      href: `${base}/context/proposals/${proposal.id}`,
    })),
    ...approvedSkills.map((skill) => ({
      kind: "Skill",
      title: skill.name,
      at: skill.created_at,
      href: `${base}/skills`,
    })),
    ...acceptedWritebacks.map((writeback) => ({
      kind: "Experience",
      title: writeback.title,
      at: writeback.created_at,
      href: `${base}/writebacks`,
    })),
  ]
    .filter((item) => item.at)
    .sort((a, b) => String(b.at).localeCompare(String(a.at) ?? ""))
    .slice(0, 12);

  const kpi = [
    {
      key: zh ? "资产" : "Assets",
      value: assets.length,
      hint:
        Object.entries(typeCounts)
          .map(([type, count]) => `${type} ${count}`)
          .join(" · ") || (zh ? "无资产" : "No assets"),
    },
    {
      key: zh ? "上下文修订" : "Context revisions",
      value: acceptedProposals.length,
      hint:
        zh
          ? `${context.streams.length} 个流含已接受 head`
          : `${context.streams.length} stream(s) with accepted head`,
    },
    {
      key: zh ? "技能" : "Skills",
      value: approvedSkills.length,
      hint: zh ? `${skills.length} 总计 · ${approvedSkills.length} 已批准` : `${skills.length} total, ${approvedSkills.length} approved`,
    },
    {
      key: zh ? "经验" : "Experiences",
      value: acceptedWritebacks.length,
      hint: zh
        ? `${writebacks.length} 写回 · ${acceptedWritebacks.length} 已接受`
        : `${writebacks.length} writebacks, ${acceptedWritebacks.length} accepted`,
    },
  ];

  return (
    <Page>
      <PageHeader
        title={zh ? "知识" : "Knowledge"}
        subtitle={
          zh
            ? "本项目积累的团队知识：归一化资产、已接受的上下文修订、技能与经验。"
            : "Team knowledge accumulated in this project: normalized assets, accepted context revisions, skills and experiences."
        }
      />

      <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpi.map((stat) => (
          <Card key={stat.key} className="p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{stat.key}</p>
            <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-900">{stat.value}</p>
            <p className="mt-1 truncate text-xs text-slate-400">{stat.hint}</p>
          </Card>
        ))}
      </section>

      <SectionLabel>{zh ? "最近沉淀" : "Recently accumulated"}</SectionLabel>
      {timeline.length ? (
        <Card className="mt-3">
          <Table headers={[zh ? "类型" : "Kind", zh ? "标题" : "Title", zh ? "时间" : "When"]}>
            {timeline.map((item, index) => (
              <tr key={`${item.kind}-${index}`} className="transition hover:bg-slate-50">
                <td className="px-5 py-3">
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
                    {kindLabel[item.kind] ? kindLabel[item.kind][lang] : item.kind}
                  </span>
                </td>
                <td className="px-5 py-3">
                  <Link href={item.href} className="font-medium text-slate-800 hover:text-blue-700">
                    {item.title}
                  </Link>
                </td>
                <td className="px-5 py-3 text-sm text-slate-400">{relativeTime(item.at, lang)}</td>
              </tr>
            ))}
          </Table>
        </Card>
      ) : (
        <EmptyState
          title={zh ? "还没有沉淀内容" : "Nothing accumulated yet"}
          hint={
            zh
              ? "已授权的 AI 工具在工作过程中会上传上下文、资产与经验。"
              : "Authorized AI tools will upload context, assets and experiences as work happens."
          }
        />
      )}

      <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { href: `${base}/assets`, title: zh ? "资产" : "Assets", hint: zh ? "浏览归一化的源材料。" : "Browse normalized source materials." },
          { href: `${base}/context`, title: zh ? "上下文" : "Context", hint: zh ? "检查上下文流、提案与已接受修订。" : "Inspect context streams, proposals and accepted revisions." },
          { href: `${base}/skills`, title: zh ? "技能" : "Skills", hint: zh ? "已批准的可复用团队技能。" : "Approved reusable team skills." },
          { href: `${base}/writebacks`, title: zh ? "写回" : "Writebacks", hint: zh ? "已接受的团队经验。" : "Review accepted team experiences." },
        ].map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="group rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-px hover:border-blue-200 hover:shadow"
          >
            <span className="text-[15px] font-semibold text-slate-900 group-hover:text-blue-700">
              {link.title} →
            </span>
            <span className="mt-0.5 block text-xs text-slate-400">{link.hint}</span>
          </Link>
        ))}
      </section>
    </Page>
  );
}
