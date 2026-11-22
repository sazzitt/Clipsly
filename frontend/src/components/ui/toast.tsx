import * as React from "react";
import { AlertCircle, CheckCircle2, AlertTriangle, Info, X } from "lucide-react";
import { cn } from "../../lib/utils";
import { ToastContext, ToastItem } from "../../context/ToastContext";

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = React.useCallback(
    (toast: Omit<ToastItem, "id">) => {
      const id = Math.random().toString(36).substring(2, 9);
      const duration = toast.duration ?? 4500;
      setToasts((prev) => [...prev, { ...toast, id }]);

      if (duration > 0) {
        setTimeout(() => removeToast(id), duration);
      }
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      {/* Toast Viewport fixed at bottom-right */}
      <div
        aria-live="polite"
        className="fixed bottom-0 right-0 z-50 flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px] gap-2 pointer-events-none"
      >
        {toasts.map((t) => (
          <ToastCard key={t.id} toast={t} onClose={() => removeToast(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastCard({ toast, onClose }: { toast: ToastItem; onClose: () => void }) {
  const icons = {
    success: <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />,
    error: <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />,
    warning: <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />,
    info: <Info className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />,
  };

  const borders = {
    success: "border-emerald-500/20 bg-card",
    error: "border-red-500/20 bg-card",
    warning: "border-amber-500/20 bg-card",
    info: "border-blue-500/20 bg-card",
  };

  return (
    <div
      role="alert"
      className={cn(
        "pointer-events-auto relative flex w-full items-start gap-3 overflow-hidden rounded-xl border p-4 shadow-lg backdrop-blur-md transition-all animate-in slide-in-from-bottom-5",
        borders[toast.type]
      )}
    >
      {icons[toast.type]}
      <div className="flex-1 space-y-1">
        <p className="text-xs font-semibold text-foreground">{toast.title}</p>
        {toast.description && (
          <p className="text-xs text-muted-foreground leading-normal">{toast.description}</p>
        )}
      </div>
      <button
        onClick={onClose}
        className="rounded-md p-1 text-muted-foreground opacity-60 hover:opacity-100 hover:bg-secondary focus:outline-none"
        aria-label="Close notification"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
