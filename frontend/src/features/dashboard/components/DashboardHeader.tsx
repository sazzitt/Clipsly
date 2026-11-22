import * as React from "react";
import { RefreshCw, Sparkles, Terminal } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { StatusIndicator } from "../../../components/ui/status-indicator";
import { SystemHealth } from "../../../types/api";

export interface DashboardHeaderProps {
  systemHealth?: SystemHealth | null;
  isRefreshing: boolean;
  onRefresh: () => void;
  lastUpdated?: Date | null;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  systemHealth,
  isRefreshing,
  onRefresh,
  lastUpdated,
}) => {
  const isHealthy = systemHealth?.status === "healthy";
  const isDegraded = systemHealth?.status === "degraded";

  return (
    <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-r from-violet-950/20 via-card to-card p-6 sm:p-8 shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-mono font-medium border border-primary/20">
            <Sparkles className="h-3 w-3" />
            <span>Local Workstation Active</span>
            <span className="text-zinc-500">•</span>
            <span>NVIDIA RTX 3050</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Clipsly Workstation Dashboard
          </h1>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Local-first AI video clipping workstation running on your local Windows machine. 
            All Whisper transcriptions, highlight detection, and NVENC rendering happen strictly on-device.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 shrink-0">
          <div className="flex items-center gap-3 px-3.5 py-2 rounded-xl bg-secondary/50 border border-border/70 text-xs">
            <StatusIndicator
              status={
                !systemHealth
                  ? "offline"
                  : isHealthy
                  ? "healthy"
                  : isDegraded
                  ? "degraded"
                  : "offline"
              }
              label={
                !systemHealth
                  ? "Connecting"
                  : isHealthy
                  ? "Backend Healthy"
                  : isDegraded
                  ? "Degraded"
                  : "Backend Offline"
              }
            />
            {lastUpdated && (
              <span className="text-[11px] font-mono text-muted-foreground">
                {lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
            )}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isRefreshing}
            className="gap-2 shrink-0 font-medium"
            aria-label="Refresh dashboard data"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            <span>{isRefreshing ? "Refreshing..." : "Refresh Telemetry"}</span>
          </Button>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-border/40 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs text-muted-foreground font-mono">
        <div className="flex items-center gap-2">
          <Terminal className="h-3.5 w-3.5 text-primary" />
          <span>Host: 127.0.0.1:8000</span>
        </div>
        <div>
          <span>Engine: SQLite WAL</span>
        </div>
        <div>
          <span>VRAM Cap: 4.0 GB</span>
        </div>
        <div>
          <span>Encoder: h264_nvenc</span>
        </div>
      </div>
    </div>
  );
};
