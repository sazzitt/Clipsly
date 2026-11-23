import React, { useEffect, useState, useMemo } from "react";
import {
  FileText,
  Search,
  Clock,
  Check,
  Edit2,
  X,
  Copy,
  Download,
  Layers,
  Sparkles,
  Zap,
  Globe,
  Tag,
  Loader2,
} from "lucide-react";
import { Button } from "../../../components/ui/button";
import { Badge } from "../../../components/ui/badge";
import { Card, CardContent, CardHeader } from "../../../components/ui/card";
import { api } from "../../../services/api";
import { useToast } from "../../../hooks/useToast";
import { Transcript, TranscriptSegment } from "../../../types/api";

interface TranscriptViewerProps {
  transcript: Transcript;
  onSegmentClick?: (startMs: number) => void;
  onRetranscribeRequested?: () => void;
}

export const TranscriptViewer: React.FC<TranscriptViewerProps> = ({
  transcript,
  onSegmentClick,
  onRetranscribeRequested,
}) => {
  const { toast } = useToast();

  const initialFallback = useMemo<TranscriptSegment[]>(() => {
    if (transcript.segments && transcript.segments.length > 0) {
      return transcript.segments;
    }
    if (transcript.full_text) {
      return [
        {
          id: `${transcript.id}_full`,
          transcript_id: transcript.id,
          segment_index: 0,
          start_ms: 0,
          end_ms: Math.round(((transcript.audio_duration_seconds ?? transcript.duration_seconds ?? 10)) * 1000),
          text: transcript.full_text,
          avg_confidence: 1.0,
          words: [],
        },
      ];
    }
    return [];
  }, [transcript]);

  const [segments, setSegments] = useState<TranscriptSegment[]>(initialFallback);
  const [isLoadingSegments, setIsLoadingSegments] = useState<boolean>(!transcript.segments?.length && !transcript.full_text);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [viewMode, setViewMode] = useState<"sentence" | "words">("sentence");

  // Inline editing state
  const [editingSegmentId, setEditingSegmentId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState<string>("");
  const [isSavingEdit, setIsSavingEdit] = useState<boolean>(false);

  // Fetch segments if not pre-populated
  useEffect(() => {
    let isMounted = true;
    if (transcript.segments && transcript.segments.length > 0) {
      setSegments(transcript.segments);
      setIsLoadingSegments(false);
      return;
    }

    const fetchSegments = async () => {
      try {
        const res = await api.transcripts.getSegments(transcript.id, { limit: 1000, offset: 0 });
        if (isMounted && res.segments && res.segments.length > 0) {
          setSegments(res.segments);
        }
      } catch (err) {
        console.warn("Failed to load transcript segments:", err);
      } finally {
        if (isMounted) {
          setIsLoadingSegments(false);
        }
      }
    };

    fetchSegments();
    return () => {
      isMounted = false;
    };
  }, [transcript.id, transcript.segments]);

  // Format millisecond timestamp as MM:SS.mmm
  const formatTimestamp = (ms: number): string => {
    const totalSeconds = ms / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = Math.floor(totalSeconds % 60);
    const millis = Math.floor(ms % 1000);
    return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}.${millis.toString().padStart(3, "0").slice(0, 2)}`;
  };

  // Filtered segments based on search
  const filteredSegments = useMemo(() => {
    if (!searchQuery.trim()) return segments;
    const q = searchQuery.toLowerCase();
    return segments.filter((s) => s.text.toLowerCase().includes(q));
  }, [segments, searchQuery]);

  // Copy full transcript text
  const handleCopyFullText = async () => {
    const textToCopy = transcript.full_text || segments.map((s) => s.text).join(" ");
    try {
      await navigator.clipboard.writeText(textToCopy);
      toast({
        title: "Copied to Clipboard",
        description: "Full transcript text copied successfully.",
        variant: "success",
      });
    } catch {
      toast({
        title: "Copy Failed",
        description: "Clipboard access was denied.",
        variant: "error",
      });
    }
  };

  // Download transcript as plain text or JSON
  const handleDownload = (format: "txt" | "json" | "srt") => {
    let content = "";
    let mimeType = "text/plain";
    const filename = `transcript_${transcript.id.slice(0, 8)}.${format}`;

    if (format === "txt") {
      content = transcript.full_text || segments.map((s) => s.text).join("\n");
      mimeType = "text/plain";
    } else if (format === "json") {
      content = JSON.stringify({ transcript, segments }, null, 2);
      mimeType = "application/json";
    } else if (format === "srt") {
      content = segments
        .map((s, idx) => {
          const start = formatTimestamp(s.start_ms).replace(".", ",");
          const end = formatTimestamp(s.end_ms).replace(".", ",");
          return `${idx + 1}\n00:${start} --> 00:${end}\n${s.text}\n`;
        })
        .join("\n");
      mimeType = "text/plain";
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Start inline editing
  const handleStartEdit = (segment: TranscriptSegment) => {
    setEditingSegmentId(segment.id);
    setEditingText(segment.text);
  };

  // Cancel inline editing
  const handleCancelEdit = () => {
    setEditingSegmentId(null);
    setEditingText("");
  };

  // Save inline editing
  const handleSaveEdit = async (segmentId: string) => {
    if (!editingText.trim()) return;
    setIsSavingEdit(true);
    try {
      const updated = await api.transcripts.updateSegment(
        transcript.id,
        segmentId,
        editingText.trim()
      );
      setSegments((prev) =>
        prev.map((s) => (s.id === segmentId ? { ...s, text: updated.text } : s))
      );
      setEditingSegmentId(null);
      setEditingText("");
      toast({
        title: "Segment Updated",
        description: "Transcript segment text was saved successfully.",
        variant: "success",
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update segment text.";
      toast({
        title: "Update Failed",
        description: msg,
        variant: "error",
      });
    } finally {
      setIsSavingEdit(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="transcript-viewer">
      {/* Overview Metadata Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-3 rounded-lg bg-card/70 border border-border space-y-1">
          <span className="text-[11px] text-muted-foreground flex items-center gap-1">
            <Zap className="h-3 w-3 text-violet-400" /> Model
          </span>
          <span className="text-xs font-semibold text-foreground font-mono block">
            {transcript.model_name} ({transcript.compute_type || "float16"})
          </span>
        </div>

        <div className="p-3 rounded-lg bg-card/70 border border-border space-y-1">
          <span className="text-[11px] text-muted-foreground flex items-center gap-1">
            <Layers className="h-3 w-3 text-zinc-400" /> Device
          </span>
          <span className="text-xs font-semibold text-emerald-400 font-mono block">
            {(transcript.device || "cuda").toUpperCase()}
          </span>
        </div>

        <div className="p-3 rounded-lg bg-card/70 border border-border space-y-1">
          <span className="text-[11px] text-muted-foreground flex items-center gap-1">
            <Globe className="h-3 w-3 text-blue-400" /> Language
          </span>
          <span className="text-xs font-semibold text-foreground font-mono block">
            {transcript.language ? transcript.language.toUpperCase() : "AUTO"}
            {transcript.language_probability != null && (
              <span className="text-[10px] text-muted-foreground ml-1">
                ({(transcript.language_probability * 100).toFixed(0)}%)
              </span>
            )}
          </span>
        </div>

        <div className="p-3 rounded-lg bg-card/70 border border-border space-y-1">
          <span className="text-[11px] text-muted-foreground flex items-center gap-1">
            <FileText className="h-3 w-3 text-zinc-400" /> Word Count
          </span>
          <span className="text-xs font-semibold text-foreground font-mono block">
            {transcript.word_count?.toLocaleString() || segments.reduce((acc, s) => acc + (s.words?.length || s.text.split(/\s+/).length), 0)} words
          </span>
        </div>

        <div className="p-3 rounded-lg bg-card/70 border border-border space-y-1">
          <span className="text-[11px] text-muted-foreground flex items-center gap-1">
            <Tag className="h-3 w-3 text-zinc-400" /> Segments
          </span>
          <span className="text-xs font-semibold text-foreground font-mono block">
            {transcript.segment_count || segments.length}
          </span>
        </div>

        <div className="p-3 rounded-lg bg-card/70 border border-border space-y-1">
          <span className="text-[11px] text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3 text-zinc-400" /> Processing Time
          </span>
          <span className="text-xs font-semibold text-foreground font-mono block">
            {transcript.processing_time_seconds ? `${transcript.processing_time_seconds.toFixed(2)}s` : "N/A"}
          </span>
        </div>
      </div>

      {/* Toolbar: Search, View Mode, Actions */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-xl border border-border bg-card/50">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search transcript text..."
            className="w-full h-8 pl-8 pr-3 text-xs rounded-md border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            data-testid="transcript-search-input"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>

        {/* View Mode Toggle & Action Buttons */}
        <div className="flex items-center gap-2 self-end sm:self-auto">
          {/* Sentence vs Words Toggle */}
          <div className="flex items-center bg-secondary/80 p-0.5 rounded-lg border border-border text-xs">
            <button
              onClick={() => setViewMode("sentence")}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                viewMode === "sentence"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              data-testid="view-sentence-btn"
            >
              Sentences
            </button>
            <button
              onClick={() => setViewMode("words")}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                viewMode === "words"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              data-testid="view-words-btn"
            >
              Word Timestamps
            </button>
          </div>

          {/* Copy Full Text */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyFullText}
            className="h-8 text-xs gap-1.5"
            data-testid="copy-transcript-btn"
          >
            <Copy className="h-3 w-3" />
            <span className="hidden sm:inline">Copy Text</span>
          </Button>

          {/* Download Dropdown or Action */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDownload("srt")}
            className="h-8 text-xs gap-1.5"
            data-testid="download-srt-btn"
          >
            <Download className="h-3 w-3" />
            <span className="hidden sm:inline">Export SRT</span>
          </Button>

          {onRetranscribeRequested && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRetranscribeRequested}
              className="h-8 text-xs gap-1.5"
              data-testid="retranscribe-btn"
            >
              <Sparkles className="h-3 w-3 text-violet-400" />
              <span className="hidden sm:inline">Retranscribe</span>
            </Button>
          )}
        </div>
      </div>

      {/* Segments Display Area */}
      <Card className="border-border bg-card/60">
        <CardHeader className="py-2.5 px-4 border-b border-border/40">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
            <span>
              Showing {filteredSegments.length} of {segments.length} segment{segments.length !== 1 ? "s" : ""}
            </span>
            <span>Click any timestamp to seek video</span>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isLoadingSegments ? (
            <div className="p-12 text-center space-y-2">
              <Loader2 className="h-6 w-6 text-primary animate-spin mx-auto" />
              <p className="text-xs text-muted-foreground">Loading transcript segments...</p>
            </div>
          ) : filteredSegments.length === 0 ? (
            <div className="p-12 text-center space-y-2">
              <FileText className="h-6 w-6 text-muted-foreground mx-auto" />
              <p className="text-xs font-semibold text-foreground">No matching segments found</p>
              {searchQuery ? (
                <p className="text-[11px] text-muted-foreground">
                  Try adjusting your search query "{searchQuery}".
                </p>
              ) : (
                <p className="text-[11px] text-muted-foreground">
                  This transcript contains no speech segments (audio may be silence or music).
                </p>
              )}
            </div>
          ) : (
            <div className="divide-y divide-border/40 max-h-[500px] overflow-y-auto" data-testid="segments-container">
              {filteredSegments.map((segment) => {
                const isEditing = editingSegmentId === segment.id;
                const confidencePct = Math.round((segment.avg_confidence ?? 1.0) * 100);

                return (
                  <div
                    key={segment.id}
                    className="p-3.5 hover:bg-card/90 transition-colors space-y-2 text-xs"
                    data-testid={`segment-row-${segment.id}`}
                  >
                    {/* Segment Header */}
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {/* Interactive Clickable Timestamp */}
                        <button
                          onClick={() => onSegmentClick && onSegmentClick(segment.start_ms)}
                          className="font-mono text-[11px] px-2 py-0.5 rounded bg-secondary/80 hover:bg-primary/20 hover:text-primary transition-colors text-muted-foreground flex items-center gap-1 font-semibold"
                          title="Seek video to timestamp"
                          data-testid={`timestamp-btn-${segment.id}`}
                        >
                          <Clock className="h-3 w-3 text-zinc-400" />
                          <span>{formatTimestamp(segment.start_ms)}</span>
                          <span className="text-zinc-600">→</span>
                          <span>{formatTimestamp(segment.end_ms)}</span>
                        </button>

                        {/* Confidence Indicator */}
                        <span
                          className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                            confidencePct >= 85
                              ? "text-emerald-400 border-emerald-500/20 bg-emerald-500/5"
                              : confidencePct >= 65
                              ? "text-amber-400 border-amber-500/20 bg-amber-500/5"
                              : "text-red-400 border-red-500/20 bg-red-500/5"
                          }`}
                        >
                          {confidencePct}% conf
                        </span>

                        {segment.speaker_id && (
                          <Badge variant="outline" className="text-[10px] font-mono">
                            {segment.speaker_id}
                          </Badge>
                        )}
                      </div>

                      {/* Edit Segment Button */}
                      {!isEditing && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleStartEdit(segment)}
                          className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                          title="Edit segment text"
                          data-testid={`edit-segment-${segment.id}`}
                        >
                          <Edit2 className="h-3 w-3" />
                        </Button>
                      )}
                    </div>

                    {/* Segment Content */}
                    {isEditing ? (
                      <div className="space-y-2 pt-1" data-testid={`editing-box-${segment.id}`}>
                        <textarea
                          value={editingText}
                          onChange={(e) => setEditingText(e.target.value)}
                          className="w-full h-20 p-2 text-xs rounded-md border border-primary/50 bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed"
                          data-testid={`edit-textarea-${segment.id}`}
                        />
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleCancelEdit}
                            disabled={isSavingEdit}
                            className="h-6 px-2 text-xs"
                          >
                            <X className="h-3 w-3 mr-1" />
                            Cancel
                          </Button>
                          <Button
                            variant="default"
                            size="sm"
                            onClick={() => handleSaveEdit(segment.id)}
                            disabled={isSavingEdit || !editingText.trim()}
                            className="h-6 px-2 text-xs bg-violet-600 hover:bg-violet-700 text-white"
                            data-testid={`save-edit-${segment.id}`}
                          >
                            {isSavingEdit ? (
                              <Loader2 className="h-3 w-3 animate-spin mr-1" />
                            ) : (
                              <Check className="h-3 w-3 mr-1" />
                            )}
                            Save
                          </Button>
                        </div>
                      </div>
                    ) : viewMode === "sentence" ? (
                      <p className="text-foreground leading-relaxed pl-1 font-sans">
                        {segment.text}
                      </p>
                    ) : (
                      /* Word-Level Timestamps View */
                      <div className="flex flex-wrap gap-1.5 pt-1 pl-1">
                        {segment.words && segment.words.length > 0 ? (
                          segment.words.map((w, wIdx) => {
                            const prob = w.probability != null ? Math.round(w.probability * 100) : null;
                            return (
                              <button
                                key={wIdx}
                                onClick={() => onSegmentClick && onSegmentClick(w.start_ms)}
                                className="group inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-border/70 bg-secondary/40 hover:bg-primary/20 hover:border-primary/40 text-foreground transition-colors font-sans text-xs"
                                title={`${formatTimestamp(w.start_ms)} - ${formatTimestamp(w.end_ms)}${prob != null ? ` (${prob}%)` : ""}`}
                              >
                                <span>{w.word}</span>
                                <span className="font-mono text-[9px] text-muted-foreground group-hover:text-primary">
                                  {formatTimestamp(w.start_ms)}
                                </span>
                              </button>
                            );
                          })
                        ) : (
                          <span className="text-[11px] text-muted-foreground italic">
                            No word-level timings available for this segment.
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
