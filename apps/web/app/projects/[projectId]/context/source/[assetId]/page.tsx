import Link from "next/link";
import { apiPost } from "../../../../../../lib/api";
import { currentLang } from "../../../../../../lib/i18n";
import { Card, Page, PageHeader } from "../../../../../../components/ui";

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
  const { projectId, assetId } = await params;
  const { session_id: sessionId, chunk_id: chunkId, start_line: startLine, end_line: endLine } = await searchParams;
  const lang = await currentLang();
  const zh = lang === "zh";

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
    <Page>
      <PageHeader
        title={zh ? "上下文来源" : "Context Source"}
        actions={
          <Link
            href={`/projects/${projectId}/context`}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
          >
            ← {zh ? "返回上下文" : "Back to context"}
          </Link>
        }
      />

      {error ? (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {source ? (
        <div className="mt-6 space-y-4">
          <Card className="p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{source.type}</p>
            <h2 className="mt-1 text-lg font-semibold text-slate-900">{source.title}</h2>
            <p className="mt-1 font-mono text-xs text-slate-400">
              {source.source_uri} · {source.asset_id}
            </p>
            {chunkId ? (
              <p className="mt-2 text-xs text-slate-500">
                {zh ? "从" : "Opened from"} {chunkId}
                {startLine && endLine ? ` · lines ${startLine}-${endLine}` : ""}
              </p>
            ) : null}
            {source.truncated ? (
              <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                {zh ? "内容已被 token 预算截断。" : "Content truncated by token budget."}
              </div>
            ) : null}
          </Card>
          <Card>
            <div className="border-b border-slate-100 px-5 py-3.5">
              <h3 className="text-sm font-semibold text-slate-900">{zh ? "内容" : "Content"}</h3>
            </div>
            <pre className="max-h-[40rem] overflow-auto whitespace-pre-wrap px-5 py-4 font-sans text-sm leading-relaxed text-slate-700">
              {source.content}
            </pre>
          </Card>
        </div>
      ) : null}
    </Page>
  );
}
