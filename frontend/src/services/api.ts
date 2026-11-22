import { SystemHealthResponse, RootApiResponse } from "../types/system";

export async function fetchSystemHealth(): Promise<SystemHealthResponse> {
  const response = await fetch("/api/v1/system/health", {
    method: "GET",
    headers: {
      "Accept": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchRootMeta(): Promise<RootApiResponse> {
  const response = await fetch("/", {
    method: "GET",
    headers: {
      "Accept": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Root meta ping failed with status ${response.status}`);
  }

  return response.json();
}
