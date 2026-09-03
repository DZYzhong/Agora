import { currentLang, makeT } from "../../lib/i18n";

export default async function ReauthPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; error?: string }>;
}) {
  const { next, error } = await searchParams;
  const lang = await currentLang();
  const t = makeT("reauth", lang);

  return (
    <main className="relative flex min-h-[calc(100vh-3.5rem)] items-center justify-center overflow-hidden bg-canvas px-4 py-12">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-40 left-1/2 h-96 w-[42rem] -translate-x-1/2 rounded-full bg-amber-100/50 blur-3xl"
      />
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <span className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-600">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5" aria-hidden="true">
              <path
                fillRule="evenodd"
                d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z"
                clipRule="evenodd"
              />
            </svg>
          </span>
          <h1 className="text-xl font-semibold tracking-tight text-ink">
            {t("title")}
          </h1>
        </div>

        {error === "invalid_password" && (
          <div
            role="alert"
            className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {t("invalid")}
          </div>
        )}

        <form
          action="/reauth/submit"
          method="post"
          className="rounded-2xl border border-edge bg-surface p-6 shadow-sm"
        >
          {next ? <input type="hidden" name="next" value={next} /> : null}
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-ink">
              {t("password")}
            </span>
            <input
              name="password"
              type="password"
              required
              autoComplete="current-password"
              autoFocus
              className="block w-full rounded-lg border border-slate-300 bg-surface px-3.5 py-2 text-sm text-ink shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </label>
          <button
            type="submit"
            className="mt-6 w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            {t("confirm")}
          </button>
          <p className="mt-4 text-center text-xs leading-relaxed text-ink-3">
            {t("subtitle")}
          </p>
        </form>
      </div>
    </main>
  );
}
