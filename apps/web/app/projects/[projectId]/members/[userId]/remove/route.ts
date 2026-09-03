import { redirect } from "next/navigation";
import { apiDeleteWithSession } from "../../../../../../lib/api";

export async function POST(request: Request) {
  const { pathname } = new URL(request.url);
  const projectId = pathname.split("/")[2];
  const userId = pathname.split("/")[4];
  try {
    await apiDeleteWithSession(`/projects/${projectId}/members/${userId}`, request);
    redirect(`/projects/${projectId}/members?ok=removed`);
  } catch {
    redirect(`/projects/${projectId}/members?error=remove_failed`);
  }
}
