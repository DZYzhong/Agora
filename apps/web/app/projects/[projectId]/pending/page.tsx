import Link from "next/link";
import { apiGet } from "../../../../lib/api";

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
  activeWorkItems: Array<{ id: string; external_key: string | null; title: string; stage: string; status: string }>;
};

export default async function PendingPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const base = `/projects/${projectId}`;
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
      activeWorkItems: workItems.filter((item) => item.status === "active" || item.status === "in_progress"),
    };
  } catch {
    return (
      <main className="page">
        <h1>Pending</h1>
        <p className="alert">Unable to load the pending queue.</p>
      </main>
    );
  }

  const totalPending = queue.proposals.length + queue.skillCandidates.length;

  return (
    <main className="page">
      <h1>Pending actions</h1>
      <p className="muted">{totalPending} item(s) waiting for review or approval.</p>

      <section className="panel">
        <h2>Context proposals awaiting approval</h2>
        {queue.proposals.length ? (
          <div className="history-list">
            <div className="history-row history-header">
              <span>Title</span>
              <span>Branch</span>
              <span>Updated</span>
            </div>
            {queue.proposals.map((proposal) => (
              <div className="history-row" key={proposal.id}>
                <span>
                  <Link href={`${base}/context/proposals/${proposal.id}`}>{proposal.title}</Link>
                </span>
                <span>{proposal.target_branch}</span>
                <span>{proposal.updated_at ? new Date(proposal.updated_at).toLocaleString() : "Unknown"}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No context proposals waiting.</p>
        )}
      </section>

      <section className="panel">
        <h2>Skill candidates awaiting approval</h2>
        {queue.skillCandidates.length ? (
          <div className="history-list">
            <div className="history-row history-header">
              <span>Name</span>
              <span>Slug</span>
            </div>
            {queue.skillCandidates.map((skill) => (
              <div className="history-row" key={skill.id}>
                <span>
                  <Link href={`${base}/skills`}>{skill.name}</Link>
                </span>
                <span>{skill.slug}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No skill candidates waiting.</p>
        )}
      </section>

      <section className="panel">
        <h2>Active work items</h2>
        {queue.activeWorkItems.length ? (
          <div className="history-list">
            <div className="history-row history-header">
              <span>Work item</span>
              <span>Stage</span>
            </div>
            {queue.activeWorkItems.map((item) => (
              <div className="history-row" key={item.id}>
                <span>
                  <Link href={`${base}/work-items/${item.id}`}>
                    {item.external_key ? `${item.external_key} · ${item.title}` : item.title}
                  </Link>
                </span>
                <span>{item.stage}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No active work items. Human confirmations happen inside the AI tool; the work item detail page shows the workflow audit.</p>
        )}
      </section>

      <div className="actions">
        <Link className="button-link secondary-link" href={`${base}/status`}>
          Back to project status
        </Link>
      </div>
    </main>
  );
}
