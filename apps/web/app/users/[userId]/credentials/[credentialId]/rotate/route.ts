import { redirect } from "next/navigation";
import { apiPostWithSession } from "../../../../../../lib/api";

export async function POST(request: Request) {
  const { pathname } = new URL(request.url);
  const parts = pathname.split("/");
  const userId = parts[2];
  const credentialId = parts[4];
  try {
    const result = await apiPostWithSession<{ credential: { id: string }; token: string }>(
      `/users/${userId}/credentials/${credentialId}/rotate`,
      {},
      request
    );
    redirect(
      `/users/${userId}/credentials?rotated=1&token=${encodeURIComponent(result.token)}`
    );
  } catch {
    redirect(`/users/${userId}/credentials?error=rotate_failed`);
  }
}
