import { useState } from "react";
import {
  Activity,
  Cpu,
  Download,
  HardDrive,
  Play,
  RotateCcw,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";
import { PageContainer } from "../../components/layout/PageContainer";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Checkbox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Input,
  Kbd,
  Label,
  Progress,
  Select,
  Separator,
  Skeleton,
  Slider,
  StatusIndicator,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
} from "../../components/ui";
import {
  EmptyVideoLibrary,
  FeatureUnavailable,
  HardwareMetricCard,
  PageToolbar,
  ProcessingStatus,
  SectionHeader,
  StorageUsageBar,
  VideoMetadataRow,
  VideoThumbnail,
} from "../../components/workstation";
import { useToast } from "../../hooks/useToast";

export function ComponentShowcasePage() {
  const toast = useToast();

  // Interactive component states
  const [sliderVal, setSliderVal] = useState(65);
  const [switchVal, setSwitchVal] = useState(true);
  const [checkboxVal, setCheckboxVal] = useState(true);
  const [selectVal, setSelectVal] = useState("small");
  const [btnLoading, setBtnLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [inputVal, setInputVal] = useState("Valid Title");
  const [inputError, setInputError] = useState(false);

  const handleSimulateLoad = () => {
    setBtnLoading(true);
    setTimeout(() => {
      setBtnLoading(false);
      toast.success(
        "Action Completed",
        "The simulated asynchronous task finished successfully."
      );
    }, 1500);
  };

  return (
    <PageContainer
      title="Design System & UI Components"
      description="Isolated internal showcase of all design tokens, primitives, form controls, and workstation-specific components."
      action={
        <Badge variant="subtle" className="font-mono text-xs">
          Phase 09 • UI Foundation
        </Badge>
      }
    >
      <Tabs defaultValue="primitives" className="space-y-6">
        <TabsList className="bg-card border border-border">
          <TabsTrigger value="primitives">UI Primitives</TabsTrigger>
          <TabsTrigger value="forms">Form Controls</TabsTrigger>
          <TabsTrigger value="workstation">Workstation Modules</TabsTrigger>
          <TabsTrigger value="tokens">Design Tokens</TabsTrigger>
        </TabsList>

        {/* TAB 1: UI PRIMITIVES */}
        <TabsContent value="primitives" className="space-y-8">
          {/* Buttons Section */}
          <Card variant="section">
            <CardHeader>
              <CardTitle>Buttons & Actions</CardTitle>
              <CardDescription>
                High-contrast action controls with loading states, accessible focus rings, and active states.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <Button variant="default">Primary Action</Button>
                <Button variant="secondary">Secondary Action</Button>
                <Button variant="outline">Outline</Button>
                <Button variant="ghost">Ghost Action</Button>
                <Button variant="destructive">Destructive</Button>
                <Button variant="subtle">Subtle Violet</Button>
                <Button variant="link">Text Link</Button>
              </div>

              <Separator />

              <div className="flex flex-wrap items-center gap-3">
                <Button loading={btnLoading} onClick={handleSimulateLoad}>
                  {btnLoading ? "Processing..." : "Click to Test Loading"}
                </Button>
                <Button disabled>Disabled Button</Button>
                <Button size="sm" variant="secondary">
                  Small Button
                </Button>
                <Button size="lg" variant="default">
                  Large Button
                </Button>
                <Button size="icon" variant="outline" aria-label="Play video">
                  <Play className="h-4 w-4" />
                </Button>
                <Button size="iconSm" variant="ghost" aria-label="Settings">
                  <Settings className="h-3.5 w-3.5" />
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Badges & Status Indicators */}
          <Card variant="section">
            <CardHeader>
              <CardTitle>Badges & Status Indicators</CardTitle>
              <CardDescription>
                Color-coded operational indicators for pipeline states and telemetry.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-2.5">
                <Badge variant="default">Default Primary</Badge>
                <Badge variant="secondary">Neutral Secondary</Badge>
                <Badge variant="success">Success / Healthy</Badge>
                <Badge variant="warning">Warning / Degraded</Badge>
                <Badge variant="destructive">Error / Failed</Badge>
                <Badge variant="info">Information</Badge>
                <Badge variant="subtle">Subtle Violet</Badge>
                <Badge variant="disabled">Disabled Feature</Badge>
              </div>

              <Separator />

              <div className="flex flex-wrap items-center gap-6 text-xs">
                <StatusIndicator status="healthy" label="Online / Healthy" pulse />
                <StatusIndicator status="processing" label="Active Worker" pulse />
                <StatusIndicator status="degraded" label="VRAM Contested" />
                <StatusIndicator status="error" label="Pipeline Failed" />
                <StatusIndicator status="offline" label="Backend Offline" />
              </div>
            </CardContent>
          </Card>

          {/* Progress Bars */}
          <Card variant="section">
            <CardHeader>
              <CardTitle>Progress & Loading</CardTitle>
              <CardDescription>
                Determinate and indeterminate progress indicators for render stages.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-mono">
                  <span>Determinate Progress (65%)</span>
                  <span>65%</span>
                </div>
                <Progress value={65} />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-mono text-amber-400">
                  <span>Warning Status (90%)</span>
                  <span>90%</span>
                </div>
                <Progress value={90} variant="warning" />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-mono text-zinc-400">
                  <span>Indeterminate State (Waiting on Worker)</span>
                  <span>PULSING</span>
                </div>
                <Progress indeterminate />
              </div>

              <div className="pt-2">
                <p className="text-xs text-muted-foreground mb-2">Skeleton Placeholders:</p>
                <div className="flex items-center gap-3">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="space-y-1.5 grow">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Dialogs & Toasts */}
          <Card variant="section">
            <CardHeader>
              <CardTitle>Overlays, Dialogs & Toasts</CardTitle>
              <CardDescription>
                Accessible modals, confirmation flows, and floating feedback toasts.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                  <DialogTrigger asChild>
                    <Button variant="outline">Open Confirmation Dialog</Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Reset Timeline Trims?</DialogTitle>
                      <DialogDescription>
                        This will restore start and end timestamps to match the original candidate highlight.
                      </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                      <Button variant="ghost" onClick={() => setDialogOpen(false)}>
                        Cancel
                      </Button>
                      <Button
                        variant="default"
                        onClick={() => {
                          setDialogOpen(false);
                          toast.info("Trims Reset", "Timeline start and end markers restored to default.");
                        }}
                      >
                        Confirm Reset
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>

                <Button
                  variant="secondary"
                  onClick={() =>
                    toast.success(
                      "Export Succeeded",
                      "Video rendered in 1080x1920 (9:16) format via NVENC."
                    )
                  }
                >
                  Trigger Success Toast
                </Button>

                <Button
                  variant="secondary"
                  onClick={() =>
                    toast.warning(
                      "CUDA Memory Warning",
                      "Free VRAM is currently below 800MB. Consider closing background apps."
                    )
                  }
                >
                  Trigger Warning Toast
                </Button>

                <Button
                  variant="destructive"
                  onClick={() =>
                    toast.error(
                      "Subprocess Failed",
                      "FFmpeg terminated unexpectedly with exit code 1."
                    )
                  }
                >
                  Trigger Error Toast
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 2: FORM CONTROLS */}
        <TabsContent value="forms" className="space-y-8">
          <Card variant="section">
            <CardHeader>
              <CardTitle>Workstation Form Controls</CardTitle>
              <CardDescription>
                Inputs, selects, sliders, and toggles tailored for video parameter configuration.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Standard Input */}
                <div className="space-y-2">
                  <Label htmlFor="demo-title">Clip Title</Label>
                  <Input
                    id="demo-title"
                    value={inputVal}
                    onChange={(e) => setInputVal(e.target.value)}
                    placeholder="Enter short-form clip title..."
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Display name for the exported video file.
                  </p>
                </div>

                {/* Invalid / Error Input */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <Label htmlFor="demo-error" required>
                      Timestamp Offset
                    </Label>
                    <button
                      type="button"
                      onClick={() => setInputError(!inputError)}
                      className="text-[11px] text-primary hover:underline"
                    >
                      Toggle Error
                    </button>
                  </div>
                  <Input
                    id="demo-error"
                    defaultValue="invalid_ms"
                    error={inputError}
                    placeholder="e.g. 5000"
                  />
                  {inputError && (
                    <p className="text-[11px] text-destructive">
                      Must be a valid positive integer in milliseconds.
                    </p>
                  )}
                </div>

                {/* Select Dropdown */}
                <div className="space-y-2">
                  <Label htmlFor="demo-model">Whisper Model Size</Label>
                  <Select
                    id="demo-model"
                    value={selectVal}
                    onChange={(e) => setSelectVal(e.target.value)}
                  >
                    <option value="tiny">Tiny (39M params • ~1GB VRAM)</option>
                    <option value="base">Base (74M params • ~1GB VRAM)</option>
                    <option value="small">Small (244M params • ~2GB VRAM • Recommended)</option>
                    <option value="medium">Medium (769M params • ~4GB VRAM • CPU only)</option>
                  </Select>
                </div>

                {/* Multi-line Textarea */}
                <div className="space-y-2">
                  <Label htmlFor="demo-text">Custom Subtitle Override</Label>
                  <Textarea
                    id="demo-text"
                    rows={3}
                    placeholder="Override word transcript text for this clip segment..."
                    defaultValue="This is how local AI video clipping works on Windows 11."
                  />
                </div>
              </div>

              <Separator />

              {/* Sliders and Toggles */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <Slider
                    label="Subtitle Font Size"
                    value={sliderVal}
                    min={14}
                    max={72}
                    showValue
                    valueSuffix=" pt"
                    onChange={setSliderVal}
                  />

                  <div className="flex items-center gap-3 pt-2">
                    <span className="text-xs text-muted-foreground">Hotkeys:</span>
                    <Kbd>Space</Kbd>
                    <Kbd>J</Kbd>
                    <Kbd>K</Kbd>
                    <Kbd>L</Kbd>
                    <Kbd>Ctrl + S</Kbd>
                  </div>
                </div>

                <div className="space-y-4">
                  <Switch
                    checked={switchVal}
                    onCheckedChange={setSwitchVal}
                    label="Burn Subtitles into Video"
                    description="Permanently render karaoke styled ASS subtitles into MP4 via FFmpeg."
                  />

                  <Checkbox
                    checked={checkboxVal}
                    onCheckedChange={setCheckboxVal}
                    label="Hardware Acceleration (NVENC)"
                    description="Offload h264 encoding to RTX 3050 GPU instead of CPU."
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Table Component */}
          <Card variant="section">
            <CardHeader>
              <CardTitle>Data Table Primitive</CardTitle>
              <CardDescription>
                Dense tabular layout for job queues, clips, and file inventories.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Resolution</TableHead>
                    <TableHead>Target Aspect</TableHead>
                    <TableHead>Encoder</TableHead>
                    <TableHead>Bitrate</TableHead>
                    <TableHead className="text-right">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell className="font-mono">1080x1920</TableCell>
                    <TableCell>9:16 Vertical</TableCell>
                    <TableCell className="font-mono">h264_nvenc</TableCell>
                    <TableCell className="font-mono">8000 kbps</TableCell>
                    <TableCell className="text-right">
                      <Badge variant="success">READY</Badge>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-mono">720x1280</TableCell>
                    <TableCell>9:16 Vertical</TableCell>
                    <TableCell className="font-mono">h264_nvenc</TableCell>
                    <TableCell className="font-mono">4500 kbps</TableCell>
                    <TableCell className="text-right">
                      <Badge variant="secondary">QUEUED</Badge>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 3: WORKSTATION SPECIFIC MODULES */}
        <TabsContent value="workstation" className="space-y-8">
          {/* Section Header & Page Toolbar */}
          <Card variant="section">
            <CardHeader>
              <CardTitle>Navigation & Toolbars</CardTitle>
              <CardDescription>
                Reusable workstation header and toolbar containers.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <SectionHeader
                title="Clips Studio Timeline"
                description="Review detected candidate clips and customize aspect ratio framing."
                badge={<Badge variant="default">14 Candidates</Badge>}
                actions={
                  <Button size="sm" variant="outline" className="gap-1.5">
                    <RotateCcw className="h-3.5 w-3.5" />
                    <span>Reset Trims</span>
                  </Button>
                }
              />

              <PageToolbar
                searchSlot={
                  <div className="relative w-64">
                    <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                    <Input placeholder="Filter clips..." className="pl-8 h-8 text-xs" />
                  </div>
                }
                filterSlot={
                  <Select className="h-8 text-xs w-36">
                    <option>All Scores (&gt;0)</option>
                    <option>High Viral (&gt;80)</option>
                    <option>Approved Only</option>
                  </Select>
                }
                actionSlot={
                  <Button size="sm" className="gap-1.5">
                    <Download className="h-3.5 w-3.5" />
                    <span>Export Selected</span>
                  </Button>
                }
              />
            </CardContent>
          </Card>

          {/* Video Thumbnail & Metadata Row */}
          <Card variant="section">
            <CardHeader>
              <CardTitle>Video Thumbnail & Stream Characteristics</CardTitle>
              <CardDescription>
                Video asset preview with duration badges, resolution pills, and technical metadata.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-muted-foreground mb-2">16:9 Landscape Aspect:</p>
                  <VideoThumbnail
                    aspectRatio="16:9"
                    durationSeconds={754}
                    resolution="1080p"
                  />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-2">9:16 Vertical Preview:</p>
                  <div className="max-w-[160px]">
                    <VideoThumbnail
                      aspectRatio="9:16"
                      durationSeconds={45}
                      resolution="9:16"
                    />
                  </div>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-2">1:1 Square Preview:</p>
                  <div className="max-w-[200px]">
                    <VideoThumbnail
                      aspectRatio="1:1"
                      durationSeconds={30}
                      resolution="1080x1080"
                    />
                  </div>
                </div>
              </div>

              <div className="pt-2">
                <p className="text-xs text-muted-foreground mb-2">Stream Metadata Row:</p>
                <VideoMetadataRow
                  durationSeconds={124.5}
                  width={1920}
                  height={1080}
                  fps={30.0}
                  videoCodec="h264"
                  audioCodec="aac"
                  audioSampleRate={48000}
                  audioChannels={2}
                  fileSizeBytes={48234496}
                />
              </div>
            </CardContent>
          </Card>

          {/* Hardware Telemetry & Storage */}
          <Card variant="section">
            <CardHeader>
              <CardTitle>Hardware Telemetry & Capacity Safeguards</CardTitle>
              <CardDescription>
                Real-time GPU, CPU, and disk monitoring cards with threshold colors.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                <HardwareMetricCard
                  title="GPU VRAM (RTX 3050)"
                  value="1.3 / 4.0 GB"
                  subValue="Safe Headroom"
                  percent={33}
                  status="safe"
                  icon={<Activity className="h-4 w-4" />}
                />
                <HardwareMetricCard
                  title="GPU Compute Load"
                  value="18%"
                  subValue="NVENC Idle"
                  percent={18}
                  status="safe"
                  icon={<Sparkles className="h-4 w-4" />}
                />
                <HardwareMetricCard
                  title="Physical RAM"
                  value="8.2 / 16.0 GB"
                  subValue="System Memory"
                  percent={51}
                  status="safe"
                  icon={<Cpu className="h-4 w-4" />}
                />
                <HardwareMetricCard
                  title="SSD Free Headroom"
                  value="142.5 GB"
                  subValue="Safe (&gt;10 GB)"
                  percent={72}
                  status="safe"
                  icon={<HardDrive className="h-4 w-4" />}
                />
              </div>

              <div className="pt-2">
                <StorageUsageBar freeSpaceGb={142.5} totalSpaceGb={512} minSafeFreeSpaceGb={10} />
              </div>
            </CardContent>
          </Card>

          {/* Processing Status & Feature Unavailable */}
          <Card variant="section">
            <CardHeader>
              <CardTitle>Pipeline Status & Inactive Feature Banners</CardTitle>
              <CardDescription>
                Clear honest representations for background tasks and future milestones.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <ProcessingStatus
                  status="PROCESSING"
                  jobType="Whisper STT"
                  progressPercent={42}
                  currentStep="Transcribing speech with base.en model..."
                />
                <ProcessingStatus
                  status="COMPLETED"
                  jobType="Highlight Scoring"
                  progressPercent={100}
                  currentStep="Detected 12 viral candidate clips."
                />
              </div>

              <FeatureUnavailable
                featureName="NVENC Hardware-Accelerated Video Export"
                activationPhase="Phase 16"
                description="Batch rendering of vertical 9:16 MP4s with burned-in karaoke subtitles using NVIDIA NVENC."
                roadmapNote="Backend API endpoints return honest 501 Not Implemented status codes until Phase 16 activation."
              />

              <EmptyVideoLibrary />
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 4: DESIGN TOKENS */}
        <TabsContent value="tokens" className="space-y-8">
          <Card variant="section">
            <CardHeader>
              <CardTitle>Theme Colors & Token Palette</CardTitle>
              <CardDescription>
                High-contrast dark workstation color system documented in docs/02-DESIGN.md.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Core Surfaces */}
              <div>
                <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">
                  Surfaces & Canvas
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="rounded-lg border border-border p-3 bg-background space-y-1">
                    <div className="h-6 w-full rounded bg-background border border-border" />
                    <p className="font-semibold text-foreground">Canvas</p>
                    <p className="font-mono text-[10px] text-muted-foreground">#09090b</p>
                  </div>
                  <div className="rounded-lg border border-border p-3 bg-card space-y-1">
                    <div className="h-6 w-full rounded bg-card border border-border" />
                    <p className="font-semibold text-foreground">Card / Panel</p>
                    <p className="font-mono text-[10px] text-muted-foreground">#0f0f12</p>
                  </div>
                  <div className="rounded-lg border border-border p-3 bg-secondary space-y-1">
                    <div className="h-6 w-full rounded bg-secondary border border-border" />
                    <p className="font-semibold text-foreground">Secondary</p>
                    <p className="font-mono text-[10px] text-muted-foreground">#27272a</p>
                  </div>
                  <div className="rounded-lg border border-border p-3 bg-card space-y-1">
                    <div className="h-6 w-full rounded bg-primary" />
                    <p className="font-semibold text-foreground">Electric Violet</p>
                    <p className="font-mono text-[10px] text-muted-foreground">#7c3aed</p>
                  </div>
                </div>
              </div>

              {/* Subtitle Karaoke Tokens */}
              <div>
                <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">
                  Subtitle Highlight & Karaoke Tokens
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="rounded-lg border border-border p-3 bg-card space-y-1">
                    <div className="h-6 w-full rounded bg-karaoke-amber" />
                    <p className="font-semibold text-foreground">Amber Hook</p>
                    <p className="font-mono text-[10px] text-muted-foreground">#f59e0b</p>
                  </div>
                  <div className="rounded-lg border border-border p-3 bg-card space-y-1">
                    <div className="h-6 w-full rounded bg-karaoke-cyan" />
                    <p className="font-semibold text-foreground">Neon Cyan</p>
                    <p className="font-mono text-[10px] text-muted-foreground">#06b6d4</p>
                  </div>
                  <div className="rounded-lg border border-border p-3 bg-card space-y-1">
                    <div className="h-6 w-full rounded bg-karaoke-mint" />
                    <p className="font-semibold text-foreground">Fresh Mint</p>
                    <p className="font-mono text-[10px] text-muted-foreground">#10b981</p>
                  </div>
                  <div className="rounded-lg border border-border p-3 bg-card space-y-1">
                    <div className="h-6 w-full rounded bg-karaoke-rose" />
                    <p className="font-semibold text-foreground">Energy Rose</p>
                    <p className="font-mono text-[10px] text-muted-foreground">#f43f5e</p>
                  </div>
                </div>
              </div>

              {/* Typography Scale */}
              <div>
                <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">
                  Typography Scale
                </h4>
                <div className="space-y-3 rounded-lg border border-border bg-card/40 p-4">
                  <div>
                    <span className="text-[10px] font-mono text-muted-foreground">DISPLAY HEADER (24px SemiBold)</span>
                    <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                      Clipsly AI Video Clipper
                    </h1>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-muted-foreground">SECTION TITLE (18px Medium)</span>
                    <h2 className="text-lg font-medium text-foreground">
                      Candidate Highlights & Viral Hooks
                    </h2>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-muted-foreground">BODY TEXT (14px Regular)</span>
                    <p className="text-sm text-foreground">
                      Local-first AI video clipping running sovereignly on your Windows 11 laptop.
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-muted-foreground">TIMECODE TABULAR (13px Mono Bold)</span>
                    <p className="font-mono text-sm font-bold tabular-nums text-primary">
                      00:01:24.500 → 00:02:10.000 (00:00:45.500)
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
}
