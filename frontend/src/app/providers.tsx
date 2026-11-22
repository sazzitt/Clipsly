import React from "react";
import { BackendHealthProvider } from "../components/providers/BackendHealthProvider";
import { ToastProvider } from "../components/ui/toast";

interface ProvidersProps {
  children: React.ReactNode;
}

export const Providers: React.FC<ProvidersProps> = ({ children }) => {
  return (
    <BackendHealthProvider>
      <ToastProvider>{children}</ToastProvider>
    </BackendHealthProvider>
  );
};
