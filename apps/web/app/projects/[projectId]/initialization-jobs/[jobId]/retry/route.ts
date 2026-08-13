import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPost } from "../../../../../../lib/api";

export async function POST(_request: Request, { params }: { params: Promise<{ projectId: string; jobId: string }> }) {
  const { projectId, jobId } = await params;

  let initError: string | null = null;
  try {
    await apiPost(`/projects/${projectId}/initialization-jobs/${jobId}/retry`, {});
  } catch (error) {
    initError = error instanceof Error ? error.message : "Retry failed";
  }

  if (initError) {
    redirect(`/projects/${projectId}?init_error=${encodeURIComponent(initError)}`);
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/assets`);
  redirect(`/projects/${projectId}`);
}
