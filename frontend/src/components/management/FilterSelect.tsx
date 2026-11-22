import * as React from "react";
import { Filter } from "lucide-react";
import { cn } from "../../lib/utils";
import { Select } from "../ui/select";

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: FilterOption[];
  label?: string;
  className?: string;
  disabled?: boolean;
}

export const FilterSelect: React.FC<FilterSelectProps> = ({
  value,
  onChange,
  options,
  label,
  className,
  disabled = false,
}) => {
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      {label && (
        <span className="text-xs text-muted-foreground shrink-0 hidden sm:inline flex items-center gap-1">
          <Filter className="h-3 w-3" />
          {label}:
        </span>
      )}
      <div className="w-36 sm:w-40">
        <Select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="h-8 text-xs bg-secondary/50 border-border"
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-card text-foreground">
              {opt.label}
            </option>
          ))}
        </Select>
      </div>
    </div>
  );
};
