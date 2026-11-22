import { SystemHealth } from "./api";

export type SystemHealthResponse = SystemHealth;

export interface RootApiResponse {
  application: string;
  version: string;
  docs: string;
  health: string;
}

export * from "./api";
