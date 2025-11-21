import * as React from "react";

import { cn } from "#/utils/utils";

const Select = React.forwardRef<
  HTMLSelectElement,
  React.ComponentProps<"select">
>(({ className, children, ...props }, ref) => (
  <div className="relative">
    <select
      ref={ref}
      className={cn(
        "flex h-auto w-full appearance-none rounded-[8px] border border-[#1a1a1a] bg-[#000000] px-4 py-3 pr-10 text-sm transition-all duration-200 ring-offset-black",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(139,92,246,0.2)] focus-visible:ring-offset-2 focus-visible:border-[#8b5cf6]",
        "hover:border-[#1a1a1a]",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "text-foreground",
        className,
      )}
      {...props}
    >
      {children}
    </select>
    {/* Violet dropdown arrow */}
    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
      <svg
        className="h-4 w-4 text-[#8b5cf6]"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M19 9l-7 7-7-7"
        />
      </svg>
    </div>
  </div>
));
Select.displayName = "Select";

export { Select };
