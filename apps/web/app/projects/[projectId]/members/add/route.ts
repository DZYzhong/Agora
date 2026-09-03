import { redirect } from "next/navigation";
import { apiPostWithSession } from "../../../../../lib/api";

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
    redirect(`/projects/${projectId}/members?ok=added`);
  } catch {
    redirect(`/projects/${projectId}/members?error=add_failed`);
  }
}
