import * as React from "react";
import { HardDrive, Upload, Video } from "lucide-react";
import { cn } from "../../lib/utils";
import { Button } from "../ui/button";

export interface EmptyVideoLibraryProps extends React.HTMLAttributes<HTMLDivElement> {
  onUploadClick?: () => void;
}

export const EmptyVideoLibrary = React.forwardRef<HTMLDivElement, EmptyVideoLibraryProps>(
  ({ onUploadClick, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 p-12 text-center",
          className
        )}
        {...props}
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-secondary/80 text-muted-foreground mb-4">
          <Video className="h-7 w-7 text-zinc-500" />
        </div>

        <h3 className="text-base font-semibold text-foreground">No Videos Ingested</h3>
        <p className="mt-1.5 max-w-sm text-xs text-muted-foreground leading-relaxed">
          Import your long-form video recordings to transcribe audio, detect viral highlights, and generate vertical clips.
        </p>

        <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
          <Button onClick={onUploadClick} className="gap-2">
            <Upload className="h-4 w-4" />
            <span>Import Local Video</span>
          </Button>
        </div>

        <div className="mt-8 flex items-center gap-2 text-[11px] text-zinc-500">
          <HardDrive className="h-3.5 w-3.5" />
          <span>Files stay strictly on your local SSD • MP4, MOV, MKV up to 4GB</span>
        </div>
      </div>
    );
  }
);
EmptyVideoLibrary.displayName = "EmptyVideoLibrary";
