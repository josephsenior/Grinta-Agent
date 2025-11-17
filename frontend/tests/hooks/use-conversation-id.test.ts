import { describe, expect, it, afterEach, vi } from "vitest";

describe("useConversationId", () => {
  afterEach(() => {
    vi.resetModules();
  });

  it("returns conversation id when present", async () => {
    vi.doMock("react-router-dom", () => ({
      useParams: () => ({ conversationId: "42" }),
    }));

    const { useConversationId } = await import("#/hooks/use-conversation-id");
    const { conversationId } = useConversationId();

    expect(conversationId).toBe("42");
  });

  it("throws error when conversation id missing", async () => {
    vi.doMock("react-router-dom", () => ({
      useParams: () => ({}),
    }));

    const { useConversationId } = await import("#/hooks/use-conversation-id");

    expect(() => useConversationId()).toThrow(
      /useConversationId must be used within a route/,
    );
  });
});
