import { redirect } from "next/navigation";
import {
  apiErrorCode,
  apiErrorMessage,
  apiPatchWithSession,
} from "../../../../../../lib/api";

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
  } catch (error) {
    const code = apiErrorCode(error) ?? "role_failed";
    const message = apiErrorMessage(error) ?? "";
    const msg = message && message !== code ? `&msg=${encodeURIComponent(message)}` : "";
    redirect(`/projects/${projectId}/members?error=${encodeURIComponent(code)}${msg}`);
  }
  redirect(`/projects/${projectId}/members?ok=role_updated`);
}
