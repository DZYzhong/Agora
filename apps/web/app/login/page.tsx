import { currentLang, makeT } from "../../lib/i18n";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; next?: string }>;
}) {
  const { error, next } = await searchParams;
  const lang = await currentLang();
  const t = makeT("login", lang);

  return (
    <main className="relative flex min-h-[calc(100vh-3.5rem)] items-center justify-center overflow-hidden bg-canvas px-4 py-12">
      <div aria-hidden="true" className="pointer-events-none absolute -top-40 left-1/2 h-96 w-[42rem] -translate-x-1/2 rounded-full bg-blue-100/60 blur-3xl" />
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <span className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600 text-xl font-bold text-white shadow-sm">
            A
          </span>
          <h1 className="text-xl font-semibold tracking-tight text-ink">
            {t("title")}
          </h1>
          <p className="mt-1.5 text-sm text-ink-3">Agora · Team AI Project Harness</p>
        </div>

        {error === "invalid_credentials" && (
          <div
            role="alert"
            className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {t("invalid")}
          </div>
        )}

        <form
          action="/login/submit"
          method="post"
          className="rounded-2xl border border-edge bg-surface p-6 shadow-sm"
        >
          {next ? <input type="hidden" name="next" value={next} /> : null}
          <div className="space-y-4">
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-ink">
                {t("username")}
              </span>
              <input
                name="username"
                required
                autoComplete="username"
                className="block w-full rounded-lg border border-slate-300 bg-surface px-3.5 py-2 text-sm text-ink shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-ink">
                {t("password")}
              </span>
              <input
                name="password"
                type="password"
                required
                autoComplete="current-password"
                className="block w-full rounded-lg border border-slate-300 bg-surface px-3.5 py-2 text-sm text-ink shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </label>
          </div>
          <button
            type="submit"
            className="mt-6 w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            {t("submit")}
          </button>
          <p className="mt-4 text-center text-xs leading-relaxed text-ink-3">
            {t("subtitle")}
          </p>
        </form>
      </div>
    </main>
  );
}
