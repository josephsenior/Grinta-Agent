import * as React from "react";

import { cn } from "#/utils/utils";

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-12 w-full rounded-lg border px-4 py-3 text-sm transition-all duration-200",
        "bg-[var(--bg-input)] border-[var(--border-primary)]",
        "text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]",
        "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-[var(--text-primary)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(139,92,246,0.2)] focus-visible:border-[var(--border-accent)]",
        "hover:border-[var(--border-accent)]",
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
