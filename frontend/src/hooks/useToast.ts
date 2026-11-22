import * as React from "react";
import { ToastContext } from "../context/ToastContext";

export function useToast() {
  const context = React.useContext(ToastContext);

  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }

  const { addToast } = context;

  return React.useMemo(
    () => ({
      toast: (title: string, description?: string) =>
        addToast({ type: "info", title, description }),
      success: (title: string, description?: string) =>
        addToast({ type: "success", title, description }),
      error: (title: string, description?: string) =>
        addToast({ type: "error", title, description }),
      warning: (title: string, description?: string) =>
        addToast({ type: "warning", title, description }),
      info: (title: string, description?: string) =>
        addToast({ type: "info", title, description }),
    }),
    [addToast]
  );
}
