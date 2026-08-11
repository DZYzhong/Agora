import { apiGet } from "../../../../lib/api";

type Asset = {
  id: string;
  type: string;
  source: string;
  source_uri: string;
  title: string;
  summary: string | null;
};

export default async function AssetsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  let assets: Asset[] = [];
  try {
    assets = await apiGet<Asset[]>(`/projects/${projectId}/assets`);
  } catch {
    assets = [];
  }

  return (
    <main className="page">
      <h1>Assets</h1>
      <p className="muted">Project {projectId}</p>
      {assets.length === 0 ? (
        <div className="panel">
          <h2>No assets</h2>
          <p className="muted">Initialize the project from a local repository to create assets.</p>
        </div>
      ) : (
        <section className="asset-list" aria-label="Project assets">
          <div className="asset-row asset-header">
            <span>Path</span>
            <span>Type</span>
            <span>Summary</span>
          </div>
          {assets.map((asset) => (
            <div className="asset-row" key={asset.id}>
              <div>
                <strong className="asset-title">{asset.title}</strong>
                <p className="asset-uri">{asset.source_uri}</p>
              </div>
              <span className="asset-type">{asset.type}</span>
              <p className="asset-summary">{asset.summary ?? ""}</p>
            </div>
          ))}
        </section>
      )}
    </main>
  );
}
