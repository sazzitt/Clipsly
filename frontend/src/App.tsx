import React from "react";
import { Header } from "./components/Header";
import { HealthStatusCard } from "./components/HealthStatusCard";
import { 
  FolderGit2, 
  Terminal, 
  Layers, 
  CheckCircle, 
  Cpu, 
  HardDrive,
  FileCode2
} from "lucide-react";

export const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Foundation Banner */}
        <div className="rounded-2xl border border-violet-500/20 bg-gradient-to-r from-violet-950/20 via-card to-card p-6 sm:p-8 shadow-lg">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-2 max-w-2xl">
              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-violet-500/10 text-violet-400 text-xs font-mono font-medium border border-violet-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse"></span>
                Phase 06 Active: Development Environment & Foundations
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
                Clipsly Workstation Foundation
              </h2>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Single-user, local-first AI video clipper configured specifically for your ASUS TUF A15 
                (Ryzen 7 7435HS, NVIDIA RTX 3050 4GB VRAM, 16GB DDR5, SQLite WAL storage).
              </p>
            </div>

            <div className="flex flex-col gap-2 shrink-0 text-xs font-mono text-muted-foreground bg-secondary/60 p-4 rounded-xl border border-border">
              <div className="flex items-center gap-2 text-foreground font-semibold">
                <Terminal className="h-4 w-4 text-violet-400" />
                <span>Runtime Configuration</span>
              </div>
              <div className="flex justify-between gap-4">
                <span>Frontend:</span>
                <span className="text-foreground">React 18 + Vite + TS</span>
              </div>
              <div className="flex justify-between gap-4">
                <span>Backend:</span>
                <span className="text-foreground">FastAPI (Python 3.14)</span>
              </div>
              <div className="flex justify-between gap-4">
                <span>Database:</span>
                <span className="text-foreground">SQLite 3 (WAL mode)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Real-time Diagnostics Card */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider">
              System Health & Diagnostics
            </h3>
            <span className="text-xs text-muted-foreground font-mono">127.0.0.1:8000 Proxy Verified</span>
          </div>
          <HealthStatusCard />
        </section>

        {/* Architecture & Verification Checklist */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1: Directory Structure */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <FolderGit2 className="h-4 w-4 text-violet-400" />
              <span>Project Architecture</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Standard monorepo with segregated storage, databases, and logs.
            </p>
            <ul className="text-xs space-y-1.5 text-muted-foreground font-mono">
              <li className="flex items-center gap-2">
                <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                <span>storage/ (uploads, audio, clips)</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                <span>data/ (clipsly.db WAL mode)</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                <span>logs/ (clipsly_app.log)</span>
              </li>
            </ul>
          </div>

          {/* Card 2: Hardware Boundary Control */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Cpu className="h-4 w-4 text-emerald-400" />
              <span>Hardware Optimization</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Strict memory segregation for 4GB VRAM constraint.
            </p>
            <ul className="text-xs space-y-1.5 text-muted-foreground font-mono">
              <li className="flex items-center gap-2">
                <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                <span>Faster-Whisper (Float16)</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                <span>NVENC Hardware Encoder</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                <span>Zero VRAM Concurrency Lock</span>
              </li>
            </ul>
          </div>

          {/* Card 3: Next Phase Readiness */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Layers className="h-4 w-4 text-blue-400" />
              <span>Phase 07 Readiness</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Backend routes and database schemas ready for next phase.
            </p>
            <ul className="text-xs space-y-1.5 text-muted-foreground font-mono">
              <li className="flex items-center gap-2">
                <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                <span>FastAPI Lifespan & CORS</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                <span>Alembic Migration Pipeline</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                <span>Next: Video Ingestion & Slicing</span>
              </li>
            </ul>
          </div>
        </section>

        {/* Footer Note */}
        <footer className="pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between text-xs text-muted-foreground gap-4">
          <div className="flex items-center gap-2">
            <FileCode2 className="h-4 w-4 text-violet-400" />
            <span>Clipsly — Local-First Single-User Architecture</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <HardDrive className="h-3.5 w-3.5" />
              Local Storage Only
            </span>
            <span>No Cloud Dependencies Required</span>
          </div>
        </footer>
      </main>
    </div>
  );
};
