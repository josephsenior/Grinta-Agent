import { useEffect, RefObject } from "react";
import { gsap } from "gsap";

interface HeroAnimationRefs {
  heroRef: RefObject<HTMLElement | null>;
  contentRef: RefObject<HTMLDivElement | null>;
  titleRef: RefObject<HTMLHeadingElement | null>;
  subtitleRef: RefObject<HTMLParagraphElement | null>;
  ctaRef: RefObject<HTMLDivElement | null>;
  codeRef: RefObject<HTMLDivElement | null>;
}

function animateBadge(
  timeline: gsap.core.Timeline,
  contentRef: RefObject<HTMLDivElement | null>,
) {
  const badge = contentRef.current?.querySelector(".badge");
  if (badge) {
    timeline.from(badge, {
      opacity: 0,
      scale: 0.8,
      duration: 0.5,
    });
  }
}

function animateTitle(
  timeline: gsap.core.Timeline,
  titleRef: RefObject<HTMLHeadingElement | null>,
): void {
  if (!titleRef.current) {
    return;
  }

  const words = titleRef.current.textContent?.split(" ") || [];
  const titleElement = titleRef.current;
  titleElement.innerHTML = words
    .map((word) => `<span class="inline-block">${word}</span>`)
    .join(" ");

  timeline.from(
    titleRef.current.children,
    {
      opacity: 0,
      y: 30,
      duration: 0.8,
      stagger: 0.05,
    },
    "-=0.2",
  );
}

function animateSubtitle(
  timeline: gsap.core.Timeline,
  subtitleRef: RefObject<HTMLParagraphElement | null>,
) {
  if (!subtitleRef.current) return;

  timeline.from(
    subtitleRef.current,
    {
      opacity: 0,
      y: 20,
      duration: 0.6,
    },
    "-=0.4",
  );
}

function animateCTA(
  timeline: gsap.core.Timeline,
  ctaRef: RefObject<HTMLDivElement | null>,
) {
  if (!ctaRef.current) return;

  timeline.from(
    ctaRef.current.children,
    {
      opacity: 0,
      scale: 0.9,
      y: 20,
      duration: 0.5,
      stagger: 0.1,
    },
    "-=0.3",
  );
}

function animateTrustSignals(
  timeline: gsap.core.Timeline,
  contentRef: RefObject<HTMLDivElement | null>,
) {
  const trustSignals = contentRef.current?.querySelectorAll(".trust-signal");
  if (trustSignals && trustSignals.length > 0) {
    timeline.from(
      trustSignals,
      {
        opacity: 0,
        x: -20,
        duration: 0.4,
        stagger: 0.1,
      },
      "-=0.2",
    );
  }
}

function animateStats(
  timeline: gsap.core.Timeline,
  contentRef: RefObject<HTMLDivElement | null>,
) {
  const stats = contentRef.current?.querySelectorAll(".stat-item");
  if (stats && stats.length > 0) {
    timeline.from(
      stats,
      {
        opacity: 0,
        y: 20,
        duration: 0.5,
        stagger: 0.1,
      },
      "-=0.3",
    );
  }
}

function animateCodePreview(
  timeline: gsap.core.Timeline,
  codeRef: RefObject<HTMLDivElement | null>,
) {
  if (!codeRef.current) return;

  timeline.from(
    codeRef.current,
    {
      opacity: 0,
      scale: 0.95,
      y: 40,
      duration: 0.8,
      ease: "back.out(1.2)",
    },
    "-=0.5",
  );
}

export function useHeroAnimations(refs: HeroAnimationRefs) {
  const { heroRef, contentRef, titleRef, subtitleRef, ctaRef, codeRef } = refs;

  useEffect(() => {
    if (!heroRef.current || typeof window === "undefined") {
      return (): void => {
        // No cleanup needed
      };
    }

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      gsap.set(
        [
          titleRef.current,
          subtitleRef.current,
          ctaRef.current,
          codeRef.current,
        ],
        { opacity: 1, y: 0 },
      );
      return (): void => {
        // No cleanup needed for reduced motion
      };
    }

    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

    animateBadge(tl, contentRef);
    animateTitle(tl, titleRef);
    animateSubtitle(tl, subtitleRef);
    animateCTA(tl, ctaRef);
    animateTrustSignals(tl, contentRef);
    animateStats(tl, contentRef);
    animateCodePreview(tl, codeRef);

    return (): void => {
      tl.kill();
    };
  }, [heroRef, contentRef, titleRef, subtitleRef, ctaRef, codeRef]);
}
