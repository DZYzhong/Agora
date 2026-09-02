import Link from "next/link";
import { apiGet } from "../../../../lib/api";

type Asset = { id: string; type: string; title: string; created_at: string | null };
type Skill = { id: string; slug: string; name: string; status: string; created_at: string | null };
type Writeback = { id: string; type: string; title: string; status: string; accepted_asset_id: string | null; created_at: string | null };
type Proposal = { id: string; title: string; status: string; accepted_revision_id: string | null; updated_at: string | null };
type ContextState = { streams: Array<{ id: string; name: string; branch: string; status: string; head_revision_id: string | null; updated_at: string | null }>; proposals: Proposal[] };

type KnowledgeItem = {
  kind: string;
  title: string;
  at: string | null;
  href: string;
};

export default async function KnowledgePage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const base = `/projects/${projectId}`;
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
      <main className="page">
        <h1>Knowledge</h1>
        <p className="alert">Unable to load project knowledge.</p>
      </main>
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
      title: `${stream.name} · ${stream.branch}${stream.head_revision_id ? " (accepted head)" : ""}`,
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

  return (
    <main className="page">
      <h1>Knowledge</h1>
      <p className="muted">Team knowledge accumulated in this project: normalized assets, accepted context revisions, skills and experiences.</p>

      <section className="grid">
        <article className="panel">
          <p className="eyebrow">Assets</p>
          <h2 className="status-title">{assets.length}</h2>
          <p className="muted">
            {Object.entries(typeCounts)
              .map(([type, count]) => `${type} ${count}`)
              .join(" · ") || "No assets"}
          </p>
        </article>
        <article className="panel">
          <p className="eyebrow">Context revisions</p>
          <h2 className="status-title">{acceptedProposals.length}</h2>
          <p className="muted">{context.streams.length} stream(s) with accepted head</p>
        </article>
        <article className="panel">
          <p className="eyebrow">Skills</p>
          <h2 className="status-title">{approvedSkills.length}</h2>
          <p className="muted">{skills.length} total, {approvedSkills.length} approved</p>
        </article>
        <article className="panel">
          <p className="eyebrow">Experiences</p>
          <h2 className="status-title">{acceptedWritebacks.length}</h2>
          <p className="muted">{writebacks.length} writebacks, {acceptedWritebacks.length} accepted</p>
        </article>
      </section>

      <section className="panel">
        <h2>Recently accumulated</h2>
        {timeline.length ? (
          <div className="history-list">
            <div className="history-row history-header">
              <span>Kind</span>
              <span>Title</span>
              <span>When</span>
            </div>
            {timeline.map((item, index) => (
              <div className="history-row" key={`${item.kind}-${index}`}>
                <span>{item.kind}</span>
                <span>
                  <Link href={item.href}>{item.title}</Link>
                </span>
                <span>{item.at ? new Date(item.at).toLocaleString() : "Unknown"}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">Nothing accumulated yet. Authorized AI tools will upload context, assets and experiences as work happens.</p>
        )}
      </section>

      <section className="grid">
        <Link className="panel" href={`${base}/assets`}>
          <h2>Assets</h2>
          <p className="muted">Browse normalized source materials.</p>
        </Link>
        <Link className="panel" href={`${base}/context`}>
          <h2>Context</h2>
          <p className="muted">Inspect context streams, proposals and accepted revisions.</p>
        </Link>
        <Link className="panel" href={`${base}/skills`}>
          <h2>Skills</h2>
          <p className="muted">Approved reusable team skills.</p>
        </Link>
        <Link className="panel" href={`${base}/writebacks`}>
          <h2>Writebacks</h2>
          <p className="muted">Review accepted team experiences.</p>
        </Link>
      </section>
    </main>
  );
}
