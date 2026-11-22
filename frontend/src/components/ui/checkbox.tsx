import * as React from "react";
import { Check } from "lucide-react";
import { cn } from "../../lib/utils";

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  label?: React.ReactNode;
  description?: string;
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, checked = false, onCheckedChange, disabled, label, description, id, ...props }, ref) => {
    const generatedId = React.useId();
    const inputId = id || generatedId;

    return (
      <div className="flex items-start gap-2.5 select-none">
        <div className="relative flex items-center justify-center mt-0.5">
          <input
            type="checkbox"
            id={inputId}
            ref={ref}
            checked={checked}
            disabled={disabled}
            onChange={(e) => onCheckedChange?.(e.target.checked)}
            className="peer sr-only"
            {...props}
          />
          <div
            onClick={() => !disabled && onCheckedChange?.(!checked)}
            className={cn(
              "flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border border-input bg-card/60 transition-colors cursor-pointer",
              "peer-focus-visible:outline-none peer-focus-visible:ring-1 peer-focus-visible:ring-ring",
              checked && "border-primary bg-primary text-primary-foreground",
              disabled && "cursor-not-allowed opacity-50",
              className
            )}
          >
            {checked && <Check className="h-3 w-3 stroke-[3]" />}
          </div>
        </div>
        {label && (
          <div className="grid gap-0.5 leading-none">
            <label
              htmlFor={inputId}
              className={cn(
                "text-xs font-medium text-foreground cursor-pointer leading-tight",
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
      </div>
    );
  }
);
Checkbox.displayName = "Checkbox";

export { Checkbox };
