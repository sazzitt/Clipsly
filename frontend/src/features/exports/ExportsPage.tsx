import React, { useCallback, useEffect, useState } from "react";
import { Download, RefreshCw, Trash2, CheckCircle2, HardDrive } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Button } from "../../components/ui/button";
import { Skeleton } from "../../components/ui/skeleton";
import { Badge } from "../../components/ui/badge";
import { useToast } from "../../hooks/useToast";
import { api, ClipslyApiError } from "../../services/api";
import { ExportJob } from "../../types/api";
import {
  SearchInput,
  FilterSelect,
  SortSelector,
  PaginationControls,
  DeleteConfirmationDialog,
  NoResultsState,
  EntityStatusBadge,
} from "../../components/management";

const STATUS_OPTIONS = [
  { value: "ALL", label: "All Statuses" },
  { value: "PENDING", label: "Pending" },
  { value: "RENDERING", label: "Rendering" },
  { value: "COMPLETED", label: "Completed" },
  { value: "FAILED", label: "Failed" },
];

const SORT_OPTIONS = [
  { value: "created_at", label: "Creation Date" },
  { value: "output_filename", label: "Output Filename" },
  { value: "file_size_bytes", label: "File Size" },
  { value: "render_time_seconds", label: "Render Time" },
  { value: "status", label: "Status" },
];

function formatBytes(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return "--";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export const ExportsPage: React.FC = () => {
  const toast = useToast();

  const [exportsList, setExportsList] = useState<ExportJob[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [limit] = useState<number>(12);
  const [search, setSearch] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<string>("created_at");
  const [order, setOrder] = useState<"asc" | "desc">("desc");

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Deletion modal
  const [exportToDelete, setExportToDelete] = useState<ExportJob | null>(null);
  const [deleteFile, setDeleteFile] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const fetchExports = useCallback(
    async (isManual = false) => {
      if (isManual) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      try {
        const res = await api.exports.list({
          page,
          limit,
          search: search.trim() || undefined,
          status: statusFilter === "ALL" ? undefined : statusFilter,
          sort_by: sortBy,
          order,
        });
        setExportsList(res.items);
        setTotal(res.total);
      } catch (err: unknown) {
        if (err instanceof ClipslyApiError) {
          setError(err.detail);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to fetch export records from backend.");
        }
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [page, limit, search, statusFilter, sortBy, order]
  );

  useEffect(() => {
    fetchExports();
  }, [fetchExports]);

  const handleClearFilters = () => {
    setSearch("");
    setStatusFilter("ALL");
    setSortBy("created_at");
    setOrder("desc");
    setPage(1);
  };

  const handleDeleteConfirm = async () => {
    if (!exportToDelete) return;
    setIsDeleting(true);

    try {
      await api.exports.delete(exportToDelete.id, deleteFile);
      toast.success("Export Record Removed", `${exportToDelete.output_filename} was removed.`);
      setExportToDelete(null);
      setDeleteFile(false);
      fetchExports(true);
    } catch (err: unknown) {
      const msg = err instanceof ClipslyApiError ? err.detail : "Failed to delete export record.";
      toast.error("Deletion Failed", msg);
    } finally {
      setIsDeleting(false);
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <PageContainer
      title="Export Queue"
      description="Monitor hardware-accelerated NVENC video rendering and manage finished 9:16 vertical exports."
      action={
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchExports(true)}
          disabled={isRefreshing || isLoading}
          className="gap-1.5 h-8 text-xs"
          aria-label="Refresh export queue"
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
          placeholder="Search by output filename..."
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="exports-loading-skeleton">
          {Array.from({ length: 6 }).map((_, idx) => (
            <div key={idx} className="rounded-xl border border-border bg-card p-4 space-y-3">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-20 w-full rounded-lg" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-8 text-center space-y-3">
          <p className="text-sm font-semibold text-destructive">Failed to Load Export Records</p>
          <p className="text-xs text-muted-foreground">{error}</p>
          <Button onClick={() => fetchExports()} variant="outline" size="sm" className="mt-2 text-xs">
            Retry
          </Button>
        </div>
      ) : total === 0 ? (
        search || statusFilter !== "ALL" ? (
          <NoResultsState
            title="No Matching Export Records"
            description="No export jobs match your current search and filter criteria."
            onClearFilters={handleClearFilters}
          />
        ) : (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 p-12 text-center space-y-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary text-muted-foreground">
              <Download className="h-6 w-6 text-zinc-500" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">No Rendered Exports</h3>
            <p className="max-w-sm text-xs text-muted-foreground leading-relaxed">
              When video clips are queued for rendering, hardware-accelerated NVENC exports will appear here with output file paths and render duration.
            </p>
          </div>
        )
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {exportsList.map((job) => (
              <div
                key={job.id}
                className="group flex flex-col justify-between rounded-xl border border-border bg-card p-4 transition-all hover:border-zinc-700 hover:bg-card-hover"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-1 min-w-0">
                      <h3
                        className="text-sm font-semibold text-foreground truncate group-hover:text-primary transition-colors"
                        title={job.output_filename}
                      >
                        {job.output_filename}
                      </h3>
                      {job.clip_title && (
                        <p className="text-[11px] font-mono text-muted-foreground truncate">
                          Source Clip: {job.clip_title}
                        </p>
                      )}
                    </div>
                    <EntityStatusBadge status={job.status} />
                  </div>

                  {/* Render Specifications */}
                  <div className="p-3 rounded-lg bg-secondary/40 border border-border/60 text-xs font-mono space-y-2">
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>Resolution:</span>
                      <span className="text-foreground font-semibold">{job.resolution} (9:16)</span>
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>Encoder:</span>
                      <span className="text-foreground font-semibold">{job.encoder}</span>
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>Render Time:</span>
                      <span className="text-foreground font-semibold">
                        {job.render_time_seconds ? `${job.render_time_seconds.toFixed(1)}s` : "--"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>File Size:</span>
                      <span className="text-foreground font-semibold">
                        {formatBytes(job.file_size_bytes)}
                      </span>
                    </div>
                  </div>

                  {/* File on disk status indicator */}
                  <div className="flex items-center justify-between text-xs pt-1">
                    <div className="flex items-center gap-1.5 text-[11px]">
                      {job.file_exists ? (
                        <>
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                          <span className="text-emerald-400 font-medium">MP4 Saved on SSD</span>
                        </>
                      ) : (
                        <>
                          <HardDrive className="h-3.5 w-3.5 text-zinc-500" />
                          <span className="text-zinc-500">Pipeline Output in Phase 16</span>
                        </>
                      )}
                    </div>

                    <Badge variant="outline" className="text-[10px] font-mono">
                      {job.fps} FPS
                    </Badge>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-border/50 flex items-center justify-between gap-2">
                  <div className="text-[11px] font-mono text-muted-foreground truncate">
                    ID: {job.id.slice(0, 8)}
                  </div>

                  <Button
                    variant="ghost"
                    size="iconSm"
                    onClick={() => setExportToDelete(job)}
                    className="h-7 w-7 text-muted-foreground hover:text-destructive transition-colors"
                    title="Delete export record"
                    aria-label={`Delete export record ${job.output_filename}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
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

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        isOpen={!!exportToDelete}
        onOpenChange={(open) => !open && setExportToDelete(null)}
        title="Delete Export Record"
        entityName={exportToDelete?.output_filename || ""}
        consequences="Deleting this record removes it from the database history. Per user safety guidelines, rendered MP4 video files in storage/exports/ are preserved on disk unless you select the purge option below."
        showPurgeFilesOption={!!exportToDelete?.file_exists}
        purgeFilesChecked={deleteFile}
        onPurgeFilesToggle={setDeleteFile}
        purgeFilesLabel="Also delete rendered MP4 video file from SSD storage"
        onConfirm={handleDeleteConfirm}
        isDeleting={isDeleting}
      />
    </PageContainer>
  );
};
