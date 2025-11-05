import React from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AgentState } from "#/types/agent-state";
import { generateAgentStateChangeEvent } from "#/services/agent-state-service";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { I18nKey } from "#/i18n/declaration";
import type { FileUploadSuccessResponse } from "#/api/open-hands.types";
import { createChatMessage } from "#/services/chat-service";
import { validateFiles } from "#/utils/file-validation";
import { convertImageToBase64 } from "#/utils/convert-image-to-base-64";

/**
 * Custom hook to handle chat message operations
 * Separates message handling logic from UI components
 */
export function useChatMessageHandlers(
  send: (message: Record<string, unknown>) => void,
  setOptimisticUserMessage: (message: string) => void,
  setMessageToSend: (message: string | null) => void,
  setLastUserMessage: (message: string | null) => void,
  uploadFiles: (files: File[]) => Promise<FileUploadSuccessResponse>,
  conversationId: string | undefined
) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleSendMessage = React.useCallback(
    async (message: string, files: File[] = [], images: File[] = []) => {
      if (!message.trim() && files.length === 0 && images.length === 0) return;

      try {
        // Validate files
        const validationResult = validateFiles(files);
        if (!validationResult.isValid) {
          displayErrorToast(validationResult.errorMessage || "Invalid file selection");
          return;
        }

        // Handle file uploads
        if (files.length > 0) {
          // uploadFiles returns `FileUploadSuccessResponse` but we don't need the value here
          await uploadFiles(files);
        }

        // Handle image uploads
        const imagePromises = images.map(async (image) => {
          const base64 = await convertImageToBase64(image);
          return { name: image.name, data: base64 };
        });
        const uploadedImages = await Promise.all(imagePromises);

        // Create and send message
        // `createChatMessage` expects (message, image_urls, file_urls, timestamp)
        const imageUrls = uploadedImages.map((i) => i.data);
        const fileUrls: string[] = [];
        const timestamp = new Date().toISOString();
        const messageToSend = createChatMessage(message, imageUrls, fileUrls, timestamp);
        send(messageToSend);
        
        setOptimisticUserMessage(message);
        setMessageToSend(null);
        setLastUserMessage(message);
      } catch (error) {
        console.error("Failed to send message:", error);
        // `t` returns a string; ensure we pass a string to the toast helper
        displayErrorToast(String(t("Failed to send message")));
      }
    },
    [send, setOptimisticUserMessage, setMessageToSend, setLastUserMessage, uploadFiles, t]
  );

  const handleStop = React.useCallback(() => {
    send(generateAgentStateChangeEvent(AgentState.STOPPED));
  }, [send]);

  const handleAskAboutCode = React.useCallback(
    (code: string) => {
      const question = `Can you explain this code?\n\n\`\`\`\n${code}\n\`\`\``;
      setMessageToSend(question);
    },
    [setMessageToSend]
  );

  const handleRunCode = React.useCallback(
    (code: string, language: string) => {
      const message = `Please run this ${language} code:\n\n\`\`\`${language}\n${code}\n\`\`\``;
      handleSendMessage(message, [], []);
    },
    [handleSendMessage]
  );

  const handleGoBack = React.useCallback(() => {
    navigate("/");
  }, [navigate]);

  return {
    handleSendMessage,
    handleStop,
    handleAskAboutCode,
    handleRunCode,
    handleGoBack,
  };
}
