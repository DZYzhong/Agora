import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { AgoraApiError, apiPostWithSession, hasSessionCookie, sessionLoginUrl } from "../../../../../../../lib/api";

export async function POST(request: Request, { params }: { params: Promise<{ projectId: string; proposalId: string }> }) {
  const { projectId, proposalId } = await params;
  const formData = await request.formData();
  const expectedHead = String(formData.get("expected_head_revision_id") ?? "").trim();
  const observedHead = String(formData.get("observed_head_sha") ?? "").trim();
  const comment = String(formData.get("comment") ?? "").trim();
  const targetBranch = String(formData.get("target_branch") ?? "main").trim() || "main";
  const mergeTargetBranch = String(formData.get("merge_target_branch") ?? "").trim();

  const proposalUrl = `/projects/${projectId}/context/proposals/${proposalId}`;
  if (!hasSessionCookie(request)) {
    redirect(sessionLoginUrl(request, proposalUrl));
  }

  const body = {
    expected_head_revision_id: expectedHead || null,
    comment: comment || null,
    revision_signal: {
      target_branch: targetBranch,
      observed_head_sha: observedHead || null,
      contains_to_commit: formData.get("contains_to_commit") === "on",
      merge_target_branch: mergeTargetBranch || null,
      merged_to_target: formData.get("merged_to_target") === "on",
    },
  };

  try {
    await apiPostWithSession(`/projects/${projectId}/context/proposals/${proposalId}/approve`, body, request);
  } catch (error) {
    if (error instanceof AgoraApiError && error.code === "APPROVAL_CREDENTIAL_REQUIRED") {
      redirect(`/reauth?next=${encodeURIComponent(proposalUrl)}`);
    }
    const message = error instanceof Error ? error.message : "Context proposal review failed";
    redirect(`${proposalUrl}?error=${encodeURIComponent(message)}`);
  }

  revalidatePath(`/projects/${projectId}/context`);
  revalidatePath(proposalUrl);
  redirect(proposalUrl);
}
