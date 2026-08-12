import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPost } from "../../../../lib/api";

export async function POST(request: Request, { params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const formData = await request.formData();
  const repoPath = String(formData.get("repo_path") ?? "").trim();
  const agentSummary = String(formData.get("agent_summary") ?? "").trim();
  const testResult = String(formData.get("test_result") ?? "").trim();
  const userMessage = agentSummary || "Capture development update";

  let captureError: string | null = null;
  try {
    const start = await apiPost<{ session_id: string }>("/harness/start-work", {
      project_id: projectId,
      user_message: userMessage,
      agent_type: "web-development-capture",
    });
    await apiPost("/harness/close-work", {
      session_id: start.session_id,
      status: "closed",
      repo_path: repoPath || null,
      agent_summary: agentSummary || null,
      test_result: testResult || null,
    });
  } catch (error) {
    captureError = error instanceof Error ? error.message : "Capture failed";
  }

  if (captureError) {
    redirect(`/projects/${projectId}?capture_error=${encodeURIComponent(captureError)}`);
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/sessions`);
  revalidatePath(`/projects/${projectId}/writebacks`);
  redirect(`/projects/${projectId}/writebacks`);
}
