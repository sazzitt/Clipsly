import * as React from "react";
import { ToastContext } from "../context/ToastContext";

export interface ToastOptions {
  title: string;
  description?: string;
  variant?: "default" | "success" | "error" | "warning" | "info" | "destructive";
  type?: "info" | "success" | "error" | "warning";
}

export function useToast() {
  const context = React.useContext(ToastContext);

  const fallback = React.useMemo(
    () => {
      const fn = () => {};
      return Object.assign(fn, {
        toast: fn,
        success: fn,
        error: fn,
        warning: fn,
        info: fn,
      });
    },
    []
  );

  const addToast = context?.addToast;

  return React.useMemo(
    () => {
      if (!addToast) return fallback;

      const triggerToast = (
        titleOrOptions: string | ToastOptions,
        description?: string
      ) => {
        if (typeof titleOrOptions === "object" && titleOrOptions !== null) {
          const rawVariant = titleOrOptions.variant || titleOrOptions.type;
          const type =
            rawVariant === "error" || rawVariant === "destructive"
              ? "error"
              : rawVariant === "success"
              ? "success"
              : rawVariant === "warning"
              ? "warning"
              : "info";
          addToast({
            type,
            title: titleOrOptions.title,
            description: titleOrOptions.description,
          });
        } else {
          addToast({ type: "info", title: titleOrOptions, description });
        }
      };

      return Object.assign(triggerToast, {
        toast: triggerToast,
        success: (title: string, description?: string) =>
          addToast({ type: "success", title, description }),
        error: (title: string, description?: string) =>
          addToast({ type: "error", title, description }),
        warning: (title: string, description?: string) =>
          addToast({ type: "warning", title, description }),
        info: (title: string, description?: string) =>
          addToast({ type: "info", title, description }),
      });
    },
    [addToast, fallback]
  );
}
