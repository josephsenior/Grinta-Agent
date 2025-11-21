import * as React from "react";

import { cn } from "#/utils/utils";

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<"textarea">
>(({ className, ...props }, ref) => (
  <textarea
    className={cn(
      "flex min-h-[100px] w-full rounded-[8px] border border-[#1a1a1a] bg-[#000000] px-4 py-3 text-sm resize-y ring-offset-black placeholder:text-text-muted transition-all duration-200",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(139,92,246,0.2)] focus-visible:ring-offset-2 focus-visible:border-[#8b5cf6]",
      "hover:border-[#1a1a1a]",
      "disabled:cursor-not-allowed disabled:opacity-50",
      className,
    )}
    ref={ref}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export { Textarea };
