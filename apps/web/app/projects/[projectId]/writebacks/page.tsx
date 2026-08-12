import { apiGet } from "../../../../lib/api";

type Writeback = {
  id: string;
  type: string;
  title: string;
  content: string;
  status: string;
  accepted_asset_id: string | null;
};

export default async function WritebacksPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  let writebacks: Writeback[] = [];
  try {
    writebacks = await apiGet<Writeback[]>(`/projects/${projectId}/writebacks`);
  } catch {
    writebacks = [];
  }

  return (
    <main className="page">
      <h1>Writebacks</h1>
      <p className="muted">Project {projectId}</p>
      <section className="grid">
        {writebacks.map((writeback) => (
          <div className="panel" key={writeback.id}>
            <div className="session-header">
              <div>
                <p className="eyebrow">{writeback.type === "development_update" ? "Development update" : writeback.type}</p>
                <h2>{writeback.title}</h2>
              </div>
              <span className="asset-type">{writeback.status}</span>
            </div>
            <pre className="writeback-content">{writeback.content}</pre>
            {writeback.accepted_asset_id ? <p className="asset-uri">Accepted asset: {writeback.accepted_asset_id}</p> : null}
            {writeback.status === "draft" ? (
              <div className="actions">
                <form action={`/projects/${projectId}/writebacks/${writeback.id}/accept`} method="post">
                  <button type="submit">Accept</button>
                </form>
                <form action={`/projects/${projectId}/writebacks/${writeback.id}/reject`} method="post">
                  <button className="secondary-button" type="submit">Reject</button>
                </form>
              </div>
            ) : null}
          </div>
        ))}
        {writebacks.length === 0 ? (
          <div className="panel">
            <h2>No writebacks</h2>
            <p className="muted">Draft writebacks will appear here after agent work.</p>
          </div>
        ) : null}
      </section>
    </main>
  );
}
