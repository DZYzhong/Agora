import { redirect } from "next/navigation";
import { apiPostWithSession } from "../../../lib/api";

export async function POST(request: Request) {
  const formData = await request.formData();
  const userId = String(formData.get("user_id") ?? "").trim();
  try {
    await apiPostWithSession(`/users/${userId}/enable`, {}, request);
  } catch {
    // fall through to the users page which shows the current state
  }
  redirect("/users");
}
