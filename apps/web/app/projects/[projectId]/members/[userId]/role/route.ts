import { redirect } from "next/navigation";
import { apiPatchWithSession } from "../../../../../../lib/api";

export async function POST(request: Request) {
  const { pathname } = new URL(request.url);
  const projectId = pathname.split("/")[2];
  const userId = pathname.split("/")[4];
  const formData = await request.formData();
  const role = String(formData.get("role") ?? "developer").trim();
  try {
    await apiPatchWithSession(
      `/projects/${projectId}/members/${userId}`,
      { role },
      request
    );
    redirect(`/projects/${projectId}/members?ok=role_updated`);
  } catch {
    redirect(`/projects/${projectId}/members?error=role_failed`);
  }
}
