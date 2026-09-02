import Link from "next/link";
import { apiGet } from "../../../lib/api";

type Project = {
  id: string;
  name: string;
  slug: string;
  git_remotes: string[];
};

type InitializationJob = {
  id: string;
  git_remote: string | null;
  status: "running" | "completed" | "failed" | string;
  asset_count: number;
  error: string | { code: string; message: string } | null;
  warnings: Array<string | { code: string; message: string }>;
  started_at: string | null;
  completed_at: string | null;
};

export default async function ProjectDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ init_error?: string }>;
}) {
  const { projectId } = await params;
  await searchParams;
  const project = await apiGet<Project>(`/projects/${projectId}`);
  let initializationJobs: InitializationJob[] = [];
  try {
    initializationJobs = await apiGet<InitializationJob[]>(`/projects/${projectId}/initialization-jobs`);
  } catch {
    initializationJobs = [];
  }
  const latestInitializationJob = initializationJobs[0];

  return (
    <main className="page">
      <h1>{project.name}</h1>
      <p className="muted">{project.slug}</p>
      <section className="panel status-panel">
        <div>
          <p className="eyebrow">Initialization</p>
          {latestInitializationJob ? (
            <>
              <h2 className="status-title">
                <span className={`status-dot status-${latestInitializationJob.status}`} aria-hidden="true" />
                {latestInitializationJob.status}
              </h2>
              <p className="muted">Context assets are supplied by authorized AI tools.</p>
            </>
          ) : (
            <>
              <h2 className="status-title">
                <span className="status-dot status-empty" aria-hidden="true" />
                Not initialized
              </h2>
              <p className="muted">Context will arrive from an authorized AI tool.</p>
            </>
          )}
        </div>
        {latestInitializationJob ? (
          <dl className="status-metrics">
            <div>
              <dt>Assets</dt>
              <dd>{latestInitializationJob.asset_count}</dd>
            </div>
            <div>
              <dt>Remote</dt>
              <dd>{latestInitializationJob.git_remote ?? "Not set"}</dd>
            </div>
            <div>
              <dt>Completed</dt>
              <dd>{latestInitializationJob.completed_at ? new Date(latestInitializationJob.completed_at).toLocaleString() : "In progress"}</dd>
            </div>
          </dl>
        ) : null}
        {latestInitializationJob?.error ? (
          <p className="alert">
            {typeof latestInitializationJob.error === "string"
              ? latestInitializationJob.error
              : latestInitializationJob.error.message}
          </p>
        ) : null}
        {latestInitializationJob?.warnings?.length ? (
          <div className="warning-list">
            <h3>Warnings</h3>
            <ul>
              {latestInitializationJob.warnings.map((warning) => (
                <li key={typeof warning === "string" ? warning : warning.code}>
                  {typeof warning === "string" ? warning : warning.message}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {latestInitializationJob?.status === "completed" ? (
          <Link className="button-link" href={`/projects/${project.id}/assets`}>
            View assets
          </Link>
        ) : null}
      </section>
      {initializationJobs.length ? (
        <section className="panel">
          <h2>Initialization history</h2>
          <div className="history-list">
            <div className="history-row initialization-history-row history-header">
              <span>Status</span>
              <span>Assets</span>
              <span>Warnings</span>
              <span>Completed</span>
            </div>
            {initializationJobs.map((job) => (
              <div className="history-row initialization-history-row" key={job.id}>
                <span>{job.status}</span>
                <span>{job.asset_count}</span>
                <span>{job.warnings.length}</span>
                <span>{job.completed_at ? new Date(job.completed_at).toLocaleString() : "In progress"}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
      <section className="grid">
        <Link className="panel" href={`/projects/${project.id}/work-items`}>
          <h2>Work items</h2>
          <p className="muted">Track AI-assisted tasks, sessions, context state, and review flow.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/status`}>
          <h2>Project status</h2>
          <p className="muted">Review work item progress, quality evidence, and pending approvals.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/pending`}>
          <h2>Pending</h2>
          <p className="muted">Approve context proposals and skill candidates waiting on you.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/operations`}>
          <h2>Operations summary</h2>
          <p className="muted">Review project governance, delivery, context, quality, and integration signal counts.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/assets`}>
          <h2>Assets</h2>
          <p className="muted">Browse normalized project assets.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/skills`}>
          <h2>Skills</h2>
          <p className="muted">Inspect built-in and project skills.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/knowledge`}>
          <h2>Knowledge</h2>
          <p className="muted">See the team knowledge accumulated in this project.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/context`}>
          <h2>Context</h2>
          <p className="muted">Inspect uploaded context state and provisional P1 material.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/sessions`}>
          <h2>Sessions</h2>
          <p className="muted">Trace AI agent work sessions.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/security`}>
          <h2>Security audit</h2>
          <p className="muted">Inspect sensitive governance approvals, denials, actors, and reasons.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/writebacks`}>
          <h2>Writebacks</h2>
          <p className="muted">Review generated knowledge drafts.</p>
        </Link>
      </section>
    </main>
  );
}
