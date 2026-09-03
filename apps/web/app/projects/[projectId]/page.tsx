import Link from "next/link";
import { apiGet } from "../../../lib/api";
import { currentLang, makeT } from "../../../lib/i18n";
import { relativeTime } from "../../../lib/format";

type LiveSession = {
  id: string;
  task_id: string | null;
  work_item: { id: string; external_key: string | null; title: string; stage: string } | null;
  agent_type: string;
  intent: string;
  status: string;
  created_at: string;
  events: Array<{ id: string; event_type: string; created_at: string }>;
};

type Project = {
  id: string;
  name: string;
  slug: string;
  git_remotes: string[];
  status: string;
};

const NAV_TILES: Array<{
  href: string;
  key: string;
  mono: string;
  tint: string;
}> = [
  { href: "/work-items", key: "workItems", mono: "WI", tint: "bg-blue-50 text-blue-600" },
  { href: "/status", key: "status", mono: "ST", tint: "bg-emerald-50 text-emerald-600" },
  { href: "/pending", key: "pending", mono: "PD", tint: "bg-amber-50 text-amber-600" },
  { href: "/operations", key: "ops", mono: "OP", tint: "bg-indigo-50 text-indigo-600" },
  { href: "/assets", key: "assets", mono: "AS", tint: "bg-violet-50 text-violet-600" },
  { href: "/skills", key: "skills", mono: "SK", tint: "bg-cyan-50 text-cyan-600" },
  { href: "/knowledge", key: "knowledge", mono: "KN", tint: "bg-teal-50 text-teal-600" },
  { href: "/context", key: "context", mono: "CT", tint: "bg-sky-50 text-sky-600" },
  { href: "/sessions", key: "sessions", mono: "SE", tint: "bg-slate-100 text-slate-600" },
  { href: "/security", key: "security", mono: "SC", tint: "bg-rose-50 text-rose-600" },
  { href: "/writebacks", key: "writebacks", mono: "WB", tint: "bg-slate-100 text-slate-600" },
];

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const lang = await currentLang();
  const t = makeT("projectHome", lang);

  const project = await apiGet<Project>(`/projects/${projectId}`);
  let liveSessions: LiveSession[] = [];
  try {
    liveSessions = await apiGet<LiveSession[]>(`/projects/${projectId}/sessions`);
  } catch {
    liveSessions = [];
  }
  const inFlight = liveSessions
    .filter((session) => session.status !== "closed")
    .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at) ?? ""))
    .slice(0, 5);

  const active = project.status !== "archived";

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <nav className="mb-4 flex items-center gap-1.5 text-sm text-slate-400" aria-label="Breadcrumb">
        <Link href="/projects" className="hover:text-slate-600">
          {lang === "zh" ? "项目" : "Projects"}
        </Link>
        <span aria-hidden="true">/</span>
        <span className="truncate font-mono text-xs text-slate-500">{project.slug}</span>
      </nav>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="truncate text-2xl font-semibold tracking-tight text-slate-900">
              {project.name}
            </h1>
            <span
              className={
                active
                  ? "inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20"
                  : "inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500 ring-1 ring-inset ring-slate-500/10"
              }
            >
              <span
                className={
                  active ? "h-1.5 w-1.5 rounded-full bg-emerald-500" : "h-1.5 w-1.5 rounded-full bg-slate-400"
                }
              />
              {active
                ? lang === "zh"
                  ? "进行中"
                  : "Active"
                : lang === "zh"
                  ? "已归档"
                  : "Archived"}
            </span>
          </div>
          <p className="mt-1 font-mono text-xs text-slate-400">{project.slug}</p>
        </div>
        <Link
          href={`/projects/${project.id}/sessions`}
          className="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
        >
          {t("sessions")} →
        </Link>
      </div>

      {inFlight.length ? (
        <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3.5">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
              </span>
              <h2 className="text-sm font-semibold text-slate-900">{t("inFlight")}</h2>
              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                {inFlight.length}
              </span>
            </div>
            <Link
              href={`/projects/${project.id}/sessions`}
              className="text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              {t("allSessions")} →
            </Link>
          </div>
          <div className="divide-y divide-slate-100">
            {inFlight.map((session) => (
              <div key={session.id} className="flex flex-wrap items-center gap-x-6 gap-y-1 px-5 py-3 text-sm">
                <span className="inline-flex items-center gap-1.5 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                  {session.agent_type}
                </span>
                <span className="min-w-0 flex-1 truncate text-slate-600">{session.intent}</span>
                <span className="w-56 truncate text-slate-400">
                  {session.work_item ? (
                    <Link
                      href={`/projects/${project.id}/sessions/${session.id}`}
                      className="text-slate-600 hover:text-blue-700"
                    >
                      {session.work_item.external_key
                        ? `${session.work_item.external_key} · ${session.work_item.title}`
                        : session.work_item.title}
                    </Link>
                  ) : (
                    t("noWorkItem")
                  )}
                </span>
                <span className="w-24 text-right text-xs text-slate-400">
                  {relativeTime(session.created_at, lang)}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : (
        <section className="mt-6 rounded-2xl border border-dashed border-slate-200 bg-white/60 px-5 py-4 text-sm text-slate-400">
          {lang === "zh"
            ? "暂无进行中的 AI 会话。"
            : "No AI tool sessions are running right now."}
        </section>
      )}

      <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {NAV_TILES.map((tile) => (
          <Link
            key={tile.href}
            href={`/projects/${project.id}${tile.href}`}
            className="group flex items-start gap-3.5 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-px hover:border-blue-200 hover:shadow"
          >
            <span
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${tile.tint}`}
            >
              {tile.mono}
            </span>
            <span className="min-w-0">
              <span className="flex items-center gap-1 text-[15px] font-semibold text-slate-900 group-hover:text-blue-700">
                {t(tile.key)}
                <span className="opacity-0 transition group-hover:opacity-100">→</span>
              </span>
              <span className="mt-0.5 block text-xs leading-relaxed text-slate-400">
                {t(`${tile.key}Hint`)}
              </span>
            </span>
          </Link>
        ))}
      </section>
    </main>
  );
}
