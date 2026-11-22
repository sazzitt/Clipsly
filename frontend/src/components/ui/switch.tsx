import * as React from "react";
import { cn } from "../../lib/utils";

export interface SwitchProps {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  label?: React.ReactNode;
  description?: string;
  className?: string;
  id?: string;
}

const Switch = React.forwardRef<HTMLButtonElement, SwitchProps>(
  ({ checked = false, onCheckedChange, disabled = false, label, description, className, id }, ref) => {
    const generatedId = React.useId();
    const switchId = id || generatedId;

    return (
      <div className="flex items-center justify-between gap-3 select-none">
        {label && (
          <div className="grid gap-0.5 leading-none">
            <label
              htmlFor={switchId}
              className={cn(
                "text-xs font-medium text-foreground cursor-pointer",
                disabled && "cursor-not-allowed opacity-70"
              )}
            >
              {label}
            </label>
            {description && (
              <p className="text-[11px] text-muted-foreground leading-normal">{description}</p>
            )}
          </div>
        )}
        <button
          type="button"
          role="switch"
          id={switchId}
          ref={ref}
          aria-checked={checked}
          disabled={disabled}
          onClick={() => onCheckedChange?.(!checked)}
          className={cn(
            "peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
            checked ? "bg-primary" : "bg-secondary",
            className
          )}
        >
          <span
            className={cn(
              "pointer-events-none block h-4 w-4 rounded-full bg-foreground shadow-lg ring-0 transition-transform",
              checked ? "translate-x-4 bg-primary-foreground" : "translate-x-0 bg-zinc-400"
            )}
          />
        </button>
      </div>
    );
  }
);
Switch.displayName = "Switch";

export { Switch };
