// Performance monitoring utilities
export class PerformanceMonitor {
  private static instance: PerformanceMonitor;

  private metrics: Record<string, number> = {};

  static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor();
    }
    return PerformanceMonitor.instance;
  }

  // Measure Core Web Vitals
  measureCoreWebVitals() {
    // First Contentful Paint
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.name === "first-contentful-paint") {
          this.metrics.fcp = entry.startTime;
          // Performance metric captured: FCP
        }
      }
    }).observe({ entryTypes: ["paint"] });

    // Largest Contentful Paint
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1];
      this.metrics.lcp = lastEntry.startTime;
      // Performance metric captured: LCP
    }).observe({ entryTypes: ["largest-contentful-paint"] });

    // Cumulative Layout Shift
    new PerformanceObserver((list) => {
      let clsValue = 0;
      for (const entry of list.getEntries()) {
        // LayoutShiftEntry has hadRecentInput and value fields
        const maybeLayoutShift = entry as PerformanceEntry & {
          hadRecentInput?: boolean;
          value?: number;
        };
        if (!maybeLayoutShift.hadRecentInput) {
          clsValue += maybeLayoutShift.value ?? 0;
        }
      }
      this.metrics.cls = clsValue;
      // Performance metric captured: CLS
    }).observe({ entryTypes: ["layout-shift"] });

    // First Input Delay
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const maybeFirstInput = entry as PerformanceEntry & {
          processingStart?: number;
        };
        if (typeof maybeFirstInput.processingStart === "number") {
          this.metrics.fid = maybeFirstInput.processingStart - entry.startTime;
          // Performance metric captured: FID
        }
      }
    }).observe({ entryTypes: ["first-input"] });

    // Time to Interactive
    this.measureTimeToInteractive();
  }

  private measureTimeToInteractive() {
    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      for (const entry of entries) {
        if (entry.entryType === "navigation") {
          const nav = entry as PerformanceNavigationTiming;
          if (
            typeof nav.loadEventEnd === "number" &&
            typeof nav.fetchStart === "number"
          ) {
            this.metrics.tti = nav.loadEventEnd - nav.fetchStart;
            // Performance metric captured: TTI
          }
        }
      }
    });
    observer.observe({ entryTypes: ["navigation"] });
  }

  // Measure bundle load times
  measureBundlePerformance() {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === "resource") {
          const resource = entry as PerformanceResourceTiming;
          if (resource.name.includes(".js") || resource.name.includes(".css")) {
            // Bundle performance tracked
            this.metrics[`bundle-${resource.name.split("/").pop()}`] =
              resource.duration;
          }
        }
      }
    });
    observer.observe({ entryTypes: ["resource"] });
  }

  // Get performance report
  getReport(): Record<string, number> {
    return { ...this.metrics };
  }

  // Initialize monitoring
  init() {
    if (typeof window !== "undefined") {
      this.measureCoreWebVitals();
      this.measureBundlePerformance();
    }
  }
}

// Initialize performance monitoring
export const performanceMonitor = PerformanceMonitor.getInstance();
