import * as React from "react";
import { Folder, Database, HardDrive, AlertTriangle } from "lucide-react";
import { StorageUsageBar } from "../../../components/workstation/StorageUsageBar";
import { DashboardStorageSummary } from "../../../types/api";

export interface DashboardStorageProps {
  storage: DashboardStorageSummary;
}

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export const DashboardStorage: React.FC<DashboardStorageProps> = ({ storage }) => {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <HardDrive className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold tracking-tight text-foreground">Storage Diagnostics</h2>
        </div>
        <span className="text-xs font-mono text-muted-foreground">
          Clipsly Storage: <strong className="text-foreground">{formatBytes(storage.clipsly_storage_bytes)}</strong>
        </span>
      </div>

      <StorageUsageBar
        freeSpaceGb={storage.ssd_free_gb}
        totalSpaceGb={storage.ssd_total_gb}
        minSafeFreeSpaceGb={10}
      />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-3 py-2 rounded-lg bg-card/40 border border-border/50 text-xs text-muted-foreground">
        <div className="flex items-center gap-2 truncate">
          <Folder className="h-3.5 w-3.5 text-zinc-500 shrink-0" />
          <span className="truncate">Storage Directory: <code className="text-zinc-300 font-mono text-[11px]">{storage.storage_path}</code></span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0 text-[11px]">
          <Database className="h-3 w-3 text-zinc-500" />
          <span>Local NVMe SSD</span>
          {storage.is_critical && (
            <span className="text-destructive font-semibold flex items-center gap-1 ml-2">
              <AlertTriangle className="h-3 w-3" />
              Low Storage Space
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
