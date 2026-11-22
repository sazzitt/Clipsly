import React from "react";
import { useLocation, Link } from "react-router-dom";
import {
  Menu,
  RefreshCw,
  Cpu,
  ChevronRight,
  Wifi,
  WifiOff,
  AlertTriangle,
} from "lucide-react";
import { useBackendHealth } from "../../hooks/useBackendHealth";

interface HeaderProps {
  onMobileMenuToggle?: () => void;
}

const routeTitles: Record<string, string> = {
  "/": "Dashboard",
  "/videos": "Video Library",
  "/upload": "Upload Video",
  "/clips": "Clips Library",
  "/exports": "Export Queue",
  "/settings": "Settings",
  "/settings/storage": "Storage Management",
};

export const Header: React.FC<HeaderProps> = ({ onMobileMenuToggle }) => {
  const location = useLocation();
  const { isConnected, isDegraded, loading, refresh, health } = useBackendHealth();

  // Determine title or dynamic route title
  let currentTitle = routeTitles[location.pathname];
  if (!currentTitle) {
    if (location.pathname.startsWith("/video/") && location.pathname.endsWith("/transcript")) {
      currentTitle = "Transcript Viewer";
    } else if (location.pathname.startsWith("/video/") && location.pathname.endsWith("/highlights")) {
      currentTitle = "Highlights Review";
    } else if (location.pathname.startsWith("/video/")) {
      currentTitle = "Video Details";
    } else if (location.pathname.startsWith("/studio/")) {
      currentTitle = "Clip Studio";
    } else {
      currentTitle = "Workstation";
    }
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-border bg-card/60 px-4 sm:px-6 backdrop-blur-md">
      {/* Left: Mobile hamburger & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMobileMenuToggle}
          className="lg:hidden p-2 text-muted-foreground hover:text-foreground rounded-lg hover:bg-secondary"
          aria-label="Open navigation sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>

        <nav aria-label="Breadcrumbs" className="flex items-center gap-1.5 text-xs">
          <Link to="/" className="text-muted-foreground hover:text-foreground transition-colors font-medium">
            Clipsly
          </Link>
          <ChevronRight className="h-3 w-3 text-muted-foreground/60" />
          <span className="font-semibold text-foreground">{currentTitle}</span>
        </nav>
      </div>

      {/* Right: Hardware badge & Backend Health Indicator */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        {/* Hardware target chip */}
        <div className="hidden md:flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-[11px] text-muted-foreground border border-border">
          <Cpu className="h-3.5 w-3.5 text-emerald-400" />
          <span className="font-mono">RTX 3050 (4GB)</span>
        </div>

        {/* Backend Connection Status Pill */}
        <div className="flex items-center gap-1.5">
          <div
            className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium border transition-colors ${
              isConnected
                ? isDegraded
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                  : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : "bg-red-500/10 text-red-400 border-red-500/20"
            }`}
            title={`Backend: 127.0.0.1:8000 | Status: ${health?.status ?? "Offline"}`}
          >
            {isConnected ? (
              isDegraded ? (
                <>
                  <AlertTriangle className="h-3 w-3 text-amber-400" />
                  <span className="font-mono hidden sm:inline">Degraded</span>
                </>
              ) : (
                <>
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <Wifi className="h-3 w-3 hidden sm:inline" />
                  <span className="font-mono">127.0.0.1:8000</span>
                </>
              )
            ) : (
              <>
                <WifiOff className="h-3 w-3 text-red-400" />
                <span className="font-mono">Offline</span>
              </>
            )}
          </div>

          <button
            onClick={() => refresh()}
            disabled={loading}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-lg hover:bg-secondary transition-colors disabled:opacity-50"
            title="Refresh Backend Telemetry"
            aria-label="Refresh telemetry"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
