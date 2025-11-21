import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  handleReducedMotion,
  calculateInitialPosition,
  setInitialState,
} from "./use-gsap-scroll-reveal/utils/animation-helpers";
import {
  createScrollTriggerConfig,
  cleanupScrollTrigger,
} from "./use-gsap-scroll-reveal/utils/scroll-trigger-helpers";

// Register ScrollTrigger plugin
if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

interface ScrollRevealOptions {
  from?: "top" | "bottom" | "left" | "right";
  distance?: number;
  duration?: number;
  delay?: number;
  stagger?: number;
  ease?: string;
  trigger?: string | Element;
  start?: string;
  end?: string;
  toggleActions?: string;
  once?: boolean;
}

/**
 * Professional scroll-triggered reveal animation hook using GSAP
 *
 * @example
 * const ref = useGSAPScrollReveal({ from: 'bottom', distance: 50, stagger: 0.1 });
 * return <div ref={ref}>Content</div>;
 */
export function useGSAPScrollReveal<T extends HTMLElement = HTMLDivElement>(
  options: ScrollRevealOptions = {},
) {
  const ref = useRef<T>(null);
  const {
    from = "bottom",
    distance = 50,
    duration = 1,
    delay = 0,
    stagger = 0,
    ease = "power3.out",
    trigger,
    start = "top 80%",
    end = "bottom 20%",
    toggleActions = "play none none reverse",
    once = true,
  } = options;

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof window === "undefined") return undefined;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    if (prefersReducedMotion) {
      handleReducedMotion(element);
      return undefined;
    }

    const target = element.children.length > 0 ? element.children : element;
    const hasChildren = element.children.length > 0;
    const { initialY, initialX } = calculateInitialPosition(from, distance);

    setInitialState(target, initialY, initialX);

    const scrollTriggerConfig = createScrollTriggerConfig(
      trigger || element,
      start,
      end,
      once,
      toggleActions,
      duration,
      delay,
    );

    const animation = gsap.to(target, {
      opacity: 1,
      y: 0,
      x: 0,
      duration,
      delay,
      stagger: hasChildren ? stagger : 0,
      ease,
      scrollTrigger: scrollTriggerConfig,
    });

    return () => {
      animation.kill();
      cleanupScrollTrigger(trigger || element);
    };
  }, [
    from,
    distance,
    duration,
    delay,
    stagger,
    ease,
    trigger,
    start,
    end,
    toggleActions,
    once,
  ]);

  return ref;
}

/**
 * Hook for scroll-based parallax effects
 */
export function useGSAPParallax<T extends HTMLElement = HTMLDivElement>(
  speed: number = 0.5,
  options: { start?: string; end?: string } = {},
) {
  const ref = useRef<T>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof window === "undefined") return undefined;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) return undefined;

    const animation = gsap.to(element, {
      y: -50 * speed,
      ease: "none",
      scrollTrigger: {
        trigger: element,
        start: options.start || "top bottom",
        end: options.end || "bottom top",
        scrub: true,
      },
    });

    return () => {
      animation.kill();
      cleanupScrollTrigger(element);
    };
  }, [speed, options.start, options.end]);

  return ref;
}
