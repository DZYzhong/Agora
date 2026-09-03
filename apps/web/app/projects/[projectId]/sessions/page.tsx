import Link from "next/link";
import { apiGet } from "../../../../lib/api";
import { currentLang } from "../../../../lib/i18n";
import { relativeTime } from "../../../../lib/format";
import { Badge, EmptyState, Page, PageHeader } from "../../../../components/ui";

type TaskSession = {
  id: string;
  project_id: string;
  task_id: string | null;
  work_item: {
    id: string;
    external_key: string | null;
    title: string;
    status: string;
    stage: string;
    source: string;
  } | null;
  agent_type: string;
  intent: string;
  status: string;
  created_at: string;
  closed_at: string | null;
  audit_counts: {
    events: number;
    context_packs: number;
    skill_runs: number;
    writebacks: number;
  };
};

type SearchParams = { intent?: string; status?: string; q?: string };

function queryString(searchParams: SearchParams): string {
  const params = new URLSearchParams();
  if (searchParams.intent) params.set("intent", searchParams.intent);
  if (searchParams.status) params.set("status", searchParams.status);
  if (searchParams.q) params.set("q", searchParams.q);
  const value = params.toString();
  return value ? `?${value}` : "";
}

function statusTone(status: string) {
  if (status === "closed") return "slate" as const;
  if (status === "failed") return "red" as const;
  return "green" as const;
}

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-surface px-3 py-2 text-sm shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

export default async function SessionsPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { projectId } = await params;
  const filters = await searchParams;
  const lang = await currentLang();
  const zh = lang === "zh";

  let sessions: TaskSession[] = [];
  try {
    sessions = await apiGet<TaskSession[]>(
      `/projects/${projectId}/sessions${queryString(filters)}`
    );
  } catch {
    sessions = [];
  }

  return (
    <Page>
      <PageHeader
        title={zh ? "会话" : "Sessions"}
        subtitle={zh ? "AI 工具工作会话与审计计数" : "AI tool work sessions and audit counts"}
        meta={
          <span className="rounded-full bg-surface px-3 py-1 text-sm text-ink-2 ring-1 ring-inset ring-edge">
            {sessions.length}
          </span>
        }
      />

      <section className="mt-6 rounded-2xl border border-edge bg-surface p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-ink">{zh ? "筛选" : "Filters"}</h2>
        <form
          className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1.4fr_auto_auto]"
          action={`/projects/${projectId}/sessions`}
          method="get"
        >
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-ink-2">
              {zh ? "意图" : "Intent"}
            </span>
            <select name="intent" defaultValue={filters.intent ?? ""} className={inputClass}>
              <option value="">{zh ? "全部意图" : "All intents"}</option>
              <option value="analysis">analysis</option>
              <option value="implementation">implementation</option>
              <option value="review">review</option>
              <option value="test_generation">test_generation</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-ink-2">
              {zh ? "状态" : "Status"}
            </span>
            <select name="status" defaultValue={filters.status ?? ""} className={inputClass}>
              <option value="">{zh ? "全部状态" : "All statuses"}</option>
              <option value="started">started</option>
              <option value="closed">closed</option>
              <option value="failed">failed</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-ink-2">
              {zh ? "搜索" : "Search"}
            </span>
            <input
              name="q"
              defaultValue={filters.q ?? ""}
              placeholder={
                zh ? "context、skill、writeback、event" : "context, skill, writeback, event"
              }
              className={inputClass}
            />
          </label>
          <button
            type="submit"
            className="self-end rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          >
            {zh ? "应用筛选" : "Apply filters"}
          </button>
          <Link
            href={`/projects/${projectId}/sessions`}
            className="self-end rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-center text-sm font-medium text-ink-2 hover:bg-canvas"
          >
            {zh ? "清除" : "Clear"}
          </Link>
        </form>
      </section>

      {sessions.length === 0 ? (
        <EmptyState
          title={zh ? "还没有工作会话" : "No agent work sessions yet"}
          hint={
            zh
              ? "由 MCP/API 调用创建的会话会显示在这里。"
              : "Harness sessions created by MCP/API calls will be listed here."
          }
        />
      ) : (
        <section className="mt-6 grid gap-4 lg:grid-cols-2">
          {sessions.map((session) => (
            <article
              key={session.id}
              className="flex flex-col rounded-2xl border border-edge bg-surface p-5 shadow-sm transition hover:border-blue-200"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-ink-3">{session.agent_type}</p>
                  <h3 className="mt-0.5 truncate text-[15px] font-semibold text-ink">
                    {session.intent}
                  </h3>
                  <p className="mt-0.5 truncate font-mono text-xs text-ink-3">{session.id}</p>
                </div>
                <Badge tone={statusTone(session.status)}>{session.status}</Badge>
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-edge-1 pt-3 text-sm">
                <div>
                  <dt className="text-xs text-ink-3">{zh ? "工作项" : "Work item"}</dt>
                  <dd className="truncate text-ink">
                    {session.work_item
                      ? session.work_item.title
                      : session.task_id ?? (zh ? "未设置" : "Not set")}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-3">{zh ? "任务键" : "Task key"}</dt>
                  <dd className="truncate font-mono text-xs text-ink-2">
                    {session.work_item?.external_key ?? session.task_id ?? "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-3">{zh ? "开始" : "Started"}</dt>
                  <dd className="text-ink">{relativeTime(session.created_at, lang)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-3">{zh ? "关闭" : "Closed"}</dt>
                  <dd className="text-ink">
                    {session.closed_at ? relativeTime(session.closed_at, lang) : zh ? "进行中" : "Open"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-3">Context</dt>
                  <dd className="text-ink">{session.audit_counts.context_packs}</dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-3">{zh ? "技能运行" : "Skill runs"}</dt>
                  <dd className="text-ink">{session.audit_counts.skill_runs}</dd>
                </div>
              </dl>
              <div className="mt-4 flex items-center gap-3 border-t border-edge-1 pt-3">
                <Link
                  href={`/projects/${projectId}/sessions/${session.id}`}
                  className="text-sm font-medium text-blue-600 hover:text-blue-700"
                >
                  {zh ? "查看审计 →" : "View audit →"}
                </Link>
                {session.work_item ? (
                  <Link
                    href={`/projects/${projectId}/work-items/${session.work_item.id}`}
                    className="text-sm font-medium text-ink-2 hover:text-ink"
                  >
                    {zh ? "查看工作项" : "View work item"}
                  </Link>
                ) : null}
              </div>
            </article>
          ))}
        </section>
      )}
    </Page>
  );
}
