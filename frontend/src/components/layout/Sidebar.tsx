import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Video,
  Upload,
  Film,
  Download,
  Settings,
  HardDrive,
  Scissors,
  X,
} from "lucide-react";
import { cn } from "../../lib/utils";

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

interface NavItem {
  label: string;
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const navItems: NavItem[] = [
  { label: "Dashboard", to: "/", icon: LayoutDashboard },
  { label: "Video Library", to: "/videos", icon: Video },
  { label: "Upload Video", to: "/upload", icon: Upload },
  { label: "Clips Library", to: "/clips", icon: Film },
  { label: "Export Queue", to: "/exports", icon: Download },
  { label: "Settings", to: "/settings", icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({ mobileOpen = false, onMobileClose }) => {
  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden animate-in fade-in"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Panel */}
      <aside
        className={cn(
          "fixed top-0 bottom-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-card/95 backdrop-blur-md transition-transform duration-200 ease-in-out lg:static lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between px-6 border-b border-border">
          <NavLink to="/" className="flex items-center gap-3" onClick={onMobileClose}>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 border border-primary/20 text-primary shadow-sm shadow-primary/10">
              <Scissors className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold tracking-tight text-foreground text-sm">Clipsly</span>
                <span className="rounded bg-primary/20 px-1.5 py-0.2 text-[10px] font-mono uppercase text-primary border border-primary/30">
                  v1.0
                </span>
              </div>
              <p className="text-[10px] text-muted-foreground">Local AI Video Clipper</p>
            </div>
          </NavLink>

          {/* Close button for mobile view */}
          {onMobileClose && (
            <button
              onClick={onMobileClose}
              className="lg:hidden p-1.5 text-muted-foreground hover:text-foreground rounded-lg hover:bg-secondary"
              aria-label="Close menu"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Navigation Section */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          <div className="px-3 pb-2 text-[11px] font-mono uppercase tracking-wider text-muted-foreground/70">
            Workstation
          </div>

          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  onClick={onMobileClose}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2 text-xs font-medium transition-colors select-none",
                      isActive
                        ? "bg-primary/15 text-primary border border-primary/25 font-semibold shadow-xs"
                        : "text-muted-foreground hover:bg-secondary/70 hover:text-foreground"
                    )
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="flex-1">{item.label}</span>
                  {item.badge && (
                    <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground font-mono">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Host / Storage Hardware Footer */}
        <div className="border-t border-border p-3 m-3 rounded-xl bg-secondary/40 border border-border/60">
          <div className="flex items-center gap-2 mb-1.5">
            <HardDrive className="h-3.5 w-3.5 text-violet-400" />
            <span className="text-[11px] font-semibold text-foreground">Local Sovereign Storage</span>
          </div>
          <p className="text-[10px] text-muted-foreground leading-relaxed">
            All media, transcripts, and SQLite databases remain on local disk.
          </p>
        </div>
      </aside>
    </>
  );
};
