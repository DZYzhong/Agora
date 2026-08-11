import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPost } from "../../../lib/api";

type Project = {
  id: string;
};

export async function POST(request: Request) {
  const formData = await request.formData();
  const orgId = String(formData.get("org_id") ?? "local-org").trim();
  const name = String(formData.get("name") ?? "").trim();
  const slug = String(formData.get("slug") ?? "").trim();
  const gitRemote = String(formData.get("git_remote") ?? "").trim();

  const project = await apiPost<Project>("/projects", {
    org_id: orgId,
    name,
    slug,
    git_remotes: gitRemote ? [gitRemote] : [],
  });

  revalidatePath("/projects");
  redirect(`/projects/${project.id}`);
}
