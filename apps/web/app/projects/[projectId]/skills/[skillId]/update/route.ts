import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPatch } from "../../../../../../lib/api";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ projectId: string; skillId: string }> },
) {
  const { projectId, skillId } = await params;
  const formData = await request.formData();
  const triggers = String(formData.get("triggers") ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  await apiPatch(`/projects/${projectId}/skills/${skillId}`, {
    name: String(formData.get("name") ?? "").trim(),
    status: String(formData.get("status") ?? "candidate"),
    definition: {
      version: String(formData.get("version") ?? "").trim(),
      triggers,
      input_schema: { type: "object" },
      instructions: String(formData.get("instructions") ?? "").trim(),
    },
  });

  revalidatePath(`/projects/${projectId}/skills`);
  redirect(`/projects/${projectId}/skills`);
}
