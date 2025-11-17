import { act, render, renderHook } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useScrollProgress, useScrollReveal, useScrollY } from "#/hooks/use-scroll-reveal";
import { useScrollToBottom } from "#/hooks/use-scroll-to-bottom";

describe("useScrollReveal", () => {
  let observers: Array<{
    observe: ReturnType<typeof vi.fn>;
    unobserve: ReturnType<typeof vi.fn>;
    disconnect: ReturnType<typeof vi.fn>;
    trigger: (entries: IntersectionObserverEntry[]) => void;
  }>;

  beforeEach(() => {
    observers = [];

    vi.stubGlobal(
      "IntersectionObserver",
      vi.fn((callback: IntersectionObserverCallback) => {
        const instance = {
          observe: vi.fn(),
          unobserve: vi.fn(),
          disconnect: vi.fn(),
          trigger(entries: IntersectionObserverEntry[]) {
            callback(entries, instance as unknown as IntersectionObserver);
          },
        };
        observers.push(instance);
        return instance as unknown as IntersectionObserver;
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("marks visible and unobserves when triggerOnce is true", () => {
    const TestComponent = () => {
      const { ref, isVisible } = useScrollReveal({ triggerOnce: true });
      return <div ref={ref} data-visible={String(isVisible)} data-testid="target" />;
    };

    const { getByTestId } = render(<TestComponent />);

    expect(observers).toHaveLength(1);
    const observer = observers[0];
    const element = getByTestId("target");
    expect(observer.observe).toHaveBeenCalledWith(element);

    act(() => {
      observer.trigger([
        {
          isIntersecting: true,
        } as IntersectionObserverEntry,
      ]);
    });

    expect(getByTestId("target").dataset.visible).toBe("true");
    expect(observer.unobserve).toHaveBeenCalledWith(element);
  });

  it("toggles visibility when triggerOnce is false", () => {
    const TestComponent = () => {
      const { ref, isVisible } = useScrollReveal({ triggerOnce: false });
      return <div ref={ref} data-visible={String(isVisible)} data-testid="target" />;
    };

    const { getByTestId, unmount } = render(<TestComponent />);
    const observer = observers[0];

    act(() => {
      observer.trigger([
        {
          isIntersecting: true,
        } as IntersectionObserverEntry,
      ]);
    });
    expect(getByTestId("target").dataset.visible).toBe("true");

    act(() => {
      observer.trigger([
        {
          isIntersecting: false,
        } as IntersectionObserverEntry,
      ]);
    });
    expect(getByTestId("target").dataset.visible).toBe("false");

    unmount();
    expect(observer.disconnect).toHaveBeenCalled();
  });
});

describe("useScrollProgress", () => {
  const originalInnerHeight = window.innerHeight;
  const originalScrollY = window.scrollY;
  let originalScrollHeight: number | undefined;

  beforeEach(() => {
    originalScrollHeight = document.documentElement.scrollHeight;
    Object.defineProperty(window, "innerHeight", { value: 500, configurable: true });
    Object.defineProperty(document.documentElement, "scrollHeight", {
      value: 1500,
      configurable: true,
    });
    Object.defineProperty(window, "scrollY", { value: 0, configurable: true, writable: true });
  });

  afterEach(() => {
    Object.defineProperty(window, "innerHeight", {
      value: originalInnerHeight,
      configurable: true,
    });
    Object.defineProperty(document.documentElement, "scrollHeight", {
      value: originalScrollHeight,
      configurable: true,
    });
    Object.defineProperty(window, "scrollY", {
      value: originalScrollY,
      configurable: true,
      writable: true,
    });
  });

  it("calculates scroll progress based on position", () => {
    const { result } = renderHook(() => useScrollProgress());

    expect(result.current).toBe(0);

    act(() => {
      window.scrollY = 250;
      window.dispatchEvent(new Event("scroll"));
    });

    expect(result.current).toBeCloseTo(0.25);

    act(() => {
      window.scrollY = 1000;
      window.dispatchEvent(new Event("scroll"));
    });

    expect(result.current).toBeCloseTo(1);
  });
});

describe("useScrollY", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb: FrameRequestCallback) => {
      cb(0);
      return 1;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("tracks scroll position with throttling", () => {
    Object.defineProperty(window, "scrollY", { value: 0, configurable: true, writable: true });

    const { result } = renderHook(() => useScrollY(100));

    expect(result.current).toBe(0);

    act(() => {
      vi.advanceTimersByTime(100);
      window.scrollY = 50;
      window.dispatchEvent(new Event("scroll"));
    });

    expect(result.current).toBe(50);

    act(() => {
      window.scrollY = 60;
      window.dispatchEvent(new Event("scroll"));
    });

    expect(result.current).toBe(50);

    act(() => {
      vi.advanceTimersByTime(100);
      window.scrollY = 120;
      window.dispatchEvent(new Event("scroll"));
    });

    expect(result.current).toBe(120);
  });
});

describe("useScrollToBottom", () => {
  let scrollElement: HTMLDivElement;
  let scrollRef: { current: HTMLDivElement | null };
  let resizeObservers: Array<{
    trigger: () => void;
    observe: ReturnType<typeof vi.fn>;
    disconnect: ReturnType<typeof vi.fn>;
  }>;
  let mutationObservers: Array<{
    trigger: () => void;
    observe: ReturnType<typeof vi.fn>;
    disconnect: ReturnType<typeof vi.fn>;
  }>;

  const setScrollMetrics = (metrics: { scrollTop?: number; scrollHeight?: number; clientHeight?: number }) => {
    if (metrics.scrollTop !== undefined) {
      Object.defineProperty(scrollElement, "scrollTop", {
        value: metrics.scrollTop,
        configurable: true,
        writable: true,
      });
    }
    if (metrics.scrollHeight !== undefined) {
      Object.defineProperty(scrollElement, "scrollHeight", {
        value: metrics.scrollHeight,
        configurable: true,
      });
    }
    if (metrics.clientHeight !== undefined) {
      Object.defineProperty(scrollElement, "clientHeight", {
        value: metrics.clientHeight,
        configurable: true,
      });
    }
  };

  beforeEach(() => {
    vi.useFakeTimers();

    resizeObservers = [];
    mutationObservers = [];

    class MockResizeObserver {
      callback: ResizeObserverCallback;
      observe = vi.fn();
      disconnect = vi.fn();
      constructor(callback: ResizeObserverCallback) {
        this.callback = callback;
        resizeObservers.push({
          trigger: () => this.callback([], this as unknown as ResizeObserver),
          observe: this.observe,
          disconnect: this.disconnect,
        });
      }
    }

    class MockMutationObserver {
      callback: MutationCallback;
      observe = vi.fn();
      disconnect = vi.fn();
      constructor(callback: MutationCallback) {
        this.callback = callback;
        mutationObservers.push({
          trigger: () => this.callback([], this as unknown as MutationObserver),
          observe: this.observe,
          disconnect: this.disconnect,
        });
      }
    }

    vi.stubGlobal("ResizeObserver", MockResizeObserver as unknown as typeof ResizeObserver);
    vi.stubGlobal("MutationObserver", MockMutationObserver as unknown as typeof MutationObserver);

    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb: FrameRequestCallback) => {
      cb(0);
      return 1;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => undefined);

    scrollElement = document.createElement("div");
    scrollElement.scrollTo = vi.fn();
    const child = document.createElement("div");
    scrollElement.appendChild(child);

    setScrollMetrics({ scrollTop: 180, scrollHeight: 400, clientHeight: 200 });

    scrollRef = { current: scrollElement };
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("auto-scrolls on mount and reacts to observers when autoscroll is enabled", () => {
    const { result } = renderHook(() => useScrollToBottom(scrollRef));

    expect(scrollElement.scrollTo).toHaveBeenCalledWith({ top: 400, behavior: "auto" });
    expect(resizeObservers).toHaveLength(1);
    expect(resizeObservers[0].observe).toHaveBeenCalled();
    expect(mutationObservers[0]?.observe).toHaveBeenCalled();

    scrollElement.scrollTo = vi.fn();

    act(() => {
      resizeObservers[0].trigger();
      mutationObservers[0]?.trigger();
      vi.advanceTimersByTime(11);
    });

    expect(scrollElement.scrollTo).toHaveBeenCalledWith({ top: 400, behavior: "auto" });
    expect(result.current.hitBottom).toBe(true);

    act(() => {
      result.current.setAutoScroll(false);
    });

    expect(resizeObservers).toHaveLength(2);
    scrollElement.scrollTo = vi.fn();

    act(() => {
      resizeObservers[1].trigger();
      mutationObservers[1]?.trigger();
      vi.advanceTimersByTime(11);
    });

    expect(scrollElement.scrollTo).not.toHaveBeenCalled();
  });

  it("observes container when no child content element exists", () => {
    scrollElement.innerHTML = "";
    const { unmount } = renderHook(() => useScrollToBottom(scrollRef));

    expect(resizeObservers[resizeObservers.length - 1].observe).toHaveBeenCalledWith(
      scrollElement,
    );

    unmount();
  });

  it("updates autoscroll state based on user scrolling and manual scroll", () => {
    const { result } = renderHook(() => useScrollToBottom(scrollRef));

    // Simulate user scrolling down (no state change)
    act(() => {
      setScrollMetrics({ scrollTop: 220 });
      result.current.onChatBodyScroll(scrollElement);
    });
    expect(result.current.autoScroll).toBe(true);

    // Scroll up to disable autoscroll
    act(() => {
      setScrollMetrics({ scrollTop: 150 });
      result.current.onChatBodyScroll(scrollElement);
    });
    expect(result.current.autoScroll).toBe(false);
    expect(result.current.hitBottom).toBe(false);

    // Scroll back to bottom to re-enable autoscroll
    act(() => {
      setScrollMetrics({ scrollTop: 400 - 200 });
      result.current.onChatBodyScroll(scrollElement);
    });
    expect(result.current.autoScroll).toBe(true);
    expect(result.current.hitBottom).toBe(true);

    // Manually scroll to bottom when autoscroll disabled
    act(() => {
      result.current.setAutoScroll(false);
      setScrollMetrics({ scrollTop: 50 });
      result.current.scrollDomToBottom();
    });

    expect(scrollElement.scrollTo).toHaveBeenCalledWith({ top: 400, behavior: "smooth" });
    expect(result.current.autoScroll).toBe(true);
    expect(result.current.hitBottom).toBe(true);
  });

  it("logs warning when MutationObserver.observe throws", () => {
    class ThrowingMutationObserver {
      observe() {
        throw new Error("not supported");
      }
      disconnect = vi.fn();
      constructor() {}
    }

    vi.stubGlobal("MutationObserver", ThrowingMutationObserver as unknown as typeof MutationObserver);
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);

    renderHook(() => useScrollToBottom(scrollRef));

    expect(warnSpy).toHaveBeenCalledWith(
      "useScrollToBottom: MutationObserver not supported fully",
      expect.any(Error),
    );
  });

  it("avoids observer setup when ref is null", () => {
    const nullRef = { current: null };

    renderHook(() => useScrollToBottom(nullRef));

    expect(resizeObservers).toHaveLength(0);
    expect(mutationObservers).toHaveLength(0);
  });

  it("swallows disconnect errors during cleanup", () => {
    const { unmount } = renderHook(() => useScrollToBottom(scrollRef));

    resizeObservers[0].disconnect.mockImplementation(() => {
      throw new Error("resize disconnect");
    });
    mutationObservers[0]?.disconnect.mockImplementation(() => {
      throw new Error("mutation disconnect");
    });

    expect(() => unmount()).not.toThrow();
  });
});
