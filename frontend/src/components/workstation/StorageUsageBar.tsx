import * as React from "react";
import { AlertTriangle, HardDrive } from "lucide-react";
import { cn } from "../../lib/utils";
import { Progress } from "../ui/progress";

export interface StorageUsageBarProps extends React.HTMLAttributes<HTMLDivElement> {
  freeSpaceGb: number;
  totalSpaceGb?: number;
  minSafeFreeSpaceGb?: number;
}

export const StorageUsageBar = React.forwardRef<HTMLDivElement, StorageUsageBarProps>(
  (
    {
      freeSpaceGb,
      totalSpaceGb = 512,
      minSafeFreeSpaceGb = 10,
      className,
      ...props
    },
    ref
  ) => {
    const isCritical = freeSpaceGb < minSafeFreeSpaceGb;
    const isWarning = freeSpaceGb < minSafeFreeSpaceGb * 2;
    const usedSpaceGb = Math.max(totalSpaceGb - freeSpaceGb, 0);
    const usedPercent = Math.min(Math.max((usedSpaceGb / totalSpaceGb) * 100, 0), 100);

    return (
      <div
        ref={ref}
        className={cn(
          "rounded-lg border border-border bg-card/60 p-4 space-y-2.5",
          isCritical && "border-destructive/40 bg-destructive/5",
          className
        )}
        {...props}
      >
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <HardDrive
              className={cn(
                "h-4 w-4",
                isCritical
                  ? "text-destructive"
                  : isWarning
                  ? "text-amber-400"
                  : "text-muted-foreground"
              )}
            />
            <span className="font-medium text-foreground">Local SSD Storage</span>
          </div>
          <div className="flex items-center gap-2 font-mono tabular-nums text-xs">
            <span className="text-foreground font-semibold">{freeSpaceGb.toFixed(1)} GB free</span>
            <span className="text-muted-foreground">/ {totalSpaceGb.toFixed(0)} GB total</span>
          </div>
        </div>

        {/* Storage Bar */}
        <Progress
          value={usedPercent}
          variant={isCritical ? "destructive" : isWarning ? "warning" : "default"}
          size="sm"
        />

        {/* Warning Alert if Below Minimum Headroom */}
        {isCritical && (
          <div className="flex items-center gap-1.5 text-xs text-destructive pt-1">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            <span>
              Storage space is critical (&lt;{minSafeFreeSpaceGb} GB). Ingestion and NVENC exports may fail.
            </span>
          </div>
        )}
      </div>
    );
  }
);
StorageUsageBar.displayName = "StorageUsageBar";
