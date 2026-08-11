import Link from "next/link";
import { apiGet } from "../../lib/api";

type Project = {
  id: string;
  name: string;
  slug: string;
  git_remotes: string[];
};

export default async function ProjectsPage() {
  let projects: Project[] = [];
  try {
    projects = await apiGet<Project[]>("/projects");
  } catch {
    projects = [];
  }

  return (
    <main className="page">
      <h1>Projects</h1>
      <p className="muted">Configured Agora project spaces.</p>
      <section className="grid">
        {projects.map((project) => (
          <Link className="panel" href={`/projects/${project.id}`} key={project.id}>
            <h2>{project.name}</h2>
            <p className="muted">{project.slug}</p>
            <p className="muted">{project.git_remotes[0] ?? "No Git remote"}</p>
          </Link>
        ))}
        {projects.length === 0 ? (
          <div className="panel">
            <h2>No projects</h2>
            <p className="muted">Create a project through the API to inspect it here.</p>
          </div>
        ) : null}
      </section>
    </main>
  );
}
