import { cookies } from "next/headers";
import Link from "next/link";
import { apiGetWithSession } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { relativeTime } from "../../../../lib/format";
import { Badge, Card, EmptyState, Page, PageHeader } from "../../../../components/ui";

type Credential = {
  id: string;
  user_id: string;
  kind: string;
  label: string | null;
  status: string;
  token_prefix: string;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
};

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-surface px-3 py-2 text-sm shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";
const labelClass = "mb-1 block text-xs font-medium text-ink-2";
function credentialKindLabel(kind: string, lang: "zh" | "en"): string {
  const label =
    kind === "human"
      ? { zh: "个人令牌", en: "Personal" }
      : kind === "agent"
        ? { zh: "Agent 令牌", en: "Agent" }
        : { zh: "CI 令牌", en: "CI" };
  return label[lang];
}

function sessionRequest(): Request {
  return new Request("http://web", {
    headers: { cookie: cookies().toString() },
  });
}

export default async function CredentialsPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId?: string; userId: string }>;
  searchParams: Promise<{
    issued?: string;
    rotated?: string;
    revoked?: string;
    token?: string;
    kind?: string;
    label?: string;
    error?: string;
  }>;
}) {
  const { userId } = await params;
  const query = await searchParams;
  const lang = await currentLang();
  const zh = lang === "zh";

  let credentials: Credential[] = [];
  let loadError = false;
  try {
    const data = await apiGetWithSession<Credential[]>(
      `/users/${userId}/credentials`,
      sessionRequest()
    );
    credentials = data;
  } catch {
    loadError = true;
  }

  return (
    <Page>
      <PageHeader
        title={zh ? "凭据管理" : "API credentials"}
        subtitle={
          zh ? "为 AI/CI 工具签发、轮换与吊销令牌" : "Issue, rotate and revoke tokens for AI and CI tools"
        }
        actions={
          <Link
            href="/users"
            className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm hover:bg-canvas"
          >
            ← {zh ? "返回用户" : "Back to users"}
          </Link>
        }
      />

      {loadError ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {zh ? "无法加载凭据（需要组织管理员登录）。" : "Could not load credentials (org admin session required)."}
        </div>
      ) : null}
      {query.error ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {zh ? "操作失败，请重试。" : "Action failed. Try again."} ({query.error})
        </div>
      ) : null}

      {query.token ? (
        <Card className="mt-4 border-amber-200 bg-amber-50/60 p-5">
          <h2 className="text-sm font-semibold text-amber-900">
            {query.rotated
              ? zh
                ? "已轮换——新令牌（只显示这一次）"
                : "Rotated — new token (shown once)"
              : zh
                ? "已签发——令牌（只显示这一次）"
                : "Issued — token (shown once)"}
          </h2>
          <p className="mt-1 text-sm text-amber-800">
            {zh
              ? `请立即保存并安全交付：${query.kind ?? ""} ${query.label ?? ""}`.trim()
              : `Save and deliver it securely now: ${query.kind ?? ""} ${query.label ?? ""}`.trim()}
          </p>
          <pre className="mt-3 select-all overflow-auto rounded-lg bg-surface px-4 py-3 font-mono text-sm text-ink ring-1 ring-inset ring-amber-200">
            {query.token}
          </pre>
        </Card>
      ) : null}

      <Card className="mt-6 p-5">
        <h2 className="text-sm font-semibold text-ink">{zh ? "签发令牌" : "Issue a token"}</h2>
        <form action={`/users/${userId}/credentials/issue`} method="post" className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1.2fr_auto]">
          <label className="block">
            <span className={labelClass}>{zh ? "类型" : "Kind"}</span>
            <select name="kind" className={inputClass} defaultValue="agent">
              <option value="human">{zh ? "个人（human）" : "Personal (human)"}</option>
              <option value="agent">Agent</option>
              <option value="ci">CI</option>
            </select>
          </label>
          <label className="block">
            <span className={labelClass}>{zh ? "标签" : "Label"}</span>
            <input name="label" placeholder={zh ? "如：CI runner" : "e.g. CI runner"} className={inputClass} />
          </label>
          <label className="block">
            <span className={labelClass}>{zh ? "过期时间（可选，ISO-8601）" : "Expires at (optional, ISO-8601)"}</span>
            <input name="expires_at" type="datetime-local" className={inputClass} />
          </label>
          <button
            type="submit"
            className="self-end rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          >
            {zh ? "签发" : "Issue"}
          </button>
        </form>
      </Card>

      <h2 className="mt-8 text-xs font-semibold uppercase tracking-wider text-ink-3">
        {zh ? "已签发令牌" : "Issued tokens"}
      </h2>
      {credentials.length === 0 ? (
        <EmptyState
          title={zh ? "还没有 API 令牌" : "No API tokens yet"}
          hint={zh ? "签发后，令牌哈希将在此列出（明文只显示一次）。" : "Issued tokens will be listed here (plaintext is shown only once)."}
        />
      ) : (
        <div className="mt-3 space-y-2">
          {credentials.map((credential) => (
            <Card key={credential.id} className="flex flex-wrap items-center gap-x-5 gap-y-2 px-5 py-3.5">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <Badge tone={credential.kind === "human" ? "blue" : credential.kind === "agent" ? "violet" : "slate"} dot={false}>
                    {credentialKindLabel(credential.kind, lang)}
                  </Badge>
                  <span className="truncate text-sm font-medium text-ink">
                    {credential.label ?? credential.kind}
                  </span>
                  <span className="font-mono text-xs text-ink-3">{credential.token_prefix}</span>
                </div>
                <p className="mt-0.5 font-mono text-[11px] text-ink-3">{credential.id}</p>
              </div>
              <div className="flex items-center gap-3 text-xs text-ink-3">
                <Badge tone={credential.status === "active" ? "green" : "slate"}>{credential.status}</Badge>
                {credential.expires_at ? (
                  <span>
                    {zh ? "过期" : "expires"}{" "}
                    <time dateTime={credential.expires_at}>{relativeTime(credential.expires_at, lang)}</time>
                  </span>
                ) : null}
                <span>
                  {zh ? "签发" : "created"}{" "}
                  <time dateTime={credential.created_at}>{relativeTime(credential.created_at, lang)}</time>
                </span>
              </div>
              <div className="flex items-center gap-2">
                {credential.status === "active" ? (
                  <>
                    <form action={`/users/${userId}/credentials/${credential.id}/rotate`} method="post">
                      <button
                        type="submit"
                        className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink-2 hover:bg-canvas"
                      >
                        {zh ? "轮换" : "Rotate"}
                      </button>
                    </form>
                    <form action={`/users/${userId}/credentials/${credential.id}/revoke`} method="post">
                      <button
                        type="submit"
                        className="rounded-lg border border-red-200 bg-surface px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
                      >
                        {zh ? "吊销" : "Revoke"}
                      </button>
                    </form>
                  </>
                ) : (
                  <span className="text-xs text-ink-3">
                    {credential.status === "revoked" ? (zh ? "已吊销" : "revoked") : credential.status}
                  </span>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </Page>
  );
}
