import { describe, expect, it } from "vitest";
import { createChatMessage } from "#/services/chat-service";
import ActionType from "#/types/action-type";

describe("createChatMessage", () => {
  it("constructs chat message payload", () => {
    const message = createChatMessage("hello", ["img"], ["file"], "now");

    expect(message).toEqual({
      action: ActionType.MESSAGE,
      args: {
        content: "hello",
        image_urls: ["img"],
        file_urls: ["file"],
        timestamp: "now",
      },
    });
  });

  it("supports empty attachments", () => {
    const payload = createChatMessage("hi", [], [], "later");
    expect(payload.args.image_urls).toEqual([]);
    expect(payload.args.file_urls).toEqual([]);
  });
});
