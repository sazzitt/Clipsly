import * as React from "react";
import { cn } from "../../lib/utils";

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  delayMs?: number;
}

export function Tooltip({ content, children, delayMs = 200 }: TooltipProps) {
  const [visible, setVisible] = React.useState(false);
  const timeoutRef = React.useRef<number | null>(null);

  const show = () => {
    timeoutRef.current = window.setTimeout(() => setVisible(true), delayMs);
  };

  const hide = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setVisible(false);
  };

  return (
    <div className="relative inline-flex" onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide}>
      {children}
      {visible && (
        <div
          role="tooltip"
          className={cn(
            "absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 overflow-hidden rounded-md bg-secondary px-2.5 py-1 text-xs text-foreground shadow-md border border-border animate-in fade-in zoom-in-95 pointer-events-none whitespace-nowrap"
          )}
        >
          {content}
        </div>
      )}
    </div>
  );
}
