import * as React from "react";
import { SearchX, RotateCcw } from "lucide-react";
import { cn } from "../../lib/utils";
import { Button } from "../ui/button";

export interface NoResultsStateProps {
  title?: string;
  description?: string;
  onClearFilters?: () => void;
  className?: string;
}

export const NoResultsState: React.FC<NoResultsStateProps> = ({
  title = "No Results Match Your Filter",
  description = "Try adjusting your search query, clearing status filters, or resetting sorting criteria.",
  onClearFilters,
  className,
}) => {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/30 p-10 text-center space-y-3",
        className
      )}
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-secondary text-muted-foreground">
        <SearchX className="h-5 w-5 text-zinc-500" />
      </div>
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        <p className="max-w-sm text-xs text-muted-foreground leading-relaxed">{description}</p>
      </div>
      {onClearFilters && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onClearFilters}
          className="gap-1.5 text-xs h-8 mt-2"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          <span>Reset Filters</span>
        </Button>
      )}
    </div>
  );
};
