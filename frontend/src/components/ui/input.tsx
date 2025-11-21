import * as React from "react";

import { cn } from "#/utils/utils";

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-auto w-full rounded-[8px] border border-[#1a1a1a] bg-[#000000] px-4 py-3 text-sm transition-all duration-200 ring-offset-black",
        "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-text-muted",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(139,92,246,0.2)] focus-visible:ring-offset-2 focus-visible:border-[#8b5cf6]",
        "hover:border-[#1a1a1a]",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export { Input };
