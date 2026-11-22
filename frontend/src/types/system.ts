export interface SystemHealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  database_connected: boolean;
  cuda_available: boolean;
  nvenc_available: boolean;
  active_jobs_count: number;
  uptime_seconds: number;
}

export interface RootApiResponse {
  application: string;
  version: string;
  docs: string;
  health: string;
}
