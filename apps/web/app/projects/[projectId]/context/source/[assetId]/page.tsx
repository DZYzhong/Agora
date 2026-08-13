import { apiPost } from "../../../../../../lib/api";

type SourceRef = {
  asset_id: string;
  title: string;
  source_uri: string;
  type: string;
  content: string;
  truncated: boolean;
  metadata: Record<string, unknown>;
};

export default async function ContextSourcePage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string; assetId: string }>;
  searchParams: Promise<{ session_id?: string; chunk_id?: string; start_line?: string; end_line?: string }>;
}) {
  const { assetId } = await params;
  const {
    session_id: sessionId,
    chunk_id: chunkId,
    start_line: startLine,
    end_line: endLine,
  } = await searchParams;
  let source: SourceRef | null = null;
  let error: string | null = null;

  if (!sessionId) {
    error = "Missing session_id";
  } else {
    try {
      source = await apiPost<SourceRef>("/harness/fetch-context-ref", {
        session_id: sessionId,
        asset_id: assetId,
        max_tokens: 4000,
      });
    } catch (caught) {
      error = caught instanceof Error ? caught.message : "Source fetch failed";
    }
  }

  return (
    <main className="page">
      <h1>Context Source</h1>
      {error ? <p className="alert">{error}</p> : null}
      {source ? (
        <section className="context-result">
          <div className="panel">
            <p className="eyebrow">{source.type}</p>
            <h2>{source.title}</h2>
            <p className="muted">{source.source_uri}</p>
            <p className="muted">{source.asset_id}</p>
            {chunkId ? (
              <p className="source-meta">
                Opened from {chunkId}
                {startLine && endLine ? ` · lines ${startLine}-${endLine}` : ""}
              </p>
            ) : null}
            {source.truncated ? <p className="alert">Content truncated by token budget.</p> : null}
          </div>
          <div className="panel">
            <p className="eyebrow">Content</p>
            <pre className="context-summary">{source.content}</pre>
          </div>
        </section>
      ) : null}
    </main>
  );
}
