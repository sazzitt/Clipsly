import * as React from "react";
import { ToastContext } from "../context/ToastContext";

export function useToast() {
  const context = React.useContext(ToastContext);

  const fallback = React.useMemo(
    () => ({
      toast: () => {},
      success: () => {},
      error: () => {},
      warning: () => {},
      info: () => {},
    }),
    []
  );

  const addToast = context?.addToast;

  return React.useMemo(
    () => {
      if (!addToast) return fallback;
      return {
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
      };
    },
    [addToast, fallback]
  );
}
