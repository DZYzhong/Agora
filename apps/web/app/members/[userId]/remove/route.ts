import { redirect } from "next/navigation";
import { apiDeleteWithSession } from "../../../../lib/api";

export async function POST(request: Request) {
  const { pathname } = new URL(request.url);
  const userId = pathname.split("/")[2];
  try {
    await apiDeleteWithSession(`/organizations/local-org/members/${userId}`, request);
    redirect("/members?ok=removed");
  } catch {
    redirect("/members?error=remove_failed");
  }
}
