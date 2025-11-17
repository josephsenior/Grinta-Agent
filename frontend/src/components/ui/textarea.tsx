import * as React from "react";

import { cn } from "#/utils/utils";

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<"textarea">
>(({ className, ...props }, ref) => (
  <textarea
    className={cn(
      "flex min-h-[100px] w-full rounded-lg border border-brand-500/25 bg-black/70 backdrop-blur-sm px-4 py-3 text-[15px] ring-offset-black placeholder:text-text-muted",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 focus-visible:ring-offset-2 focus-visible:border-brand-500/40 focus-visible:bg-black/80",
      "hover:border-brand-500/35 hover:bg-black/75 disabled:cursor-not-allowed disabled:opacity-50 md:text-[15px]",
      className,
    )}
    ref={ref}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export { Textarea };
