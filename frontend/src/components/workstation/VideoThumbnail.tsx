import * as React from "react";
import { Play, Video as VideoIcon } from "lucide-react";
import { cn } from "../../lib/utils";

export interface VideoThumbnailProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string | null;
  alt?: string;
  durationSeconds?: number;
  resolution?: string;
  aspectRatio?: "16:9" | "9:16" | "1:1";
  showPlayOverlay?: boolean;
}

function formatDuration(seconds?: number): string {
  if (!seconds || seconds <= 0) return "00:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export const VideoThumbnail = React.forwardRef<HTMLDivElement, VideoThumbnailProps>(
  (
    {
      src,
      alt = "Video thumbnail",
      durationSeconds,
      resolution,
      aspectRatio = "16:9",
      showPlayOverlay = true,
      className,
      ...props
    },
    ref
  ) => {
    const aspectStyles = {
      "16:9": "aspect-video",
      "9:16": "aspect-[9/16]",
      "1:1": "aspect-square",
    };

    return (
      <div
        ref={ref}
        className={cn(
          "group relative overflow-hidden rounded-lg border border-border bg-card/80 transition-all select-none",
          aspectStyles[aspectRatio],
          className
        )}
        {...props}
      >
        {src ? (
          <img
            src={src}
            alt={alt}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center bg-zinc-900/60 text-muted-foreground gap-2">
            <VideoIcon className="h-8 w-8 stroke-1 text-zinc-600" />
            <span className="text-[11px] font-medium text-zinc-500">No Preview</span>
          </div>
        )}

        {/* Hover Play Overlay */}
        {showPlayOverlay && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 backdrop-blur-[1px] transition-opacity duration-200 group-hover:opacity-100">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/90 text-primary-foreground shadow-lg transition-transform group-hover:scale-110">
              <Play className="h-4 w-4 fill-current ml-0.5" />
            </div>
          </div>
        )}

        {/* Badges Overlay */}
        <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between pointer-events-none">
          {resolution && (
            <span className="rounded bg-black/75 px-1.5 py-0.5 font-mono text-[10px] font-medium text-zinc-300 backdrop-blur-sm">
              {resolution}
            </span>
          )}
          {durationSeconds !== undefined && durationSeconds > 0 && (
            <span className="ml-auto rounded bg-black/75 px-1.5 py-0.5 font-mono text-[10px] font-medium text-zinc-200 backdrop-blur-sm tabular-nums">
              {formatDuration(durationSeconds)}
            </span>
          )}
        </div>
      </div>
    );
  }
);
VideoThumbnail.displayName = "VideoThumbnail";
