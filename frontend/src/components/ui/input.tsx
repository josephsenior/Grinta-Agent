import * as React from "react";

import { cn } from "#/utils/utils";

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-lg border border-brand-500/25 bg-black/70 backdrop-blur-sm px-4 py-2 text-[15px] transition-all duration-200 ring-offset-black",
        "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-text-muted",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 focus-visible:ring-offset-2 focus-visible:border-brand-500/40 focus-visible:bg-black/80",
        "focus-visible:shadow-lg focus-visible:shadow-brand-500/10 hover:border-brand-500/35 hover:bg-black/75",
        "disabled:cursor-not-allowed disabled:opacity-50 md:text-[15px]",
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export { Input };
