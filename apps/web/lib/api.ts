const API_BASE_URL = process.env.NEXT_PUBLIC_AGORA_API_URL ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Agora API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
