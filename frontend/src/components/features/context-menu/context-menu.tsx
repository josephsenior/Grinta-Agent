import React from "react";
import { cn } from "#/utils/utils";

interface ContextMenuProps {
  ref?: React.RefObject<HTMLUListElement | null>;
  testId?: string;
  children: React.ReactNode;
  className?: React.HTMLAttributes<HTMLUListElement>["className"];
}

export function ContextMenu({
  testId,
  children,
  className,
  ref,
}: ContextMenuProps) {
  return (
    <div
      data-testid={testId}
      ref={ref as unknown as React.RefObject<HTMLDivElement>}
      // z-50 ensures the menu stacks above clickable parent elements (like NavLink)
      className={cn(
        "bg-background-secondary backdrop-blur-xl border border-border rounded-2xl overflow-hidden z-50 shadow-2xl",
        className,
      )}
      role="menu"
      tabIndex={-1}
      onClick={(e) => {
        // Safety: prevent any clicks on the menu container from bubbling up
        e.stopPropagation();
      }}
    >
      {children}
    </div>
  );
}
