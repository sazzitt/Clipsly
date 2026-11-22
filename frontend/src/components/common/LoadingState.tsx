import React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../../lib/utils";

interface LoadingStateProps {
  title?: string;
  description?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  title = "Loading...",
  description,
  className,
}) => {
  return (
    <div
      className={cn(
        "flex min-h-[220px] flex-col items-center justify-center rounded-xl border border-border/60 bg-card/40 p-8 text-center animate-in fade-in",
        className
      )}
    >
      <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      {description && (
        <p className="mt-1 text-xs text-muted-foreground max-w-sm">{description}</p>
      )}
    </div>
  );
};
