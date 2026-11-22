import React from "react";
import { Link } from "react-router-dom";
import { HardDrive, Cpu, ShieldCheck, Sparkles } from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import { useBackendHealth } from "../../hooks/useBackendHealth";

export const SettingsPage: React.FC = () => {
  const { health } = useBackendHealth();

  return (
    <PageContainer
      title="Application Settings"
      description="Configure hardware acceleration preferences, storage paths, and model configurations."
      action={
        <div className="flex items-center gap-2">
          <Button asChild variant="outline" size="sm" className="gap-2">
            <Link to="/design-system">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              Design System
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm" className="gap-2">
            <Link to="/settings/storage">
              <HardDrive className="h-3.5 w-3.5 text-primary" />
              Storage
            </Link>
          </Button>
        </div>
      }
    >
      <Tabs defaultValue="hardware" className="space-y-6">
        <TabsList>
          <TabsTrigger value="hardware">Hardware & Acceleration</TabsTrigger>
          <TabsTrigger value="transcription">Transcription Defaults</TabsTrigger>
          <TabsTrigger value="security">Local Isolation</TabsTrigger>
        </TabsList>

        <TabsContent value="hardware" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-emerald-400" />
                  <CardTitle className="text-sm">NVIDIA GPU Acceleration</CardTitle>
                </div>
                <CardDescription>Target hardware configuration.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-xs font-mono">
                <div className="flex justify-between border-b border-border/40 pb-1.5">
                  <span className="text-muted-foreground">GPU Model:</span>
                  <span className="text-foreground">NVIDIA RTX 3050 Laptop</span>
                </div>
                <div className="flex justify-between border-b border-border/40 pb-1.5">
                  <span className="text-muted-foreground">VRAM Total:</span>
                  <span className="text-foreground">4096 MiB GDDR6</span>
                </div>
                <div className="flex justify-between border-b border-border/40 pb-1.5">
                  <span className="text-muted-foreground">CUDA Available:</span>
                  <span className={health?.cuda_available ? "text-emerald-400" : "text-amber-400"}>
                    {health?.cuda_available ? "Yes (Active)" : "No (CPU Fallback)"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">NVENC Ready:</span>
                  <span className={health?.nvenc_available ? "text-emerald-400" : "text-amber-400"}>
                    {health?.nvenc_available ? "Yes (h264_nvenc)" : "No"}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <HardDrive className="h-4 w-4 text-violet-400" />
                  <CardTitle className="text-sm">Storage Configuration</CardTitle>
                </div>
                <CardDescription>Local storage paths and quotas.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-xs font-mono">
                <div className="flex justify-between border-b border-border/40 pb-1.5">
                  <span className="text-muted-foreground">Database:</span>
                  <span className="text-foreground">data/clipsly.db (WAL)</span>
                </div>
                <div className="flex justify-between border-b border-border/40 pb-1.5">
                  <span className="text-muted-foreground">Upload Buffer:</span>
                  <span className="text-foreground">storage/uploads/</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Export Target:</span>
                  <span className="text-foreground">storage/exports/</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="transcription" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Speech-to-Text Defaults</CardTitle>
              <CardDescription>Model weights and compute precision for Faster-Whisper.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-secondary/50 border border-border/60">
                <p className="font-semibold text-foreground">Default Model: Faster-Whisper small (Float16)</p>
                <p className="text-muted-foreground mt-0.5">
                  Optimized for 4GB VRAM ceiling. Consumes ~1.1GB VRAM during transcription.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-blue-400" />
                <CardTitle className="text-sm">Sovereign Localhost Loopback</CardTitle>
              </div>
              <CardDescription>Network and isolation policies.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-muted-foreground">
              <p>
                Clipsly runs strictly on <code className="text-foreground font-mono">127.0.0.1:8000</code>. No telemetry or external cloud egress is permitted.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
};
