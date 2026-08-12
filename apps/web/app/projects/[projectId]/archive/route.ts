import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPost } from "../../../../lib/api";

export async function POST(_request: Request, { params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  await apiPost(`/projects/${projectId}/archive`, {});
  revalidatePath("/projects");
  redirect("/projects");
}
