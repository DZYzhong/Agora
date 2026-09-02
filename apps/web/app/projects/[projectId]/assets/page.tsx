import Link from "next/link";
import { apiGet } from "../../../../lib/api";

type Asset = {
  id: string;
  type: string;
  source: string;
  source_uri: string;
  title: string;
  summary: string | null;
};

export default async function AssetsPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ type?: string; source?: string }>;
}) {
  const { projectId } = await params;
  const filters = await searchParams;
  let assets: Asset[] = [];
  try {
    assets = await apiGet<Asset[]>(`/projects/${projectId}/assets`);
  } catch {
    assets = [];
  }
  const filtered = assets.filter(
    (asset) =>
      (!filters.type || asset.type === filters.type) &&
      (!filters.source || asset.source === filters.source)
  );
  const types = Array.from(new Set(assets.map((asset) => asset.type))).sort();
  const sources = Array.from(new Set(assets.map((asset) => asset.source))).sort();

  return (
    <main className="page">
      <h1>Assets</h1>
      <p className="muted">Project {projectId}</p>
      {assets.length ? (
        <div className="actions">
          <Link className="button-link secondary-link" href={`/projects/${projectId}/assets`}>All</Link>
          {types.map((type) => (
            <Link key={type} className="button-link secondary-link" href={`/projects/${projectId}/assets?type=${encodeURIComponent(type)}`}>
              {type}
            </Link>
          ))}
        </div>
      ) : null}
      {filtered.length === 0 ? (
        <div className="panel">
          <h2>No assets</h2>
          <p className="muted">No assets match the current filters. Initialize the project from a local repository to create assets.</p>
        </div>
      ) : (
        <section className="asset-list" aria-label="Project assets">
          <div className="asset-row asset-header">
            <span>Path</span>
            <span>Type</span>
            <span>Summary</span>
          </div>
          {filtered.map((asset) => (
            <div className="asset-row" key={asset.id}>
              <div>
                <Link href={`/projects/${projectId}/assets/${asset.id}`}><strong className="asset-title">{asset.title}</strong></Link>
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
