import React from "react";
import { useParams, Link } from "react-router-dom";
import { Scissors, ArrowLeft, Type, Maximize2 } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { DisabledFeatureBadge } from "../../components/common/DisabledFeatureBadge";

export const StudioPage: React.FC = () => {
  const { clipId } = useParams<{ clipId: string }>();

  return (
    <PageContainer
      title={`Studio Editor: ${clipId || "Draft"}`}
      description="Interactive preview player, dual-handle trim timeline, and subtitle styler."
      action={
        <Button asChild variant="outline" size="sm" className="gap-2">
          <Link to="/clips">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Clips
          </Link>
        </Button>
      }
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: 9:16 Preview Player Container */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="flex flex-col items-center justify-center p-8 min-h-[460px] bg-black/40 border-dashed">
            <div className="w-52 h-96 rounded-xl border border-border/80 bg-zinc-950 flex flex-col items-center justify-center p-4 text-center shadow-2xl relative">
              <span className="absolute top-3 left-3 text-[10px] font-mono text-muted-foreground bg-secondary/80 px-2 py-0.5 rounded">
                9:16 Vertical
              </span>
              <Scissors className="h-8 w-8 text-primary mb-3" />
              <p className="text-xs font-semibold text-foreground">Interactive Video Player</p>
              <p className="text-[11px] text-muted-foreground mt-1">
                HTML5 Video with synchronized subtitle overlays.
              </p>
            </div>
            <div className="mt-4">
              <DisabledFeatureBadge phase="Phase 15" featureName="Interactive Studio" />
            </div>
          </Card>
        </div>

        {/* Right: Studio Controls Panel */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Maximize2 className="h-4 w-4 text-primary" />
                <CardTitle className="text-sm">Aspect Ratio & Re-Framing</CardTitle>
              </div>
              <CardDescription>Select between 9:16 vertical blur-fill or center crop.</CardDescription>
            </CardHeader>
            <CardContent>
              <DisabledFeatureBadge phase="Phase 13" featureName="Vertical Blur Fill" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Type className="h-4 w-4 text-emerald-400" />
                <CardTitle className="text-sm">Karaoke Subtitles</CardTitle>
              </div>
              <CardDescription>Preset font styling and animation highlights.</CardDescription>
            </CardHeader>
            <CardContent>
              <DisabledFeatureBadge phase="Phase 14" featureName="Subtitle Styler" />
            </CardContent>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
};
