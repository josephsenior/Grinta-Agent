import React from "react";
import posthog from "posthog-js";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AgentState } from "#/types/agent-state";
import { generateAgentStateChangeEvent } from "#/services/agent-state-service";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import type { FileUploadSuccessResponse } from "#/api/forge.types";
import { logger } from "#/utils/logger";
import { RootState } from "#/store";
import {
  processImages,
  validateAllFiles,
  uploadAttachments,
  reportSkippedFiles,
} from "./use-chat-message-handlers/process-files";
import {
  buildPromptWithFiles,
  createMessagePayload,
} from "./use-chat-message-handlers/build-message";

const MESSAGE_EMPTY_ERROR = "Please enter a message before sending.";
const CONVERSATION_NOT_READY_ERROR =
  "Conversation is not ready yet. Please try again.";

const ensureMessageContent = (content: string) => {
  if (!content || content.trim().length === 0) {
    displayErrorToast(MESSAGE_EMPTY_ERROR);
    return null;
  }
  return content;
};

const ensureConversationReady = (conversationId: string | undefined) => {
  if (!conversationId) {
    displayErrorToast(CONVERSATION_NOT_READY_ERROR);
    return false;
  }
  return true;
};

function getEntryPoint(
  hasRepository: boolean | null,
  hasReplayJson: boolean | null,
): string {
  if (hasRepository) {
    return "github";
  }
  if (hasReplayJson) {
    return "replay";
  }
  return "direct";
}

const trackUserMessageEvents = ({
  events,
  contentLength,
  selectedRepository,
  replayJson,
}: {
  events: unknown[];
  contentLength: number;
  selectedRepository: RootState["initialQuery"]["selectedRepository"];
  replayJson: RootState["initialQuery"]["replayJson"];
}) => {
  if (events.length === 0) {
    posthog.capture("initial_query_submitted", {
      entry_point: getEntryPoint(
        selectedRepository !== null,
        replayJson !== null,
      ),
      query_character_length: contentLength,
      replay_json_size: replayJson?.length,
    });
    return;
  }

  posthog.capture("user_message_sent", {
    session_message_count: events.length,
    current_message_length: contentLength,
  });
};

/**
 * Custom hook to handle chat message operations
 * Separates message handling logic from UI components
 */
export function useChatMessageHandlers(
  send: (message: Record<string, unknown>) => void,
  setOptimisticUserMessage: (message: string) => void,
  setMessageToSend: (message: string | null) => void,
  setLastUserMessage: (message: string | null) => void,
  uploadFiles: (variables: {
    conversationId: string;
    files: File[];
  }) => Promise<FileUploadSuccessResponse>,
  conversationId: string | undefined,
  events: unknown[],
  selectedRepository: RootState["initialQuery"]["selectedRepository"],
  replayJson: RootState["initialQuery"]["replayJson"],
) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleSendMessage = React.useCallback(
    async (content: string, originalImages: File[], originalFiles: File[]) => {
      const messageContent = ensureMessageContent(content);
      if (!messageContent) {
        return;
      }

      if (!ensureConversationReady(conversationId)) {
        return;
      }

      setLastUserMessage(messageContent);
      trackUserMessageEvents({
        events,
        contentLength: messageContent.length,
        selectedRepository,
        replayJson,
      });

      const images = [...originalImages];
      const files = [...originalFiles];
      const validation = validateAllFiles(images, files);

      if (!validation.isValid) {
        displayErrorToast(`Error: ${validation.errorMessage}`);
        return;
      }

      try {
        const imageUrls = await processImages(images);
        const timestamp = new Date().toISOString();

        const uploadResult = await uploadAttachments({
          conversationId: conversationId!,
          files,
          uploadFiles,
        });

        reportSkippedFiles(uploadResult.skippedFiles);

        const prompt = buildPromptWithFiles({
          content: messageContent,
          uploadedFiles: uploadResult.uploadedFiles,
          isSopMessage: false,
          t,
        });

        if (!prompt) {
          return;
        }

        const messagePayload = createMessagePayload(
          prompt,
          imageUrls,
          uploadResult.uploadedFiles,
          timestamp,
        );

        send(messagePayload);
        setOptimisticUserMessage(messageContent);
        setMessageToSend(null);
      } catch (error) {
        logger.error("Failed to send message:", error);
        displayErrorToast(String(t("Failed to send message")));
      }
    },
    [
      conversationId,
      events,
      replayJson,
      selectedRepository,
      send,
      setOptimisticUserMessage,
      setMessageToSend,
      setLastUserMessage,
      t,
      uploadFiles,
    ],
  );

  const handleStop = React.useCallback(() => {
    posthog.capture("stop_button_clicked");
    send(generateAgentStateChangeEvent(AgentState.STOPPED));
  }, [send]);

  const handleAskAboutCode = React.useCallback(
    (code: string) => {
      const question = `Can you explain this code?\n\n\`\`\`\n${code}\n\`\`\``;
      setMessageToSend(question);
    },
    [setMessageToSend],
  );

  const handleRunCode = React.useCallback(
    (code: string, language: string) => {
      const message = `Please run this ${language} code:\n\n\`\`\`${language}\n${code}\n\`\`\``;
      handleSendMessage(message, [], []);
    },
    [handleSendMessage],
  );

  const handleGoBack = React.useCallback(() => {
    navigate("/conversations");
  }, [navigate]);

  return {
    handleSendMessage,
    handleStop,
    handleAskAboutCode,
    handleRunCode,
    handleGoBack,
  };
}
