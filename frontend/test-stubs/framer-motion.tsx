import React from "react";

// Minimal framer-motion stub for Vitest that avoids accessing `window` at import time.
// motion.<el> returns a simple functional component that renders the corresponding
// HTML element as a plain div (props are forwarded). AnimatePresence and LazyMotion
// are no-op wrappers that render children directly.
export const motion: Record<string, unknown> = new Proxy(
  {},
  {
    get: () => (props: React.ComponentPropsWithoutRef<"div">) =>
      React.createElement("div", props),
  },
);

export function AnimatePresence({ children }: { children?: React.ReactNode }) {
  return React.createElement(React.Fragment, null, children);
}

export function LazyMotion({ children }: { children?: React.ReactNode }) {
  return React.createElement(React.Fragment, null, children);
}

export default { motion, AnimatePresence, LazyMotion };
