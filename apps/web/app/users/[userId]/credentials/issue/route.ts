import { redirect } from "next/navigation";
import { apiPostWithSession } from "../../../../../lib/api";

type IssueResult = { credential: { id: string }; token: string };

export async function POST(request: Request) {
  const { pathname } = new URL(request.url);
  const userId = pathname.split("/")[2];
  const formData = await request.formData();
  const kind = String(formData.get("kind") ?? "agent").trim();
  const label = String(formData.get("label") ?? "").trim();
  const expiresAt = String(formData.get("expires_at") ?? "").trim() || undefined;
  let result: IssueResult | null = null;
  try {
    result = await apiPostWithSession<IssueResult>(
      `/users/${userId}/credentials`,
      { kind, label, expires_at: expiresAt },
      request
    );
  } catch {
    redirect(`/users/${userId}/credentials?error=issue_failed`);
  }
  if (result === null) {
    redirect(`/users/${userId}/credentials?error=issue_failed`);
  }
  redirect(
    `/users/${userId}/credentials?issued=1&token=${encodeURIComponent(result.token)}&kind=${encodeURIComponent(kind)}&label=${encodeURIComponent(label)}`
  );
}
