import ActionType from "#/types/action-type";

export function createChatMessage(
  message: string,
  image_urls: string[],
  file_urls: string[],
  timestamp: string,
) {
  return {
    action: ActionType.MESSAGE,
    args: { content: message, image_urls, file_urls, timestamp },
  };
}
// MetaGPT envelope and tool helpers removed; chat service only exposes core message builder.
