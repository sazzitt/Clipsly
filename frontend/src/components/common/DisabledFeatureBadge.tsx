import React from "react";
import { Lock } from "lucide-react";
import { Badge } from "../ui/badge";

interface DisabledFeatureBadgeProps {
  phase: string;
  featureName?: string;
}

export const DisabledFeatureBadge: React.FC<DisabledFeatureBadgeProps> = ({
  phase,
  featureName,
}) => {
  return (
    <div className="inline-flex items-center gap-1.5">
      <Badge variant="secondary" className="gap-1 text-[11px] font-mono border-border/80">
        <Lock className="h-3 w-3 text-muted-foreground" />
        <span>{phase}</span>
      </Badge>
      {featureName && (
        <span className="text-xs text-muted-foreground">({featureName})</span>
      )}
    </div>
  );
};
