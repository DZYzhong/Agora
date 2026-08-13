import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPost } from "../../../../../../lib/api";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ projectId: string; skillId: string }> },
) {
  const { projectId, skillId } = await params;
  const formData = await request.formData();
  const summary = String(formData.get("summary") ?? "").trim();

  await apiPost(`/projects/${projectId}/skills/${skillId}/run`, {
    input: { summary },
    context: { summary },
  });

  revalidatePath(`/projects/${projectId}/skills`);
  redirect(`/projects/${projectId}/skills`);
}
