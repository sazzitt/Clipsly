import React from "react";
import { Download } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { EmptyState } from "../../components/common/EmptyState";
import { DisabledFeatureBadge } from "../../components/common/DisabledFeatureBadge";

export const ExportsPage: React.FC = () => {
  return (
    <PageContainer
      title="Export Queue"
      description="Monitor active FFmpeg rendering tasks and download exported MP4 clips from storage/exports/."
    >
      <div className="flex items-center justify-between p-3 rounded-xl border border-border bg-card/60">
        <div className="flex items-center gap-2">
          <Download className="h-4 w-4 text-emerald-400" />
          <span className="text-xs font-semibold text-foreground">Hardware Encoder: FFmpeg h264_nvenc</span>
        </div>
        <DisabledFeatureBadge phase="Phase 16" featureName="NVENC Render Pipeline" />
      </div>

      <EmptyState
        icon={<Download className="h-6 w-6 text-muted-foreground" />}
        title="No Rendered Exports"
        description="Videos queued for export will render sequentially using hardware NVENC encoding in Phase 16."
      />
    </PageContainer>
  );
};
