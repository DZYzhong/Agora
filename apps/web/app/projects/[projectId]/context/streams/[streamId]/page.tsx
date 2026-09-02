import Link from "next/link";
import { apiGet } from "../../../../../../lib/api";

type Stream = {
  id: string;
  name: string;
  branch: string;
  status: string;
  head_revision_id: string | null;
  updated_at: string | null;
};

type Revision = {
  id: string;
  schema_version: string;
  parent_revision_id: string | null;
  commit_sha: string | null;
  content: Record<string, unknown>;
  source_anchors: Array<{ path?: string }>;
  created_at: string | null;
  is_head: boolean;
};

export default async function StreamRevisionsPage({
  params,
}: {
  params: Promise<{ projectId: string; streamId: string }>;
}) {
  const { projectId, streamId } = await params;
  let data: { stream: Stream; revisions: Revision[] } | null = null;
  try {
    data = await apiGet(`/projects/${projectId}/context/streams/${streamId}/revisions`);
  } catch {
    data = null;
  }

  if (!data) {
    return (
      <main className="page">
        <h1>Revision history</h1>
        <p className="alert">Unable to load revision history.</p>
      </main>
    );
  }

  const { stream, revisions } = data;
  const ordered = [...revisions].sort((a, b) => String(a.created_at).localeCompare(String(b.created_at) ?? "") || a.id.localeCompare(b.id));
  const serial = new Map(ordered.map((revision, index) => [revision.id, index + 1]));

  return (
    <main className="page">
      <h1>Context revision history</h1>
      <p className="muted">
        <Link href={`/projects/${projectId}/context`}>Context</Link> · {stream.name} · {stream.branch}
      </p>

      <section className="panel">
        <div className="session-header">
          <div>
            <p className="eyebrow">Stream</p>
            <h2>{stream.name} · {stream.branch}</h2>
          </div>
          <span className="asset-type">{stream.status}</span>
        </div>
        <p className="muted">
          Head revision: {stream.head_revision_id ? `#${serial.get(stream.head_revision_id) ?? stream.head_revision_id}` : "None"}
        </p>
      </section>

      <section className="panel">
        <h2>Versions</h2>
        {ordered.length ? (
          <div className="history-list">
            <div className="history-row history-header">
              <span>Version</span>
              <span>Commit</span>
              <span>Anchors</span>
              <span>Created</span>
              <span>Head</span>
            </div>
            {ordered.map((revision) => (
              <div className="history-row" key={revision.id}>
                <span>
                  <strong>#{serial.get(revision.id)}</strong>
                  <p className="asset-uri">{revision.id.slice(0, 8)} · {revision.schema_version}</p>
                </span>
                <span>{revision.commit_sha ?? "None"}</span>
                <span>{revision.source_anchors.length}</span>
                <span>{revision.created_at ? new Date(revision.created_at).toLocaleString() : "Unknown"}</span>
                <span>{revision.is_head ? "✓" : ""}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No accepted revisions yet for this stream.</p>
        )}
      </section>

      {ordered.length ? (
        <section className="panel">
          <h2>Content by version</h2>
          {ordered.map((revision) => (
            <details className="event-row" key={`content-${revision.id}`}>
              <summary>
                #{serial.get(revision.id)} · {revision.schema_version}
                {revision.is_head ? " · current head" : ""}
              </summary>
              <div className="writeback-content">
                <pre>{JSON.stringify(revision.content, null, 2)}</pre>
                {revision.source_anchors.length ? (
                  <p className="muted">
                    Anchors: {revision.source_anchors.map((anchor) => anchor.path).join(", ")}
                  </p>
                ) : null}
              </div>
            </details>
          ))}
        </section>
      ) : null}
    </main>
  );
}
