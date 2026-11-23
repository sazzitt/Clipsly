import React, { useEffect, useState } from "react";
import { Highlight } from "../../../types/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../../components/ui/dialog";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { Textarea } from "../../../components/ui/textarea";

interface HighlightEditDialogProps {
  highlight: Highlight | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (
    highlightId: string,
    updates: { start_ms: number; end_ms: number; summary: string }
  ) => Promise<void>;
  videoDurationSeconds?: number;
}

export const HighlightEditDialog: React.FC<HighlightEditDialogProps> = ({
  highlight,
  isOpen,
  onClose,
  onSave,
  videoDurationSeconds,
}) => {
  const [startSeconds, setStartSeconds] = useState<number>(0);
  const [endSeconds, setEndSeconds] = useState<number>(0);
  const [summary, setSummary] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  useEffect(() => {
    if (highlight) {
      const s = highlight.start_ms ? highlight.start_ms / 1000 : highlight.start_time ?? 0;
      const e = highlight.end_ms ? highlight.end_ms / 1000 : highlight.end_time ?? 0;
      setStartSeconds(Number(s.toFixed(2)));
      setEndSeconds(Number(e.toFixed(2)));
      setSummary(highlight.summary || highlight.hook_sentence || "");
      setError(null);
    }
  }, [highlight]);

  const duration = Math.max(0, endSeconds - startSeconds);

  const validate = (): boolean => {
    if (startSeconds < 0) {
      setError("Start time cannot be negative.");
      return false;
    }
    if (endSeconds <= startSeconds) {
      setError("End time must be strictly greater than start time.");
      return false;
    }
    if (duration < 10.0) {
      setError("Highlight duration must be at least 10 seconds.");
      return false;
    }
    if (duration > 180.0) {
      setError("Highlight duration cannot exceed 180 seconds (3 minutes).");
      return false;
    }
    if (videoDurationSeconds && endSeconds > videoDurationSeconds + 1.0) {
      setError(`End time cannot exceed video duration (${videoDurationSeconds.toFixed(1)}s).`);
      return false;
    }
    setError(null);
    return true;
  };

  const handleSave = async () => {
    if (!highlight) return;
    if (!validate()) return;

    try {
      setIsSaving(true);
      await onSave(highlight.id, {
        start_ms: Math.round(startSeconds * 1000),
        end_ms: Math.round(endSeconds * 1000),
        summary: summary.trim(),
      });
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update highlight.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base font-semibold">Fine-Tune Highlight</DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Adjust the boundary timestamps and summary description for this highlight candidate.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {error && (
            <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="start-sec" className="text-xs">
                Start Time (seconds)
              </Label>
              <Input
                id="start-sec"
                type="number"
                step="0.1"
                min="0"
                value={startSeconds}
                onChange={(e) => {
                  setStartSeconds(parseFloat(e.target.value) || 0);
                  setError(null);
                }}
                className="font-mono text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="end-sec" className="text-xs">
                End Time (seconds)
              </Label>
              <Input
                id="end-sec"
                type="number"
                step="0.1"
                min="0"
                value={endSeconds}
                onChange={(e) => {
                  setEndSeconds(parseFloat(e.target.value) || 0);
                  setError(null);
                }}
                className="font-mono text-xs"
              />
            </div>
          </div>

          <div className="p-2.5 rounded-lg bg-secondary/40 border border-border/50 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Adjusted Duration:</span>
            <span
              className={`font-mono font-bold ${
                duration >= 10 && duration <= 180 ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {duration.toFixed(1)}s (
              {Math.floor(duration / 60)}m {Math.round(duration % 60)}s)
            </span>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="highlight-summary" className="text-xs">
              Editorial Summary
            </Label>
            <Textarea
              id="highlight-summary"
              rows={3}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Describe the highlight premise..."
              className="text-xs"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" size="sm" onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button size="sm" onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Saving..." : "Save Changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
