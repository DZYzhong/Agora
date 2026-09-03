import { cookies } from "next/headers";
import Link from "next/link";
import { currentLang, makeT } from "../lib/i18n";

export async function Nav() {
  const cookieStore = await cookies();
  const hasSession = Boolean(cookieStore.get("agora_session"));
  const lang = await currentLang();
  const t = makeT("common", lang);
  const switchTo = lang === "zh" ? "en" : "zh";

  return (
    <header className="sticky top-0 z-20 border-b border-edge bg-surface/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/projects" className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
            A
          </span>
          <span className="text-[15px] font-semibold tracking-tight text-ink">
            Agora
          </span>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2" aria-label="Primary">
          <Link
            href="/projects"
            className="rounded-md px-2.5 py-1.5 text-sm font-medium text-ink-2 hover:bg-fill hover:text-ink"
          >
            {t("projects")}
          </Link>
          <Link
            href="/users"
            className="rounded-md px-2.5 py-1.5 text-sm font-medium text-ink-2 hover:bg-fill hover:text-ink"
          >
            {t("users")}
          </Link>

          <span className="mx-1 hidden h-4 w-px bg-slate-200 sm:block" />

          <Link
            href={`/lang?lang=${switchTo}&next=/projects`}
            className="rounded-md px-2.5 py-1.5 text-sm font-medium text-ink-2 hover:bg-fill hover:text-ink"
            title="Switch language"
          >
            {switchTo === "en" ? "EN" : "中"}
          </Link>

          {hasSession ? (
            <form action="/logout" method="post">
              <button
                type="submit"
                className="rounded-lg border border-slate-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm hover:bg-canvas"
              >
                {t("signOut")}
              </button>
            </form>
          ) : (
            <Link
              href="/login"
              className="rounded-lg bg-blue-600 px-3.5 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
            >
              {t("signIn")}
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
