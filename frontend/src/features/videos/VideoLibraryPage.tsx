import React from "react";
import { Link } from "react-router-dom";
import { Video, Upload, Search, Filter } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { EmptyState } from "../../components/common/EmptyState";
import { DisabledFeatureBadge } from "../../components/common/DisabledFeatureBadge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";

export const VideoLibraryPage: React.FC = () => {
  return (
    <PageContainer
      title="Video Library"
      description="Manage and inspect ingested source video files stored locally in storage/uploads/."
      action={
        <Button asChild size="sm" className="gap-2">
          <Link to="/upload">
            <Upload className="h-3.5 w-3.5" />
            Upload Video
          </Link>
        </Button>
      }
    >
      {/* Search and Filters Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 rounded-xl border border-border bg-card/60">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search local videos..."
            className="pl-9 h-8 text-xs bg-secondary/50"
            disabled
          />
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
          <Button variant="outline" size="sm" className="gap-1.5 text-xs h-8" disabled>
            <Filter className="h-3.5 w-3.5 text-muted-foreground" />
            Filter
          </Button>
          <DisabledFeatureBadge phase="Phase 08" featureName="Video Catalog" />
        </div>
      </div>

      {/* Empty State */}
      <EmptyState
        icon={<Video className="h-6 w-6 text-muted-foreground" />}
        title="No Videos Ingested Yet"
        description="Your local video library is empty. Upload your first MP4, MOV, or MKV file to begin transcription and highlight extraction."
        actionLabel="Go to Upload"
        onAction={() => window.location.assign("/upload")}
      />
    </PageContainer>
  );
};
