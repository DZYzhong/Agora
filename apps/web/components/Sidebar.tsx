import { cookies } from "next/headers";
import Link from "next/link";
import { currentLang, makeT } from "../lib/i18n";

export async function Sidebar() {
  const cookieStore = await cookies();
  const hasSession = Boolean(cookieStore.get("agora_session"));
  const lang = await currentLang();
  const t = makeT("common", lang);
  const switchTo = lang === "zh" ? "en" : "zh";

  const links = [
    { href: "/projects", label: t("projects"), icon: "▦" },
    { href: "/users", label: t("users"), icon: "👥" },
    { href: "/members", label: t("orgMembers"), icon: "🏛" },
  ];

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
      <div className="px-4 pb-2 pt-5">
        <Link href="/projects" className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
            A
          </span>
          <span className="text-[15px] font-semibold tracking-tight text-slate-900">Agora</span>
        </Link>
      </div>

      <nav className="mt-3 flex-1 space-y-1 px-3" aria-label="Sidebar">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
          >
            <span className="w-5 text-center text-slate-400" aria-hidden="true">
              {link.icon}
            </span>
            {link.label}
          </Link>
        ))}
      </nav>

      <div className="space-y-2 border-t border-slate-200 p-3">
        <Link
          href={`/lang?lang=${switchTo}&next=/projects`}
          className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-900"
        >
          {switchTo === "en" ? "English" : "中文"}
        </Link>
        {hasSession ? (
          <form action="/logout" method="post">
            <button
              type="submit"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
            >
              {t("signOut")}
            </button>
          </form>
        ) : (
          <Link
            href="/login"
            className="block rounded-lg bg-blue-600 px-3 py-2 text-center text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          >
            {t("signIn")}
          </Link>
        )}
      </div>
    </aside>
  );
}
