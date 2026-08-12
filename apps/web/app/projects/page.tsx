import Link from "next/link";
import { apiGet } from "../../lib/api";

type Project = {
  id: string;
  name: string;
  slug: string;
  git_remotes: string[];
  status: string;
};

export default async function ProjectsPage({ searchParams }: { searchParams: Promise<{ include_archived?: string }> }) {
  const { include_archived: includeArchivedParam } = await searchParams;
  const includeArchived = includeArchivedParam === "true";
  let projects: Project[] = [];
  try {
    projects = await apiGet<Project[]>(includeArchived ? "/projects?include_archived=true" : "/projects");
  } catch {
    projects = [];
  }

  return (
    <main className="page">
      <h1>Projects</h1>
      <p className="muted">Configured Agora project spaces.</p>
      <div className="actions">
        <a className="button-link secondary-link" href={includeArchived ? "/projects" : "/projects?include_archived=true"}>
          {includeArchived ? "Hide archived" : "Show archived"}
        </a>
      </div>
      <form className="panel form" action="/projects/create" method="post">
        <h2>Create project</h2>
        <label>
          Organization
          <input name="org_id" defaultValue="local-org" required />
        </label>
        <label>
          Project name
          <input name="name" placeholder="Payment Service" required />
        </label>
        <label>
          Slug
          <input name="slug" placeholder="payment-service" required />
        </label>
        <label>
          Git remote
          <input name="git_remote" placeholder="git@example.com:team/payment.git" />
        </label>
        <button type="submit">Create</button>
      </form>
      <section className="grid">
        {projects.map((project) => (
          <article className="panel" key={project.id}>
            <div className="session-header">
              <div>
                <Link href={`/projects/${project.id}`}>
                  <h2>{project.name}</h2>
                </Link>
                <p className="muted">{project.slug}</p>
                <p className="muted">{project.git_remotes[0] ?? "No Git remote"}</p>
              </div>
              <span className="asset-type">{project.status}</span>
            </div>
            {project.status !== "archived" ? (
              <form className="inline-form" action={`/projects/${project.id}/archive`} method="post">
                <button className="secondary-button" type="submit">Archive</button>
              </form>
            ) : null}
          </article>
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
