import * as React from "react";
import { Clock, Film, HardDrive, Monitor, Music } from "lucide-react";
import { cn } from "../../lib/utils";

export interface VideoMetadataRowProps extends React.HTMLAttributes<HTMLDivElement> {
  durationSeconds?: number;
  width?: number;
  height?: number;
  fps?: number;
  videoCodec?: string;
  audioCodec?: string;
  audioSampleRate?: number;
  audioChannels?: number;
  fileSizeBytes?: number;
  compact?: boolean;
}

function formatBytes(bytes?: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function formatDuration(seconds?: number): string {
  if (!seconds || seconds <= 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s}s`;
}

export const VideoMetadataRow = React.forwardRef<HTMLDivElement, VideoMetadataRowProps>(
  (
    {
      durationSeconds,
      width,
      height,
      fps,
      videoCodec,
      audioCodec,
      audioSampleRate,
      audioChannels,
      fileSizeBytes,
      compact = false,
      className,
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-wrap items-center gap-2 text-xs text-muted-foreground select-none",
          className
        )}
        {...props}
      >
        {/* Duration */}
        {durationSeconds !== undefined && (
          <div className="flex items-center gap-1 rounded bg-secondary/60 px-2 py-1">
            <Clock className="h-3 w-3 text-zinc-400" />
            <span className="font-mono tabular-nums">{formatDuration(durationSeconds)}</span>
          </div>
        )}

        {/* Resolution */}
        {width && height && (
          <div className="flex items-center gap-1 rounded bg-secondary/60 px-2 py-1">
            <Monitor className="h-3 w-3 text-zinc-400" />
            <span className="font-mono tabular-nums">
              {width}x{height}
            </span>
          </div>
        )}

        {/* FPS */}
        {fps !== undefined && (
          <div className="flex items-center gap-1 rounded bg-secondary/60 px-2 py-1">
            <Film className="h-3 w-3 text-zinc-400" />
            <span className="font-mono tabular-nums">{Math.round(fps)} fps</span>
          </div>
        )}

        {/* Video Codec */}
        {videoCodec && (
          <div className="flex items-center gap-1 rounded bg-secondary/60 px-2 py-1 uppercase font-mono">
            <span>{videoCodec}</span>
          </div>
        )}

        {/* Audio */}
        {!compact && (audioCodec || audioChannels) && (
          <div className="flex items-center gap-1 rounded bg-secondary/60 px-2 py-1">
            <Music className="h-3 w-3 text-zinc-400" />
            <span className="font-mono">
              {audioCodec || "audio"}
              {audioChannels ? ` (${audioChannels}ch)` : ""}
              {audioSampleRate ? ` @ ${Math.round(audioSampleRate / 1000)}kHz` : ""}
            </span>
          </div>
        )}

        {/* File Size */}
        {fileSizeBytes !== undefined && (
          <div className="flex items-center gap-1 rounded bg-secondary/60 px-2 py-1">
            <HardDrive className="h-3 w-3 text-zinc-400" />
            <span className="font-mono tabular-nums">{formatBytes(fileSizeBytes)}</span>
          </div>
        )}
      </div>
    );
  }
);
VideoMetadataRow.displayName = "VideoMetadataRow";
