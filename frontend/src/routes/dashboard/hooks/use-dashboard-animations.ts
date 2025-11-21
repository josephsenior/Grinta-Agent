import { useEffect, RefObject } from "react";
import { gsap } from "gsap";

interface DashboardAnimationRefs {
  quickStatsRef: RefObject<HTMLDivElement | null>;
  quickActionsRef: RefObject<HTMLDivElement | null>;
  recentConversationsRef: RefObject<HTMLDivElement | null>;
  activityFeedRef: RefObject<HTMLDivElement | null>;
}

interface UseDashboardAnimationsProps {
  refs: DashboardAnimationRefs;
  isLoading: boolean;
  hasError: boolean;
  stats: any;
}

export function useDashboardAnimations({
  refs,
  isLoading,
  hasError,
  stats,
}: UseDashboardAnimationsProps) {
  const {
    quickStatsRef,
    quickActionsRef,
    recentConversationsRef,
    activityFeedRef,
  } = refs;

  useEffect(() => {
    if (isLoading || !quickStatsRef.current) return;

    const cards = Array.from(quickStatsRef.current.children) as HTMLElement[];
    if (cards.length === 0) return;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      gsap.set(cards, { opacity: 1, y: 0 });
      return;
    }

    gsap.set(cards, { opacity: 0, y: 20 });
    gsap.to(cards, {
      opacity: 1,
      y: 0,
      duration: 0.6,
      stagger: 0.1,
      ease: "power3.out",
      delay: 0.2,
    });
  }, [isLoading, stats, quickStatsRef]);

  useEffect(() => {
    if (isLoading || !quickActionsRef.current) return;

    const actions = Array.from(
      quickActionsRef.current.children,
    ) as HTMLElement[];
    if (actions.length === 0) return;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      gsap.set(actions, { opacity: 1, x: 0 });
      return;
    }

    gsap.set(actions, { opacity: 0, x: 20 });
    gsap.to(actions, {
      opacity: 1,
      x: 0,
      duration: 0.5,
      stagger: 0.08,
      ease: "power2.out",
      delay: 0.4,
    });
  }, [isLoading, quickActionsRef]);

  useEffect(() => {
    if (isLoading || !recentConversationsRef.current) return;
    if (hasError) return;

    const conversations = Array.from(
      recentConversationsRef.current.children,
    ) as HTMLElement[];
    if (conversations.length === 0) return;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      gsap.set(conversations, { opacity: 1, y: 0 });
      return;
    }

    gsap.set(conversations, { opacity: 0, y: 15 });
    gsap.to(conversations, {
      opacity: 1,
      y: 0,
      duration: 0.5,
      stagger: 0.06,
      ease: "power2.out",
      delay: 0.1,
    });
  }, [isLoading, stats, hasError, recentConversationsRef]);

  useEffect(() => {
    if (!activityFeedRef.current) return;
    if (!stats?.activity_feed || stats.activity_feed.length === 0) return;

    const feedContainer = activityFeedRef.current.querySelector(
      ".space-y-0",
    ) as HTMLElement;
    if (!feedContainer) return;

    const items = Array.from(feedContainer.children) as HTMLElement[];
    if (items.length === 0) return;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      gsap.set(items, { opacity: 1, x: 0 });
      return;
    }

    gsap.set(items, { opacity: 0, x: -10 });
    gsap.to(items, {
      opacity: 1,
      x: 0,
      duration: 0.4,
      stagger: 0.05,
      ease: "power2.out",
      delay: 0.2,
    });
  }, [stats?.activity_feed, activityFeedRef]);
}
