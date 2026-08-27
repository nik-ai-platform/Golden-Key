const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://localhost:8000/api/v1" : "/api/v1");

export interface ApiHealth {
  online: boolean;
  apiVersion?: string;
}

export async function checkApiHealth(): Promise<ApiHealth> {
  try {
    const response = await fetch(`${API_BASE_URL}/version`, { cache: "no-store" });
    if (!response.ok) return { online: false };

    const data = await response.json() as { api_version?: string };
    return { online: true, apiVersion: data.api_version };
  } catch {
    return { online: false };
  }
}
