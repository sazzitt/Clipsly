import * as React from "react";
import { Link } from "react-router-dom";
import { Video, Film, Activity, Download, ArrowUpRight } from "lucide-react";
import { Card } from "../../../components/ui/card";
import { DashboardCounts } from "../../../types/api";

export interface DashboardMetricsProps {
  counts: DashboardCounts;
}

export const DashboardMetrics: React.FC<DashboardMetricsProps> = ({ counts }) => {
  const metrics = [
    {
      title: "Total Videos",
      value: counts.total_videos,
      subValue: "Ingested source files",
      icon: <Video className="h-4 w-4 text-emerald-400" />,
      linkTo: "/videos",
      linkLabel: "View library",
      borderHover: "hover:border-emerald-500/40",
    },
    {
      title: "Generated Clips",
      value: counts.total_clips,
      subValue: "9:16 vertical shorts ready",
      icon: <Film className="h-4 w-4 text-blue-400" />,
      linkTo: "/clips",
      linkLabel: "Browse clips",
      borderHover: "hover:border-blue-500/40",
    },
    {
      title: "Active Jobs",
      value: counts.active_jobs,
      subValue: `${counts.total_transcripts} transcripts, ${counts.total_highlights} highlights`,
      icon: <Activity className="h-4 w-4 text-amber-400" />,
      linkTo: undefined,
      linkLabel: "Real-time queue",
      borderHover: "hover:border-amber-500/40",
    },
    {
      title: "Completed Exports",
      value: counts.completed_exports,
      subValue: "Rendered via h264_nvenc",
      icon: <Download className="h-4 w-4 text-primary" />,
      linkTo: "/exports",
      linkLabel: "Export queue",
      borderHover: "hover:border-primary/40",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric) => (
        <Card
          key={metric.title}
          variant="metric"
          className={`group transition-all duration-200 ${metric.borderHover} space-y-3`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">{metric.title}</span>
            <div className="p-2 rounded-lg bg-secondary/80 shrink-0">
              {metric.icon}
            </div>
          </div>

          <div>
            <div className="font-mono text-3xl font-bold tracking-tight text-foreground tabular-nums">
              {metric.value}
            </div>
            <p className="text-xs text-muted-foreground mt-1 truncate">
              {metric.subValue}
            </p>
          </div>

          <div className="pt-2 border-t border-border/40 flex items-center justify-between text-xs">
            {metric.linkTo ? (
              <Link
                to={metric.linkTo}
                className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-foreground font-medium transition-colors"
              >
                <span>{metric.linkLabel}</span>
                <ArrowUpRight className="h-3 w-3 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </Link>
            ) : (
              <span className="text-xs text-zinc-500">{metric.linkLabel}</span>
            )}
            <span className="text-[10px] font-mono text-zinc-500 uppercase">Local SQLite</span>
          </div>
        </Card>
      ))}
    </div>
  );
};
