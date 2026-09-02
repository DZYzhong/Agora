import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { AgoraApiError, apiPostWithSession, hasSessionCookie, sessionLoginUrl } from "../../../../../../lib/api";

export async function POST(request: Request, { params }: { params: Promise<{ projectId: string; skillId: string }> }) {
  const { projectId, skillId } = await params;
  const formData = await request.formData();
  const triggers = String(formData.get("triggers") ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const riskConstraints = String(formData.get("risk_constraints") ?? "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

  const skillsUrl = `/projects/${projectId}/skills`;
  if (!hasSessionCookie(request)) {
    redirect(sessionLoginUrl(request, skillsUrl));
  }

  const body = {
    name: String(formData.get("name") ?? "").trim() || undefined,
    definition: {
      version: String(formData.get("version") ?? "").trim() || "1.0.0",
      summary: String(formData.get("summary") ?? "").trim(),
      triggers,
      input_schema: { type: "object" },
      output_schema: { type: "object" },
      instructions: String(formData.get("instructions") ?? "").trim(),
      risk_constraints: riskConstraints,
    },
  };

  try {
    await apiPostWithSession(`/projects/${projectId}/skills/${skillId}/approve`, body, request);
  } catch (error) {
    if (error instanceof AgoraApiError && error.code === "APPROVAL_CREDENTIAL_REQUIRED") {
      redirect(`/reauth?next=${encodeURIComponent(skillsUrl)}`);
    }
    redirect(`${skillsUrl}?error=${encodeURIComponent(error instanceof Error ? error.message : "Skill approval failed")}`);
  }
  revalidatePath(skillsUrl);
  redirect(skillsUrl);
}
