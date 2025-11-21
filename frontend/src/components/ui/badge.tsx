import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "#/utils/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "bg-[rgba(239,68,68,0.12)] text-[#EF4444] border-transparent",
        outline: "text-foreground",
        success: "bg-[rgba(16,185,129,0.12)] text-[#10B981] border-transparent",
        warning: "bg-[rgba(245,158,11,0.12)] text-[#F59E0B] border-transparent",
        info: "bg-[rgba(59,130,246,0.12)] text-[#3B82F6] border-transparent",
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
