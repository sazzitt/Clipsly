import { cva } from "class-variance-authority";

export const cardVariants = cva(
  "rounded-xl border border-border bg-card text-card-foreground shadow-sm transition-all",
  {
    variants: {
      variant: {
        default: "",
        interactive:
          "hover:border-zinc-700 hover:bg-card-hover cursor-pointer active:scale-[0.995]",
        metric:
          "bg-card/90 border-border p-4 flex flex-col justify-between",
        section:
          "bg-card/60 border-border backdrop-blur-sm",
        compact:
          "p-3 rounded-lg",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);
