import { redirect } from "next/navigation";
import { apiPostWithSession } from "../../../../../../lib/api";

export async function POST(request: Request) {
  const { pathname } = new URL(request.url);
  const parts = pathname.split("/");
  const userId = parts[2];
  const credentialId = parts[4];
  try {
    await apiPostWithSession(
      `/users/${userId}/credentials/${credentialId}/revoke`,
      {},
      request
    );
  } catch {
    redirect(`/users/${userId}/credentials?error=revoke_failed`);
  }
    redirect(`/users/${userId}/credentials?revoked=1`);
}
