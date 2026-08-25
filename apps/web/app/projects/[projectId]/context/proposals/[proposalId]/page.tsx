import Link from "next/link";
import { notFound } from "next/navigation";
import { apiGet } from "../../../../../../lib/api";

type Project = {
  id: string;
  name: string;
  slug: string;
};

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
  stream: {
    id: string;
    branch: string;
    head_revision_id: string | null;
  } | null;
};

function pretty(value: unknown): string {
  return JSON.stringify(value, null, 2);
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
  const project = await apiGet<Project>(`/projects/${projectId}`);
  const proposals = await apiGet<ContextProposal[]>(`/projects/${projectId}/context/proposals`);
  const proposal = proposals.find((item) => item.id === proposalId);
  if (!proposal) {
    notFound();
  }

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <h1>Context proposal</h1>
          <p className="muted">{project.name} / {project.slug}</p>
        </div>
        <Link className="button-link secondary-link" href={`/projects/${project.id}/context`}>
          Back to context
        </Link>
      </div>

      {query.error ? <p className="alert">{query.error}</p> : null}

      <section className="panel status-panel">
        <div className="session-header">
          <div>
            <p className="eyebrow">Proposal</p>
            <h2>{proposal.title}</h2>
            <p className="muted">{proposal.summary}</p>
          </div>
          <span className="asset-type">{proposal.status}</span>
        </div>
        <dl className="status-metrics">
          <div>
            <dt>Type</dt>
            <dd>{proposal.type}</dd>
          </div>
          <div>
            <dt>Target branch</dt>
            <dd>{proposal.target_branch}</dd>
          </div>
          <div>
            <dt>Expected head</dt>
            <dd>{proposal.expected_head_revision_id ?? "None"}</dd>
          </div>
          <div>
            <dt>Current head</dt>
            <dd>{proposal.stream?.head_revision_id ?? "None"}</dd>
          </div>
          <div>
            <dt>Target commit</dt>
            <dd>{proposal.to_commit_sha ?? "None"}</dd>
          </div>
          <div>
            <dt>Accepted revision</dt>
            <dd>{proposal.accepted_revision_id ?? "Not accepted"}</dd>
          </div>
        </dl>
      </section>

      {proposal.status !== "approved" ? (
        <section className="panel form">
          <h2>Human review</h2>
          <h3>Revision signal</h3>
          <form action={`/projects/${project.id}/context/proposals/${proposal.id}/approve`} method="post">
            <input type="hidden" name="target_branch" value={proposal.target_branch} />
            <label>
              Expected head
              <input name="expected_head_revision_id" defaultValue={proposal.expected_head_revision_id ?? ""} />
            </label>
            <label>
              Observed head SHA
              <input name="observed_head_sha" defaultValue={proposal.to_commit_sha ?? ""} />
            </label>
            <label className="checkbox-label">
              <input type="checkbox" name="contains_to_commit" defaultChecked={Boolean(proposal.to_commit_sha)} />
              Contains target commit
            </label>
            <label>
              Merge target branch
              <input name="merge_target_branch" defaultValue="" />
            </label>
            <label className="checkbox-label">
              <input type="checkbox" name="merged_to_target" />
              Merged to target branch
            </label>
            <label>
              Comment
              <textarea name="comment" defaultValue="" />
            </label>
            <button type="submit">Approve proposal</button>
          </form>
        </section>
      ) : null}

      <section className="panel">
        <h2>Context content</h2>
        <pre className="writeback-content">{pretty(proposal.content)}</pre>
      </section>

      <section className="panel">
        <h2>Source anchors</h2>
        <pre className="writeback-content">{pretty(proposal.source_anchors)}</pre>
      </section>

      <section className="panel">
        <h2>Provenance</h2>
        <pre className="writeback-content">{pretty(proposal.provenance)}</pre>
      </section>
    </main>
  );
}
