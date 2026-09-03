import { cookies } from "next/headers";
import Link from "next/link";
import { apiGetWithSession } from "../../lib/api";
import { currentLang } from "../../lib/i18n";
import { Badge, Card, EmptyState, Page, PageHeader } from "../../components/ui";

type User = {
  id: string;
  org_id: string;
  username: string | null;
  display_name: string;
  status: string;
  created_at: string;
};

type UsersResponse = { users: User[] };

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";
const labelClass = "mb-1 block text-xs font-medium text-slate-500";

function sessionRequest(): Request {
  return new Request("http://web", {
    headers: { cookie: cookies().toString() },
  });
}

export default async function UsersPage({
  searchParams,
}: {
  searchParams: Promise<{
    activation_token?: string;
    reset_token?: string;
    username?: string;
    error?: string;
  }>;
}) {
  const params = await searchParams;
  const lang = await currentLang();
  const zh = lang === "zh";

  let users: User[] = [];
  let sessionError = false;
  try {
    const response = await apiGetWithSession<UsersResponse>(
      "/users?org_id=local-org",
      sessionRequest()
    );
    users = response.users;
  } catch {
    sessionError = true;
  }

  return (
    <Page>
      <PageHeader
        title={zh ? "用户" : "Users"}
        subtitle={
          zh
            ? "管理本地 Agora 账号。新用户会收到一次性激活令牌。"
            : "Manage local Agora accounts. New users receive a one-time activation token."
        }
        meta={
          <span className="rounded-full bg-white px-3 py-1 text-sm text-slate-500 ring-1 ring-inset ring-slate-200">
            {users.length}
          </span>
        }
      />

      {sessionError && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {zh ? "无法加载用户列表，请先登录：" : "Could not load users. Sign in first:"}{" "}
          <Link href="/login" className="font-semibold underline">
            {zh ? "登录" : "Sign in"}
          </Link>
        </div>
      )}
      {params.error ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {params.error}
        </div>
      ) : null}

      {params.activation_token && params.username ? (
        <Card className="mt-4 border-emerald-200 bg-emerald-50/60 p-5">
          <h2 className="text-sm font-semibold text-emerald-900">
            {zh ? "交付一次性激活令牌" : "Deliver this one-time activation token"}
          </h2>
          <p className="mt-1 text-sm text-emerald-800">
            {zh
              ? `请通过已认证的外部渠道将令牌发送给 ${params.username}。30 分钟有效且只能使用一次。`
              : `Send the following token to ${params.username} over an authenticated external channel. It expires in 30 minutes and can only be used once.`}
          </p>
          <pre className="mt-3 overflow-auto rounded-lg bg-white px-4 py-3 font-mono text-sm text-slate-800 ring-1 ring-inset ring-emerald-200">
            {params.activation_token}
          </pre>
        </Card>
      ) : null}

      {params.reset_token && params.username ? (
        <Card className="mt-4 border-blue-200 bg-blue-50/60 p-5">
          <h2 className="text-sm font-semibold text-blue-900">
            {zh ? "交付一次性重置令牌" : "Deliver this one-time reset token"}
          </h2>
          <p className="mt-1 text-sm text-blue-800">
            {zh
              ? `请通过已认证的外部渠道将令牌发送给 ${params.username}。15 分钟有效且只能使用一次。`
              : `Send the following token to ${params.username} over an authenticated external channel. It expires in 15 minutes and can only be used once.`}
          </p>
          <pre className="mt-3 overflow-auto rounded-lg bg-white px-4 py-3 font-mono text-sm text-slate-800 ring-1 ring-inset ring-blue-200">
            {params.reset_token}
          </pre>
        </Card>
      ) : null}

      <Card className="mt-6 p-5">
        <h2 className="text-sm font-semibold text-slate-900">{zh ? "创建用户" : "Create user"}</h2>
        <form action="/users/create" method="post" className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
          <label className="block">
            <span className={labelClass}>Username</span>
            <input name="username" placeholder="alice" required minLength={2} maxLength={64} className={inputClass} />
          </label>
          <label className="block">
            <span className={labelClass}>{zh ? "显示名" : "Display name"}</span>
            <input name="display_name" placeholder="Alice" required maxLength={128} className={inputClass} />
          </label>
          <button
            type="submit"
            className="self-end rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          >
            {zh ? "创建用户" : "Create user"}
          </button>
        </form>
      </Card>

      {users.length === 0 ? (
        <EmptyState
          title={zh ? "还没有用户" : "No users yet"}
          hint={zh ? "创建用户后，通过激活令牌交付登录。" : "Create users and deliver activation tokens to onboard them."}
        />
      ) : (
        <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {users.map((user) => (
            <Card key={user.id} className="flex flex-col p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-[15px] font-semibold text-slate-900">
                    {user.display_name}
                  </h3>
                  <p className="mt-0.5 truncate font-mono text-xs text-slate-400">
                    {user.username ?? "(no username)"}
                  </p>
                </div>
                <Badge tone={user.status === "active" ? "green" : "slate"}>{user.status}</Badge>
              </div>
              <p className="mt-1 font-mono text-[11px] text-slate-300">{user.id}</p>
              <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
                {user.status === "active" ? (
                  <form action="/users/disable" method="post">
                    <input type="hidden" name="user_id" value={user.id} />
                    <button
                      type="submit"
                      className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
                    >
                      {zh ? "禁用" : "Disable"}
                    </button>
                  </form>
                ) : (
                  <form action="/users/enable" method="post">
                    <input type="hidden" name="user_id" value={user.id} />
                    <button
                      type="submit"
                      className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700"
                    >
                      {zh ? "启用" : "Enable"}
                    </button>
                  </form>
                )}
                <form action="/users/reset" method="post">
                  <input type="hidden" name="user_id" value={user.id} />
                  <button
                    type="submit"
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
                  >
                    {zh ? "重置密码" : "Reset password"}
                  </button>
                </form>
              </div>
            </Card>
          ))}
        </section>
      )}
    </Page>
  );
}
