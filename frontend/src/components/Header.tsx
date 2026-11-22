import React from "react";
import { Scissors, ShieldCheck, Cpu } from "lucide-react";

export const Header: React.FC = () => {
  return (
    <header className="border-b border-border bg-card/60 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shadow-sm shadow-primary/10">
            <Scissors className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold tracking-tight text-foreground">Clipsly</h1>
              <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-primary/20 text-primary border border-primary/30">
                Phase 06
              </span>
            </div>
            <p className="text-xs text-muted-foreground">Local-First AI Video Clipper</p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-secondary border border-border text-muted-foreground">
            <Cpu className="h-3.5 w-3.5 text-emerald-400" />
            <span className="font-mono">RTX 3050 (4GB VRAM)</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-secondary border border-border text-muted-foreground">
            <ShieldCheck className="h-3.5 w-3.5 text-blue-400" />
            <span className="font-mono">127.0.0.1:8000</span>
          </div>
        </div>
      </div>
    </header>
  );
};
