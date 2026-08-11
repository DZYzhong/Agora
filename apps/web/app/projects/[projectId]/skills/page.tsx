const SKILLS = ["task-context-summary", "impact-analysis", "test-case-generation", "risk-check", "knowledge-writeback"];

export default async function SkillsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  return (
    <main className="page">
      <h1>Skills</h1>
      <p className="muted">Project {projectId}</p>
      <section className="grid">
        {SKILLS.map((skill) => (
          <div className="panel" key={skill}>
            <h2>{skill}</h2>
            <p className="muted">approved system skill</p>
          </div>
        ))}
      </section>
    </main>
  );
}
