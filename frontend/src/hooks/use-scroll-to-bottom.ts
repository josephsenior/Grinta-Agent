import { RefObject, useEffect, useState, useCallback, useRef } from "react";
import { logger } from "#/utils/logger";

export function useScrollToBottom(scrollRef: RefObject<HTMLDivElement | null>) {
  // Track whether we should auto-scroll to the bottom when content changes
  const [autoscroll, setAutoscroll] = useState(true);

  // Track whether the user is currently at the bottom of the scroll area
  const [hitBottom, setHitBottom] = useState(true);

  // Store previous scroll position to detect scroll direction
  const prevScrollTopRef = useRef<number>(0);

  // Check if the scroll position is at the bottom
  const isAtBottom = useCallback((element: HTMLElement): boolean => {
    // Use a fixed 20px buffer
    const bottomThreshold = 20;
    const bottomPosition = element.scrollTop + element.clientHeight;
    return bottomPosition >= element.scrollHeight - bottomThreshold;
  }, []);

  // Handle scroll events
  const onChatBodyScroll = useCallback(
    (e: HTMLElement) => {
      const isCurrentlyAtBottom = isAtBottom(e);
      setHitBottom(isCurrentlyAtBottom);

      // Get current scroll position
      const currentScrollTop = e.scrollTop;

      // Detect scroll direction
      const isScrollingUp = currentScrollTop < prevScrollTopRef.current;

      // Update previous scroll position for next comparison
      prevScrollTopRef.current = currentScrollTop;

      // Turn off autoscroll only when scrolling up
      if (isScrollingUp) {
        setAutoscroll(false);
      }

      // Turn on autoscroll when scrolled to the bottom
      if (isCurrentlyAtBottom) {
        setAutoscroll(true);
      }
    },
    [isAtBottom],
  );

  // Scroll to bottom function with animation
  const scrollDomToBottom = useCallback(() => {
    const dom = scrollRef.current;
    if (dom) {
      requestAnimationFrame(() => {
        // Set autoscroll to true when manually scrolling to bottom
        setAutoscroll(true);
        setHitBottom(true);

        // Use smooth scrolling but with a fast duration
        dom.scrollTo({
          top: dom.scrollHeight,
          behavior: "smooth",
        });
      });
    }
  }, [scrollRef]);

  // Auto-scroll effect that runs when content changes
  // Use a ResizeObserver to detect when the scrollable content grows and
  // keep the viewport pinned to the bottom when autoscroll is enabled.
  useEffect(() => {
    const dom = scrollRef.current;
    if (!dom) {
      return undefined;
    }

    // If autoscroll is enabled on mount, ensure we're at the bottom
    if (autoscroll) {
      requestAnimationFrame(() => {
        dom.scrollTo({ top: dom.scrollHeight, behavior: "auto" });
      });
    }
    // Prefer observing the scrollable content (first child) because the
    // container's own bounding box may not resize when children grow. This
    // ensures we react when message content increases the scrollHeight.
    const contentEl = (dom.firstElementChild as HTMLElement) || dom;

    const ro = new ResizeObserver(() => {
      // Only adjust scroll when autoscroll is active
      if (autoscroll) {
        // Use multiple attempts to ensure scrolling works
        requestAnimationFrame(() => {
          dom.scrollTo({ top: dom.scrollHeight, behavior: "auto" });
          setHitBottom(true);
        });

        setTimeout(() => {
          if (autoscroll) {
            dom.scrollTo({ top: dom.scrollHeight, behavior: "auto" });
            setHitBottom(true);
          }
        }, 10);
      }
    });

    ro.observe(contentEl);

    // MutationObserver fallback: some environments may change children without
    // producing ResizeObserver notifications on the content element. Watch
    // for additions/character changes and adjust scroll when autoscroll is on.
    const mo = new MutationObserver(() => {
      if (autoscroll) {
        // Use multiple attempts to ensure scrolling works
        requestAnimationFrame(() => {
          dom.scrollTo({ top: dom.scrollHeight, behavior: "auto" });
          setHitBottom(true);
        });

        setTimeout(() => {
          if (autoscroll) {
            dom.scrollTo({ top: dom.scrollHeight, behavior: "auto" });
            setHitBottom(true);
          }
        }, 10);
      }
    });

    try {
      mo.observe(contentEl, {
        childList: true,
        subtree: true,
        characterData: true,
      });
    } catch (e) {
      // Some environments may throw when observing with these options.
      // Swallow intentionally — this is a best-effort observer only.
      logger.warn("useScrollToBottom: MutationObserver not supported fully", e);
    }

    return () => {
      try {
        ro.disconnect();
      } catch (e) {
        // ignore
      }
      try {
        mo.disconnect();
      } catch (e) {
        // ignore
      }
    };
    // We purposely include autoscroll so that toggling autoscroll will
    // immediately adjust behavior; scrollRef is stable.
  }, [autoscroll, scrollRef]);

  return {
    scrollRef,
    autoScroll: autoscroll,
    setAutoScroll: setAutoscroll,
    scrollDomToBottom,
    hitBottom,
    setHitBottom,
    onChatBodyScroll,
  };
}
