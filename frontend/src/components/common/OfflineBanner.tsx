import React from "react";
import { WifiOff, RefreshCw } from "lucide-react";
import { useBackendHealth } from "../../hooks/useBackendHealth";

export const OfflineBanner: React.FC = () => {
  const { isConnected, loading, refresh, error } = useBackendHealth();

  if (isConnected) {
    return null;
  }

  return (
    <div className="bg-red-950/80 border-b border-red-800/60 px-4 py-2.5 text-xs text-red-200">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <WifiOff className="h-4 w-4 text-red-400 shrink-0" />
          <span>
            <strong>Local Backend Offline:</strong> Unable to connect to FastAPI service at{" "}
            <code className="text-white font-mono bg-red-900/40 px-1 py-0.5 rounded">
              http://127.0.0.1:8000
            </code>
            {error && <span className="opacity-80"> — {error}</span>}
          </span>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-red-900/60 hover:bg-red-800/80 text-white font-medium text-[11px] border border-red-700/60 transition-colors shrink-0 disabled:opacity-50"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          Retry Connection
        </button>
      </div>
    </div>
  );
};
