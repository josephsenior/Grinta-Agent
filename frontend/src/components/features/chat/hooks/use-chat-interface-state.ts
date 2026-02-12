import React from "react";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { RootState } from "#/store";
import { AgentState } from "#/types/agent-state";
import { useAgentState } from "#/hooks/use-agent-state";
import { useOptimisticUserMessage } from "#/hooks/use-optimistic-user-message";
import { useWsClient } from "#/context/ws-client-provider";
import { useScrollToBottom } from "#/hooks/use-scroll-to-bottom";
import { useConfig } from "#/hooks/query/use-config";
import { useActiveConversation } from "#/hooks/query/use-active-conversation";
import { useWSErrorMessage } from "#/hooks/use-ws-error-message";
import { useConversationSearch } from "./use-conversation-search";
import { useUploadFiles } from "#/hooks/mutation/use-upload-files";

/**
 * Custom hook to manage ChatInterface state and side effects
 * Separates complex state logic from the UI component
 */
export function useChatInterfaceState() {
  // Core hooks
  useActiveConversation();
  const { getErrorMessage } = useWSErrorMessage();
  const { send, isLoadingMessages, parsedEvents } = useWsClient();
  const { setOptimisticUserMessage, getOptimisticUserMessage } =
    useOptimisticUserMessage();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: config } = useConfig();
  const { mutateAsync: uploadFiles } = useUploadFiles();

  // State selectors
  const curAgentState = useAgentState();
  const { selectedRepository, replayJson } = useSelector(
    (state: RootState) => state.initialQuery,
  );

  // Refs
  const scrollRef = React.useRef<HTMLDivElement>(null);

  // Custom hooks for specific functionality
  const {
    scrollDomToBottom,
    onChatBodyScroll,
    hitBottom,
    autoScroll,
    setAutoScroll,
    setHitBottom,
  } = useScrollToBottom(scrollRef);
  const { isOpen: isSearchOpen, setIsOpen: setIsSearchOpen } =
    useConversationSearch();

  // Component state
  const [messageToSend, setMessageToSend] = React.useState<string | null>(null);
  const [lastUserMessage, setLastUserMessage] = React.useState<string | null>(
    null,
  );
  const [isInputFocused, setIsInputFocused] = React.useState(false);

  // Technical details toggle with localStorage persistence
  const [showTechnicalDetails, setShowTechnicalDetails] =
    React.useState<boolean>(() => {
      try {
        return localStorage.getItem("Forge.showTechnicalDetails") === "true";
      } catch {
        return false;
      }
    });

  React.useEffect(() => {
    try {
      localStorage.setItem(
        "Forge.showTechnicalDetails",
        showTechnicalDetails ? "true" : "false",
      );
    } catch {
      /* ignore */
    }
  }, [showTechnicalDetails]);

  // Optimistic user message
  const optimisticUserMessage = getOptimisticUserMessage();
  const errorMessage = getErrorMessage() ?? null;

  // Derived state
  const isAwaitingUserConfirmation =
    curAgentState === AgentState.AWAITING_USER_CONFIRMATION;

  return {
    // Core state
    curAgentState,
    isAwaitingUserConfirmation,
    parsedEvents,
    isLoadingMessages,
    config,
    t,
    navigate,
    send,
    uploadFiles,

    // Redux state
    selectedRepository,
    replayJson,

    // Refs
    scrollRef,

    // Scroll management
    scrollDomToBottom,
    onChatBodyScroll,
    hitBottom,
    autoScroll,
    setAutoScroll,
    setHitBottom,

    // UI state
    messageToSend,
    setMessageToSend,
    lastUserMessage,
    setLastUserMessage,
    isInputFocused,
    setIsInputFocused,
    showTechnicalDetails,
    setShowTechnicalDetails,

    // Search and navigation
    isSearchOpen,
    setIsSearchOpen,

    // Messages
    optimisticUserMessage,
    errorMessage,

    // Optimistic message handlers
    setOptimisticUserMessage,
    getOptimisticUserMessage,
  };
}
