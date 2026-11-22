import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Upload, RefreshCw, Eye, Trash2 } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Button } from "../../components/ui/button";
import { Skeleton } from "../../components/ui/skeleton";
import { EmptyVideoLibrary } from "../../components/workstation/EmptyVideoLibrary";
import { VideoThumbnail } from "../../components/workstation/VideoThumbnail";
import { VideoMetadataRow } from "../../components/workstation/VideoMetadataRow";
import { useToast } from "../../hooks/useToast";
import { api, ClipslyApiError } from "../../services/api";
import { Video } from "../../types/api";
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
  { value: "READY", label: "Ready" },
  { value: "PROCESSING", label: "Processing" },
  { value: "UPLOADED", label: "Uploaded" },
  { value: "FAILED", label: "Failed" },
];

const SORT_OPTIONS = [
  { value: "created_at", label: "Import Date" },
  { value: "duration_seconds", label: "Duration" },
  { value: "filename", label: "Filename" },
  { value: "file_size_bytes", label: "File Size" },
];

export const VideoLibraryPage: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();

  const [videos, setVideos] = useState<Video[]>([]);
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

  // Deletion modal state
  const [videoToDelete, setVideoToDelete] = useState<Video | null>(null);
  const [purgeFiles, setPurgeFiles] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const fetchVideos = useCallback(
    async (isManual = false) => {
      if (isManual) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      try {
        const res = await api.videos.list({
          page,
          limit,
          search: search.trim() || undefined,
          status: statusFilter === "ALL" ? undefined : statusFilter,
          sort_by: sortBy,
          order,
        });
        setVideos(res.items);
        setTotal(res.total);
      } catch (err: unknown) {
        if (err instanceof ClipslyApiError) {
          setError(err.detail);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to fetch video catalog from backend.");
        }
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [page, limit, search, statusFilter, sortBy, order]
  );

  useEffect(() => {
    fetchVideos();
  }, [fetchVideos]);

  const handleClearFilters = () => {
    setSearch("");
    setStatusFilter("ALL");
    setSortBy("created_at");
    setOrder("desc");
    setPage(1);
  };

  const handleDeleteConfirm = async () => {
    if (!videoToDelete) return;
    setIsDeleting(true);

    try {
      await api.videos.delete(videoToDelete.id, purgeFiles);
      toast.success(
        "Video Removed",
        `${videoToDelete.original_filename || videoToDelete.filename} was successfully deleted.`
      );
      setVideoToDelete(null);
      setPurgeFiles(false);
      fetchVideos(true);
    } catch (err: unknown) {
      const msg = err instanceof ClipslyApiError ? err.detail : "Failed to delete video.";
      toast.error("Deletion Failed", msg);
    } finally {
      setIsDeleting(false);
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <PageContainer
      title="Video Library"
      description="Manage and inspect ingested source video files stored locally on your SSD."
      action={
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchVideos(true)}
            disabled={isRefreshing || isLoading}
            className="gap-1.5 h-8 text-xs"
            aria-label="Refresh video list"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </Button>

          <Button asChild size="sm" className="gap-2 h-8 text-xs">
            <Link to="/upload">
              <Upload className="h-3.5 w-3.5" />
              <span>Import Video</span>
            </Link>
          </Button>
        </div>
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
          placeholder="Search by filename or title..."
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="videos-loading-skeleton">
          {Array.from({ length: 6 }).map((_, idx) => (
            <div key={idx} className="rounded-xl border border-border bg-card p-4 space-y-3">
              <Skeleton className="aspect-video w-full rounded-lg" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-8 text-center space-y-3">
          <p className="text-sm font-semibold text-destructive">Failed to Load Video Catalog</p>
          <p className="text-xs text-muted-foreground">{error}</p>
          <Button onClick={() => fetchVideos()} variant="outline" size="sm" className="mt-2 text-xs">
            Retry
          </Button>
        </div>
      ) : total === 0 ? (
        search || statusFilter !== "ALL" ? (
          <NoResultsState
            title="No Matching Videos"
            description="No ingested videos matched your current search and filter criteria."
            onClearFilters={handleClearFilters}
          />
        ) : (
          <EmptyVideoLibrary onUploadClick={() => navigate("/upload")} />
        )
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {videos.map((video) => (
              <div
                key={video.id}
                className="group flex flex-col justify-between rounded-xl border border-border bg-card p-4 transition-all hover:border-zinc-700 hover:bg-card-hover"
              >
                <div className="space-y-3">
                  <div className="relative">
                    <VideoThumbnail
                      durationSeconds={video.duration_seconds}
                      resolution={`${video.width}x${video.height}`}
                      aspectRatio="16:9"
                      className="w-full"
                    />
                    <div className="absolute top-2 right-2 z-10">
                      <EntityStatusBadge status={video.status} />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <h3
                      className="text-sm font-semibold text-foreground truncate group-hover:text-primary transition-colors"
                      title={video.original_filename || video.filename}
                    >
                      {video.original_filename || video.filename}
                    </h3>
                    <p className="text-[11px] font-mono text-muted-foreground truncate">
                      {video.filename}
                    </p>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-border/50 space-y-3">
                  <VideoMetadataRow
                    durationSeconds={video.duration_seconds}
                    width={video.width}
                    height={video.height}
                    fps={video.fps}
                    fileSizeBytes={video.file_size_bytes}
                    compact
                  />

                  <div className="flex items-center justify-between gap-2 pt-1">
                    <Button asChild variant="outline" size="sm" className="h-7 text-xs gap-1.5 flex-1">
                      <Link to={`/video/${video.id}`} aria-label={`View details for ${video.filename}`}>
                        <Eye className="h-3 w-3" />
                        <span>Inspect</span>
                      </Link>
                    </Button>

                    <Button
                      variant="ghost"
                      size="iconSm"
                      onClick={() => setVideoToDelete(video)}
                      className="h-7 w-7 text-muted-foreground hover:text-destructive transition-colors"
                      title="Delete video"
                      aria-label={`Delete video ${video.filename}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
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
        isOpen={!!videoToDelete}
        onOpenChange={(open) => !open && setVideoToDelete(null)}
        title="Delete Source Video"
        entityName={videoToDelete?.original_filename || videoToDelete?.filename || ""}
        consequences="This will delete the database record and cascade removal of all associated audio transcripts, AI highlights, and draft clips. Finished exported MP4s in storage/exports/ are preserved on disk."
        showPurgeFilesOption={true}
        purgeFilesChecked={purgeFiles}
        onPurgeFilesToggle={setPurgeFiles}
        purgeFilesLabel="Also permanently delete source video file from SSD storage"
        onConfirm={handleDeleteConfirm}
        isDeleting={isDeleting}
      />
    </PageContainer>
  );
};
