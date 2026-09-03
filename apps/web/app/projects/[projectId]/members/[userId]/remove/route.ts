import { redirect } from "next/navigation";
import {
  apiErrorCode,
  apiErrorMessage,
  apiDeleteWithSession,
} from "../../../../../../lib/api";

export async function POST(request: Request) {
  const { pathname } = new URL(request.url);
  const projectId = pathname.split("/")[2];
  const userId = pathname.split("/")[4];
  try {
    await apiDeleteWithSession(`/projects/${projectId}/members/${userId}`, request);
  } catch (error) {
    const code = apiErrorCode(error) ?? "remove_failed";
    const message = apiErrorMessage(error) ?? "";
    const msg = message && message !== code ? `&msg=${encodeURIComponent(message)}` : "";
    redirect(`/projects/${projectId}/members?error=${encodeURIComponent(code)}${msg}`);
  }
  redirect(`/projects/${projectId}/members?ok=removed`);
}
