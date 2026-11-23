import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Film, RefreshCw, Scissors, Trash2, Download, StopCircle } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Button } from "../../components/ui/button";
import { Skeleton } from "../../components/ui/skeleton";
import { Badge } from "../../components/ui/badge";
import { useToast } from "../../hooks/useToast";
import { api, ClipslyApiError } from "../../services/api";
import { Clip } from "../../types/api";
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
  { value: "DRAFT", label: "Draft" },
  { value: "READY", label: "Ready" },
  { value: "EXPORTED", label: "Exported" },
];

const SORT_OPTIONS = [
  { value: "created_at", label: "Creation Date" },
  { value: "title", label: "Clip Title" },
  { value: "duration_ms", label: "Duration" },
  { value: "start_ms", label: "Start Timestamp" },
];

function formatTimecode(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function formatBytes(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return "";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export const ClipsLibraryPage: React.FC = () => {
  const toast = useToast();

  const [clips, setClips] = useState<Clip[]>([]);
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
  const [clipToDelete, setClipToDelete] = useState<Clip | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const fetchClips = useCallback(
    async (isManual = false) => {
      if (isManual) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      try {
        const res = await api.clips.list({
          page,
          limit,
          search: search.trim() || undefined,
          status: statusFilter === "ALL" ? undefined : statusFilter,
          sort_by: sortBy,
          order,
        });
        setClips(res.items);
        setTotal(res.total);
      } catch (err: unknown) {
        if (err instanceof ClipslyApiError) {
          setError(err.detail);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to fetch clips library.");
        }
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [page, limit, search, statusFilter, sortBy, order]
  );

  useEffect(() => {
    fetchClips();
  }, [fetchClips]);

  const handleClearFilters = () => {
    setSearch("");
    setStatusFilter("ALL");
    setSortBy("created_at");
    setOrder("desc");
    setPage(1);
  };

  const handleDeleteConfirm = async () => {
    if (!clipToDelete) return;
    setIsDeleting(true);

    try {
      await api.clips.delete(clipToDelete.id);
      toast.success("Clip Deleted", `"${clipToDelete.title}" was removed.`);
      setClipToDelete(null);
      fetchClips(true);
    } catch (err: unknown) {
      const msg = err instanceof ClipslyApiError ? err.detail : "Failed to delete clip.";
      toast.error("Deletion Failed", msg);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancelClip = async (clipId: string) => {
    try {
      await api.clips.cancel(clipId);
      toast.success("Clip Cancelled", "Clip generation job was cancelled.");
      fetchClips(true);
    } catch (err: unknown) {
      const msg = err instanceof ClipslyApiError ? err.detail : "Failed to cancel clip.";
      toast.error("Cancellation Failed", msg);
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <PageContainer
      title="Clips Library"
      description="Review, inspect timeline boundaries, and manage 9:16 vertical clip configurations."
      action={
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchClips(true)}
          disabled={isRefreshing || isLoading}
          className="gap-1.5 h-8 text-xs"
          aria-label="Refresh clips library"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          <span>{isRefreshing ? "Refreshing..." : "Refresh"}</span>
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
          placeholder="Search clips by title..."
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="clips-loading-skeleton">
          {Array.from({ length: 6 }).map((_, idx) => (
            <div key={idx} className="rounded-xl border border-border bg-card p-4 space-y-3">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-16 w-full rounded-lg" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-8 text-center space-y-3">
          <p className="text-sm font-semibold text-destructive">Failed to Load Clips</p>
          <p className="text-xs text-muted-foreground">{error}</p>
          <Button onClick={() => fetchClips()} variant="outline" size="sm" className="mt-2 text-xs">
            Retry
          </Button>
        </div>
      ) : total === 0 ? (
        search || statusFilter !== "ALL" ? (
          <NoResultsState
            title="No Matching Clips"
            description="No clips match your current search and filter criteria."
            onClearFilters={handleClearFilters}
          />
        ) : (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 p-12 text-center space-y-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary text-muted-foreground">
              <Film className="h-6 w-6 text-zinc-500" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">No Clips Created Yet</h3>
            <p className="max-w-sm text-xs text-muted-foreground leading-relaxed">
              Clips are configured from video highlights or trimmed manually in the Studio. 
              Import a video to begin generating short-form clips.
            </p>
          </div>
        )
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {clips.map((clip) => {
              const durationSec = (clip.duration_ms / 1000).toFixed(1);

              return (
                <div
                  key={clip.id}
                  className="group flex flex-col justify-between rounded-xl border border-border bg-card p-4 transition-all hover:border-zinc-700 hover:bg-card-hover"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1 min-w-0">
                        <h3 className="text-sm font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                          {clip.title}
                        </h3>
                        {clip.video_filename && (
                          <p className="text-[11px] font-mono text-muted-foreground truncate">
                            Source: {clip.video_filename}
                          </p>
                        )}
                      </div>
                      <EntityStatusBadge status={clip.status} />
                    </div>

                    {/* Timeline visualization indicator */}
                    <div className="p-3 rounded-lg bg-secondary/40 border border-border/60 text-xs font-mono space-y-2">
                      <div className="flex items-center justify-between text-muted-foreground">
                        <span>Bounds:</span>
                        <span className="text-foreground font-semibold">
                          {formatTimecode(clip.start_ms)} – {formatTimecode(clip.end_ms)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-muted-foreground">
                        <span>Duration:</span>
                        <span className="text-foreground font-semibold">{durationSec}s</span>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <Badge variant="outline" className="text-[10px]">
                        {clip.conversion_mode || clip.aspect_ratio_mode}
                      </Badge>
                      {clip.width && clip.height && (
                        <Badge variant="secondary" className="text-[10px] font-mono">
                          {clip.width}x{clip.height}
                        </Badge>
                      )}
                      {clip.file_size_bytes && clip.file_size_bytes > 0 && (
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {formatBytes(clip.file_size_bytes)}
                        </span>
                      )}
                      {clip.encoding_backend && (
                        <span className="text-[10px] text-zinc-500 font-mono">
                          {clip.encoding_backend}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-border/50 flex items-center justify-between gap-2">
                    <Button asChild variant="outline" size="sm" className="h-7 text-xs gap-1.5 flex-1">
                      <Link to={`/studio/${clip.id}`}>
                        <Scissors className="h-3 w-3" />
                        <span>Open Studio</span>
                      </Link>
                    </Button>

                    {clip.status === "COMPLETED" && (
                      <Button asChild variant="ghost" size="iconSm" className="h-7 w-7 text-muted-foreground hover:text-primary transition-colors" title="Download MP4">
                        <a href={api.clips.getDownloadUrl(clip.id)} download={clip.output_filename || `${clip.title}.mp4`}>
                          <Download className="h-3.5 w-3.5" />
                        </a>
                      </Button>
                    )}

                    {(clip.status === "QUEUED" || clip.status === "PROCESSING") && (
                      <Button
                        variant="ghost"
                        size="iconSm"
                        onClick={() => handleCancelClip(clip.id)}
                        className="h-7 w-7 text-amber-400 hover:text-amber-300 transition-colors"
                        title="Cancel generation"
                        aria-label={`Cancel clip ${clip.title}`}
                      >
                        <StopCircle className="h-3.5 w-3.5" />
                      </Button>
                    )}

                    <Button
                      variant="ghost"
                      size="iconSm"
                      onClick={() => setClipToDelete(clip)}
                      className="h-7 w-7 text-muted-foreground hover:text-destructive transition-colors"
                      title="Delete clip"
                      aria-label={`Delete clip ${clip.title}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
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

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        isOpen={!!clipToDelete}
        onOpenChange={(open) => !open && setClipToDelete(null)}
        title="Delete Clip Configuration"
        entityName={clipToDelete?.title || ""}
        consequences="This will permanently delete this clip configuration and its associated export job records. Source video files and finished exported MP4s on disk will not be affected."
        showPurgeFilesOption={false}
        onConfirm={handleDeleteConfirm}
        isDeleting={isDeleting}
      />
    </PageContainer>
  );
};
