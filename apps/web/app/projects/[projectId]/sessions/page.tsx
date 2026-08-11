export default async function SessionsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  return (
    <main className="page">
      <h1>Sessions</h1>
      <p className="muted">Project {projectId}</p>
      <div className="panel">
        <h2>Agent work sessions</h2>
        <p className="muted">Harness sessions created by MCP/API calls will be listed here.</p>
      </div>
    </main>
  );
}
