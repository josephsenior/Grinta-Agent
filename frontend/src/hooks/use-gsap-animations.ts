/**
 * Comprehensive GSAP animation hooks for the main application.
 *
 * Provides reusable, performant animations with accessibility support.
 */

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

// Register plugins if needed
if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

/**
 * Check if user prefers reduced motion
 */
function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Common animation options
 */
interface BaseAnimationOptions {
  duration?: number;
  delay?: number;
  ease?: string;
  onComplete?: () => void;
  onStart?: () => void;
}

/**
 * Fade in animation hook
 */
export function useGSAPFadeIn<T extends HTMLElement = HTMLDivElement>(
  options: BaseAnimationOptions & {
    from?: number;
    to?: number;
    autoPlay?: boolean;
  } = {},
) {
  const ref = useRef<T>(null);
  const {
    duration = 0.6,
    delay = 0,
    ease = "power2.out",
    from = 0,
    to = 1,
    autoPlay = true,
    onComplete,
    onStart,
  } = options;

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof window === "undefined") return undefined;

    if (prefersReducedMotion()) {
      gsap.set(element, { opacity: to });
      return undefined;
    }

    gsap.set(element, { opacity: from });

    if (autoPlay) {
      const animation = gsap.to(element, {
        opacity: to,
        duration,
        delay,
        ease,
        onComplete,
        onStart,
      });

      return () => {
        animation.kill();
      };
    }
    return undefined;
  }, [duration, delay, ease, from, to, autoPlay, onComplete, onStart]);

  return ref;
}

/**
 * Slide in animation hook
 */
export function useGSAPSlideIn<T extends HTMLElement = HTMLDivElement>(
  options: BaseAnimationOptions & {
    direction?: "up" | "down" | "left" | "right";
    distance?: number;
    autoPlay?: boolean;
  } = {},
) {
  const ref = useRef<T>(null);
  const {
    duration = 0.6,
    delay = 0,
    ease = "power3.out",
    direction = "up",
    distance = 30,
    autoPlay = true,
    onComplete,
    onStart,
  } = options;

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof window === "undefined") return undefined;

    if (prefersReducedMotion()) {
      gsap.set(element, { opacity: 1, x: 0, y: 0 });
      return undefined;
    }

    const initialX = (() => {
      if (direction === "left") return -distance;
      if (direction === "right") return distance;
      return 0;
    })();
    const initialY = (() => {
      if (direction === "up") return distance;
      if (direction === "down") return -distance;
      return 0;
    })();

    gsap.set(element, {
      opacity: 0,
      x: initialX,
      y: initialY,
    });

    if (autoPlay) {
      const animation = gsap.to(element, {
        opacity: 1,
        x: 0,
        y: 0,
        duration,
        delay,
        ease,
        onComplete,
        onStart,
      });

      return () => {
        animation.kill();
      };
    }
    return undefined;
  }, [
    duration,
    delay,
    ease,
    direction,
    distance,
    autoPlay,
    onComplete,
    onStart,
  ]);

  return ref;
}

/**
 * Scale animation hook
 */
export function useGSAPScale<T extends HTMLElement = HTMLDivElement>(
  options: BaseAnimationOptions & {
    from?: number;
    to?: number;
    autoPlay?: boolean;
  } = {},
) {
  const ref = useRef<T>(null);
  const {
    duration = 0.5,
    delay = 0,
    ease = "back.out(1.2)",
    from = 0.8,
    to = 1,
    autoPlay = true,
    onComplete,
    onStart,
  } = options;

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof window === "undefined") return undefined;

    if (prefersReducedMotion()) {
      gsap.set(element, { opacity: 1, scale: to });
      return undefined;
    }

    gsap.set(element, {
      opacity: 0,
      scale: from,
    });

    if (autoPlay) {
      const animation = gsap.to(element, {
        opacity: 1,
        scale: to,
        duration,
        delay,
        ease,
        onComplete,
        onStart,
      });

      return () => {
        animation.kill();
      };
    }
    return undefined;
  }, [duration, delay, ease, from, to, autoPlay, onComplete, onStart]);

  return ref;
}

/**
 * Stagger animation hook for lists
 */
export function useGSAPStagger<T extends HTMLElement = HTMLDivElement>(
  options: BaseAnimationOptions & {
    stagger?: number;
    from?: "top" | "bottom" | "left" | "right";
    distance?: number;
    autoPlay?: boolean;
  } = {},
) {
  const ref = useRef<T>(null);
  const {
    duration = 0.5,
    delay = 0,
    ease = "power2.out",
    stagger = 0.1,
    from = "bottom",
    distance = 20,
    autoPlay = true,
    onComplete,
    onStart,
  } = options;

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof window === "undefined") return undefined;

    if (prefersReducedMotion()) {
      gsap.set(element.children, { opacity: 1, x: 0, y: 0 });
      return undefined;
    }

    const children = Array.from(element.children) as HTMLElement[];
    if (children.length === 0) {
      return undefined;
    }

    const initialY = (() => {
      if (from === "bottom") return distance;
      if (from === "top") return -distance;
      return 0;
    })();
    const initialX = (() => {
      if (from === "right") return distance;
      if (from === "left") return -distance;
      return 0;
    })();

    gsap.set(children, {
      opacity: 0,
      x: initialX,
      y: initialY,
    });

    if (autoPlay) {
      const animation = gsap.to(children, {
        opacity: 1,
        x: 0,
        y: 0,
        duration,
        delay,
        stagger,
        ease,
        onComplete,
        onStart,
      });

      return () => {
        animation.kill();
      };
    }
    return undefined;
  }, [
    duration,
    delay,
    ease,
    stagger,
    from,
    distance,
    autoPlay,
    onComplete,
    onStart,
  ]);

  return ref;
}

/**
 * Enhanced hover animation hook
 */
export function useGSAPHover<T extends HTMLElement = HTMLDivElement>(
  options: {
    scale?: number;
    y?: number;
    duration?: number;
    ease?: string;
  } = {},
) {
  const ref = useRef<T>(null);
  const { scale = 1.02, y = -4, duration = 0.3, ease = "power2.out" } = options;

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof window === "undefined") return undefined;

    if (prefersReducedMotion()) return undefined;

    const handleMouseEnter = () => {
      gsap.to(element, {
        scale,
        y,
        duration,
        ease,
      });
    };

    const handleMouseLeave = () => {
      gsap.to(element, {
        scale: 1,
        y: 0,
        duration,
        ease,
      });
    };

    element.addEventListener("mouseenter", handleMouseEnter);
    element.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      element.removeEventListener("mouseenter", handleMouseEnter);
      element.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, [scale, y, duration, ease]);

  return ref;
}

/**
 * Pulse animation hook
 */
export function useGSAPPulse<T extends HTMLElement = HTMLDivElement>(
  options: {
    scale?: number;
    duration?: number;
    repeat?: number;
    autoPlay?: boolean;
  } = {},
) {
  const ref = useRef<T>(null);
  const { scale = 1.1, duration = 1, repeat = -1, autoPlay = true } = options;

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof window === "undefined") {
      return undefined;
    }

    if (prefersReducedMotion() || !autoPlay) {
      return undefined;
    }

    const animation = gsap.to(element, {
      scale,
      duration,
      repeat,
      yoyo: true,
      ease: "power1.inOut",
    });

    return () => {
      animation.kill();
    };
  }, [scale, duration, repeat, autoPlay]);

  return ref;
}

/**
 * Timeline-based animation hook for complex sequences
 */
export function useGSAPTimeline<T extends HTMLElement = HTMLDivElement>(
  setup: (tl: gsap.core.Timeline, element: T) => void,
  dependencies: unknown[] = [],
) {
  const ref = useRef<T>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof window === "undefined") {
      return undefined;
    }

    if (prefersReducedMotion()) {
      gsap.set(element, { opacity: 1 });
      return undefined;
    }

    const tl = gsap.timeline();
    setup(tl, element);

    return () => {
      tl.kill();
    };
  }, dependencies);

  return ref;
}

/**
 * Scroll-triggered animation hook (simplified version)
 */
export function useGSAPScrollTrigger<T extends HTMLElement = HTMLDivElement>(
  options: BaseAnimationOptions & {
    trigger?: string | Element;
    start?: string;
    end?: string;
    toggleActions?: string;
    once?: boolean;
    animation: (element: T) => gsap.core.Tween;
  } = {} as {
    start?: string;
    end?: string;
    toggleActions?: string;
    once?: boolean;
    animation: (element: T) => gsap.core.Tween;
  },
) {
  const ref = useRef<T>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof window === "undefined") {
      return undefined;
    }

    if (prefersReducedMotion()) {
      gsap.set(element, { opacity: 1 });
      return undefined;
    }

    try {
      const {
        trigger,
        start = "top 80%",
        end = "bottom 20%",
        toggleActions = "play none none none",
        once = true,
        animation,
        onComplete,
      } = options;

      // Create the tween first (paused so we can control it with ScrollTrigger)
      const tween = animation(element);
      tween.pause();

      // Create ScrollTrigger with callbacks to control the animation
      const scrollTrigger = ScrollTrigger.create({
        trigger: trigger || element,
        start,
        end,
        toggleActions: once ? "play none none none" : toggleActions,
        onEnter: () => {
          tween.play();
          onComplete?.();
        },
        onLeave: () => {
          if (!once) tween.reverse();
        },
        onEnterBack: () => {
          if (!once) tween.play();
        },
        onLeaveBack: () => {
          if (!once) tween.reverse();
        },
      });

      return () => {
        tween.kill();
        scrollTrigger.kill();
      };
    } catch {
      // ScrollTrigger not available, just run animation
      const tween = options.animation(element);
      return () => {
        tween.kill();
      };
    }
  }, [options]);

  return ref;
}
