import * as React from "react";
import { AlertCircle, CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";
import { cn } from "../../lib/utils";
import { Badge } from "../ui/badge";
import { Progress } from "../ui/progress";

export type JobStatus = "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED" | "CANCELLED";

export interface ProcessingStatusProps extends React.HTMLAttributes<HTMLDivElement> {
  status: JobStatus;
  progressPercent?: number;
  currentStep?: string;
  errorMessage?: string | null;
  jobType?: string;
}

export const ProcessingStatus = React.forwardRef<HTMLDivElement, ProcessingStatusProps>(
  (
    {
      status,
      progressPercent = 0,
      currentStep,
      errorMessage,
      jobType,
      className,
      ...props
    },
    ref
  ) => {
    const statusConfig: Record<
      JobStatus,
      {
        badgeVariant: "default" | "secondary" | "destructive" | "success" | "warning";
        icon: React.ReactNode;
        label: string;
      }
    > = {
      QUEUED: {
        badgeVariant: "secondary",
        icon: <Clock className="h-3.5 w-3.5 text-zinc-400" />,
        label: "Queued",
      },
      PROCESSING: {
        badgeVariant: "default",
        icon: <Loader2 className="h-3.5 w-3.5 animate-spin text-primary-foreground" />,
        label: "Processing",
      },
      COMPLETED: {
        badgeVariant: "success",
        icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />,
        label: "Completed",
      },
      FAILED: {
        badgeVariant: "destructive",
        icon: <AlertCircle className="h-3.5 w-3.5 text-destructive-foreground" />,
        label: "Failed",
      },
      CANCELLED: {
        badgeVariant: "warning",
        icon: <XCircle className="h-3.5 w-3.5 text-amber-400" />,
        label: "Cancelled",
      },
    };

    const currentConfig = statusConfig[status] || statusConfig.QUEUED;

    return (
      <div
        ref={ref}
        className={cn(
          "rounded-lg border border-border bg-card/60 p-4 space-y-3",
          className
        )}
        {...props}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Badge variant={currentConfig.badgeVariant} className="gap-1.5">
              {currentConfig.icon}
              <span>{currentConfig.label}</span>
            </Badge>
            {jobType && (
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {jobType}
              </span>
            )}
          </div>
          {status === "PROCESSING" && (
            <span className="font-mono text-xs font-semibold text-primary tabular-nums">
              {Math.round(progressPercent)}%
            </span>
          )}
        </div>

        {/* Progress Bar */}
        {(status === "PROCESSING" || status === "QUEUED") && (
          <Progress
            value={progressPercent}
            indeterminate={status === "QUEUED"}
            size="sm"
          />
        )}

        {/* Step description */}
        {currentStep && (
          <p className="text-xs text-muted-foreground flex items-center gap-1.5">
            <span className="h-1 w-1 rounded-full bg-zinc-500" />
            <span>{currentStep}</span>
          </p>
        )}

        {/* Error message */}
        {status === "FAILED" && errorMessage && (
          <div className="rounded border border-destructive/20 bg-destructive/10 p-2.5 text-xs text-destructive">
            <p className="font-medium">Error occurred:</p>
            <p className="mt-0.5 text-destructive/80 font-mono text-[11px]">{errorMessage}</p>
          </div>
        )}
      </div>
    );
  }
);
ProcessingStatus.displayName = "ProcessingStatus";
