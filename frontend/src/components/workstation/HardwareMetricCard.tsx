import * as React from "react";
import { cn } from "../../lib/utils";
import { Card } from "../ui/card";
import { Progress } from "../ui/progress";

export interface HardwareMetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  value: string | number;
  subValue?: string;
  icon: React.ReactNode;
  percent?: number;
  status?: "safe" | "warning" | "error" | "neutral";
}

export const HardwareMetricCard = React.forwardRef<HTMLDivElement, HardwareMetricCardProps>(
  (
    {
      title,
      value,
      subValue,
      icon,
      percent,
      status = "safe",
      className,
      ...props
    },
    ref
  ) => {
    const statusStyles = {
      safe: "text-emerald-400",
      warning: "text-amber-400",
      error: "text-destructive",
      neutral: "text-muted-foreground",
    };

    const progressVariantMap: Record<string, "default" | "success" | "warning" | "destructive"> = {
      safe: "success",
      warning: "warning",
      error: "destructive",
      neutral: "default",
    };

    return (
      <Card
        ref={ref}
        variant="metric"
        className={cn("space-y-3", className)}
        {...props}
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">{title}</span>
          <div className={cn("h-4 w-4 shrink-0", statusStyles[status])}>
            {icon}
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex items-baseline justify-between">
            <span className="font-mono text-xl font-bold tracking-tight text-foreground tabular-nums">
              {value}
            </span>
            {percent !== undefined && (
              <span className={cn("font-mono text-xs font-semibold tabular-nums", statusStyles[status])}>
                {Math.round(percent)}%
              </span>
            )}
          </div>
          {subValue && (
            <p className="text-[11px] text-muted-foreground leading-none">{subValue}</p>
          )}
        </div>

        {percent !== undefined && (
          <Progress
            value={percent}
            variant={progressVariantMap[status] || "default"}
            size="sm"
          />
        )}
      </Card>
    );
  }
);
HardwareMetricCard.displayName = "HardwareMetricCard";
