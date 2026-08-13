import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPost } from "../../../../../../lib/api";

export async function POST(_: Request, { params }: { params: Promise<{ projectId: string; skillId: string }> }) {
  const { projectId, skillId } = await params;
  await apiPost(`/projects/${projectId}/skills/${skillId}/approve`, {});
  revalidatePath(`/projects/${projectId}/skills`);
  redirect(`/projects/${projectId}/skills`);
}
