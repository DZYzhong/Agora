import Link from "next/link";
import { apiGet } from "../../../lib/api";

type Project = {
  id: string;
  name: string;
  slug: string;
  git_remotes: string[];
};

export default async function ProjectDetailPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const project = await apiGet<Project>(`/projects/${projectId}`);

  return (
    <main className="page">
      <h1>{project.name}</h1>
      <p className="muted">{project.slug}</p>
      <section className="grid">
        <Link className="panel" href={`/projects/${project.id}/assets`}>
          <h2>Assets</h2>
          <p className="muted">Browse normalized project assets.</p>
        </Link>
        <Link className="panel" href={`/projects/${project.id}/skills`}>
          <h2>Skills</h2>
          <p className="muted">Inspect built-in and project skills.</p>
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
