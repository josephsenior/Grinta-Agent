import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const useIsMutatingMock = vi.hoisted(() => vi.fn());

vi.mock("@tanstack/react-query", () => ({
  useIsMutating: (args: unknown) => useIsMutatingMock(args),
}));

import { useIsCreatingConversation } from "#/hooks/use-is-creating-conversation";

describe("useIsCreatingConversation", () => {
  it("returns true when there are pending create conversation mutations", () => {
    useIsMutatingMock.mockReturnValueOnce(2);

    const { result } = renderHook(() => useIsCreatingConversation());

    expect(useIsMutatingMock).toHaveBeenCalledWith({ mutationKey: ["create-conversation"] });
    expect(result.current).toBe(true);
  });

  it("returns false when there are no pending mutations", () => {
    useIsMutatingMock.mockReturnValueOnce(0);

    const { result } = renderHook(() => useIsCreatingConversation());

    expect(result.current).toBe(false);
  });
});
