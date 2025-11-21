import React from "react";
import { cn } from "#/utils/utils";

/**
 * Skip link component for keyboard navigation accessibility
 * Allows users to skip navigation and go directly to main content
 * WCAG 2.1 AA compliant - visible when focused
 */
export function SkipLink() {
  return (
    <a
      href="#main-content"
      className={cn(
        // Screen reader only by default, visible on focus
        "sr-only focus:static focus:block focus:fixed focus:top-4 focus:left-4 focus:z-[100]",
        "px-4 py-2 rounded-lg",
        "bg-white text-black",
        "font-semibold text-sm",
        "focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-black",
        "transition-all duration-200",
      )}
      onClick={(e) => {
        e.preventDefault();
        const mainContent = document.getElementById("main-content");
        if (mainContent) {
          mainContent.focus();
          mainContent.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }}
    >
      Skip to main content
    </a>
  );
}
