import { apiGet } from "../../../../lib/api";

type Skill = {
  id: string;
  slug: string;
  name: string;
  status: string;
  definition: {
    version?: string;
    triggers?: string[];
    input_schema?: Record<string, unknown>;
    instructions?: string;
    builtin?: boolean;
  };
  builtin: boolean;
};

type SkillRun = {
  id: string;
  skill_id: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  warnings: string[];
  status: string;
  created_at: string;
};

export default async function SkillsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  let skills: Skill[] = [];
  let runs: SkillRun[] = [];
  try {
    [skills, runs] = await Promise.all([
      apiGet<Skill[]>(`/projects/${projectId}/skills`),
      apiGet<SkillRun[]>(`/projects/${projectId}/skill-runs`),
    ]);
  } catch {
    skills = [];
    runs = [];
  }
  const skillNames = new Map(skills.map((skill) => [skill.id, skill.name]));

  return (
    <main className="page">
      <h1>Skills</h1>
      <p className="muted">Project {projectId}</p>
      <section className="panel form">
        <h2>Create skill</h2>
        <form action={`/projects/${projectId}/skills/create`} method="post">
          <label>
            Slug
            <input name="slug" placeholder="release-risk-review" required />
          </label>
          <label>
            Name
            <input name="name" placeholder="Release Risk Review" required />
          </label>
          <label>
            Version
            <input name="version" defaultValue="0.1.0" />
          </label>
          <label>
            Triggers
            <input name="triggers" placeholder="release, risk, rollback" />
          </label>
          <label>
            Instructions
            <textarea name="instructions" placeholder="Review release risk and produce concise findings." required />
          </label>
          <button type="submit">Create candidate</button>
        </form>
      </section>
      <section className="skill-list">
        {skills.map((skill) => (
          <article className="panel" key={skill.id}>
            <div className="session-header">
              <div>
                <p className="eyebrow">{skill.builtin ? "Built-in" : "Project skill"}</p>
                <h2>{skill.name}</h2>
                <p className="asset-uri">{skill.slug}</p>
              </div>
              <span className="asset-type">{skill.status}</span>
            </div>
            <dl className="status-metrics">
              <div>
                <dt>Version</dt>
                <dd>{skill.definition.version ?? "Not set"}</dd>
              </div>
              <div>
                <dt>Triggers</dt>
                <dd>{skill.definition.triggers?.join(", ") || "Not set"}</dd>
              </div>
              <div>
                <dt>Runs</dt>
                <dd>{runs.filter((run) => run.skill_id === skill.id).length}</dd>
              </div>
            </dl>
            {skill.definition.instructions ? <p className="asset-summary">{skill.definition.instructions}</p> : null}
            {!skill.builtin ? (
              <form className="inline-form" action={`/projects/${projectId}/skills/${skill.id}/update`} method="post">
                <input name="name" defaultValue={skill.name} />
                <input name="version" defaultValue={skill.definition.version ?? ""} />
                <input name="triggers" defaultValue={skill.definition.triggers?.join(", ") ?? ""} />
                <input name="instructions" defaultValue={skill.definition.instructions ?? ""} />
                <select name="status" defaultValue={skill.status}>
                  <option value="candidate">candidate</option>
                  <option value="draft">draft</option>
                  <option value="approved">approved</option>
                  <option value="deprecated">deprecated</option>
                </select>
                <button type="submit">Save</button>
              </form>
            ) : null}
            <div className="actions">
              {!skill.builtin && skill.status !== "approved" ? (
                <form action={`/projects/${projectId}/skills/${skill.id}/approve`} method="post">
                  <button type="submit">Approve</button>
                </form>
              ) : null}
              {!skill.builtin && skill.status !== "deprecated" ? (
                <form action={`/projects/${projectId}/skills/${skill.id}/deprecate`} method="post">
                  <button type="submit">Deprecate</button>
                </form>
              ) : null}
              <form className="inline-form" action={`/projects/${projectId}/skills/${skill.id}/run`} method="post">
                <input name="summary" placeholder="Context summary for this run" />
                <button type="submit">Run</button>
              </form>
            </div>
          </article>
        ))}
      </section>
      <section className="panel">
        <h2>Skill runs</h2>
        {runs.length ? (
          <div className="event-list">
            {runs.map((run) => (
              <div className="event-row" key={run.id}>
                <strong>{skillNames.get(run.skill_id) ?? run.skill_id}</strong>
                <p className="asset-uri">{run.status} · {new Date(run.created_at).toLocaleString()}</p>
                <pre>{JSON.stringify({ input: run.input, output: run.output, warnings: run.warnings }, null, 2)}</pre>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No skill runs recorded.</p>
        )}
      </section>
    </main>
  );
}
