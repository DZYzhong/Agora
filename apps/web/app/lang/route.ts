import { NextResponse } from "next/server";
import { LANG_COOKIE } from "../../lib/i18n";

// GET /lang?lang=zh|en&next=/projects — switches the UI language cookie.
export function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const lang = searchParams.get("lang") === "en" ? "en" : "zh";
  const next = searchParams.get("next") || "/projects";
  const response = NextResponse.redirect(new URL(next, request.url));
  response.cookies.set(LANG_COOKIE, lang, {
    path: "/",
    httpOnly: false,
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 365,
  });
  return response;
}
