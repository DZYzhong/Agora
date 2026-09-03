import { redirect } from "next/navigation";
import { apiPostWithSession } from "../../../../../lib/api";

export async function POST(request: Request) {
  const { pathname } = new URL(request.url);
  const userId = pathname.split("/")[2];
  const formData = await request.formData();
  const kind = String(formData.get("kind") ?? "agent").trim();
  const label = String(formData.get("label") ?? "").trim();
  const expiresAt = String(formData.get("expires_at") ?? "").trim() || undefined;
  try {
    const result = await apiPostWithSession<{ credential: { id: string }; token: string }>(
      `/users/${userId}/credentials`,
      { kind, label, expires_at: expiresAt },
      request
    );
    redirect(
      `/users/${userId}/credentials?issued=1&token=${encodeURIComponent(result.token)}&kind=${encodeURIComponent(kind)}&label=${encodeURIComponent(label)}`
    );
  } catch {
    redirect(`/users/${userId}/credentials?error=issue_failed`);
  }
}
