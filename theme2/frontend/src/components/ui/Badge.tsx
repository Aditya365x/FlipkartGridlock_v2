import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badge = cva("stat-chip border", {
  variants: {
    tone: {
      neutral: "border-line bg-white/5 text-ink-muted",
      brand: "border-brand/40 bg-brand/10 text-brand-bright",
      danger: "border-danger/50 bg-danger/10 text-danger",
      warn: "border-warn/50 bg-warn/10 text-warn",
      amber: "border-amber/50 bg-amber/10 text-amber",
      safe: "border-safe/50 bg-safe/10 text-safe",
    },
  },
  defaultVariants: { tone: "neutral" },
});

export interface BadgeProps extends VariantProps<typeof badge> {
  className?: string;
  children: React.ReactNode;
}

export function Badge({ tone, className, children }: BadgeProps) {
  return <span className={cn(badge({ tone }), className)}>{children}</span>;
}
