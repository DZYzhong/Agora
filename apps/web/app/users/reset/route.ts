import { redirect } from "next/navigation";
import { apiPostWithSession } from "../../../lib/api";

type ResetResult = {
  reset_token: string;
  username: string;
};

export async function POST(request: Request) {
  const formData = await request.formData();
  const userId = String(formData.get("user_id") ?? "").trim();
  try {
    const result = await apiPostWithSession<ResetResult>(`/users/${userId}/reset`, {}, request);
    redirect(`/users?reset_token=${encodeURIComponent(result.reset_token)}&username=${encodeURIComponent(result.username)}`);
  } catch {
    redirect("/users?error=reset_failed");
  }
}
