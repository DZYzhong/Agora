import { redirect } from "next/navigation";
import {
  apiErrorCode,
  apiErrorMessage,
  apiPostWithSession,
} from "../../../../../lib/api";

export async function POST(request: Request) {
  const { pathname } = new URL(request.url);
  const projectId = pathname.split("/")[2];
  const formData = await request.formData();
  const role = String(formData.get("role") ?? "developer").trim();
  const user_id = String(formData.get("user_id") ?? "").trim();
  const username = String(formData.get("username") ?? "").trim();
  const body: Record<string, string> = { role };
  if (user_id) body.user_id = user_id;
  if (username) body.username = username;
  try {
    await apiPostWithSession(`/projects/${projectId}/members`, body, request);
  } catch (error) {
    const code = apiErrorCode(error) ?? "add_failed";
    const message = apiErrorMessage(error) ?? "";
    const msg = message && message !== code ? `&msg=${encodeURIComponent(message)}` : "";
    redirect(`/projects/${projectId}/members?error=${encodeURIComponent(code)}${msg}`);
  }
  redirect(`/projects/${projectId}/members?ok=added`);
}
