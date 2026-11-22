import React from "react";
import { 
  Activity, 
  Database, 
  Cpu, 
  Video, 
  Clock, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle 
} from "lucide-react";
import { useBackendHealth } from "../hooks/useBackendHealth";

export const HealthStatusCard: React.FC = () => {
  const { health, isConnected, isDegraded, loading, error, lastChecked, refresh } = useBackendHealth();

  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-secondary text-primary">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-foreground">Backend & Hardware Diagnostics</h2>
              <p className="text-xs text-muted-foreground">
                Verifying local FastAPI service, SQLite WAL storage, and NVIDIA GPU runtime
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            {loading && !health ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <RefreshCw className="h-3 w-3 animate-spin" />
                Querying...
              </span>
            ) : isConnected ? (
              isDegraded ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Degraded
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Backend Healthy
                </span>
              )
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">
                <XCircle className="h-3.5 w-3.5" />
                Backend Offline
              </span>
            )}
          </div>

          <button
            onClick={() => refresh()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-secondary hover:bg-secondary/80 text-foreground border border-border transition-colors disabled:opacity-50"
            aria-label="Refresh telemetry diagnostics"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && !health ? (
        <div className="mt-6 p-4 rounded-lg bg-red-950/30 border border-red-800/40 text-red-300 text-xs flex items-start gap-3">
          <XCircle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-red-200">Connection Failed</p>
            <p className="text-red-300/90">{error}</p>
            <p className="text-muted-foreground pt-1">
              Ensure the Python backend is running on <code className="text-foreground font-mono">http://127.0.0.1:8000</code>.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {/* Database Check */}
          <div className="p-4 rounded-lg bg-secondary/50 border border-border/80 flex items-start gap-3">
            <div className="p-2 rounded-md bg-secondary text-foreground shrink-0">
              <Database className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="space-y-0.5">
              <p className="text-xs text-muted-foreground">Database Storage</p>
              <p className="text-sm font-medium text-foreground">
                {health?.database_connected ? "SQLite 3 (WAL Mode)" : "Disconnected"}
              </p>
              <p className="text-[11px] text-muted-foreground">data/clipsly.db</p>
            </div>
          </div>

          {/* CUDA Acceleration */}
          <div className="p-4 rounded-lg bg-secondary/50 border border-border/80 flex items-start gap-3">
            <div className="p-2 rounded-md bg-secondary text-foreground shrink-0">
              <Cpu className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="space-y-0.5">
              <p className="text-xs text-muted-foreground">AI Compute Support</p>
              <p className="text-sm font-medium text-foreground">
                {health?.cuda_available ? "NVIDIA CUDA Ready" : "CPU Fallback Mode"}
              </p>
              <p className="text-[11px] text-muted-foreground">RTX 3050 Laptop GPU</p>
            </div>
          </div>

          {/* NVENC Hardware Encoder */}
          <div className="p-4 rounded-lg bg-secondary/50 border border-border/80 flex items-start gap-3">
            <div className="p-2 rounded-md bg-secondary text-foreground shrink-0">
              <Video className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="space-y-0.5">
              <p className="text-xs text-muted-foreground">Hardware Encoder</p>
              <p className="text-sm font-medium text-foreground">
                {health?.nvenc_available ? "FFmpeg h264_nvenc" : "Software x264"}
              </p>
              <p className="text-[11px] text-muted-foreground">NVENC Accelerated</p>
            </div>
          </div>

          {/* Uptime & Version */}
          <div className="p-4 rounded-lg bg-secondary/50 border border-border/80 flex items-start gap-3">
            <div className="p-2 rounded-md bg-secondary text-foreground shrink-0">
              <Clock className="h-4 w-4 text-primary" />
            </div>
            <div className="space-y-0.5">
              <p className="text-xs text-muted-foreground">Backend Uptime</p>
              <p className="text-sm font-medium text-foreground font-mono">
                {health ? `${health.uptime_seconds.toFixed(1)}s` : "--"}
              </p>
              <p className="text-[11px] text-muted-foreground">
                API Version: {health?.version ?? "1.0.0"}
              </p>
            </div>
          </div>
        </div>
      )}

      {lastChecked && (
        <div className="mt-4 pt-3 border-t border-border/50 text-[11px] text-muted-foreground flex justify-between items-center">
          <span>Endpoint: <code className="text-foreground">GET /api/v1/system/health</code></span>
          <span>Last synchronized: {lastChecked.toLocaleTimeString()}</span>
        </div>
      )}
    </div>
  );
};
