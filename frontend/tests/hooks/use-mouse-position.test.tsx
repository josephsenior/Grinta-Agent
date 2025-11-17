import { act, fireEvent, renderHook, render, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import { useMousePosition, useMagneticHover } from "#/hooks/use-mouse-position";

describe("useMousePosition", () => {
  let addEventListenerSpy: ReturnType<typeof vi.spyOn>;
  let removeEventListenerSpy: ReturnType<typeof vi.spyOn>;
  let animationFrame = 0;

  beforeEach(() => {
    vi.useFakeTimers();
    animationFrame = 0;
    addEventListenerSpy = vi.spyOn(window, "addEventListener");
    removeEventListenerSpy = vi.spyOn(window, "removeEventListener");
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb: FrameRequestCallback) => {
      animationFrame += 1;
      cb(performance.now());
      return animationFrame;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("tracks mouse position with throttling", () => {
    const { result, unmount } = renderHook(() => useMousePosition(50));

    expect(addEventListenerSpy).toHaveBeenCalledWith("mousemove", expect.any(Function));

    const handler = addEventListenerSpy.mock.calls.find((call) => call[0] === "mousemove")?.[1] as
      | ((e: MouseEvent) => void)
      | undefined;

    expect(result.current).toEqual({ x: 0, y: 0 });

    act(() => {
      handler?.({ clientX: 10, clientY: 20 } as MouseEvent);
    });

    expect(result.current).toEqual({ x: 10, y: 20 });

    act(() => {
      handler?.({ clientX: 30, clientY: 40 } as MouseEvent);
    });

    expect(result.current).toEqual({ x: 10, y: 20 });

    act(() => {
      vi.advanceTimersByTime(60);
      handler?.({ clientX: 30, clientY: 40 } as MouseEvent);
    });

    expect(result.current).toEqual({ x: 30, y: 40 });

    unmount();
    expect(removeEventListenerSpy).toHaveBeenCalledWith("mousemove", handler);
  });
});

describe("useMagneticHover", () => {
  it("updates offset based on mouse movement and hover state", () => {
    const element = document.createElement("div");
    Object.defineProperty(element, "getBoundingClientRect", {
      value: () => ({ left: 0, top: 0, width: 100, height: 100 }),
    });

    const ref = { current: element };
    const eventMap: Record<string, EventListener> = {};
    vi.spyOn(element, "addEventListener").mockImplementation((type, handler) => {
      eventMap[type] = handler as EventListener;
      return element;
    });
    vi.spyOn(element, "removeEventListener").mockImplementation((type) => {
      delete eventMap[type];
      return element;
    });

    const { result } = renderHook(() => useMagneticHover(ref, 0.5));

    expect(eventMap.mouseenter).toBeDefined();
    expect(eventMap.mousemove).toBeDefined();
    expect(eventMap.mouseleave).toBeDefined();

    act(() => {
      eventMap.mouseenter?.(new Event("mouseenter"));
    });

    expect(result.current.isHovered).toBe(true);

    act(() => {
      eventMap.mousemove?.({ clientX: 100, clientY: 100 } as MouseEvent);
    });

    expect(result.current.offset).toEqual({ x: 25, y: 25 });

    act(() => {
      eventMap.mouseleave?.(new Event("mouseleave"));
    });

    expect(result.current.isHovered).toBe(false);
    expect(result.current.offset).toEqual({ x: 0, y: 0 });
  });

  it("gracefully handles missing element", async () => {
    const { result } = renderHook(() => useMagneticHover({ current: null }, 0.5));

    await waitFor(() => expect(result.current.isHovered).toBe(false));
    expect(result.current.offset).toEqual({ x: 0, y: 0 });
  });
});
