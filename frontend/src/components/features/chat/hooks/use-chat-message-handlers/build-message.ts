import { useTranslation } from "react-i18next";
import { createChatMessage } from "#/services/chat-service";
import { displayErrorToast } from "#/utils/custom-toast-handlers";

const SOP_EMPTY_ERROR =
  "Please provide details with SOP enabled (message cannot be empty).";

export function buildPromptWithFiles({
  content,
  uploadedFiles,
  isSopMessage,
  t,
}: {
  content: string;
  uploadedFiles: string[];
  isSopMessage: boolean;
  t: ReturnType<typeof useTranslation>["t"];
}): string | null {
  const trimmedContent = content.trim();

  if (isSopMessage && trimmedContent.length === 0) {
    displayErrorToast(SOP_EMPTY_ERROR);
    return null;
  }

  const contentToSend = isSopMessage ? `sop:${content}` : content;

  if (uploadedFiles.length === 0) {
    return contentToSend;
  }

  const filePrompt = `${t("CHAT_INTERFACE$AUGMENTED_PROMPT_FILES_TITLE")}: ${uploadedFiles.join(
    "\n\n",
  )}`;

  return `${contentToSend}\n\n${filePrompt}`;
}

export function createMessagePayload(
  prompt: string,
  imageUrls: string[],
  uploadedFiles: string[],
  timestamp: string,
): Record<string, unknown> {
  return createChatMessage(prompt, imageUrls, uploadedFiles, timestamp);
}
