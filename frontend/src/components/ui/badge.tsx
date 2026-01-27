import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "#/utils/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-[var(--text-accent)] text-white hover:bg-[var(--text-accent)]/80",
        secondary:
          "border-transparent bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]/80",
        destructive:
          "bg-[var(--text-danger)]/10 text-[var(--text-danger)] border-transparent",
        outline: "border-[var(--border-primary)] text-[var(--text-primary)]",
        success:
          "bg-[var(--text-success)]/10 text-[var(--text-success)] border-transparent",
        warning:
          "bg-[var(--text-warning)]/10 text-[var(--text-warning)] border-transparent",
        info: "bg-[var(--text-info)]/10 text-[var(--text-info)] border-transparent",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
