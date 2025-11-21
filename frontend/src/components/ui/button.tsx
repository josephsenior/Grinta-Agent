import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "#/utils/utils";
import tokens from "#/styles/designTokens";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-black disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-gradient-to-r from-brand-500 to-brand-600 text-white rounded-[8px] px-6 py-3 hover:brightness-110 active:brightness-95",
        destructive:
          "bg-danger-500 text-white shadow-md shadow-danger-500/20 hover:shadow-lg hover:shadow-danger-500/30 hover:bg-danger-600",
        outline:
          "border border-border-primary bg-transparent text-white hover:bg-brand-500/10",
        secondary:
          "border border-border-primary bg-transparent text-white hover:bg-brand-500/10",
        ghost: "bg-transparent text-foreground-secondary hover:bg-white/5",
        link: "text-brand-500 underline-offset-4 hover:underline hover:text-brand-400",
      },
      size: {
        default: "h-auto px-6 py-3",
        sm: "h-9 rounded-md px-3 text-xs",
        lg: "h-11 rounded-lg px-8 text-base",
        icon: "h-10 w-10 rounded-full bg-black/60 hover:bg-brand-500/10",
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
    const style: React.CSSProperties | undefined =
      variant === "default"
        ? { background: tokens.gradients.luxury }
        : undefined;

    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        style={style}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
