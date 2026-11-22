import * as React from "react";
import { cn } from "../../lib/utils";

export interface PageToolbarProps extends React.HTMLAttributes<HTMLDivElement> {
  searchSlot?: React.ReactNode;
  filterSlot?: React.ReactNode;
  actionSlot?: React.ReactNode;
}

export const PageToolbar = React.forwardRef<HTMLDivElement, PageToolbarProps>(
  ({ searchSlot, filterSlot, actionSlot, className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 rounded-lg border border-border/60 bg-card/40 p-2.5",
          className
        )}
        {...props}
      >
        <div className="flex flex-1 flex-wrap items-center gap-2">
          {searchSlot}
          {filterSlot}
          {children}
        </div>
        {actionSlot && <div className="flex items-center gap-2 shrink-0">{actionSlot}</div>}
      </div>
    );
  }
);
PageToolbar.displayName = "PageToolbar";
