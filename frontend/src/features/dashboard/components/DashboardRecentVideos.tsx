import * as React from "react";
import { Link } from "react-router-dom";
import { Video as VideoIcon, ArrowRight, Clock } from "lucide-react";
import { DashboardRecentVideoItem } from "../../../types/api";
import { EmptyVideoLibrary } from "../../../components/workstation/EmptyVideoLibrary";
import { VideoThumbnail } from "../../../components/workstation/VideoThumbnail";
import { VideoMetadataRow } from "../../../components/workstation/VideoMetadataRow";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";

export interface DashboardRecentVideosProps {
  videos: DashboardRecentVideoItem[];
  totalVideosCount: number;
  onUploadClick: () => void;
}

export const DashboardRecentVideos: React.FC<DashboardRecentVideosProps> = ({
  videos,
  totalVideosCount,
  onUploadClick,
}) => {
  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "ready":
        return <Badge variant="success">Ready</Badge>;
      case "processing":
        return <Badge variant="warning">Processing</Badge>;
      case "failed":
        return <Badge variant="destructive">Failed</Badge>;
      case "uploaded":
      default:
        return <Badge variant="secondary">Uploaded</Badge>;
    }
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <VideoIcon className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold tracking-tight text-foreground">Recent Videos</h2>
          {totalVideosCount > 0 && (
            <span className="text-xs font-mono text-muted-foreground">({totalVideosCount} total)</span>
          )}
        </div>
        {totalVideosCount > 0 && (
          <Button asChild variant="ghost" size="sm" className="gap-1 text-xs">
            <Link to="/videos">
              <span>View All Library</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        )}
      </div>

      {videos.length === 0 ? (
        <EmptyVideoLibrary onUploadClick={onUploadClick} />
      ) : (
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
                    {getStatusBadge(video.status)}
                  </div>
                </div>

                <div className="space-y-1">
                  <h3
                    className="text-sm font-semibold text-foreground truncate group-hover:text-primary transition-colors"
                    title={video.original_filename || video.filename}
                  >
                    {video.original_filename || video.filename}
                  </h3>
                  {video.created_at && (
                    <div className="flex items-center gap-1 text-[11px] text-muted-foreground font-mono">
                      <Clock className="h-3 w-3" />
                      <span>{formatDate(video.created_at)}</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-border/50">
                <VideoMetadataRow
                  durationSeconds={video.duration_seconds}
                  width={video.width}
                  height={video.height}
                  fps={video.fps}
                  fileSizeBytes={video.file_size_bytes}
                  compact
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
