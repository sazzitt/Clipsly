import React, { useEffect, useState, useCallback, useRef } from "react";
import { SystemHealth } from "../../types/api";
import { api } from "../../services/api";
import { BackendHealthContext } from "../../context/BackendHealthContext";

export interface BackendHealthProviderProps {
  children: React.ReactNode;
  pollIntervalMs?: number;
  autoPoll?: boolean;
}

export const BackendHealthProvider: React.FC<BackendHealthProviderProps> = ({
  children,
  pollIntervalMs = 20000,
  autoPoll = true,
}) => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const checkHealth = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    try {
      const data = await api.system.getHealth(controller.signal);
      setHealth(data);
      setError(null);
      setLastChecked(new Date());
    } catch (err: unknown) {
      if (controller.signal.aborted) {
        return;
      }
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to connect to local backend service");
      }
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();

    if (!autoPoll) return;

    const intervalId = setInterval(() => {
      checkHealth();
    }, pollIntervalMs);

    return () => {
      clearInterval(intervalId);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [checkHealth, autoPoll, pollIntervalMs]);

  const isConnected = !!health && !error;
  const isDegraded = health?.status === "degraded";

  return (
    <BackendHealthContext.Provider
      value={{
        health,
        isConnected,
        isDegraded,
        loading,
        error,
        lastChecked,
        refresh: checkHealth,
      }}
    >
      {children}
    </BackendHealthContext.Provider>
  );
};
