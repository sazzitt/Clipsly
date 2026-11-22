import React from "react";
import { useParams, Link } from "react-router-dom";
import { FileText, ArrowLeft, Volume2 } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { EmptyState } from "../../components/common/EmptyState";
import { DisabledFeatureBadge } from "../../components/common/DisabledFeatureBadge";
import { Button } from "../../components/ui/button";

export const TranscriptViewerPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <PageContainer
      title="Transcript Viewer"
      description={`Word-level timestamped transcription for video ${id || ""}.`}
      action={
        <Button asChild variant="outline" size="sm" className="gap-2">
          <Link to={`/video/${id}`}>
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Video
          </Link>
        </Button>
      }
    >
      <div className="flex items-center justify-between p-3 rounded-xl border border-border bg-card/60">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-primary" />
          <span className="text-xs font-semibold text-foreground">Faster-Whisper Model: small (Float16)</span>
        </div>
        <DisabledFeatureBadge phase="Phase 09" featureName="Interactive Transcript Editor" />
      </div>

      <EmptyState
        icon={<Volume2 className="h-6 w-6 text-muted-foreground" />}
        title="No Transcript Available"
        description="The speech-to-text pipeline runs in Phase 09 using local Faster-Whisper on your RTX 3050 GPU."
      />
    </PageContainer>
  );
};
