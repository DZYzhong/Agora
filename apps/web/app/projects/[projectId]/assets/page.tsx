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
      <section className="grid">
        {assets.map((asset) => (
          <div className="panel" key={asset.id}>
            <h2>{asset.title}</h2>
            <p className="muted">{asset.type} / {asset.source}</p>
            <p className="muted">{asset.source_uri}</p>
            <p>{asset.summary ?? ""}</p>
          </div>
        ))}
        {assets.length === 0 ? (
          <div className="panel">
            <h2>No assets</h2>
            <p className="muted">Initialize the project from a local repository to create assets.</p>
          </div>
        ) : null}
      </section>
    </main>
  );
}
