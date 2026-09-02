import { redirect } from "next/navigation";
import { apiPostWithSession, hasSessionCookie } from "../../../lib/api";

const FALLBACK_NEXT = "/projects";

export async function POST(request: Request) {
  const formData = await request.formData();
  const password = String(formData.get("password") ?? "");
  const next = String(formData.get("next") ?? "").trim() || FALLBACK_NEXT;

  if (!hasSessionCookie(request)) {
    redirect(`/login?next=${encodeURIComponent(next)}`);
  }

  try {
    await apiPostWithSession("/auth/reauth", { password }, request);
  } catch {
    redirect(`/reauth?error=invalid_password&next=${encodeURIComponent(next)}`);
  }
  redirect(next);
}
