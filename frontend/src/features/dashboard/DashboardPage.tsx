import React from "react";
import { Link } from "react-router-dom";
import { 
  Upload, 
  Video, 
  Film, 
  Download, 
  ArrowRight,
  Layers,
  CheckCircle,
  Terminal,
  Cpu
} from "lucide-react";
import { HealthStatusCard } from "../../components/HealthStatusCard";
import { PageContainer } from "../../components/layout/PageContainer";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";

export const DashboardPage: React.FC = () => {
  return (
    <PageContainer>
      {/* Welcome & Phase 07 Status Hero */}
      <div className="rounded-2xl border border-violet-500/20 bg-gradient-to-r from-violet-950/20 via-card to-card p-6 sm:p-8 shadow-lg">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-violet-500/10 text-violet-400 text-xs font-mono font-medium border border-violet-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
              Phase 07 Active: Frontend Architecture & Scalable Router
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Clipsly Workstation Dashboard
            </h1>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Complete single-user local web client with centralized API services, React Router navigation, 
              shadcn design tokens, and real-time backend connectivity.
            </p>
          </div>

          <div className="flex flex-col gap-2 shrink-0 text-xs font-mono text-muted-foreground bg-secondary/60 p-4 rounded-xl border border-border">
            <div className="flex items-center gap-2 text-foreground font-semibold">
              <Terminal className="h-4 w-4 text-violet-400" />
              <span>Target Environment</span>
            </div>
            <div className="flex justify-between gap-4">
              <span>Platform:</span>
              <span className="text-foreground">Windows 11 (64-bit)</span>
            </div>
            <div className="flex justify-between gap-4">
              <span>GPU:</span>
              <span className="text-foreground">RTX 3050 (4GB)</span>
            </div>
            <div className="flex justify-between gap-4">
              <span>Database:</span>
              <span className="text-foreground">SQLite WAL Mode</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Action Navigation Grid */}
      <section className="space-y-3">
        <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
          Workstation Navigation
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="hover:border-primary/40 transition-colors">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded-lg bg-primary/10 text-primary">
                  <Upload className="h-4 w-4" />
                </div>
                <Button asChild variant="ghost" size="iconSm">
                  <Link to="/upload" aria-label="Go to upload">
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
              <CardTitle className="text-sm mt-2">Upload Video</CardTitle>
              <CardDescription>Ingest local MP4/MOV files to SSD storage.</CardDescription>
            </CardHeader>
          </Card>

          <Card className="hover:border-primary/40 transition-colors">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded-lg bg-secondary text-foreground">
                  <Video className="h-4 w-4 text-emerald-400" />
                </div>
                <Button asChild variant="ghost" size="iconSm">
                  <Link to="/videos" aria-label="Go to video library">
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
              <CardTitle className="text-sm mt-2">Video Library</CardTitle>
              <CardDescription>Browse ingested videos and transcripts.</CardDescription>
            </CardHeader>
          </Card>

          <Card className="hover:border-primary/40 transition-colors">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded-lg bg-secondary text-foreground">
                  <Film className="h-4 w-4 text-blue-400" />
                </div>
                <Button asChild variant="ghost" size="iconSm">
                  <Link to="/clips" aria-label="Go to clips">
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
              <CardTitle className="text-sm mt-2">Clips Library</CardTitle>
              <CardDescription>Preview highlights, aspect ratios, and styles.</CardDescription>
            </CardHeader>
          </Card>

          <Card className="hover:border-primary/40 transition-colors">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded-lg bg-secondary text-foreground">
                  <Download className="h-4 w-4 text-violet-400" />
                </div>
                <Button asChild variant="ghost" size="iconSm">
                  <Link to="/exports" aria-label="Go to exports">
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
              <CardTitle className="text-sm mt-2">Export Queue</CardTitle>
              <CardDescription>Monitor NVENC rendered 9:16 vertical exports.</CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* Backend & Hardware Diagnostics (Preserves Phase 06 functionality) */}
      <section className="space-y-3">
        <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
          Telemetry & Hardware Health
        </h2>
        <HealthStatusCard />
      </section>

      {/* Roadmap Milestone Readiness */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Layers className="h-4 w-4 text-violet-400" />
              <span>Frontend Architecture</span>
            </div>
            <CardDescription>Established modular directories and router.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-xs font-mono text-muted-foreground">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
              <span>React Router 6.28</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
              <span>shadcn/ui Design Tokens</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
              <span>Centralized API Client</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Cpu className="h-4 w-4 text-emerald-400" />
              <span>Memory Guardrails</span>
            </div>
            <CardDescription>Respects 4GB VRAM ceiling.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-xs font-mono text-muted-foreground">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
              <span>Sequential Model Execution</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
              <span>Zero Concurrent VRAM Load</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
              <span>NVENC Hardware Accelerated</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Terminal className="h-4 w-4 text-blue-400" />
              <span>Next Phase Scope</span>
            </div>
            <CardDescription>Pipeline activation starts next.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-xs font-mono text-muted-foreground">
            <div className="flex items-center gap-2 text-foreground font-semibold">
              <ArrowRight className="h-3.5 w-3.5 text-violet-400" />
              <span>Phase 08: Video Ingestion & FFprobe</span>
            </div>
            <div className="text-[11px] text-muted-foreground">
              Local file chunking, SQLite schema mapping, and probe analysis.
            </div>
          </CardContent>
        </Card>
      </section>
    </PageContainer>
  );
};
