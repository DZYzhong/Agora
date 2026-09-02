import { redirect } from "next/navigation";

const API_BASE_URL = process.env.AGORA_API_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const cookie = request.headers.get("cookie") ?? "";
  const csrf = cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith("agora_csrf="))
    ?.split("=").slice(1).join("=");

  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      headers: {
        Cookie: cookie,
        ...(csrf ? { "X-CSRF-Token": csrf } : {}),
        Origin: new URL(request.url).origin,
      },
    });
  } catch {
    // logout must still clear the local cookies even if the API is unreachable
  }

  const webResponse = new Response(null, {
    status: 303,
    headers: {
      Location: "/login",
      "set-cookie":
        "agora_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0; " +
        "agora_csrf=; SameSite=Strict; Path=/; Max-Age=0",
    },
  });
  return webResponse;
}
