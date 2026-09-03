import Link from "next/link";
import { apiGet } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { Badge, EmptyState, Page, PageHeader, Table } from "../../../../components/ui";

type Asset = {
  id: string;
  type: string;
  source: string;
  source_uri: string;
  title: string;
  summary: string | null;
  created_at: string;
};

function typeTone(type: string) {
  const lower = type.toLowerCase();
  if (lower.includes("doc") || lower.includes("design")) return "violet" as const;
  if (lower.includes("code") || lower.includes("src")) return "blue" as const;
  if (lower.includes("test")) return "green" as const;
  return "slate" as const;
}

export default async function AssetsPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ type?: string; source?: string }>;
}) {
  const { projectId } = await params;
  const filters = await searchParams;
  const lang = await currentLang();
  const zh = lang === "zh";

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

  const pillClass = (active: boolean) =>
    active
      ? "rounded-full bg-blue-600 px-3 py-1 text-sm font-medium text-white"
      : "rounded-full bg-white px-3 py-1 text-sm font-medium text-slate-600 ring-1 ring-inset ring-slate-200 hover:bg-slate-50";

  return (
    <Page>
      <PageHeader
        title={zh ? "资产" : "Assets"}
        subtitle={zh ? "归一化后的项目资产" : "Normalized project assets"}
        meta={
          <span className="rounded-full bg-white px-3 py-1 text-sm text-slate-500 ring-1 ring-inset ring-slate-200">
            {filtered.length} / {assets.length}
          </span>
        }
      />

      {assets.length ? (
        <div className="mt-6 flex flex-wrap items-center gap-2">
          <Link href={`/projects/${projectId}/assets`} className={pillClass(!filters.type && !filters.source)}>
            {zh ? "全部" : "All"}
          </Link>
          {types.map((type) => (
            <Link
              key={type}
              href={`/projects/${projectId}/assets?type=${encodeURIComponent(type)}`}
              className={pillClass(filters.type === type)}
            >
              {type}
            </Link>
          ))}
          {sources.length > 1
            ? sources.map((source) => (
                <Link
                  key={source}
                  href={`/projects/${projectId}/assets?source=${encodeURIComponent(source)}`}
                  className={pillClass(filters.source === source)}
                >
                  {source}
                </Link>
              ))
            : null}
        </div>
      ) : null}

      {filtered.length === 0 ? (
        <EmptyState
          title={zh ? "没有匹配的资产" : "No assets match the current filters"}
          hint={
            zh
              ? "由已授权 AI 工具上传的资产会显示在这里。"
              : "Assets uploaded by authorized AI tools will appear here."
          }
        />
      ) : (
        <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <Table headers={[zh ? "路径" : "Path", zh ? "类型" : "Type", zh ? "摘要" : "Summary"]}>
            {filtered.map((asset) => (
              <tr key={asset.id} className="transition hover:bg-slate-50">
                <td className="px-5 py-3.5">
                  <Link href={`/projects/${projectId}/assets/${asset.id}`} className="block max-w-md">
                    <span className="font-medium text-slate-900 hover:text-blue-700">
                      {asset.title}
                    </span>
                    <span className="mt-0.5 block truncate font-mono text-xs text-slate-400">
                      {asset.source_uri}
                    </span>
                  </Link>
                </td>
                <td className="px-5 py-3.5">
                  <Badge tone={typeTone(asset.type)}>{asset.type}</Badge>
                </td>
                <td className="max-w-md px-5 py-3.5">
                  <p className="line-clamp-2 text-sm text-slate-500">{asset.summary ?? ""}</p>
                </td>
              </tr>
            ))}
          </Table>
        </section>
      )}
    </Page>
  );
}
