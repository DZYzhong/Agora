import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPost } from "../../../../lib/api";

export async function POST(request: Request, { params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const formData = await request.formData();
  const repoPath = String(formData.get("repo_path") ?? "").trim();

  let initError: string | null = null;
  try {
    await apiPost(`/projects/${projectId}/initialize-local`, {
      repo_path: repoPath,
    });
  } catch (error) {
    initError = error instanceof Error ? error.message : "Initialize failed";
  }

  if (initError) {
    redirect(`/projects/${projectId}?init_error=${encodeURIComponent(initError)}`);
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/assets`);
  redirect(`/projects/${projectId}/assets`);
}
