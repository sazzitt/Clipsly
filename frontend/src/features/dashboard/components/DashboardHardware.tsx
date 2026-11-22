import * as React from "react";
import { Cpu, Zap, Activity, HardDrive } from "lucide-react";
import { HardwareMetricCard } from "../../../components/workstation/HardwareMetricCard";
import { SystemHardwareTelemetry } from "../../../types/api";

export interface DashboardHardwareProps {
  hardware: SystemHardwareTelemetry;
}

export const DashboardHardware: React.FC<DashboardHardwareProps> = ({ hardware }) => {
  const vramPercent =
    hardware.gpu_vram_total_mb > 0
      ? Math.round((hardware.gpu_vram_used_mb / hardware.gpu_vram_total_mb) * 100)
      : 0;

  const ramPercent =
    hardware.system_ram_total_gb > 0
      ? Math.round((hardware.system_ram_used_gb / hardware.system_ram_total_gb) * 100)
      : 0;

  const hasGpu = hardware.gpu_vram_total_mb > 0;

  const getVramStatus = (): "safe" | "warning" | "error" | "neutral" => {
    if (!hasGpu) return "neutral";
    if (vramPercent > 90) return "error";
    if (vramPercent > 75) return "warning";
    return "safe";
  };

  const getCpuStatus = (): "safe" | "warning" | "error" | "neutral" => {
    if (hardware.cpu_load_percent > 85) return "warning";
    return "safe";
  };

  const getRamStatus = (): "safe" | "warning" | "error" | "neutral" => {
    if (ramPercent > 85) return "warning";
    return "safe";
  };

  const getGpuLoadStatus = (): "safe" | "warning" | "error" | "neutral" => {
    if (!hasGpu) return "neutral";
    if (hardware.gpu_utilization_percent > 90) return "warning";
    return "safe";
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold tracking-tight text-foreground">Hardware Telemetry</h2>
        </div>
        <span className="text-xs font-mono text-muted-foreground">
          {hasGpu ? "RTX 3050 Laptop GPU (4GB VRAM)" : "CPU Fallback Mode"}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* GPU VRAM Card */}
        <HardwareMetricCard
          title="GPU VRAM"
          value={hasGpu ? `${hardware.gpu_vram_used_mb} MB` : "N/A"}
          subValue={hasGpu ? `/ ${hardware.gpu_vram_total_mb} MB` : "CPU Mode"}
          icon={<Zap className="h-4 w-4" />}
          percent={hasGpu ? vramPercent : 0}
          status={getVramStatus()}
        />

        {/* GPU Compute Load */}
        <HardwareMetricCard
          title="GPU Compute Load"
          value={hasGpu ? `${hardware.gpu_utilization_percent}%` : "0%"}
          subValue={hasGpu ? "Active Utilization" : "Idle"}
          icon={<Activity className="h-4 w-4" />}
          percent={hasGpu ? hardware.gpu_utilization_percent : 0}
          status={getGpuLoadStatus()}
        />

        {/* CPU Load */}
        <HardwareMetricCard
          title="CPU Load"
          value={`${hardware.cpu_load_percent}%`}
          subValue="AMD Ryzen 7"
          icon={<Cpu className="h-4 w-4" />}
          percent={hardware.cpu_load_percent}
          status={getCpuStatus()}
        />

        {/* System RAM */}
        <HardwareMetricCard
          title="System RAM"
          value={`${hardware.system_ram_used_gb.toFixed(1)} GB`}
          subValue={`/ ${hardware.system_ram_total_gb.toFixed(0)} GB`}
          icon={<HardDrive className="h-4 w-4" />}
          percent={ramPercent}
          status={getRamStatus()}
        />
      </div>
    </div>
  );
};
