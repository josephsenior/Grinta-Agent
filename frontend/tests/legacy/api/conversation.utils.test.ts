import { describe, expect, it, vi } from "vitest";
import { getConversationUrl } from "#/api/conversation.utils";

vi.mock("#/api/forge", () => ({
  __esModule: true,
  default: {
    getConversationUrl: vi.fn().mockReturnValue("/conversations/123"),
  },
}));

describe("conversation utils", () => {
  it("delegates to Forge.getConversationUrl", () => {
    const url = getConversationUrl("123");
    expect(url).toBe("/conversations/123");
  });
});
