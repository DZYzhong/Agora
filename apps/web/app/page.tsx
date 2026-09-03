export default function Home() {
  return (
    <main className="page">
      <h1>Agora</h1>
      <p className="muted">Team AI Project Harness</p>
      <section className="grid">
        <div className="panel">
          <h2>Project Memory</h2>
          <p className="muted">Create projects and review what team AI tools have produced.</p>
        </div>
        <div className="panel">
          <h2>Harness Sessions</h2>
          <p className="muted">Trace how agents resolve project context and run skills.</p>
        </div>
        <div className="panel">
          <h2>Writebacks</h2>
          <p className="muted">Review AI-generated knowledge before it is accepted into the project.</p>
        </div>
      </section>
    </main>
  );
}
