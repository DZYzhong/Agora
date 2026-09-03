import Link from "next/link";
import { apiGet } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { Badge, Card, EmptyState, Page, PageHeader } from "../../../../components/ui";

type Writeback = {
  id: string;
  type: string;
  title: string;
  content: string;
  status: string;
  accepted_asset_id: string | null;
};

function statusTone(status: string) {
  if (status === "accepted") return "green" as const;
  if (status === "rejected") return "red" as const;
  return "amber" as const;
}

export default async function WritebacksPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const lang = await currentLang();
  const zh = lang === "zh";

  let writebacks: Writeback[] = [];
  try {
    writebacks = await apiGet<Writeback[]>(`/projects/${projectId}/writebacks`);
  } catch {
    writebacks = [];
  }

  return (
    <Page>
      <PageHeader
        title={zh ? "写回草稿" : "Writebacks"}
        subtitle={
          zh
            ? "审阅 AI 生成的知识草稿，接受后入库为资产"
            : "Review AI-generated knowledge drafts before accepting them into the project."
        }
        meta={
          <span className="rounded-full bg-surface px-3 py-1 text-sm text-ink-2 ring-1 ring-inset ring-edge">
            {writebacks.length}
          </span>
        }
      />

      {writebacks.length === 0 ? (
        <EmptyState
          title={zh ? "还没有写回草稿" : "No writebacks yet"}
          hint={
            zh
              ? "AI 工具工作结束后产生的草稿会出现在这里。"
              : "Draft writebacks will appear here after agent work."
          }
        />
      ) : (
        <section className="mt-6 grid gap-4 lg:grid-cols-2">
          {writebacks.map((writeback) => (
            <Card key={writeback.id} className="flex flex-col">
              <div className="flex items-start justify-between gap-3 border-b border-edge-1 px-5 py-4">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-ink-3">
                    {writeback.type === "development_update"
                      ? zh
                        ? "开发更新"
                        : "Development update"
                      : writeback.type}
                  </p>
                  <h3 className="mt-0.5 truncate text-[15px] font-semibold text-ink">
                    {writeback.title}
                  </h3>
                </div>
                <Badge tone={statusTone(writeback.status)}>{writeback.status}</Badge>
              </div>
              <pre className="max-h-48 flex-1 overflow-auto whitespace-pre-wrap px-5 py-4 font-sans text-sm leading-relaxed text-ink-2">
                {writeback.content}
              </pre>
              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-edge-1 px-5 py-3">
                {writeback.accepted_asset_id ? (
                  <span className="truncate font-mono text-xs text-ink-3">
                    {zh ? "已接受资产" : "Accepted asset"}: {writeback.accepted_asset_id}
                  </span>
                ) : (
                  <span />
                )}
                {writeback.status === "draft" ? (
                  <div className="flex items-center gap-2">
                    <form action={`/projects/${projectId}/writebacks/${writeback.id}/accept`} method="post">
                      <button
                        type="submit"
                        className="rounded-lg bg-emerald-600 px-3.5 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700"
                      >
                        {zh ? "接受" : "Accept"}
                      </button>
                    </form>
                    <form action={`/projects/${projectId}/writebacks/${writeback.id}/reject`} method="post">
                      <button
                        type="submit"
                        className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink-2 hover:bg-red-50 hover:text-red-600"
                      >
                        {zh ? "拒绝" : "Reject"}
                      </button>
                    </form>
                  </div>
                ) : (
                  <Link
                    href={`/projects/${projectId}/writebacks`}
                    className="text-xs text-ink-3"
                  >
                    {writeback.status}
                  </Link>
                )}
              </div>
            </Card>
          ))}
        </section>
      )}
    </Page>
  );
}
