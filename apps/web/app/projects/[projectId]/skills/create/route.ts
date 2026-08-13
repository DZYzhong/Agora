import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPost } from "../../../../../lib/api";

export async function POST(request: Request, { params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const formData = await request.formData();
  const slug = String(formData.get("slug") ?? "").trim();
  const name = String(formData.get("name") ?? "").trim();
  const version = String(formData.get("version") ?? "").trim();
  const triggers = String(formData.get("triggers") ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const instructions = String(formData.get("instructions") ?? "").trim();

  await apiPost(`/projects/${projectId}/skills`, {
    slug,
    name,
    status: "candidate",
    definition: {
      version,
      triggers,
      input_schema: { type: "object" },
      instructions,
    },
  });

  revalidatePath(`/projects/${projectId}/skills`);
  redirect(`/projects/${projectId}/skills`);
}
