import React from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, RefreshCw, Terminal } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Button } from "../../components/ui/button";
import { Skeleton } from "../../components/ui/skeleton";
import { useDashboardData } from "./hooks/useDashboardData";
import {
  DashboardHeader,
  DashboardMetrics,
  DashboardStorage,
  DashboardHardware,
  DashboardRecentVideos,
  DashboardRecentActivity,
  DashboardQuickActions,
  DashboardSystemStatus,
} from "./components";

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { summary, isLoading, isRefreshing, error, refresh } = useDashboardData();

  if (isLoading && !summary) {
    return (
      <PageContainer>
        <div className="space-y-6" data-testid="dashboard-loading-skeleton">
          {/* Header Skeleton */}
          <div className="rounded-2xl border border-border/80 bg-card/60 p-8 space-y-4">
            <Skeleton className="h-6 w-48 rounded-full" />
            <Skeleton className="h-9 w-96 max-w-full" />
            <Skeleton className="h-4 w-3/4" />
            <div className="pt-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-4 w-28" />
            </div>
          </div>

          {/* Metrics Skeleton */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, idx) => (
              <div key={idx} className="rounded-xl border border-border bg-card/90 p-4 space-y-3">
                <div className="flex justify-between items-center">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-7 w-7 rounded-lg" />
                </div>
                <Skeleton className="h-8 w-16" />
                <Skeleton className="h-3 w-32" />
              </div>
            ))}
          </div>

          {/* Quick Actions Skeleton */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {Array.from({ length: 5 }).map((_, idx) => (
              <div key={idx} className="rounded-xl border border-border bg-card p-4 space-y-2">
                <Skeleton className="h-8 w-8 rounded-lg" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-3 w-full" />
              </div>
            ))}
          </div>

          {/* Telemetry Skeleton */}
          <div className="rounded-xl border border-border bg-card/60 p-6 space-y-4">
            <Skeleton className="h-5 w-40" />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, idx) => (
                <Skeleton key={idx} className="h-28 rounded-xl" />
              ))}
            </div>
          </div>
        </div>
      </PageContainer>
    );
  }

  if (error && !summary) {
    return (
      <PageContainer>
        <div
          data-testid="dashboard-error-state"
          className="rounded-2xl border border-destructive/40 bg-destructive/10 p-8 sm:p-12 text-center max-w-2xl mx-auto my-8 space-y-4 shadow-lg"
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-destructive/20 text-destructive mx-auto">
            <AlertCircle className="h-7 w-7" />
          </div>

          <div className="space-y-1.5">
            <h2 className="text-lg font-bold text-foreground">Backend Connection Failed</h2>
            <p className="text-sm text-destructive font-mono">{error}</p>
          </div>

          <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
            Ensure the Clipsly FastAPI local server is running on <code className="text-foreground font-mono bg-secondary px-1.5 py-0.5 rounded">http://127.0.0.1:8000</code>.
          </p>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Button onClick={() => refresh()} variant="default" className="gap-2">
              <RefreshCw className="h-4 w-4" />
              <span>Retry Connection</span>
            </Button>
          </div>

          <div className="pt-4 border-t border-destructive/20 text-[11px] font-mono text-muted-foreground flex items-center justify-center gap-2">
            <Terminal className="h-3 w-3" />
            <span>Command: python -m uvicorn app.main:app --port 8000</span>
          </div>
        </div>
      </PageContainer>
    );
  }

  if (!summary) {
    return null;
  }

  return (
    <PageContainer>
      <div className="space-y-8 pb-12">
        {/* Header Hero */}
        <DashboardHeader
          systemHealth={summary.system}
          isRefreshing={isRefreshing}
          onRefresh={refresh}
        />

        {/* Overview Metric Cards */}
        <DashboardMetrics
          counts={
            summary.counts ?? {
              total_videos: 0,
              total_clips: 0,
              active_jobs: 0,
              completed_exports: 0,
              total_transcripts: 0,
              total_highlights: 0,
            }
          }
        />

        {/* Quick Navigation Cards */}
        <DashboardQuickActions />

        {/* Storage Diagnostics */}
        {summary.storage && <DashboardStorage storage={summary.storage} />}

        {/* Hardware Telemetry */}
        {summary.hardware && <DashboardHardware hardware={summary.hardware} />}

        {/* Recent Ingested Videos (Real DB Entities or Clean Empty State) */}
        <DashboardRecentVideos
          videos={summary.recent_videos ?? []}
          totalVideosCount={summary.counts?.total_videos ?? 0}
          onUploadClick={() => navigate("/upload")}
        />

        {/* Recent Background Activity (Real Jobs or Idle State) */}
        <DashboardRecentActivity jobs={summary.recent_jobs ?? []} />

        {/* Backend & Hardware Readiness Diagnostics */}
        {summary.system && <DashboardSystemStatus system={summary.system} />}
      </div>
    </PageContainer>
  );
};
