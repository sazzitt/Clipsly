import React from "react";
import { Link } from "react-router-dom";
import { HardDrive, ArrowLeft, Trash2, FolderCheck } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Progress } from "../../components/ui/progress";

export const StoragePage: React.FC = () => {
  return (
    <PageContainer
      title="Storage Management"
      description="Inspect local SSD partition allocation across uploads, clips, exports, and SQLite storage."
      action={
        <Button asChild variant="outline" size="sm" className="gap-2">
          <Link to="/settings">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Settings
          </Link>
        </Button>
      }
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <HardDrive className="h-4 w-4 text-primary" />
                <CardTitle className="text-sm">SSD Capacity & Allocation</CardTitle>
              </div>
              <span className="text-xs font-mono text-emerald-400">75+ GB Free Space</span>
            </div>
            <CardDescription>Target Drive: C:\ (NVMe SSD)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">SSD Usage</span>
                <span className="text-foreground font-mono">Healthy Headroom</span>
              </div>
              <Progress value={20} />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              <div className="p-3 rounded-xl bg-secondary/40 border border-border/60 space-y-1">
                <p className="text-xs font-medium text-foreground">Uploads Buffer</p>
                <p className="text-[11px] text-muted-foreground font-mono">storage/uploads/</p>
                <p className="text-xs text-muted-foreground pt-1">0 files (0 MB)</p>
              </div>

              <div className="p-3 rounded-xl bg-secondary/40 border border-border/60 space-y-1">
                <p className="text-xs font-medium text-foreground">Exported MP4s</p>
                <p className="text-[11px] text-muted-foreground font-mono">storage/exports/</p>
                <p className="text-xs text-muted-foreground pt-1">0 files (0 MB)</p>
              </div>

              <div className="p-3 rounded-xl bg-secondary/40 border border-border/60 space-y-1">
                <p className="text-xs font-medium text-foreground">Audio & Transcripts</p>
                <p className="text-[11px] text-muted-foreground font-mono">storage/audio/ & transcripts/</p>
                <p className="text-xs text-muted-foreground pt-1">0 files (0 MB)</p>
              </div>

              <div className="p-3 rounded-xl bg-secondary/40 border border-border/60 space-y-1">
                <p className="text-xs font-medium text-foreground">SQLite WAL Database</p>
                <p className="text-[11px] text-muted-foreground font-mono">data/clipsly.db</p>
                <p className="text-xs text-muted-foreground pt-1">Active (4.0 KB)</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Maintenance Actions */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <FolderCheck className="h-4 w-4 text-emerald-400" />
              <CardTitle className="text-sm">Maintenance</CardTitle>
            </div>
            <CardDescription>Clean temporary working buffers.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button variant="outline" size="sm" className="w-full justify-start gap-2" disabled>
              <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
              Clear Temp Buffer
            </Button>
            <p className="text-[11px] text-muted-foreground">
              Storage cleanup and automated vacuuming activate in Phase 18.
            </p>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
};
