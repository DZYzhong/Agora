import { redirect } from "next/navigation";
import { apiPostWithSession } from "../../../lib/api";

type CreateUserResult = {
  activation_token: string;
  user: { username: string };
};

export async function POST(request: Request) {
  const formData = await request.formData();
  const username = String(formData.get("username") ?? "").trim();
  const displayName = String(formData.get("display_name") ?? "").trim();

  try {
    const result = await apiPostWithSession<CreateUserResult>("/users", {
      org_id: "local-org",
      username,
      display_name: displayName,
    }, request);
    redirect(`/users?activation_token=${encodeURIComponent(result.activation_token)}&username=${encodeURIComponent(result.user.username)}`);
  } catch {
    redirect("/users?error=create_failed");
  }
}
