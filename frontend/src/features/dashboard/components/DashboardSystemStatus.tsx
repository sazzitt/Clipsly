import * as React from "react";
import { Database, Cpu, Video, Clock, CheckCircle2, AlertTriangle, ShieldCheck } from "lucide-react";
import { SystemHealth } from "../../../types/api";

export interface DashboardSystemStatusProps {
  system: SystemHealth;
}

export const DashboardSystemStatus: React.FC<DashboardSystemStatusProps> = ({ system }) => {
  const isHealthy = system.status === "healthy";

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold tracking-tight text-foreground">Backend & Pipeline Readiness</h2>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          {isHealthy ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <CheckCircle2 className="h-3 w-3" />
              All Systems Operational
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <AlertTriangle className="h-3 w-3" />
              Pipeline Degraded
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Database Check */}
        <div className="p-4 rounded-xl bg-card border border-border flex items-start gap-3">
          <div className="p-2 rounded-lg bg-secondary text-foreground shrink-0">
            <Database className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="space-y-0.5 min-w-0">
            <p className="text-xs text-muted-foreground">Database Storage</p>
            <p className="text-sm font-medium text-foreground truncate">
              {system.database_connected ? "SQLite 3 (WAL Mode)" : "Disconnected"}
            </p>
            <p className="text-[11px] text-muted-foreground truncate">data/clipsly.db</p>
          </div>
        </div>

        {/* CUDA Acceleration */}
        <div className="p-4 rounded-xl bg-card border border-border flex items-start gap-3">
          <div className="p-2 rounded-lg bg-secondary text-foreground shrink-0">
            <Cpu className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="space-y-0.5 min-w-0">
            <p className="text-xs text-muted-foreground">AI Compute Support</p>
            <p className="text-sm font-medium text-foreground truncate">
              {system.cuda_available ? "NVIDIA CUDA Ready" : "CPU Fallback Mode"}
            </p>
            <p className="text-[11px] text-muted-foreground truncate">RTX 3050 Laptop GPU</p>
          </div>
        </div>

        {/* NVENC Hardware Encoder */}
        <div className="p-4 rounded-xl bg-card border border-border flex items-start gap-3">
          <div className="p-2 rounded-lg bg-secondary text-foreground shrink-0">
            <Video className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="space-y-0.5 min-w-0">
            <p className="text-xs text-muted-foreground">Hardware Encoder</p>
            <p className="text-sm font-medium text-foreground truncate">
              {system.nvenc_available ? "FFmpeg h264_nvenc" : "Software x264"}
            </p>
            <p className="text-[11px] text-muted-foreground truncate">NVENC 9:16 Pipeline</p>
          </div>
        </div>

        {/* Uptime & Version */}
        <div className="p-4 rounded-xl bg-card border border-border flex items-start gap-3">
          <div className="p-2 rounded-lg bg-secondary text-foreground shrink-0">
            <Clock className="h-4 w-4 text-primary" />
          </div>
          <div className="space-y-0.5 min-w-0">
            <p className="text-xs text-muted-foreground">Backend Uptime</p>
            <p className="text-sm font-medium text-foreground font-mono">
              {system.uptime_seconds.toFixed(1)}s
            </p>
            <p className="text-[11px] text-muted-foreground truncate">
              v{system.version} • {system.active_jobs_count} active jobs
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
