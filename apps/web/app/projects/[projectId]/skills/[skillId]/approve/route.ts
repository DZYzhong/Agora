import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPost } from "../../../../../../lib/api";

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

  await apiPost(`/projects/${projectId}/skills/${skillId}/approve`, {
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
  });
  revalidatePath(`/projects/${projectId}/skills`);
  redirect(`/projects/${projectId}/skills`);
}
