const API_BASE_URL = process.env.AGORA_API_URL ?? "http://localhost:8000";
const WEB_HUMAN_TOKEN = process.env.AGORA_WEB_HUMAN_TOKEN;

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return response.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "content-type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return response.json() as Promise<T>;
}

function authHeaders(): Record<string, string> {
  return WEB_HUMAN_TOKEN ? { Authorization: `Bearer ${WEB_HUMAN_TOKEN}` } : {};
}

export const SESSION_COOKIE = "agora_session";
export const CSRF_COOKIE = "agora_csrf";

function sessionCookieHeader(request: Request): Record<string, string> {
  const cookie = request.headers.get("cookie");
  return cookie ? { Cookie: cookie } : {};
}

function csrfHeader(request: Request): Record<string, string> {
  const cookie = request.headers.get("cookie") ?? "";
  const csrf = cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${CSRF_COOKIE}=`))
    ?.split("=").slice(1).join("=");
  return csrf ? { "X-CSRF-Token": csrf } : {};
}

export async function apiGetWithSession<T>(path: string, request: Request): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    headers: sessionCookieHeader(request),
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return response.json() as Promise<T>;
}

export async function apiPostWithSession<T>(path: string, body: unknown, request: Request): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...sessionCookieHeader(request),
      ...csrfHeader(request),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return response.json() as Promise<T>;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // Fall through to the status-only message when the API does not return JSON.
  }
  return `Agora API request failed: ${response.status}`;
}
