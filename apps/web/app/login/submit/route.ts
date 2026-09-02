import { redirect } from "next/navigation";

const API_BASE_URL = process.env.AGORA_API_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const formData = await request.formData();
  const username = String(formData.get("username") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    redirect(`/login?error=invalid_credentials`);
  }
  const setCookies = response.headers.getSetCookie();
  if (setCookies.length === 0) {
    redirect(`/login?error=invalid_credentials`);
  }

  const webResponse = new Response(null, {
    status: 303,
    headers: { Location: "/projects" },
  });
  for (const setCookie of setCookies) {
    webResponse.headers.append("set-cookie", setCookie);
  }
  return webResponse;
}
