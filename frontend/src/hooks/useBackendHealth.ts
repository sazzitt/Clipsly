import { useContext } from "react";
import { BackendHealthContext, BackendHealthContextValue } from "../context/BackendHealthContext";

export function useBackendHealth(): BackendHealthContextValue {
  const context = useContext(BackendHealthContext);
  if (!context) {
    throw new Error("useBackendHealth must be used within a BackendHealthProvider");
  }
  return context;
}
