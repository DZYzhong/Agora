import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPost } from "../../../../../../../lib/api";

export async function POST(request: Request, { params }: { params: Promise<{ projectId: string; proposalId: string }> }) {
  const { projectId, proposalId } = await params;
  const formData = await request.formData();
  const expectedHead = String(formData.get("expected_head_revision_id") ?? "").trim();
  const observedHead = String(formData.get("observed_head_sha") ?? "").trim();
  const comment = String(formData.get("comment") ?? "").trim();
  const targetBranch = String(formData.get("target_branch") ?? "main").trim() || "main";
  const mergeTargetBranch = String(formData.get("merge_target_branch") ?? "").trim();

  try {
    await apiPost(`/projects/${projectId}/context/proposals/${proposalId}/approve`, {
      expected_head_revision_id: expectedHead || null,
      comment: comment || null,
      revision_signal: {
        target_branch: targetBranch,
        observed_head_sha: observedHead || null,
        contains_to_commit: formData.get("contains_to_commit") === "on",
        merge_target_branch: mergeTargetBranch || null,
        merged_to_target: formData.get("merged_to_target") === "on",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Context proposal review failed";
    redirect(`/projects/${projectId}/context/proposals/${proposalId}?error=${encodeURIComponent(message)}`);
  }

  revalidatePath(`/projects/${projectId}/context`);
  revalidatePath(`/projects/${projectId}/context/proposals/${proposalId}`);
  redirect(`/projects/${projectId}/context/proposals/${proposalId}`);
}
