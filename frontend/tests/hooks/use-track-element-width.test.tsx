import { act, renderHook } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { useTrackElementWidth } from "#/hooks/use-track-element-width";

class MockResizeObserver {
  static instances: MockResizeObserver[] = [];

  callback: ResizeObserverCallback;
  observe = vi.fn();
  disconnect = vi.fn();

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    MockResizeObserver.instances.push(this);
  }

  trigger(entries: Partial<ResizeObserverEntry>[]) {
    this.callback(entries as ResizeObserverEntry[], this as unknown as ResizeObserver);
  }
}

describe("useTrackElementWidth", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockResizeObserver.instances = [];
    vi.stubGlobal("ResizeObserver", MockResizeObserver);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  const createRef = () => {
    const element = document.createElement("div");
    return { current: element };
  };

  const createContentRect = (width: number): DOMRectReadOnly =>
    ({
      x: 0,
      y: 0,
      width,
      height: 0,
      top: 0,
      left: 0,
      right: width,
      bottom: 0,
      toJSON: () => ({}),
    }) as DOMRectReadOnly;

  it("invokes callback after the specified delay with observed width", () => {
    const callback = vi.fn();
    const elementRef = createRef();

    renderHook(() =>
      useTrackElementWidth({ elementRef, callback, delay: 200 }),
    );

    const observer = MockResizeObserver.instances[0];
    expect(observer.observe).toHaveBeenCalledWith(elementRef.current);

    act(() => {
      observer.trigger([{ contentRect: createContentRect(128) }]);
    });

    expect(callback).not.toHaveBeenCalled();
    vi.advanceTimersByTime(199);
    expect(callback).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(callback).toHaveBeenCalledWith(128);
  });

  it("debounces rapid width updates and only invokes the callback once with the latest width", () => {
    const callback = vi.fn();
    const elementRef = createRef();

    renderHook(() =>
      useTrackElementWidth({ elementRef, callback, delay: 100 }),
    );

    const observer = MockResizeObserver.instances[0];

    act(() => {
      observer.trigger([{ contentRect: createContentRect(40) }]);
      vi.advanceTimersByTime(50);
      observer.trigger([{ contentRect: createContentRect(60) }]);
    });

    vi.advanceTimersByTime(99);
    expect(callback).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith(60);
  });

  it("cleans up pending timeouts and disconnects the observer on unmount", () => {
    const callback = vi.fn();
    const elementRef = createRef();

    const { unmount } = renderHook(() =>
      useTrackElementWidth({ elementRef, callback, delay: 100 }),
    );

    const observer = MockResizeObserver.instances[0];

    act(() => {
      observer.trigger([{ contentRect: createContentRect(75) }]);
    });

    unmount();

    expect(observer.disconnect).toHaveBeenCalled();

    vi.advanceTimersByTime(200);
    expect(callback).not.toHaveBeenCalled();
  });
});

