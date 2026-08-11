export default async function AssetsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  return (
    <main className="page">
      <h1>Assets</h1>
      <p className="muted">Project {projectId}</p>
      <div className="panel">
        <h2>Asset browser</h2>
        <p className="muted">P0 backend stores assets; list API wiring follows the core ingestion path.</p>
      </div>
    </main>
  );
}
