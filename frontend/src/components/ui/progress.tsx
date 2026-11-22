import * as React from "react";
import { cn } from "../../lib/utils";

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  max?: number;
  indeterminate?: boolean;
  variant?: "default" | "success" | "warning" | "destructive";
  size?: "sm" | "default" | "lg";
}

const variantStyles = {
  default: "bg-primary",
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  destructive: "bg-destructive",
};

const sizeStyles = {
  sm: "h-1.5",
  default: "h-2",
  lg: "h-3",
};

export const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  (
    {
      className,
      value,
      max = 100,
      indeterminate = false,
      variant = "default",
      size = "default",
      ...props
    },
    ref
  ) => {
    const isIndeterminate = indeterminate || value === undefined || value === null;
    const percentage = isIndeterminate ? 100 : Math.min(Math.max(((value || 0) / max) * 100, 0), 100);

    return (
      <div
        ref={ref}
        role="progressbar"
        aria-valuenow={isIndeterminate ? undefined : value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-busy={isIndeterminate ? "true" : undefined}
        className={cn(
          "relative w-full overflow-hidden rounded-full bg-secondary",
          sizeStyles[size],
          className
        )}
        {...props}
      >
        <div
          className={cn(
            "h-full w-full flex-1 rounded-full transition-all duration-300 ease-in-out",
            variantStyles[variant],
            isIndeterminate && "animate-pulse origin-left"
          )}
          style={{ transform: isIndeterminate ? "none" : `translateX(-${100 - percentage}%)` }}
        />
      </div>
    );
  }
);
Progress.displayName = "Progress";
