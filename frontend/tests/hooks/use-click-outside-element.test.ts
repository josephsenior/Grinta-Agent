import { renderHook, act, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useClickOutsideElement } from "#/hooks/use-click-outside-element";

describe("useClickOutsideElement", () => {
  const addSpy = vi.spyOn(document, "addEventListener");
  const removeSpy = vi.spyOn(document, "removeEventListener");

  beforeEach(() => {
    addSpy.mockClear();
    removeSpy.mockClear();
  });

  afterEach(() => {
    cleanup();
  });

  it("invokes callback when clicking outside", () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useClickOutsideElement<HTMLDivElement>(callback));

    const node = document.createElement("div");
    result.current.current = node;

    act(() => {
      document.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(callback).toHaveBeenCalled();
  });

  it("does not invoke callback when clicking inside", () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useClickOutsideElement<HTMLDivElement>(callback));

    const node = document.createElement("div");
    const child = document.createElement("span");
    node.appendChild(child);
    result.current.current = node;

    act(() => {
      child.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(callback).not.toHaveBeenCalled();
  });

  it("cleans up event listener on unmount", () => {
    const callback = vi.fn();
    const { unmount } = renderHook(() => useClickOutsideElement<HTMLDivElement>(callback));

    expect(addSpy).toHaveBeenCalledWith("click", expect.any(Function));

    unmount();

    expect(removeSpy).toHaveBeenCalledWith("click", addSpy.mock.calls[0][1]);
  });
});
