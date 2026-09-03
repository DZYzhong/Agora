import { redirect } from "next/navigation";
import { apiPostWithSession } from "../../../lib/api";

export async function POST(request: Request) {
  const formData = await request.formData();
  const role = String(formData.get("role") ?? "member").trim();
  const user_id = String(formData.get("user_id") ?? "").trim();
  const username = String(formData.get("username") ?? "").trim();

  const body: Record<string, string> = { role };
  if (user_id) body.user_id = user_id;
  if (username) body.username = username;

  try {
    await apiPostWithSession("/organizations/local-org/members", body, request);
    redirect("/members?ok=added");
  } catch {
    redirect("/members?error=add_failed");
  }
}
