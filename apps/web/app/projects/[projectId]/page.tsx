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
  repo_path: string;
  git_remote: string | null;
  status: "running" | "completed" | "failed" | string;
  asset_count: number;
  error: string | null;
  warnings: string[];
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
  const { init_error: initError } = await searchParams;
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
              <p className="muted">{latestInitializationJob.repo_path}</p>
            </>
          ) : (
            <>
              <h2 className="status-title">
                <span className="status-dot status-empty" aria-hidden="true" />
                Not initialized
              </h2>
              <p className="muted">Initialize from a local repository to build Agora assets.</p>
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
        {latestInitializationJob?.error ? <p className="alert">{latestInitializationJob.error}</p> : null}
        {latestInitializationJob?.status === "completed" ? (
          <Link className="button-link" href={`/projects/${project.id}/assets`}>
            View assets
          </Link>
        ) : null}
      </section>
      <form className="panel form" action={`/projects/${project.id}/initialize`} method="post">
        <h2>Initialize from local repository</h2>
        {initError ? <p className="alert">{initError}</p> : null}
        <label>
          Repository path
          <input name="repo_path" placeholder="/Users/daniel/Documents/Agora/.worktrees/agora-p0/tests/fixtures/sample_repo" required />
        </label>
        <button type="submit">Initialize</button>
      </form>
      <section className="grid">
        <Link className="panel" href={`/projects/${project.id}/assets`}>
          <h2>Assets</h2>
          <p className="muted">Browse normalized project assets.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/skills`}>
          <h2>Skills</h2>
          <p className="muted">Inspect built-in and project skills.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/context`}>
          <h2>Context</h2>
          <p className="muted">Run the same context planning flow used by agents.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/sessions`}>
          <h2>Sessions</h2>
          <p className="muted">Trace AI agent work sessions.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/writebacks`}>
          <h2>Writebacks</h2>
          <p className="muted">Review generated knowledge drafts.</p>
        </Link>
      </section>
    </main>
  );
}
