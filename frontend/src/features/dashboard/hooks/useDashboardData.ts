import { useCallback, useEffect, useRef, useState } from "react";
import { api, ClipslyApiError } from "../../../services/api";
import { DashboardSummary } from "../../../types/api";

export interface UseDashboardDataReturn {
  summary: DashboardSummary | null;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useDashboardData(): UseDashboardDataReturn {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchDashboard = useCallback(async (isManualRefresh = false) => {
    // Abort previous in-flight request if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    if (isManualRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const data = await api.system.getDashboard(controller.signal);
      setSummary(data);
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      if (err instanceof ClipslyApiError) {
        setError(err.detail || "Failed to load workstation dashboard.");
      } else if (err instanceof Error) {
        setError(err.message || "Failed to communicate with local backend.");
      } else {
        setError("An unexpected error occurred while fetching dashboard telemetry.");
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard(false);

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchDashboard]);

  const refresh = useCallback(async () => {
    await fetchDashboard(true);
  }, [fetchDashboard]);

  return {
    summary,
    isLoading,
    isRefreshing,
    error,
    refresh,
  };
}
