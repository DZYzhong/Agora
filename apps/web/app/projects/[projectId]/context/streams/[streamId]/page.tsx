import Link from "next/link";
import { apiGet } from "../../../../../../lib/api";
import { currentLang } from "../../../../../../lib/i18n";
import { relativeTime } from "../../../../../../lib/format";
import { Badge, Card, EmptyState, Page, PageHeader, Table } from "../../../../../../components/ui";

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
  const lang = await currentLang();
  const zh = lang === "zh";

  let data: { stream: Stream; revisions: Revision[] } | null = null;
  try {
    data = await apiGet(`/projects/${projectId}/context/streams/${streamId}/revisions`);
  } catch {
    data = null;
  }

  if (!data) {
    return (
      <Page>
        <PageHeader title={zh ? "修订历史" : "Revision history"} />
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {zh ? "无法加载修订历史。" : "Unable to load revision history."}
        </div>
      </Page>
    );
  }

  const { stream, revisions } = data;
  const ordered = [...revisions].sort(
    (a, b) =>
      String(a.created_at).localeCompare(String(b.created_at) ?? "") || a.id.localeCompare(b.id)
  );
  const serial = new Map(ordered.map((revision, index) => [revision.id, index + 1]));

  return (
    <Page>
      <PageHeader
        title={zh ? "上下文修订历史" : "Context revision history"}
        subtitle={
          <span className="text-sm text-ink-2">
            <Link href={`/projects/${projectId}/context`} className="text-blue-600 hover:underline">
              {zh ? "上下文" : "Context"}
            </Link>{" "}
            · {stream.name} · <span className="font-mono">{stream.branch}</span>
          </span>
        }
      />

      <Card className="mt-6 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-3">{zh ? "流" : "Stream"}</p>
            <h2 className="mt-0.5 text-lg font-semibold text-ink">
              {stream.name} · <span className="font-mono text-base">{stream.branch}</span>
            </h2>
          </div>
          <Badge tone={stream.status === "active" ? "green" : "slate"}>{stream.status}</Badge>
        </div>
        <p className="mt-2 text-sm text-ink-2">
          {zh ? "Head 修订：" : "Head revision:"}{" "}
          <span className="font-mono text-xs">
            {stream.head_revision_id
              ? `#${serial.get(stream.head_revision_id) ?? stream.head_revision_id}`
              : zh
                ? "无"
                : "None"}
          </span>
        </p>
      </Card>

      {ordered.length ? (
        <Card className="mt-6">
          <Table
            headers={[
              zh ? "版本" : "Version",
              zh ? "提交" : "Commit",
              zh ? "锚点" : "Anchors",
              zh ? "创建" : "Created",
              zh ? "Head" : "Head",
            ]}
          >
            {ordered.map((revision) => (
              <tr key={revision.id} className="transition hover:bg-canvas">
                <td className="px-5 py-3">
                  <span className="font-semibold text-ink">#{serial.get(revision.id)}</span>
                  <span className="mt-0.5 block font-mono text-xs text-ink-3">
                    {revision.id.slice(0, 8)} · {revision.schema_version}
                  </span>
                </td>
                <td className="px-5 py-3 font-mono text-xs text-ink-2">
                  {revision.commit_sha ?? "—"}
                </td>
                <td className="px-5 py-3 text-ink">{revision.source_anchors.length}</td>
                <td className="px-5 py-3 text-sm text-ink-3">
                  {revision.created_at ? relativeTime(revision.created_at, lang) : "—"}
                </td>
                <td className="px-5 py-3">
                  {revision.is_head ? (
                    <Badge tone="green" dot={false}>
                      ✓ {zh ? "当前 head" : "head"}
                    </Badge>
                  ) : (
                    <span className="text-slate-200">—</span>
                  )}
                </td>
              </tr>
            ))}
          </Table>
        </Card>
      ) : (
        <EmptyState
          title={zh ? "此流还没有已接受的修订" : "No accepted revisions yet for this stream"}
        />
      )}

      {ordered.length ? (
        <Card className="mt-6">
          <div className="border-b border-edge-1 px-5 py-3.5">
            <h2 className="text-sm font-semibold text-ink">
              {zh ? "各版本内容" : "Content by version"}
            </h2>
          </div>
          <div className="divide-y divide-edge-1">
            {ordered.map((revision) => (
              <details key={`content-${revision.id}`} className="group px-5">
                <summary className="flex cursor-pointer list-none items-center gap-2 py-3 text-sm font-medium text-ink hover:text-blue-700">
                  <span className="text-ink-3 transition group-open:rotate-90">›</span>
                  #{serial.get(revision.id)} · {revision.schema_version}
                  {revision.is_head ? (
                    <Badge tone="green" dot={false}>
                      {zh ? "当前 head" : "head"}
                    </Badge>
                  ) : null}
                </summary>
                <div className="pb-4">
                  <pre className="max-h-96 overflow-auto rounded-lg bg-canvas p-3 text-xs text-ink-2">
                    {JSON.stringify(revision.content, null, 2)}
                  </pre>
                  {revision.source_anchors.length ? (
                    <p className="mt-2 text-xs text-ink-3">
                      {zh ? "锚点" : "Anchors"}:{" "}
                      {revision.source_anchors
                        .map((anchor) => anchor.path)
                        .filter(Boolean)
                        .join(", ")}
                    </p>
                  ) : null}
                </div>
              </details>
            ))}
          </div>
        </Card>
      ) : null}
    </Page>
  );
}
