import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "#/utils/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(139,92,246,0.2)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-primary)] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 active:scale-95",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--text-accent)] text-white rounded-lg px-6 py-3 hover:bg-[var(--text-accent)]/90 hover:shadow-lg hover:shadow-[var(--text-accent)]/20 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]",
        destructive:
          "bg-[var(--text-danger)] text-white hover:brightness-110 hover:shadow-lg hover:shadow-[var(--text-danger)]/20",
        outline:
          "border border-[var(--border-primary)] bg-transparent text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] hover:border-[var(--border-accent)]",
        secondary:
          "border border-[var(--border-primary)] bg-[var(--bg-elevated)] text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] hover:border-[var(--border-accent)]",
        ghost:
          "bg-transparent text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]",
        link: "text-[var(--text-accent)] underline-offset-4 hover:underline hover:text-[var(--border-accent)]",
      },
      size: {
        default: "h-auto px-6 py-3",
        sm: "h-9 rounded-md px-3 text-xs",
        lg: "h-11 rounded-lg px-8 text-base",
        icon: "h-10 w-10 rounded-full bg-[var(--bg-elevated)] hover:bg-[var(--bg-tertiary)]",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";

    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
