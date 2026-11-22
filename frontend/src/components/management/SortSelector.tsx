import * as React from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { cn } from "../../lib/utils";
import { Select } from "../ui/select";
import { Button } from "../ui/button";

export interface SortOption {
  value: string;
  label: string;
}

export interface SortSelectorProps {
  sortBy: string;
  onSortChange: (value: string) => void;
  order: "asc" | "desc";
  onOrderToggle: () => void;
  options: SortOption[];
  className?: string;
  disabled?: boolean;
}

export const SortSelector: React.FC<SortSelectorProps> = ({
  sortBy,
  onSortChange,
  order,
  onOrderToggle,
  options,
  className,
  disabled = false,
}) => {
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <span className="text-xs text-muted-foreground shrink-0 hidden sm:inline flex items-center gap-1">
        <ArrowUpDown className="h-3 w-3" />
        Sort:
      </span>
      <div className="w-36 sm:w-40">
        <Select
          value={sortBy}
          onChange={(e) => onSortChange(e.target.value)}
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

      <Button
        type="button"
        variant="outline"
        size="iconSm"
        onClick={onOrderToggle}
        disabled={disabled}
        className="h-8 w-8 shrink-0 bg-secondary/50 border-border"
        title={order === "asc" ? "Sort Ascending (click for Descending)" : "Sort Descending (click for Ascending)"}
        aria-label="Toggle sort direction"
      >
        {order === "asc" ? (
          <ArrowUp className="h-3.5 w-3.5 text-foreground" />
        ) : (
          <ArrowDown className="h-3.5 w-3.5 text-foreground" />
        )}
      </Button>
    </div>
  );
};
