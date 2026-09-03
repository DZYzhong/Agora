import Link from "next/link";
import { apiGet } from "../../../../../lib/api";
import { currentLang } from "../../../../../lib/i18n";
import { relativeTime } from "../../../../../lib/format";
import { Badge, Card, Page, PageHeader } from "../../../../../components/ui";

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
  const lang = await currentLang();
  const zh = lang === "zh";

  let asset: AssetDetail | null = null;
  try {
    asset = await apiGet(`/projects/${projectId}/assets/${assetId}`);
  } catch {
    asset = null;
  }

  if (!asset) {
    return (
      <Page>
        <PageHeader title={zh ? "资产" : "Asset"} />
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {zh ? "无法加载资产。" : "Unable to load asset."}
        </div>
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader
        title={asset.title}
        subtitle={asset.summary ?? undefined}
        meta={
          <span className="flex items-center gap-2">
            <Badge tone="violet" dot={false}>
              {asset.type}
            </Badge>
            <Badge tone="slate" dot={false}>
              {asset.source}
            </Badge>
          </span>
        }
        actions={
          <Link
            href={`/projects/${projectId}/assets`}
            className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm hover:bg-canvas"
          >
            ← {zh ? "返回资产列表" : "Back to assets"}
          </Link>
        }
      />

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-xs text-ink-3">
        <span>{asset.source_uri}</span>
        <span>
          {zh ? "哈希" : "Hash"} {asset.content_hash?.slice(0, 12) ?? "unknown"}
        </span>
        <span>
          {zh ? "创建于" : "Created"}{" "}
          {asset.created_at ? relativeTime(asset.created_at, lang) : "—"}
        </span>
      </div>

      <Card className="mt-6">
        <div className="border-b border-edge-1 px-5 py-3.5">
          <h2 className="text-sm font-semibold text-ink">{zh ? "内容" : "Content"}</h2>
        </div>
        <pre className="max-h-[36rem] overflow-auto whitespace-pre-wrap px-5 py-4 font-sans text-sm leading-relaxed text-ink">
          {asset.content}
        </pre>
      </Card>
    </Page>
  );
}
