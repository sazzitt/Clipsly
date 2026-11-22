import React from "react";
import { useParams, Link } from "react-router-dom";
import { Video, FileText, Sparkles, ArrowLeft } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { DisabledFeatureBadge } from "../../components/common/DisabledFeatureBadge";

export const VideoDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <PageContainer
      title={`Video: ${id || "Unknown"}`}
      description="Inspect video stream metadata, transcription status, and highlight extraction candidates."
      action={
        <Button asChild variant="outline" size="sm" className="gap-2">
          <Link to="/videos">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Videos
          </Link>
        </Button>
      }
    >
      {/* Subnavigation Bar */}
      <div className="flex items-center gap-2 border-b border-border pb-2">
        <Button variant="default" size="sm" className="gap-2">
          <Video className="h-3.5 w-3.5" />
          Overview
        </Button>
        <Button asChild variant="ghost" size="sm" className="gap-2">
          <Link to={`/video/${id}/transcript`}>
            <FileText className="h-3.5 w-3.5" />
            Transcript
          </Link>
        </Button>
        <Button asChild variant="ghost" size="sm" className="gap-2">
          <Link to={`/video/${id}/highlights`}>
            <Sparkles className="h-3.5 w-3.5" />
            Highlights
          </Link>
        </Button>
      </div>

      {/* Overview Details Placeholder */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Source Video Stream</CardTitle>
            <CardDescription>Container and codec details parsed via FFprobe.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="p-4 rounded-xl bg-secondary/40 border border-border/60 text-xs space-y-2 font-mono">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Video ID:</span>
                <span className="text-foreground">{id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Storage Status:</span>
                <span className="text-amber-400">Placeholder (No video loaded)</span>
              </div>
            </div>
            <DisabledFeatureBadge phase="Phase 08" featureName="FFprobe Metadata Extraction" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Processing Pipeline State</CardTitle>
            <CardDescription>Sequential job execution tracking.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground leading-relaxed">
              When a video is uploaded in Phase 08, its audio extraction, Whisper transcription, 
              and heuristic scoring stages will appear here with live SSE progress.
            </p>
            <DisabledFeatureBadge phase="Phase 09" featureName="Pipeline Job Monitor" />
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
};
