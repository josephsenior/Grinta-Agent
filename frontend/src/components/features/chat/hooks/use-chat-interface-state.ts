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
import { useKeyboardShortcuts } from "./use-keyboard-shortcuts";
import { useMetaSOPOrchestration } from "#/hooks/use-metasop-orchestration";
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
  const { setOptimisticUserMessage, getOptimisticUserMessage } = useOptimisticUserMessage();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: config } = useConfig();
  const { mutateAsync: uploadFiles } = useUploadFiles();

  // State selectors
  const { curAgentState } = useSelector((state: RootState) => state.agent);
  const { tasks, isTaskPanelOpen, toggleTaskPanel } = useTasks();

  // Refs
  const scrollRef = React.useRef<HTMLDivElement>(null);

  // Custom hooks for specific functionality
  // Auto-navigation handled by server detection (automatic) + Playwright URL sync (robust)
  const { scrollDomToBottom, onChatBodyScroll, hitBottom, autoScroll, setAutoScroll, setHitBottom } = useScrollToBottom(scrollRef);
  const { isOpen: isSearchOpen, setIsOpen: setIsSearchOpen } = useConversationSearch();
  const bookmarksHook = useConversationBookmarks();
  const { steps, isOrchestrating, hasSteps } = useMetaSOPOrchestration();

  // Component state
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const [feedbackPolarity, setFeedbackPolarity] = React.useState<"positive" | "negative">("positive");
  const [feedbackModalIsOpen, setFeedbackModalIsOpen] = React.useState(false);
  const [messageToSend, setMessageToSend] = React.useState<string | null>(null);
  const [lastUserMessage, setLastUserMessage] = React.useState<string | null>(null);
  const [showShortcutsPanel, setShowShortcutsPanel] = React.useState(false);
  const [isInputFocused, setIsInputFocused] = React.useState(false);
  const [showOrchestrationPanel, setShowOrchestrationPanel] = React.useState(false);

  // Technical details toggle with localStorage persistence
  const [showTechnicalDetails, setShowTechnicalDetails] = React.useState<boolean>(() => {
    try {
      return localStorage.getItem("openhands.showTechnicalDetails") === "true";
    } catch {
      return false;
    }
  });

  React.useEffect(() => {
    try {
      localStorage.setItem("openhands.showTechnicalDetails", showTechnicalDetails ? "true" : "false");
    } catch {
      /* ignore */
    }
  }, [showTechnicalDetails]);

  // Optimistic user message
  const optimisticUserMessage = getOptimisticUserMessage();
  const errorMessage = getErrorMessage();

  // Derived state
  const isAwaitingUserConfirmation = curAgentState === AgentState.AWAITING_USER_CONFIRMATION;

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
    showShortcutsPanel,
    setShowShortcutsPanel,
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
    
    // Messages
    optimisticUserMessage,
    errorMessage,
    
    // Optimistic message handlers
    setOptimisticUserMessage,
    getOptimisticUserMessage,
  };
}
