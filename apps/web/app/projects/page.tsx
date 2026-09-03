import Link from "next/link";
import { apiGet } from "../../lib/api";
import { currentLang, makeT } from "../../lib/i18n";

type Project = {
  id: string;
  name: string;
  slug: string;
  git_remotes: string[];
  status: string;
};

function statusBadge(status: string, lang: "zh" | "en") {
  const active = status !== "archived";
  const label =
    status === "archived"
      ? lang === "zh"
        ? "已归档"
        : "Archived"
      : lang === "zh"
        ? "进行中"
        : "Active";
  return active ? (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
      {label}
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-fill px-2.5 py-0.5 text-xs font-medium text-ink-2 ring-1 ring-inset ring-slate-500/10">
      <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
      {label}
    </span>
  );
}

export default async function ProjectsPage({
  searchParams,
}: {
  searchParams: Promise<{ include_archived?: string }>;
}) {
  const { include_archived: includeArchivedParam } = await searchParams;
  const includeArchived = includeArchivedParam === "true";
  const lang = await currentLang();
  const t = makeT("projects", lang);

  let projects: Project[] = [];
  try {
    projects = await apiGet<Project[]>(
      includeArchived ? "/projects?include_archived=true" : "/projects"
    );
  } catch {
    projects = [];
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            {t("title")}
          </h1>
          <p className="mt-1 text-sm text-ink-2">{t("subtitle")}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-full bg-surface px-3 py-1 text-sm text-ink-2 ring-1 ring-inset ring-edge">
            {projects.length} {t("count")}
          </span>
          <Link
            href={includeArchived ? "/projects" : "/projects?include_archived=true"}
            className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm hover:bg-canvas"
          >
            {includeArchived ? t("hideArchived") : t("showArchived")}
          </Link>
        </div>
      </div>

      <section className="mt-6 rounded-2xl border border-edge bg-surface p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-50 text-blue-600">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5" aria-hidden="true">
              <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
            </svg>
          </span>
          <h2 className="text-sm font-semibold text-ink">{t("createTitle")}</h2>
        </div>
        <p className="mt-1 text-xs text-ink-3">{t("createSub")}</p>
        <form action="/projects/create" method="post" className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_1.2fr_auto]">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-ink-2">{t("org")}</span>
            <input
              name="org_id"
              defaultValue="local-org"
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-ink-2">{t("name")}</span>
            <input
              name="name"
              placeholder="Payment Service"
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-ink-2">{t("slug")}</span>
            <input
              name="slug"
              placeholder="payment-service"
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-ink-2">{t("gitRemote")}</span>
            <input
              name="git_remote"
              placeholder="git@example.com:team/payment.git"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </label>
          <button
            type="submit"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 sm:self-end"
          >
            {t("create")}
          </button>
        </form>
      </section>

      {projects.length === 0 ? (
        <div className="mt-10 flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-surface/60 px-6 py-16 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-fill text-ink-3">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-6 w-6" aria-hidden="true">
              <path
                fillRule="evenodd"
                d="M3.5 2A1.5 1.5 0 002 3.5v13A1.5 1.5 0 003.5 18h13a1.5 1.5 0 001.5-1.5v-13A1.5 1.5 0 0016.5 2h-13zM6 6.75A.75.75 0 016.75 6h6.5a.75.75 0 010 1.5h-6.5A.75.75 0 016 6.75zM6.75 10a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5z"
                clipRule="evenodd"
              />
            </svg>
          </span>
          <h3 className="mt-4 text-sm font-semibold text-ink">{t("noProjects")}</h3>
          <p className="mt-1 max-w-sm text-sm text-ink-2">{t("noProjectsHint")}</p>
        </div>
      ) : (
        <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <article
              key={project.id}
              className="group flex flex-col rounded-2xl border border-edge bg-surface p-5 shadow-sm transition hover:border-blue-200 hover:shadow"
            >
              <div className="flex items-start justify-between gap-3">
                <Link href={`/projects/${project.id}`} className="min-w-0">
                  <h2 className="truncate text-[15px] font-semibold text-ink group-hover:text-blue-700">
                    {project.name}
                  </h2>
                  <p className="mt-0.5 truncate font-mono text-xs text-ink-3">
                    {project.slug}
                  </p>
                </Link>
                {statusBadge(project.status, lang)}
              </div>
              <p className="mt-3 truncate text-xs text-ink-2">
                {project.git_remotes[0] ?? t("noGitRemote")}
              </p>
              <div className="mt-4 flex items-center justify-between border-t border-edge-1 pt-3">
                <Link
                  href={`/projects/${project.id}`}
                  className="text-sm font-medium text-blue-600 hover:text-blue-700"
                >
                  {lang === "zh" ? "进入项目 →" : "Open →"}
                </Link>
                {project.status !== "archived" ? (
                  <form action={`/projects/${project.id}/archive`} method="post">
                    <button
                      type="submit"
                      className="text-xs font-medium text-ink-3 hover:text-red-600"
                    >
                      {t("archive")}
                    </button>
                  </form>
                ) : null}
              </div>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
