const API_BASE_URL = process.env.AGORA_API_URL ?? "http://localhost:8000";
const WEB_HUMAN_TOKEN = process.env.AGORA_WEB_HUMAN_TOKEN;
const WEB_ORIGIN = process.env.AGORA_WEB_ORIGIN ?? "http://127.0.0.1:13140";

export class AgoraApiError extends Error {
  status: number;
  code: string | null;

  constructor(status: number, message: string, code: string | null = null) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    headers: { ...authHeaders(), ...(await browserCookieHeaders()) },
  });
  if (!response.ok) {
    throw await apiError(response);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...authHeaders(),
      ...(await browserWriteHeaders()),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw await apiError(response);
  }
  return response.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: {
      "content-type": "application/json",
      ...authHeaders(),
      ...(await browserWriteHeaders()),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw await apiError(response);
  }
  return response.json() as Promise<T>;
}

function authHeaders(): Record<string, string> {
  return WEB_HUMAN_TOKEN ? { Authorization: `Bearer ${WEB_HUMAN_TOKEN}` } : {};
}

async function browserCookieString(): Promise<string | null> {
  try {
    const { cookies } = await import("next/headers");
    const store = await cookies();
    const serialized = store.toString();
    return serialized || null;
  } catch {
    return null;
  }
}

async function browserCookieHeaders(): Promise<Record<string, string>> {
  const cookie = await browserCookieString();
  return cookie ? { Cookie: cookie, Origin: WEB_ORIGIN } : {};
}

async function browserWriteHeaders(): Promise<Record<string, string>> {
  const cookie = await browserCookieString();
  if (!cookie) {
    return {};
  }
  const csrf = cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${CSRF_COOKIE}=`))
    ?.split("=").slice(1).join("=");
  return {
    Cookie: cookie,
    Origin: WEB_ORIGIN,
    ...(csrf ? { "X-CSRF-Token": csrf } : {}),
  };
}

export const SESSION_COOKIE = "agora_session";
export const CSRF_COOKIE = "agora_csrf";

export function hasSessionCookie(request: Request): boolean {
  return Boolean(request.headers.get("cookie")?.includes(`${SESSION_COOKIE}=`));
}

export function sessionLoginUrl(request: Request, next: string): string {
  return `/login?next=${encodeURIComponent(next)}`;
}

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

function originHeader(): Record<string, string> {
  return { Origin: WEB_ORIGIN };
}

export async function apiGetWithSession<T>(path: string, request: Request): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    headers: { ...sessionCookieHeader(request), ...originHeader() },
  });
  if (!response.ok) {
    throw await apiError(response);
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
      ...originHeader(),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw await apiError(response);
  }
  return response.json() as Promise<T>;
}

export async function apiPatchWithSession<T>(path: string, body: unknown, request: Request): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: {
      "content-type": "application/json",
      ...sessionCookieHeader(request),
      ...csrfHeader(request),
      ...originHeader(),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw await apiError(response);
  }
  return response.json() as Promise<T>;
}

export async function apiDeleteWithSession<T>(path: string, request: Request): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    headers: {
      ...sessionCookieHeader(request),
      ...csrfHeader(request),
      ...originHeader(),
    },
  });
  if (!response.ok) {
    throw await apiError(response);
  }
  const text = await response.text();
  return (text ? JSON.parse(text) : {}) as T;
}

async function apiError(response: Response): Promise<AgoraApiError> {
  let message = `Agora API request failed: ${response.status}`;
  let code: string | null = null;
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      message = body.detail;
    } else if (body.detail && typeof body.detail === "object") {
      const detail = body.detail as { code?: string; message?: string };
      code = detail.code ?? null;
      message = detail.message ?? message;
    } else if (Array.isArray(body.detail)) {
      const first = body.detail[0];
      message = first?.msg ? String(first.msg) : message;
    }
  } catch {
    // Fall through to the status-only message.
  }
  return new AgoraApiError(response.status, message, code);
}
