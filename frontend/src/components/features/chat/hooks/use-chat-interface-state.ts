import React from "react";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { RootState } from "#/store";
import { AgentState } from "#/types/agent-state";
import { useOptimisticUserMessage } from "#/hooks/use-optimistic-user-message";
import { useWsClient } from "#/context/ws-client-provider";
import { useTasks } from "#/context/task-context";
import { useScrollToBottom } from "#/hooks/use-scroll-to-bottom";
import { useConfig } from "#/hooks/query/use-config";
import { useActiveConversation } from "#/hooks/query/use-active-conversation";
import { useWSErrorMessage } from "#/hooks/use-ws-error-message";
// Removed fragile message pattern matching - auto-navigation now via server detection + Playwright URL sync
import { useConversationSearch } from "./use-conversation-search";
import { useConversationBookmarks } from "./use-conversation-bookmarks";
import { useMetaSOPOrchestration } from "#/hooks/use-metasop-orchestration";
import { useUploadFiles } from "#/hooks/mutation/use-upload-files";

/**
 * Hook for SOP preference with localStorage persistence
 */
function useSopPreference() {
  const [useSop, setUseSop] = React.useState<boolean>(() => {
    try {
      return localStorage.getItem("Forge.useSop") === "1";
    } catch {
      return false;
    }
  });

  React.useEffect(() => {
    try {
      localStorage.setItem("Forge.useSop", useSop ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [useSop]);

  return [useSop, setUseSop] as const;
}

/**
 * Hook for optimistic SOP indicator
 */
function useOptimisticSopIndicator(isOrchestrating: boolean) {
  const [optimisticSopStarting, setOptimisticSopStarting] =
    React.useState(false);
  const timerRef = React.useRef<number | null>(null);

  const clearTimer = React.useCallback(() => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  React.useEffect(() => {
    if (isOrchestrating && optimisticSopStarting) {
      setOptimisticSopStarting(false);
      clearTimer();
    }
  }, [isOrchestrating, optimisticSopStarting, clearTimer]);

  React.useEffect(() => () => clearTimer(), [clearTimer]);

  const triggerOptimisticSop = React.useCallback(() => {
    setOptimisticSopStarting(true);
    clearTimer();
    timerRef.current = window.setTimeout(() => {
      setOptimisticSopStarting(false);
      timerRef.current = null;
    }, 8000);
  }, [clearTimer]);

  return { optimisticSopStarting, triggerOptimisticSop } as const;
}

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
  const { curAgentState } = useSelector((state: RootState) => state.agent);
  const { selectedRepository, replayJson } = useSelector(
    (state: RootState) => state.initialQuery,
  );
  const { tasks, isTaskPanelOpen, toggleTaskPanel } = useTasks();

  // Refs
  const scrollRef = React.useRef<HTMLDivElement>(null);

  // Custom hooks for specific functionality
  // Auto-navigation handled by server detection (automatic) + Playwright URL sync (robust)
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
  const bookmarksHook = useConversationBookmarks();
  const { steps, isOrchestrating, hasSteps } = useMetaSOPOrchestration();

  // SOP support
  const [useSop, setUseSop] = useSopPreference();
  const { optimisticSopStarting, triggerOptimisticSop } =
    useOptimisticSopIndicator(isOrchestrating);

  // Component state
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const [feedbackPolarity, setFeedbackPolarity] = React.useState<
    "positive" | "negative"
  >("positive");
  const [feedbackModalIsOpen, setFeedbackModalIsOpen] = React.useState(false);
  const [messageToSend, setMessageToSend] = React.useState<string | null>(null);
  const [lastUserMessage, setLastUserMessage] = React.useState<string | null>(
    null,
  );
  const [isInputFocused, setIsInputFocused] = React.useState(false);
  const [showOrchestrationPanel, setShowOrchestrationPanel] =
    React.useState(false);

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
    tasks,
    isTaskPanelOpen,
    toggleTaskPanel,
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
    isMobileMenuOpen,
    setIsMobileMenuOpen,
    feedbackPolarity,
    setFeedbackPolarity,
    feedbackModalIsOpen,
    setFeedbackModalIsOpen,
    messageToSend,
    setMessageToSend,
    lastUserMessage,
    setLastUserMessage,
    isInputFocused,
    setIsInputFocused,
    showOrchestrationPanel,
    setShowOrchestrationPanel,
    showTechnicalDetails,
    setShowTechnicalDetails,

    // Search and navigation
    isSearchOpen,
    setIsSearchOpen,
    bookmarksHook,

    // MetaSOP
    steps,
    isOrchestrating,
    hasSteps,

    // SOP support
    useSop,
    setUseSop,
    optimisticSopStarting,
    triggerOptimisticSop,

    // Messages
    optimisticUserMessage,
    errorMessage,

    // Optimistic message handlers
    setOptimisticUserMessage,
    getOptimisticUserMessage,
  };
}
