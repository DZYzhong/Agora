import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPost } from "../../../../../../lib/api";

export async function POST(_: Request, { params }: { params: Promise<{ projectId: string; writebackId: string }> }) {
  const { projectId, writebackId } = await params;
  await apiPost(`/projects/${projectId}/writebacks/${writebackId}/accept`, {});
  revalidatePath(`/projects/${projectId}/writebacks`);
  redirect(`/projects/${projectId}/writebacks`);
}
