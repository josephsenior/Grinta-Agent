/**
 * Animation utility functions for modern landing page effects
 */

/**
 * Easing functions for smooth animations
 */
export const easings = {
  // Smooth easing (bolt.new style)
  smooth: "cubic-bezier(0.4, 0.0, 0.2, 1)",
  
  // Elastic bounce
  bounce: "cubic-bezier(0.68, -0.55, 0.265, 1.55)",
  
  // Sharp entrance
  sharpIn: "cubic-bezier(0.4, 0.0, 1, 1)",
  
  // Smooth exit
  smoothOut: "cubic-bezier(0.0, 0.0, 0.2, 1)",
  
  // Organic movement
  organic: "cubic-bezier(0.45, 0.05, 0.55, 0.95)",
};

/**
 * Generate staggered delay for sequential animations
 */
export function getStaggerDelay(index: number, baseDelay: number = 50): number {
  return index * baseDelay;
}

/**
 * Calculate magnetic pull towards cursor
 */
export function calculateMagneticOffset(
  elementRect: DOMRect,
  mouseX: number,
  mouseY: number,
  strength: number = 0.3
): { x: number; y: number } {
  const centerX = elementRect.left + elementRect.width / 2;
  const centerY = elementRect.top + elementRect.height / 2;

  const deltaX = (mouseX - centerX) * strength;
  const deltaY = (mouseY - centerY) * strength;

  return { x: deltaX, y: deltaY };
}

/**
 * Generate random value within range
 */
export function randomInRange(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}

/**
 * Interpolate between two values
 */
export function lerp(start: number, end: number, t: number): number {
  return start + (end - start) * t;
}

/**
 * Clamp value between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Check if reduced motion is preferred
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Animated counter for stat numbers
 */
export function animateValue(
  start: number,
  end: number,
  duration: number,
  callback: (value: number) => void
) {
  const startTime = Date.now();
  
  const animate = () => {
    const now = Date.now();
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // Ease out cubic
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    const current = start + (end - start) * easeProgress;
    
    callback(Math.round(current));
    
    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  };
  
  requestAnimationFrame(animate);
}

/**
 * Generate mesh gradient colors
 */
export function generateMeshGradient(baseHue: number = 270) {
  // Violet base (270deg hue)
  const colors = [
    `hsl(${baseHue}, 70%, 60%)`,
    `hsl(${baseHue + 30}, 65%, 55%)`,
    `hsl(${baseHue - 30}, 75%, 65%)`,
    `hsl(${baseHue + 60}, 60%, 50%)`,
  ];
  
  return colors;
}

/**
 * Debounce function for performance
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number,
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => {
      // call but ignore returned value
      void func(...args);
    }, wait);
  };
}

/**
 * Throttle function for scroll/mouse events
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  func: T,
  limit: number,
): (...args: Parameters<T>) => void {
  let inThrottle = false;

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      // call but ignore returned value
      void func(...args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}

