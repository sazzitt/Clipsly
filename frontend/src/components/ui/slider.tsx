import * as React from "react";
import { cn } from "../../lib/utils";

export interface SliderProps {
  value: number;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  onChange: (value: number) => void;
  className?: string;
  showValue?: boolean;
  valueSuffix?: string;
  label?: string;
}

export const Slider = React.forwardRef<HTMLInputElement, SliderProps>(
  (
    {
      value,
      min = 0,
      max = 100,
      step = 1,
      disabled = false,
      onChange,
      className,
      showValue = false,
      valueSuffix = "",
      label,
    },
    ref
  ) => {
    const percentage = Math.min(Math.max(((value - min) / (max - min)) * 100, 0), 100);

    return (
      <div className={cn("w-full space-y-1.5", className)}>
        {(label || showValue) && (
          <div className="flex items-center justify-between text-xs">
            {label && <span className="font-medium text-foreground">{label}</span>}
            {showValue && (
              <span className="font-mono tabular-nums text-muted-foreground">
                {value}
                {valueSuffix}
              </span>
            )}
          </div>
        )}
        <div className="relative flex items-center select-none touch-none w-full h-5">
          <input
            ref={ref}
            type="range"
            min={min}
            max={max}
            step={step}
            value={value}
            disabled={disabled}
            onChange={(e) => onChange(Number(e.target.value))}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed z-10"
          />
          <div className="relative h-2 w-full grow overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full bg-primary transition-all rounded-full"
              style={{ width: `${percentage}%` }}
            />
          </div>
          <div
            className={cn(
              "absolute h-4 w-4 rounded-full border border-primary/50 bg-background shadow transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none pointer-events-none -ml-2",
              disabled && "opacity-50"
            )}
            style={{ left: `${percentage}%` }}
          />
        </div>
      </div>
    );
  }
);
Slider.displayName = "Slider";
