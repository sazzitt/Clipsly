import { cva } from "class-variance-authority";

export const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-1 focus:ring-ring",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-border bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-destructive/30 bg-destructive/15 text-destructive-foreground hover:bg-destructive/25",
        outline: "border-border text-foreground hover:bg-secondary/50",
        success:
          "border-emerald-500/30 bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25",
        warning:
          "border-amber-500/30 bg-amber-500/15 text-amber-400 hover:bg-amber-500/25",
        info:
          "border-blue-500/30 bg-blue-500/15 text-blue-400 hover:bg-blue-500/25",
        subtle:
          "border-primary/30 bg-primary/10 text-primary",
        disabled:
          "border-zinc-800 bg-zinc-900/60 text-zinc-500 cursor-not-allowed",
      },
      size: {
        default: "px-2.5 py-0.5 text-xs",
        sm: "px-2 py-0.2 text-[10px] tracking-wide",
        lg: "px-3 py-1 text-sm font-semibold",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);
