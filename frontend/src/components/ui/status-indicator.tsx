import * as React from "react";
import { cn } from "../../lib/utils";

export type StatusType = "healthy" | "degraded" | "error" | "processing" | "offline" | "neutral";

export interface StatusIndicatorProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: StatusType;
  label?: string;
  pulse?: boolean;
  size?: "sm" | "default" | "lg";
}

const statusColors: Record<StatusType, { dot: string; ping: string; text: string }> = {
  healthy: {
    dot: "bg-emerald-500",
    ping: "bg-emerald-400",
    text: "text-emerald-400",
  },
  degraded: {
    dot: "bg-amber-500",
    ping: "bg-amber-400",
    text: "text-amber-400",
  },
  error: {
    dot: "bg-destructive",
    ping: "bg-red-400",
    text: "text-destructive",
  },
  processing: {
    dot: "bg-primary",
    ping: "bg-violet-400",
    text: "text-primary",
  },
  offline: {
    dot: "bg-zinc-500",
    ping: "bg-zinc-400",
    text: "text-zinc-400",
  },
  neutral: {
    dot: "bg-zinc-400",
    ping: "bg-zinc-300",
    text: "text-muted-foreground",
  },
};

const sizeStyles = {
  sm: "h-1.5 w-1.5",
  default: "h-2 w-2",
  lg: "h-2.5 w-2.5",
};

export const StatusIndicator = React.forwardRef<HTMLSpanElement, StatusIndicatorProps>(
  ({ status, label, pulse = false, size = "default", className, ...props }, ref) => {
    const config = statusColors[status] || statusColors.neutral;

    return (
      <span
        ref={ref}
        className={cn("inline-flex items-center gap-1.5 select-none", className)}
        {...props}
      >
        <span className="relative flex shrink-0 items-center justify-center">
          {pulse && (
            <span
              className={cn(
                "absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping",
                config.ping
              )}
            />
          )}
          <span className={cn("relative inline-flex rounded-full", sizeStyles[size], config.dot)} />
        </span>
        {label && (
          <span className={cn("text-xs font-medium leading-none", config.text)}>{label}</span>
        )}
      </span>
    );
  }
);
StatusIndicator.displayName = "StatusIndicator";
