import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "#/utils/utils";

const cardVariants = cva("block text-foreground transition-colors", {
  variants: {
    variant: {
      standard: "border rounded-[12px] shadow-luxury",
      elevated: "border rounded-[12px] shadow-luxury-lg",
      glass: "backdrop-blur-[12px] border rounded-[12px]",
    },
  },
  defaultVariants: {
    variant: "standard",
  },
});

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, ...props }, ref) => {
    const getCardStyle = () => {
      switch (variant) {
        case "elevated":
          return {
            backgroundColor: "var(--bg-primary)",
            borderColor: "var(--border-accent)",
          };
        case "glass":
          return {
            backgroundColor: "var(--glass-bg)",
            borderColor: "var(--glass-border)",
          };
        default:
          return {
            backgroundColor: "var(--bg-primary)",
            borderColor: "var(--border-primary)",
          };
      }
    };

    return (
      <div
        ref={ref}
        className={cn(cardVariants({ variant, className }))}
        style={getCardStyle()}
        {...props}
      />
    );
  },
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "text-2xl font-semibold leading-none tracking-tight",
      className,
    )}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
));
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
};
