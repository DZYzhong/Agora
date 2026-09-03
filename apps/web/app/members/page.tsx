import { cookies } from "next/headers";
import Link from "next/link";
import { apiGetWithSession } from "../../lib/api";
import { currentLang } from "../../lib/i18n";
import { Badge, Card, EmptyState, Page, PageHeader, Table } from "../../components/ui";

type Member = {
  user: {
    id: string;
    org_id: string;
    username: string;
    display_name: string;
    status: string;
  };
  role: string;
};

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-surface px-3 py-2 text-sm shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";
const labelClass = "mb-1 block text-xs font-medium text-ink-2";

function sessionRequest(): Request {
  return new Request("http://web", {
    headers: { cookie: cookies().toString() },
  });
}

export default async function OrgMembersPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string; error?: string }>;
}) {
  const query = await searchParams;
  const lang = await currentLang();
  const zh = lang === "zh";

  let members: Member[] = [];
  let loadError = false;
  try {
    const data = await apiGetWithSession<Member[]>(
      "/organizations/local-org/members",
      sessionRequest()
    );
    members = data;
  } catch {
    loadError = true;
  }

  return (
    <Page>
      <PageHeader
        title={zh ? "组织成员" : "Organization members"}
        subtitle={zh ? "管理 local-org 的成员与组织角色" : "Manage members and roles of local-org"}
        meta={
          <span className="rounded-full bg-surface px-3 py-1 text-sm text-ink-2 ring-1 ring-inset ring-edge">
            {members.length}
          </span>
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
          {zh ? "无法加载成员（需要组织管理员会话）。" : "Could not load members (org admin session required)."}
        </div>
      ) : null}
      {query.error ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {zh ? "操作失败，请重试。" : "Action failed. Try again."} ({query.error})
        </div>
      ) : null}
      {query.ok ? (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {zh ? "操作成功。" : "Done."}
        </div>
      ) : null}

      <Card className="mt-6 p-5">
        <h2 className="text-sm font-semibold text-ink">{zh ? "添加成员" : "Add member"}</h2>
        <form action="/members/add" method="post" className="mt-4 grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className={labelClass}>{zh ? "用户名（或用户 ID）" : "Username (or user id)"}</span>
            <input name="username" placeholder="alice" className={inputClass} />
          </label>
          <label className="block">
            <span className={labelClass}>{zh ? "用户 ID" : "User id"}</span>
            <input name="user_id" placeholder={zh ? "（可选，二选一）" : "(optional, either one)"} className={inputClass} />
          </label>
          <label className="block">
            <span className={labelClass}>{zh ? "角色" : "Role"}</span>
            <select name="role" className={inputClass} defaultValue="member">
              <option value="member">{zh ? "成员" : "Member"}</option>
              <option value="admin">{zh ? "管理员" : "Admin"}</option>
            </select>
          </label>
          <button
            type="submit"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 sm:col-start-3"
          >
            {zh ? "添加" : "Add"}
          </button>
        </form>
      </Card>

      {members.length === 0 ? (
        <EmptyState title={zh ? "暂无成员" : "No members"} />
      ) : (
        <Card className="mt-6">
          <Table headers={[zh ? "用户" : "User", zh ? "角色" : "Role", zh ? "操作" : "Actions"]}>
            {members.map((member) => (
              <tr key={member.user.id} className="align-middle">
                <td className="px-5 py-3">
                  <span className="font-medium text-ink">{member.user.display_name}</span>
                  <span className="mt-0.5 block font-mono text-xs text-ink-3">
                    {member.user.username} · {member.user.id.slice(0, 8)}
                  </span>
                </td>
                <td className="px-5 py-3">
                  <Badge tone={member.role === "owner" ? "violet" : member.role === "admin" ? "blue" : "slate"} dot={false}>
                    {member.role}
                  </Badge>
                </td>
                <td className="px-5 py-3">
                  {member.role === "owner" ? (
                    <span className="text-xs text-ink-3">
                      {zh ? "owner 不可在此调整" : "owner is not adjustable here"}
                    </span>
                  ) : (
                    <div className="flex flex-wrap items-center gap-2">
                      <form action={`/members/${member.user.id}/role`} method="post" className="flex items-center gap-2">
                        <select
                          name="role"
                          defaultValue={member.role}
                          className="rounded-lg border border-slate-300 bg-surface px-2 py-1 text-sm shadow-sm outline-none"
                        >
                          <option value="member">{zh ? "成员" : "Member"}</option>
                          <option value="admin">{zh ? "管理员" : "Admin"}</option>
                        </select>
                        <button
                          type="submit"
                          className="rounded-lg border border-slate-300 bg-surface px-2.5 py-1 text-xs font-medium text-ink-2 hover:bg-canvas"
                        >
                          {zh ? "改角色" : "Set role"}
                        </button>
                      </form>
                      <form action={`/members/${member.user.id}/remove`} method="post">
                        <button
                          type="submit"
                          className="rounded-lg border border-red-200 bg-surface px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                        >
                          {zh ? "移除" : "Remove"}
                        </button>
                      </form>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </Table>
        </Card>
      )}
    </Page>
  );
}
