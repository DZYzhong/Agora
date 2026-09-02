import Link from "next/link";
import { apiGet } from "../../../../../lib/api";

type AssetDetail = {
  id: string;
  type: string;
  source: string;
  source_uri: string;
  title: string;
  summary: string | null;
  content: string;
  content_hash: string | null;
  created_at: string | null;
};

export default async function AssetDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; assetId: string }>;
}) {
  const { projectId, assetId } = await params;
  let asset: AssetDetail | null = null;
  try {
    asset = await apiGet(`/projects/${projectId}/assets/${assetId}`);
  } catch {
    asset = null;
  }

  if (!asset) {
    return (
      <main className="page">
        <h1>Asset</h1>
        <p className="alert">Unable to load asset.</p>
      </main>
    );
  }

  return (
    <main className="page">
      <div className="session-header">
        <div>
          <p className="eyebrow">{asset.type} · {asset.source}</p>
          <h1>{asset.title}</h1>
        </div>
        <span className="asset-type">{asset.source_uri}</span>
      </div>
      {asset.summary ? <p className="muted">{asset.summary}</p> : null}
      <section className="panel">
        <h2>Content</h2>
        <pre className="writeback-content">{asset.content}</pre>
      </section>
      <p className="muted">
        Hash {asset.content_hash?.slice(0, 12) ?? "unknown"} · Created {asset.created_at ? new Date(asset.created_at).toLocaleString() : "Unknown"}
      </p>
      <div className="actions">
        <Link className="button-link secondary-link" href={`/projects/${projectId}/assets`}>
          Back to assets
        </Link>
      </div>
    </main>
  );
}
