import React from "react";
import { Film, SlidersHorizontal } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { EmptyState } from "../../components/common/EmptyState";
import { DisabledFeatureBadge } from "../../components/common/DisabledFeatureBadge";
import { Button } from "../../components/ui/button";

export const ClipsLibraryPage: React.FC = () => {
  return (
    <PageContainer
      title="Clips Library"
      description="Review, customize, and export cut video clips formatted for vertical social feeds."
      action={
        <Button variant="outline" size="sm" className="gap-2" disabled>
          <SlidersHorizontal className="h-3.5 w-3.5" />
          Batch Export
        </Button>
      }
    >
      <div className="flex items-center justify-between p-3 rounded-xl border border-border bg-card/60">
        <span className="text-xs text-muted-foreground">
          Saved clip configurations and rendered short-form previews.
        </span>
        <DisabledFeatureBadge phase="Phase 12" featureName="FFmpeg Cut & Slice" />
      </div>

      <EmptyState
        icon={<Film className="h-6 w-6 text-muted-foreground" />}
        title="No Clips Created Yet"
        description="Clips are generated automatically from highlights or created manually via the Studio in Phases 11–13."
      />
    </PageContainer>
  );
};
