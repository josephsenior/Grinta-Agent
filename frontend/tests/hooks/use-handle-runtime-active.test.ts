import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const runtimeReadyMock = vi.fn();

vi.mock("#/hooks/use-runtime-is-ready", () => ({
  useRuntimeIsReady: () => runtimeReadyMock(),
}));

import { useHandleRuntimeActive } from "#/hooks/use-handle-runtime-active";

describe("useHandleRuntimeActive", () => {
  it("returns runtime active state", () => {
    runtimeReadyMock.mockReturnValueOnce(true);

    const { result } = renderHook(() => useHandleRuntimeActive());

    expect(runtimeReadyMock).toHaveBeenCalled();
    expect(result.current.runtimeActive).toBe(true);

    runtimeReadyMock.mockReturnValueOnce(false);
    const { result: second } = renderHook(() => useHandleRuntimeActive());
    expect(second.current.runtimeActive).toBe(false);
  });
});
