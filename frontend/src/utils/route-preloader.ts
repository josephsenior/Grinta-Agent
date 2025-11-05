// Route preloading utilities for performance optimization

// Export React import for the component
import React, { useState, useEffect } from "react";

export interface PreloadConfig {
  route: string;
  priority: "high" | "medium" | "low";
  condition?: () => boolean;
  delay?: number;
}

// Configuration for route preloading
const ROUTE_PRELOAD_CONFIG: PreloadConfig[] = [
  {
    route: "/conversation",
    priority: "high",
    condition: () =>
      // Preload conversation route if user is likely to start a conversation
      window.location.pathname === "/" ||
      window.location.pathname.startsWith("/conversation"),
    delay: 2000, // Wait 2 seconds after page load
  },
  {
    route: "/settings",
    priority: "medium",
    condition: () =>
      // Preload settings if user has been on the page for a while
      true,
    delay: 5000, // Wait 5 seconds after page load
  },
  {
    route: "/about",
    priority: "low",
    condition: () =>
      // Preload about if user seems to be exploring
      true,
    delay: 10000, // Wait 10 seconds after page load
  },
  {
    route: "/contact",
    priority: "low",
    condition: () =>
      // Preload contact if user seems to be exploring
      true,
    delay: 12000, // Wait 12 seconds after page load
  },
];

// Function to get route hash (simplified)
function getRouteHash(route: string): string {
  // Create a small stable hash from the route string without using bitwise ops
  let h = 0;
  for (let i = 0; i < route.length; i += 1) {
    h = (h * 31 + route.charCodeAt(i)) % 1000000000;
  }

  return Math.abs(h).toString(36);
}

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

// Function to preload route modules
export function preloadRouteModule(route: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined") {
      resolve();
      return;
    }

    // Try to preload the route module
    const modulePath = `/assets/${route}-${getRouteHash(route)}.js`;

    const link = document.createElement("link");
    link.rel = "modulepreload";
    link.href = modulePath;

    link.onload = () => resolve();
    link.onerror = () =>
      reject(new Error(`Failed to preload route module: ${route}`));

    document.head.appendChild(link);
  });
}

// Function to preload critical resources for a route
export function preloadRouteResources(route: string): void {
  const resourceMap: Record<
    string,
    Array<{ href: string; as: string; type?: string }>
  > = {
    "/conversation": [
      { href: "/assets/chat-interface.js", as: "script" },
      { href: "/assets/terminal-vendor.js", as: "script" },
      { href: "/assets/editor-vendor.js", as: "script" },
    ],
    "/settings": [{ href: "/assets/settings.js", as: "script" }],
    "/about": [{ href: "/assets/about.js", as: "script" }],
    "/contact": [{ href: "/assets/contact.js", as: "script" }],
  };

  const resources = resourceMap[route] || [];

  resources.forEach(({ href, as, type }) => {
    const link = document.createElement("link");
    link.rel = "preload";
    link.href = href;
    link.as = as;
    if (type) link.type = type;

    document.head.appendChild(link);
  });
}

// Schedule preloads for a set of configs. Returns timeout ids for cleanup.
function schedulePreloads(
  configs: PreloadConfig[],
  preloadedRoutes: Set<string>,
  markPreloaded: (route: string) => void,
): number[] {
  const timeouts: number[] = [];

  for (const cfg of configs) {
    const { route, priority, condition, delay } = cfg;

    const shouldSkip =
      preloadedRoutes.has(route) ||
      (typeof condition === "function" && !condition());

    if (!shouldSkip) {
      const timeoutId = window.setTimeout(() => {
        preloadRoute(route, priority);
        markPreloaded(route);
      }, delay || 0);

      timeouts.push(timeoutId);
    }
  }

  return timeouts;
}

// (Duplicate helper implementations removed - kept the hoisted versions above)

// Component for intelligent route preloading
export function RoutePreloader(): React.ReactElement {
  const [preloadedRoutes, setPreloadedRoutes] = useState<Set<string>>(
    new Set(),
  );

  useEffect(() => {
    const timeouts = schedulePreloads(
      ROUTE_PRELOAD_CONFIG,
      preloadedRoutes,
      (route: string) => {
        setPreloadedRoutes((prev) => new Set(prev).add(route));
      },
    );

    return () => {
      timeouts.forEach((id: number) => clearTimeout(id));
    };
  }, [preloadedRoutes]);

  // Return empty fragment - preloading happens via useEffect
  // PrefetchPageLinks only works in React Router framework mode
  return React.createElement(React.Fragment, null);
}

// (Duplicate helper implementations removed - kept the hoisted versions above)

// Hook for intelligent preloading based on user behavior
export function useIntelligentPreloading() {
  const [userBehavior, setUserBehavior] = useState({
    timeOnPage: 0,
    scrollDepth: 0,
    interactions: 0,
  });

  useEffect(() => {
    const startTime = Date.now();
    let scrollDepth = 0;
    let interactions = 0;

    // Track time on page
    const timeInterval = setInterval(() => {
      setUserBehavior((prev) => ({
        ...prev,
        timeOnPage: Date.now() - startTime,
      }));
    }, 1000);

    // Track scroll depth
    const handleScroll = () => {
      const scrollTop =
        window.pageYOffset || document.documentElement.scrollTop;
      const scrollHeight =
        document.documentElement.scrollHeight - window.innerHeight;
      const newScrollDepth = Math.round((scrollTop / scrollHeight) * 100);

      if (newScrollDepth > scrollDepth) {
        scrollDepth = newScrollDepth;
        setUserBehavior((prev) => ({
          ...prev,
          scrollDepth: newScrollDepth,
        }));
      }
    };

    // Track interactions
    const handleInteraction = () => {
      interactions += 1;
      setUserBehavior((prev) => ({ ...prev, interactions }));
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("click", handleInteraction);
    window.addEventListener("keydown", handleInteraction);

    return () => {
      clearInterval(timeInterval);
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("click", handleInteraction);
      window.removeEventListener("keydown", handleInteraction);
    };
  }, []);

  // Preload routes based on user behavior
  useEffect(() => {
    const { timeOnPage, scrollDepth, interactions } = userBehavior;

    // Preload conversation route if user is engaged
    if (timeOnPage > 3000 && (scrollDepth > 20 || interactions > 2)) {
      preloadRoute("/conversation", "high");
    }

    // Preload settings if user has been exploring
    if (timeOnPage > 10000 && interactions > 5) {
      preloadRoute("/settings", "medium");
    }

    // Preload about if user seems to be exploring
    if (timeOnPage > 15000 && scrollDepth > 50 && interactions > 3) {
      preloadRoute("/about", "low");
    }

    // Preload contact if user seems lost
    if (timeOnPage > 20000 && scrollDepth > 70 && interactions < 3) {
      preloadRoute("/contact", "low");
    }
  }, [userBehavior]);

  return userBehavior;
}

// Function to preload on hover
export function useHoverPreloading() {
  const handleMouseEnter = (route: string) => {
    // Preload route when user hovers over navigation
    preloadRoute(route, "high");
  };

  return { handleMouseEnter };
}

// Function to preload on focus
export function useFocusPreloading() {
  const handleFocus = (route: string) => {
    // Preload route when user focuses on navigation
    preloadRoute(route, "high");
  };

  return { handleFocus };
}
