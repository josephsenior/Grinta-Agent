import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useEffectOnce } from "#/hooks/use-effect-once";

describe("useEffectOnce", () => {
  it("runs the latest callback only once across re-renders", () => {
    const effect = vi.fn();
    const { rerender } = renderHook(({ cb }) => useEffectOnce(cb), {
      initialProps: { cb: effect },
    });

    expect(effect).toHaveBeenCalledTimes(1);

    const nextEffect = vi.fn();
    rerender({ cb: nextEffect });
    rerender({ cb: nextEffect });

    expect(effect).toHaveBeenCalledTimes(1);
    expect(nextEffect).not.toHaveBeenCalled();
  });

  it("runs cleanup when unmounted", () => {
    const cleanup = vi.fn();
    const effect = vi.fn(() => cleanup);

    const { unmount } = renderHook(() => useEffectOnce(effect));

    expect(effect).toHaveBeenCalledTimes(1);

    act(() => {
      unmount();
    });

    expect(cleanup).toHaveBeenCalledTimes(1);
  });
});
