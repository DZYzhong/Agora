import { redirect } from "next/navigation";
import { apiPatchWithSession } from "../../../../lib/api";

export async function POST(request: Request) {
  const { pathname } = new URL(request.url);
  const userId = pathname.split("/")[2];
  const formData = await request.formData();
  const role = String(formData.get("role") ?? "member").trim();
  try {
    await apiPatchWithSession(
      `/organizations/local-org/members/${userId}`,
      { role },
      request
    );
  } catch {
    redirect("/members?error=role_failed");
  }
    redirect("/members?ok=role_updated");
}
