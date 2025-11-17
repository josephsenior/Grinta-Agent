import { renderHook, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const useActiveConversationMock = vi.fn();

vi.mock("#/hooks/query/use-active-conversation", () => ({
  useActiveConversation: () => useActiveConversationMock(),
}));

describe("useDocumentTitleFromState", () => {
  let useDocumentTitleFromState: typeof import("#/hooks/use-document-title-from-state").useDocumentTitleFromState;

  beforeEach(async () => {
    vi.resetModules();
    useActiveConversationMock.mockReturnValue({ data: { title: "Initial" } });
    ({ useDocumentTitleFromState } = await import("#/hooks/use-document-title-from-state"));
  });

  afterEach(() => {
    document.title = "";
  });

  it("updates document title when conversation title is present", () => {
    renderHook(({ suffix }) => useDocumentTitleFromState(suffix), {
      initialProps: { suffix: "Forge" },
    });

    expect(document.title).toBe("Initial | Forge");
  });

  it("restores last known title when conversation title becomes falsy", async () => {
    const { rerender } = renderHook(({ suffix }) => useDocumentTitleFromState(suffix), {
      initialProps: { suffix: "Forge" },
    });

    expect(document.title).toBe("Initial | Forge");

    useActiveConversationMock.mockReturnValue({ data: {} });
    rerender({ suffix: "Forge" });

    expect(document.title).toBe("Initial | Forge");
  });

  it("cleans up to suffix on unmount", () => {
    const { unmount } = renderHook(({ suffix }) => useDocumentTitleFromState(suffix), {
      initialProps: { suffix: "Forge" },
    });

    expect(document.title).toBe("Initial | Forge");

    act(() => {
      unmount();
    });

    expect(document.title).toBe("Forge");
  });
});
