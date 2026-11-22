import React from "react";
import { UploadCloud, FileVideo, HardDrive, AlertCircle } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Card, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { DisabledFeatureBadge } from "../../components/common/DisabledFeatureBadge";

export const UploadPage: React.FC = () => {
  return (
    <PageContainer
      title="Upload Video"
      description="Select or drop a local video file to ingest into sovereign local SSD storage."
    >
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Upload Dropzone Container */}
        <div className="relative rounded-2xl border-2 border-dashed border-border bg-card/40 p-8 sm:p-12 text-center transition-colors hover:border-primary/50">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary border border-primary/20 mb-4 shadow-sm shadow-primary/10">
            <UploadCloud className="h-8 w-8" />
          </div>

          <h2 className="text-base font-semibold text-foreground">
            Drop your local video file here, or click to browse
          </h2>
          <p className="mt-1.5 text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
            Fast local SSD ingestion directly into <code className="text-foreground font-mono">storage/uploads/</code>.
            Supported containers: <span className="text-foreground font-medium">MP4, MOV, MKV, WebM</span>.
          </p>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
            <span className="px-2.5 py-1 rounded-md bg-secondary text-[11px] font-mono text-muted-foreground border border-border">
              Max Size: 4GB
            </span>
            <span className="px-2.5 py-1 rounded-md bg-secondary text-[11px] font-mono text-muted-foreground border border-border">
              Constant Frame Rate (CFR)
            </span>
            <span className="px-2.5 py-1 rounded-md bg-secondary text-[11px] font-mono text-muted-foreground border border-border">
              Localhost Loopback Only
            </span>
          </div>

          <div className="mt-8 pt-6 border-t border-border/60 flex items-center justify-center gap-3">
            <DisabledFeatureBadge phase="Phase 08" featureName="Chunked File Ingestion" />
            <span className="text-xs text-muted-foreground">
              Ingestion engine activates in next phase.
            </span>
          </div>
        </div>

        {/* Ingestion Rules & Specifications */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <FileVideo className="h-4 w-4 text-emerald-400" />
                <CardTitle className="text-xs">Codec Requirements</CardTitle>
              </div>
              <CardDescription>
                H.264 (AVC) or H.265 (HEVC) with AAC audio recommended for optimal GPU throughput.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <HardDrive className="h-4 w-4 text-blue-400" />
                <CardTitle className="text-xs">Storage Quota</CardTitle>
              </div>
              <CardDescription>
                Requires at least 10 GB free SSD space before initiating file upload.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>

        {/* Notice Banner */}
        <div className="p-4 rounded-xl bg-secondary/50 border border-border/80 flex items-start gap-3 text-xs text-muted-foreground">
          <AlertCircle className="h-4 w-4 text-primary shrink-0 mt-0.5" />
          <p>
            No external cloud upload occurs. All video bytes remain on this workstation's local NVMe drive.
          </p>
        </div>
      </div>
    </PageContainer>
  );
};
