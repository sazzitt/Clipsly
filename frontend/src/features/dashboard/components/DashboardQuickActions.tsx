import * as React from "react";
import { Link } from "react-router-dom";
import { Upload, Video, Film, Download, Settings, ArrowRight } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";

export const DashboardQuickActions: React.FC = () => {
  const actions = [
    {
      title: "Import Video",
      description: "Ingest local MP4/MOV recordings to local SSD storage.",
      icon: <Upload className="h-4 w-4 text-emerald-400" />,
      to: "/upload",
      ariaLabel: "Go to video import",
    },
    {
      title: "Video Library",
      description: "Browse ingested videos, transcripts, and metadata.",
      icon: <Video className="h-4 w-4 text-blue-400" />,
      to: "/videos",
      ariaLabel: "Go to video library",
    },
    {
      title: "Clips Studio",
      description: "Review detected highlights, aspect ratios, and styles.",
      icon: <Film className="h-4 w-4 text-violet-400" />,
      to: "/clips",
      ariaLabel: "Go to clips studio",
    },
    {
      title: "Export Queue",
      description: "Monitor hardware-accelerated NVENC 9:16 vertical exports.",
      icon: <Download className="h-4 w-4 text-amber-400" />,
      to: "/exports",
      ariaLabel: "Go to export queue",
    },
    {
      title: "Settings",
      description: "Configure local storage directories and AI model limits.",
      icon: <Settings className="h-4 w-4 text-zinc-400" />,
      to: "/settings",
      ariaLabel: "Go to settings",
    },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
          Workstation Navigation
        </h2>
        <span className="text-[11px] font-mono text-zinc-500">Quick Access</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {actions.map((action) => (
          <Card
            key={action.title}
            className="group hover:border-primary/40 hover:bg-card-hover transition-all"
          >
            <CardHeader className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded-lg bg-secondary text-foreground">
                  {action.icon}
                </div>
                <Button asChild variant="ghost" size="iconSm">
                  <Link to={action.to} aria-label={action.ariaLabel}>
                    <ArrowRight className="h-4 w-4 opacity-70 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                  </Link>
                </Button>
              </div>
              <div>
                <CardTitle className="text-sm font-semibold mt-1">
                  <Link to={action.to} className="hover:text-primary transition-colors">
                    {action.title}
                  </Link>
                </CardTitle>
                <CardDescription className="text-xs text-muted-foreground mt-1 line-clamp-2 leading-relaxed">
                  {action.description}
                </CardDescription>
              </div>
            </CardHeader>
          </Card>
        ))}
      </div>
    </div>
  );
};
