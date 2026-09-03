import { cookies } from "next/headers";
import Link from "next/link";
import { apiGetWithSession } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { Badge, Card, EmptyState, Page, PageHeader, Table } from "../../../../components/ui";

type Member = {
  user: {
    id: string;
    org_id: string;
    username: string | null;
    display_name: string;
    status: string;
  };
  role: string;
};

type OrgUser = {
  id: string;
  org_id: string;
  username: string | null;
  display_name: string;
  status: string;
};

type UserDirectory = { users: OrgUser[] };

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-surface px-3 py-2 text-sm shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";
const labelClass = "mb-1 block text-xs font-medium text-ink-2";

const PROJECT_ROLES = [
  "owner",
  "admin",
  "reviewer",
  "pm",
  "quality",
  "developer",
  "viewer",
];

function sessionRequest(): Request {
  return new Request("http://web", {
    headers: { cookie: cookies().toString() },
  });
}

function roleTone(role: string): "violet" | "blue" | "green" | "amber" | "slate" {
  if (role === "owner") return "violet";
  if (role === "admin") return "blue";
  if (role === "reviewer" || role === "quality") return "green";
  if (role === "pm" || role === "developer") return "amber";
  return "slate";
}

function memberErrorText(
  code: string | undefined,
  msg: string | undefined,
  zh: boolean
): string | null {
  if (!code) return null;
  const known: Record<string, [string, string]> = {
    USER_NOT_FOUND: [
      "用户不存在（检查用户名或用户 ID 是否正确）",
      "User not found (check the username or user id)",
    ],
    IDENTIFIER_REQUIRED: [
      "必须填写用户名或用户 ID 之一",
      "Provide exactly one of username or user id",
    ],
    USER_NOT_IN_ORG: ["该用户不属于本组织", "User is not a member of this organization"],
    ROLE_NOT_ALLOWED: ["该角色不允许", "Role not allowed"],
    ORG_ADMIN_REQUIRED: ["需要组织管理员权限", "Organization admin required"],
    PROJECT_MANAGER_REQUIRED: [
      "需要项目 owner/admin 或组织管理员权限",
      "Project owner/admin or organization admin required",
    ],
    add_failed: ["添加成员失败", "Failed to add member"],
    role_failed: ["修改角色失败", "Failed to update role"],
    remove_failed: ["移除成员失败", "Failed to remove member"],
  };
  const entry = known[code];
  if (entry) return entry[zh ? 0 : 1];
  return msg && msg !== code ? msg : code;
}

export default async function ProjectMembersPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ ok?: string; error?: string; msg?: string }>;
}) {
  const { projectId } = await params;
  const query = await searchParams;
  const lang = await currentLang();
  const zh = lang === "zh";

  let members: Member[] = [];
  let loadError = false;
  try {
    const data = await apiGetWithSession<Member[]>(
      `/projects/${projectId}/members`,
      sessionRequest()
    );
    members = data;
  } catch {
    loadError = true;
  }

  // Org user directory powers the add-member picker so users WITHOUT a
  // username (e.g. the bootstrap agent identity) remain selectable. Listing
  // requires an org-admin session; when unavailable we fall back to manual
  // username/user_id inputs.
  let directory: OrgUser[] | null = null;
  try {
    const dir = await apiGetWithSession<UserDirectory>("/users", sessionRequest());
    directory = dir.users;
  } catch {
    directory = null;
  }

  return (
    <Page>
      <PageHeader
        title={zh ? "项目成员" : "Project members"}
        subtitle={zh ? "管理本项目成员与角色" : "Manage project members and roles"}
        actions={
          <Link
            href={`/projects/${projectId}`}
            className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm hover:bg-canvas"
          >
            ← {zh ? "返回项目" : "Back to project"}
          </Link>
        }
      />

      {loadError ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {zh ? "无法加载成员（需要项目 owner/admin 或组织管理员会话）。" : "Could not load members (project owner/admin or org admin session required)."}
        </div>
      ) : null}
      {query.error ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {memberErrorText(query.error, query.msg, zh)}
        </div>
      ) : null}
      {query.ok ? (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {zh ? "操作成功。" : "Done."}
        </div>
      ) : null}

      <Card className="mt-6 p-5">
        <h2 className="text-sm font-semibold text-ink">{zh ? "添加成员" : "Add member"}</h2>
        <form action={`/projects/${projectId}/members/add`} method="post" className="mt-4 grid gap-3 sm:grid-cols-3">
          {directory !== null ? (
            <label className="block sm:col-span-2">
              <span className={labelClass}>{zh ? "从用户列表选择（含无用户名用户）" : "Choose a user (users without a username are included)"}</span>
              <select name="user_id" className={inputClass} defaultValue="">
                <option value="" disabled>
                  {zh ? "— 选择用户 —" : "— choose a user —"}
                </option>
                {directory.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.username
                      ? `${user.username}（${user.display_name}）`
                      : `${user.display_name}（${zh ? "无用户名" : "no username"}）`}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <>
              <label className="block">
                <span className={labelClass}>{zh ? "用户名（或用户 ID）" : "Username (or user id)"}</span>
                <input name="username" placeholder="alice" className={inputClass} />
              </label>
              <label className="block">
                <span className={labelClass}>{zh ? "用户 ID" : "User id"}</span>
                <input name="user_id" placeholder={zh ? "（可选，二选一）" : "(optional, either one)"} className={inputClass} />
              </label>
            </>
          )}
          <label className="block">
            <span className={labelClass}>{zh ? "角色" : "Role"}</span>
            <select name="role" className={inputClass} defaultValue="developer">
              {PROJECT_ROLES.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 sm:col-start-3"
          >
            {zh ? "添加" : "Add"}
          </button>
        </form>
        {directory === null ? (
          <p className="mt-3 text-xs text-ink-3">
            {zh
              ? "提示：无法加载用户列表（需要组织管理员会话）。无用户名的账号（如引导 agent 身份）只能填用户 ID，见成员列表中的 ID。"
              : "User directory unavailable (org admin session required). Accounts without a username (e.g. the bootstrap agent identity) can only be added by user id — see the ids in the member list."}
          </p>
        ) : null}
      </Card>

      {members.length === 0 ? (
        <EmptyState title={zh ? "暂无成员" : "No members yet"} />
      ) : (
        <Card className="mt-6">
          <Table headers={[zh ? "用户" : "User", zh ? "角色" : "Role", zh ? "操作" : "Actions"]}>
            {members.map((member) => (
              <tr key={member.user.id} className="align-middle">
                <td className="px-5 py-3">
                  <span className="font-medium text-ink">{member.user.display_name}</span>
                  <span className="mt-0.5 block font-mono text-xs text-ink-3">
                    {member.user.username ??
                      (zh ? "（无用户名）" : "(no username)")}{" "}
                    · {member.user.id}
                  </span>
                </td>
                <td className="px-5 py-3">
                  <Badge tone={roleTone(member.role)} dot={false}>
                    {member.role}
                  </Badge>
                </td>
                <td className="px-5 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <form action={`/projects/${projectId}/members/${member.user.id}/role`} method="post" className="flex items-center gap-2">
                      <select
                        name="role"
                        defaultValue={member.role}
                        className="rounded-lg border border-slate-300 bg-surface px-2 py-1 text-sm shadow-sm outline-none"
                      >
                        {PROJECT_ROLES.map((role) => (
                          <option key={role} value={role}>
                            {role}
                          </option>
                        ))}
                      </select>
                      <button
                        type="submit"
                        className="rounded-lg border border-slate-300 bg-surface px-2.5 py-1 text-xs font-medium text-ink-2 hover:bg-canvas"
                      >
                        {zh ? "改角色" : "Set role"}
                      </button>
                    </form>
                    <form action={`/projects/${projectId}/members/${member.user.id}/remove`} method="post">
                      <button
                        type="submit"
                        className="rounded-lg border border-red-200 bg-surface px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                      >
                        {zh ? "移除" : "Remove"}
                      </button>
                    </form>
                  </div>
                </td>
              </tr>
            ))}
          </Table>
        </Card>
      )}
    </Page>
  );
}
