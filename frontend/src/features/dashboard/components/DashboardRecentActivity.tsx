import * as React from "react";
import { Activity, Clock } from "lucide-react";
import { DashboardRecentJobItem } from "../../../types/api";
import { ProcessingStatus, JobStatus } from "../../../components/workstation/ProcessingStatus";

export interface DashboardRecentActivityProps {
  jobs: DashboardRecentJobItem[];
}

export const DashboardRecentActivity: React.FC<DashboardRecentActivityProps> = ({ jobs }) => {
  const normalizeJobStatus = (status: string): JobStatus => {
    const s = status.toUpperCase();
    if (s === "PENDING" || s === "QUEUED") return "QUEUED";
    if (s === "PROCESSING" || s === "RUNNING") return "PROCESSING";
    if (s === "COMPLETED") return "COMPLETED";
    if (s === "FAILED") return "FAILED";
    if (s === "CANCELLED") return "CANCELLED";
    return "QUEUED";
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "";
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold tracking-tight text-foreground">Recent Processing Jobs</h2>
        </div>
        <span className="text-xs font-mono text-muted-foreground">FIFO Background Queue</span>
      </div>

      {jobs.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 p-8 text-center space-y-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary text-muted-foreground">
            <Activity className="h-5 w-5 text-zinc-500" />
          </div>
          <h3 className="text-sm font-medium text-foreground">No Background Tasks</h3>
          <p className="max-w-md text-xs text-muted-foreground">
            All AI transcription, highlight scoring, and NVENC rendering queues are currently idle.
            Import a video or generate clips to view real-time job execution.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="rounded-xl border border-border bg-card p-4 space-y-2"
            >
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="font-mono text-[11px]">Job ID: {job.id.slice(0, 8)}</span>
                {job.created_at && (
                  <span className="flex items-center gap-1 font-mono text-[11px]">
                    <Clock className="h-3 w-3" />
                    {formatDate(job.created_at)}
                  </span>
                )}
              </div>

              <ProcessingStatus
                jobType={job.job_type}
                status={normalizeJobStatus(job.status)}
                progressPercent={job.progress_percent}
                currentStep={job.current_step}
                errorMessage={job.error_message}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
