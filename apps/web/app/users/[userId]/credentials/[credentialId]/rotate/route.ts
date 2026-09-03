import { redirect } from "next/navigation";
import { apiPostWithSession } from "../../../../../../lib/api";

type RotateResult = { credential: { id: string }; token: string };

export async function POST(request: Request) {
  const { pathname } = new URL(request.url);
  const parts = pathname.split("/");
  const userId = parts[2];
  const credentialId = parts[4];
  let result: RotateResult | null = null;
  try {
    result = await apiPostWithSession<RotateResult>(
      `/users/${userId}/credentials/${credentialId}/rotate`,
      {},
      request
    );
  } catch {
    redirect(`/users/${userId}/credentials?error=rotate_failed`);
  }
  if (result === null) {
    redirect(`/users/${userId}/credentials?error=rotate_failed`);
  }
  redirect(
    `/users/${userId}/credentials?rotated=1&token=${encodeURIComponent(result.token)}`
  );
}
