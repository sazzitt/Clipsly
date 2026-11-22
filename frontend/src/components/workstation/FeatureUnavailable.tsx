import * as React from "react";
import { Info, Lock } from "lucide-react";
import { cn } from "../../lib/utils";
import { Badge } from "../ui/badge";

export interface FeatureUnavailableProps extends React.HTMLAttributes<HTMLDivElement> {
  featureName: string;
  activationPhase: string;
  description?: string;
  roadmapNote?: string;
}

export const FeatureUnavailable = React.forwardRef<HTMLDivElement, FeatureUnavailableProps>(
  (
    {
      featureName,
      activationPhase,
      description,
      roadmapNote,
      className,
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-xl border border-border/80 bg-card/60 p-6 space-y-3",
          className
        )}
        {...props}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary text-zinc-400">
              <Lock className="h-4 w-4" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-foreground">{featureName}</h4>
              <p className="text-xs text-muted-foreground">Pipeline Module Inactive</p>
            </div>
          </div>
          <Badge variant="disabled" className="gap-1 font-mono text-[10px]">
            <span>Activates in {activationPhase}</span>
          </Badge>
        </div>

        {description && (
          <p className="text-xs text-muted-foreground leading-relaxed">
            {description}
          </p>
        )}

        {roadmapNote && (
          <div className="flex items-start gap-2 rounded-lg border border-border/50 bg-secondary/30 p-2.5 text-xs text-zinc-400">
            <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
            <span className="text-[11px] leading-relaxed">{roadmapNote}</span>
          </div>
        )}
      </div>
    );
  }
);
FeatureUnavailable.displayName = "FeatureUnavailable";
