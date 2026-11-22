import { createContext } from "react";
import { SystemHealth } from "../types/api";

export interface BackendHealthContextValue {
  health: SystemHealth | null;
  isConnected: boolean;
  isDegraded: boolean;
  loading: boolean;
  error: string | null;
  lastChecked: Date | null;
  refresh: () => Promise<void>;
}

export const BackendHealthContext = createContext<BackendHealthContextValue | null>(null);
