import { useState, useEffect } from "react";

interface MousePosition {
  x: number;
  y: number;
}

/**
 * Track mouse position for magnetic hover effects and particle interactions
 * Optimized with throttling for performance
 */
export function useMousePosition(throttleMs: number = 16): MousePosition {
  const [mousePosition, setMousePosition] = useState<MousePosition>({ x: 0, y: 0 });

  useEffect(() => {
    let lastUpdate = 0;
    let rafId: number | null = null;

    const updateMousePosition = (e: MouseEvent) => {
      const now = Date.now();
      
      // Throttle updates to avoid performance issues
      if (now - lastUpdate < throttleMs) {
        return;
      }

      // Use requestAnimationFrame for smooth updates
      if (rafId) {
        cancelAnimationFrame(rafId);
      }

      rafId = requestAnimationFrame(() => {
        setMousePosition({ x: e.clientX, y: e.clientY });
        lastUpdate = now;
      });
    };

    window.addEventListener("mousemove", updateMousePosition);

    return () => {
      window.removeEventListener("mousemove", updateMousePosition);
      if (rafId) {
        cancelAnimationFrame(rafId);
      }
    };
  }, [throttleMs]);

  return mousePosition;
}

/**
 * Calculate magnetic offset for element that follows cursor
 * Returns transform values for smooth magnetic effect
 */
export function useMagneticHover(
  elementRef: React.RefObject<HTMLElement | null>,
  strength: number = 0.3
) {
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = element.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      const deltaX = (e.clientX - centerX) * strength;
      const deltaY = (e.clientY - centerY) * strength;

      setOffset({ x: deltaX, y: deltaY });
    };

    const handleMouseEnter = () => setIsHovered(true);
    const handleMouseLeave = () => {
      setIsHovered(false);
      setOffset({ x: 0, y: 0 });
    };

    element.addEventListener("mouseenter", handleMouseEnter);
    element.addEventListener("mouseleave", handleMouseLeave);
    element.addEventListener("mousemove", handleMouseMove);

    return () => {
      element.removeEventListener("mouseenter", handleMouseEnter);
      element.removeEventListener("mouseleave", handleMouseLeave);
      element.removeEventListener("mousemove", handleMouseMove);
    };
  }, [elementRef, strength]);

  return { offset, isHovered };
}

