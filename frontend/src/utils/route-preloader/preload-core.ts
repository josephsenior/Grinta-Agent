// Core preload function extracted to break circular dependency

// Function to preload a specific route
export function preloadRoute(
  route: string,
  priority: "high" | "medium" | "low" = "medium",
): void {
  if (typeof window === "undefined") return;

  // Create a link element for preloading
  const link = document.createElement("link");
  link.rel = "prefetch";
  link.href = route;

  // Add priority hints
  if (priority === "high") {
    link.setAttribute("fetchpriority", "high");
  } else if (priority === "low") {
    link.setAttribute("fetchpriority", "low");
  }

  document.head.appendChild(link);
}
