import React, { useCallback, useEffect, useState } from "react";
import { Activity, RefreshCw, XCircle, Clock, AlertCircle } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Button } from "../../components/ui/button";
import { Skeleton } from "../../components/ui/skeleton";
import { ProcessingStatus, JobStatus } from "../../components/workstation/ProcessingStatus";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { useToast } from "../../hooks/useToast";
import { api, ClipslyApiError } from "../../services/api";
import { ProcessingJob } from "../../types/api";
import {
  SearchInput,
  FilterSelect,
  SortSelector,
  PaginationControls,
  NoResultsState,
} from "../../components/management";

const STATUS_OPTIONS = [
  { value: "ALL", label: "All Statuses" },
  { value: "QUEUED", label: "Queued" },
  { value: "PROCESSING", label: "Processing" },
  { value: "COMPLETED", label: "Completed" },
  { value: "FAILED", label: "Failed" },
  { value: "CANCELLED", label: "Cancelled" },
];

const JOB_TYPE_OPTIONS = [
  { value: "ALL", label: "All Types" },
  { value: "INGESTION", label: "Ingestion" },
  { value: "AUDIO_EXTRACTION", label: "Audio Extraction" },
  { value: "WHISPER_TRANSCRIPTION", label: "Whisper Transcription" },
  { value: "HIGHLIGHT_SCORING", label: "Highlight Scoring" },
  { value: "CLIP_GENERATION", label: "Clip Generation" },
  { value: "EXPORT_RENDER", label: "Export Render" },
];

const SORT_OPTIONS = [
  { value: "created_at", label: "Created Date" },
  { value: "updated_at", label: "Updated Date" },
  { value: "progress_percent", label: "Progress" },
  { value: "status", label: "Status" },
  { value: "job_type", label: "Job Type" },
];

export const JobsPage: React.FC = () => {
  const toast = useToast();

  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [limit] = useState<number>(15);
  const [search, setSearch] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [jobTypeFilter, setJobTypeFilter] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<string>("created_at");
  const [order, setOrder] = useState<"asc" | "desc">("desc");

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Job cancellation modal
  const [jobToCancel, setJobToCancel] = useState<ProcessingJob | null>(null);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);

  const fetchJobs = useCallback(
    async (isManual = false) => {
      if (isManual) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      try {
        const res = await api.jobs.list({
          page,
          limit,
          status: statusFilter === "ALL" ? undefined : statusFilter,
          job_type: jobTypeFilter === "ALL" ? undefined : jobTypeFilter,
          search: search.trim() || undefined,
          sort_by: sortBy,
          order,
        });
        setJobs(res.items);
        setTotal(res.total);
      } catch (err: unknown) {
        if (err instanceof ClipslyApiError) {
          setError(err.detail);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to fetch jobs queue from backend.");
        }
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [page, limit, statusFilter, jobTypeFilter, search, sortBy, order]
  );

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleClearFilters = () => {
    setSearch("");
    setStatusFilter("ALL");
    setJobTypeFilter("ALL");
    setSortBy("created_at");
    setOrder("desc");
    setPage(1);
  };

  const handleCancelConfirm = async () => {
    if (!jobToCancel) return;
    setIsCancelling(true);

    try {
      await api.jobs.cancel(jobToCancel.id);
      toast.success("Job Cancelled", `Job ${jobToCancel.id.slice(0, 8)} was stopped.`);
      setJobToCancel(null);
      fetchJobs(true);
    } catch (err: unknown) {
      const msg = err instanceof ClipslyApiError ? err.detail : "Failed to cancel job.";
      toast.error("Cancellation Failed", msg);
    } finally {
      setIsCancelling(false);
    }
  };

  const normalizeJobStatus = (status: string): JobStatus => {
    const s = status.toUpperCase();
    if (s === "PENDING" || s === "QUEUED") return "QUEUED";
    if (s === "PROCESSING" || s === "RUNNING") return "PROCESSING";
    if (s === "COMPLETED") return "COMPLETED";
    if (s === "FAILED") return "FAILED";
    if (s === "CANCELLED") return "CANCELLED";
    return "QUEUED";
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <PageContainer
      title="Processing Jobs"
      description="Inspect background task execution, sequential AI pipeline progress, and cancel active jobs."
      action={
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchJobs(true)}
          disabled={isRefreshing || isLoading}
          className="gap-1.5 h-8 text-xs"
          aria-label="Refresh job queue"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          <span>{isRefreshing ? "Refreshing..." : "Refresh Queue"}</span>
        </Button>
      }
    >
      {/* Search and Filters Toolbar */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 p-3.5 rounded-xl border border-border bg-card/60 shadow-sm">
        <SearchInput
          value={search}
          onChange={(val) => {
            setSearch(val);
            setPage(1);
          }}
          placeholder="Search by job ID, step, error..."
        />

        <div className="flex flex-wrap items-center gap-3">
          <FilterSelect
            label="Status"
            value={statusFilter}
            onChange={(val) => {
              setStatusFilter(val);
              setPage(1);
            }}
            options={STATUS_OPTIONS}
          />

          <FilterSelect
            label="Type"
            value={jobTypeFilter}
            onChange={(val) => {
              setJobTypeFilter(val);
              setPage(1);
            }}
            options={JOB_TYPE_OPTIONS}
          />

          <SortSelector
            sortBy={sortBy}
            onSortChange={(val) => {
              setSortBy(val);
              setPage(1);
            }}
            order={order}
            onOrderToggle={() => {
              setOrder((prev) => (prev === "asc" ? "desc" : "asc"));
              setPage(1);
            }}
            options={SORT_OPTIONS}
          />
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading && !isRefreshing ? (
        <div className="space-y-3" data-testid="jobs-loading-skeleton">
          {Array.from({ length: 4 }).map((_, idx) => (
            <div key={idx} className="rounded-xl border border-border bg-card p-4 space-y-3">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-2 w-full" />
              <Skeleton className="h-3 w-32" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-8 text-center space-y-3">
          <p className="text-sm font-semibold text-destructive">Failed to Load Processing Jobs</p>
          <p className="text-xs text-muted-foreground">{error}</p>
          <Button onClick={() => fetchJobs()} variant="outline" size="sm" className="mt-2 text-xs">
            Retry
          </Button>
        </div>
      ) : total === 0 ? (
        search || statusFilter !== "ALL" || jobTypeFilter !== "ALL" ? (
          <NoResultsState
            title="No Matching Processing Jobs"
            description="No background jobs match your current search and filter criteria."
            onClearFilters={handleClearFilters}
          />
        ) : (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 p-12 text-center space-y-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary text-muted-foreground">
              <Activity className="h-6 w-6 text-zinc-500" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">No Background Tasks Queued</h3>
            <p className="max-w-sm text-xs text-muted-foreground leading-relaxed">
              When audio extraction, Faster-Whisper, and NVENC video exports run, live task progress will appear here.
            </p>
          </div>
        )
      ) : (
        <div className="space-y-4">
          <div className="space-y-3">
            {jobs.map((job) => {
              const isCancellable =
                job.status.toUpperCase() === "QUEUED" ||
                job.status.toUpperCase() === "PROCESSING" ||
                job.status.toUpperCase() === "PENDING" ||
                job.status.toUpperCase() === "RUNNING";

              return (
                <div
                  key={job.id}
                  className="rounded-xl border border-border bg-card p-4 space-y-3 transition-colors hover:border-zinc-700"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-muted-foreground font-mono">
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-foreground">
                        Job: {job.id.slice(0, 8)}
                      </span>
                      <span>•</span>
                      <span>Video ID: {job.video_id.slice(0, 8)}</span>
                      {job.process_pid && (
                        <>
                          <span>•</span>
                          <span>PID: {job.process_pid}</span>
                        </>
                      )}
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1 text-[11px]">
                        <Clock className="h-3 w-3" />
                        {new Date(job.created_at).toLocaleString([], {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </span>

                      {isCancellable && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setJobToCancel(job)}
                          className="h-6 text-xs text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 gap-1 px-2"
                        >
                          <XCircle className="h-3 w-3" />
                          <span>Cancel</span>
                        </Button>
                      )}
                    </div>
                  </div>

                  <ProcessingStatus
                    jobType={job.job_type}
                    status={normalizeJobStatus(job.status)}
                    progressPercent={job.progress_percent}
                    currentStep={job.current_step}
                    errorMessage={job.error_message}
                  />
                </div>
              );
            })}
          </div>

          <PaginationControls
            currentPage={page}
            totalPages={totalPages}
            totalItems={total}
            limit={limit}
            onPageChange={(p) => setPage(p)}
          />
        </div>
      )}

      {/* Job Cancellation Confirmation Dialog */}
      <Dialog open={!!jobToCancel} onOpenChange={(open) => !open && setJobToCancel(null)}>
        <DialogContent className="max-w-md border-amber-500/30 bg-card p-6 shadow-2xl">
          <DialogHeader className="space-y-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500/15 text-amber-400">
              <AlertCircle className="h-5 w-5" />
            </div>
            <DialogTitle className="text-base font-semibold text-foreground">
              Cancel Processing Task
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground leading-relaxed">
              Are you sure you want to stop job{" "}
              <strong className="text-foreground font-mono">{jobToCancel?.id.slice(0, 8)}</strong> (
              {jobToCancel?.job_type})?
            </DialogDescription>
          </DialogHeader>

          <p className="my-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 leading-relaxed">
            Stopping an active task will terminate execution and clear temporary scratch files.
          </p>

          <DialogFooter className="gap-2 sm:gap-0 mt-4">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setJobToCancel(null)}
              disabled={isCancelling}
              className="text-xs"
            >
              Keep Running
            </Button>
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={handleCancelConfirm}
              loading={isCancelling}
              disabled={isCancelling}
              className="text-xs gap-1.5 bg-amber-600 hover:bg-amber-700 text-white"
            >
              <XCircle className="h-3.5 w-3.5" />
              <span>{isCancelling ? "Cancelling..." : "Cancel Task"}</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
};
