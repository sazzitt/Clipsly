import React from "react";
import { useParams, Link } from "react-router-dom";
import { Sparkles, ArrowLeft, BarChart3 } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { EmptyState } from "../../components/common/EmptyState";
import { DisabledFeatureBadge } from "../../components/common/DisabledFeatureBadge";
import { Button } from "../../components/ui/button";

export const HighlightsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <PageContainer
      title="AI Highlight Detection"
      description={`Ranked highlight segments and engagement scores for video ${id || ""}.`}
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
          <Sparkles className="h-4 w-4 text-primary" />
          <span className="text-xs font-semibold text-foreground">Scoring Formula: Hook (30%) + Flow (30%) + Density (25%) + Energy (15%)</span>
        </div>
        <DisabledFeatureBadge phase="Phase 10" featureName="Heuristic Scoring Engine" />
      </div>

      <EmptyState
        icon={<BarChart3 className="h-6 w-6 text-muted-foreground" />}
        title="No Highlights Detected Yet"
        description="Highlight scoring evaluates audio energy, speech density, and hook sentences in Phase 10."
      />
    </PageContainer>
  );
};
