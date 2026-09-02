import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "agora_session";

// In production the governance UI requires a cookie web session. Public
// authentication routes and the users page (which handles login guidance
// itself) are excluded. Local development with AGORA_WEB_HUMAN_TOKEN is not
// gated so the bearer flow keeps working without a browser login.
const isProduction = process.env.AGORA_ENV === "production";

export function middleware(request: NextRequest) {
  if (!isProduction) {
    return NextResponse.next();
  }
  const { pathname } = request.nextUrl;
  if (pathname === "/login" || pathname.startsWith("/login") || pathname.startsWith("/reauth") || pathname.startsWith("/users")) {
    return NextResponse.next();
  }
  if (!request.cookies.get(SESSION_COOKIE)) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/projects/:path*", "/"],
};
