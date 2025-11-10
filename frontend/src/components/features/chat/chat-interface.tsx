import { useSelector } from "react-redux";
import React from "react";
import posthog from "posthog-js";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ChevronLeft } from "lucide-react";
import { convertImageToBase64 } from "#/utils/convert-image-to-base-64";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { AgentControlBar } from "#/components/features/controls/agent-control-bar";
import { AgentStatusBar } from "#/components/features/controls/agent-status-bar";
import { createChatMessage } from "#/services/chat-service";
import { InteractiveChatBox } from "./interactive-chat-box";
import { RootState } from "#/store";
import { AgentState } from "#/types/agent-state";
import { isForgeAction, isTaskTrackingObservation } from "#/types/core/guards";
import { generateAgentStateChangeEvent } from "#/services/agent-state-service";
import { FeedbackModal } from "../feedback/feedback-modal";
import { shouldRenderEvent } from "#/utils/should-render-event";
import { ErrorMessageBanner } from "./error-message-banner";
import { useScrollToBottom } from "#/hooks/use-scroll-to-bottom";
import { useWsClient } from "#/context/ws-client-provider";
import { useWSErrorMessage } from "#/hooks/use-ws-error-message";
import { useOptimisticUserMessage } from "#/hooks/use-optimistic-user-message";
import { Messages } from "./messages";
// ChatSuggestions removed (onboarding suggestions) per request
import { ActionSuggestions } from "./action-suggestions";
import { SmartSuggestions } from "./smart-suggestions";
// Beta launch: Keyboard shortcuts disabled
// import { KeyboardShortcutsPanel, useKeyboardShortcuts } from "./keyboard-shortcuts-panel";
import { EmptyState } from "./empty-state";
import { MessageSkeleton } from "./message-skeleton";
import {
  ConversationSearch,
  useConversationSearch,
} from "./conversation-search";
// Beta launch: Bookmarks disabled
// import { ConversationBookmarks, useConversationBookmarks } from "./conversation-bookmarks";
import { ScrollProvider } from "#/context/scroll-context";
// Beta launch: Removed fragile message pattern matching auto-navigation
// Robust auto-navigation now happens via:
// 1. Automatic server detection in terminal output (server_detector.py)
// 2. Playwright URL sync when agent navigates
// 3. Server-ready events from backend
// Beta launch: Orchestration disabled
// import { OrchestrationDiagramPanel } from "../orchestration/orchestration-diagram-panel";
import { useMetaSOPOrchestration } from "#/hooks/use-metasop-orchestration";

import { ScrollToBottomButton } from "#/components/shared/buttons/scroll-to-bottom-button";
import { useUploadFiles } from "#/hooks/mutation/use-upload-files";
import { useConfig } from "#/hooks/query/use-config";
import { validateFiles } from "#/utils/file-validation";
import { useActiveConversation } from "#/hooks/query/use-active-conversation";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { TaskPanel } from "../task-panel/task-panel";
import { useTasks } from "#/context/task-context";
import { StatusIndicator } from "./status-indicator";

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

export function ChatInterface() {
  useActiveConversation();
  const { getErrorMessage } = useWSErrorMessage();
  const { send, isLoadingMessages, parsedEvents } = useWsClient();
  const { setOptimisticUserMessage, getOptimisticUserMessage } =
    useOptimisticUserMessage();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = useParams();
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const { tasks, isTaskPanelOpen, toggleTaskPanel } = useTasks();
  const { mutateAsync: uploadFiles } = useUploadFiles();

  // Auto-navigation now handled via:
  // 1. Server detection in terminal (automatic)
  // 2. Playwright URL sync (via BrowserObservation.url)
  // 3. Server-ready events (ws-client-provider.tsx)
  // No fragile message pattern matching needed!

  const {
    scrollDomToBottom,
    onChatBodyScroll,
    hitBottom,
    autoScroll,
    setAutoScroll,
    setHitBottom,
  } = useScrollToBottom(scrollRef);
  const { data: config } = useConfig();

  const { curAgentState } = useSelector((state: RootState) => state.agent);
  const { selectedRepository, replayJson } = useSelector(
    (state: RootState) => state.initialQuery,
  );
  const events = parsedEvents;

  const [feedbackPolarity, setFeedbackPolarity] = React.useState<
    "positive" | "negative"
  >("positive");
  const [feedbackModalIsOpen, setFeedbackModalIsOpen] = React.useState(false);
  // Advanced features disabled for beta launch

  const [isInputFocused, setIsInputFocused] = React.useState(false);
  const { isOpen: isSearchOpen, setIsOpen: setIsSearchOpen } =
    useConversationSearch();

  useSearchShortcut(isInputFocused, isSearchOpen, setIsSearchOpen);

  const [useSop, setUseSop] = useSopPreference();

  const { steps, isOrchestrating, hasSteps } = useMetaSOPOrchestration();
  const { optimisticSopStarting, triggerOptimisticSop } =
    useOptimisticSopIndicator(isOrchestrating);

  // State for optimistic SOP with setter for compatibility
  const [_optimisticSopStarting, setOptimisticSopStarting] = React.useState(
    optimisticSopStarting,
  );
  React.useEffect(() => {
    setOptimisticSopStarting(optimisticSopStarting);
  }, [optimisticSopStarting]);

  const messaging = useChatMessaging({
    events,
    selectedRepository,
    replayJson,
    send,
    conversationId: params.conversationId ?? undefined,
    uploadFiles,
    t,
    setOptimisticUserMessage: (msg: string | null) => {
      if (msg) setOptimisticUserMessage(msg);
    },
    triggerOptimisticSop,
    useSop,
  });

  const {
    messageToSend,
    setMessageToSend,
    lastUserMessage,
    handleSendMessage,
    handleAskAboutCode,
    handleRunCode,
  } = messaging;

  // Orchestration panel disabled for beta
  const showOrchestrationPanel = false;
  // const [showOrchestrationPanel, setShowOrchestrationPanel] = React.useState(false);

  // Technical details hardcoded to false for beta launch
  // Post-beta: Re-enable with proper UI controls (not console-accessible)
  const showTechnicalDetails = false;

  // Optimistic MetaSOP indicator: show immediately after sending sop: message
  const optimisticTimerRef = React.useRef<number | null>(null);

  // If backend confirms orchestration started, drop the optimistic flag early
  React.useEffect(() => {
    if (isOrchestrating && optimisticSopStarting) {
      setOptimisticSopStarting(false);
      if (optimisticTimerRef.current) {
        window.clearTimeout(optimisticTimerRef.current);
        optimisticTimerRef.current = null;
      }
    }
  }, [isOrchestrating, optimisticSopStarting]);

  // Streaming state
  const [isStreamingEnabled, setIsStreamingEnabled] = React.useState(true);
  const [streamingSpeed, setStreamingSpeed] = React.useState(2);
  const [streamingDelay, setStreamingDelay] = React.useState(100);

  // Global keyboard shortcuts disabled for beta
  // useKeyboardShortcuts(() => setShowShortcutsPanel(true), isInputFocused);

  // SOP toggle state with persistence
  React.useEffect(() => {
    try {
      localStorage.setItem("Forge.useSop", useSop ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [useSop]);

  const optimisticUserMessage = getOptimisticUserMessage() ?? null;
  const errorMessage = getErrorMessage() ?? null;

  // Filter events based on shouldRenderEvent and showTechnicalDetails
  const filteredEvents = React.useMemo(() => {
    const baseFiltered = parsedEvents.filter((event) =>
      shouldRenderEvent(event, showTechnicalDetails),
    );

    // If showing all technical details, return everything
    if (showTechnicalDetails) {
      return baseFiltered;
    }

    // Otherwise, apply additional filtering (this logic should match EventMessage's filtering)
    // We keep the filtering in EventMessage for now to avoid duplication
    // The EventMessage component will return null for filtered events
    return baseFiltered;
  }, [parsedEvents, showTechnicalDetails]);

  // Check if there are any substantive agent actions (not just system messages)
  const hasSubstantiveAgentActions = React.useMemo(
    () =>
      parsedEvents.some(
        (event) =>
          isForgeAction(event) &&
          event.source === "agent" &&
          event.action !== "system",
      ),
    [parsedEvents],
  );

  const handleStop = () => {
    posthog.capture("stop_button_clicked");
    send(generateAgentStateChangeEvent(AgentState.STOPPED));
  };

  const isWaitingForUserInput =
    curAgentState === AgentState.AWAITING_USER_INPUT ||
    curAgentState === AgentState.FINISHED;

  // Create a ScrollProvider with the scroll hook values
  const scrollProviderValue = {
    scrollRef,
    autoScroll,
    setAutoScroll,
    scrollDomToBottom,
    hitBottom,
    setHitBottom,
    onChatBodyScroll,
  };

  const lastEvent =
    parsedEvents.length > 0 ? parsedEvents[parsedEvents.length - 1] : null;

  const taskCount = isTaskTrackingObservation(lastEvent)
    ? (lastEvent.extras?.task_list?.length ?? 0)
    : 0;

  return (
    <ScrollProvider value={scrollProviderValue}>
      <div className="h-full flex relative overflow-hidden bg-black">
        <ChatMainColumn
          navigate={navigate}
          hitBottom={hitBottom}
          scrollDomToBottom={scrollDomToBottom}
          tasks={tasks}
          isTaskPanelOpen={isTaskPanelOpen}
          toggleTaskPanel={toggleTaskPanel}
          scrollRef={scrollRef}
          onChatBodyScroll={onChatBodyScroll}
          isLoadingMessages={isLoadingMessages}
          events={events}
          handleSendMessage={handleSendMessage}
          handleStop={handleStop}
          messageToSend={messageToSend}
          setMessageToSend={setMessageToSend}
          curAgentState={curAgentState}
          showTechnicalDetails={showTechnicalDetails}
          handleAskAboutCode={handleAskAboutCode}
          handleRunCode={handleRunCode}
          isWaitingForUserInput={isWaitingForUserInput}
          hasSubstantiveAgentActions={hasSubstantiveAgentActions}
          optimisticUserMessage={optimisticUserMessage}
          useSop={useSop}
          setUseSop={setUseSop}
          optimisticSopStarting={optimisticSopStarting}
          isOrchestrating={isOrchestrating}
          errorMessage={errorMessage}
          parsedEvents={parsedEvents}
          lastEvent={lastEvent}
          lastUserMessage={lastUserMessage}
          taskCount={taskCount}
        />
      </div>

      {config?.APP_MODE !== "saas" && (
        <div className="animate-scale-in">
          <FeedbackModal
            isOpen={feedbackModalIsOpen}
            onClose={() => setFeedbackModalIsOpen(false)}
            polarity={feedbackPolarity}
          />
        </div>
      )}

      <ConversationSearch
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        messages={filteredEvents}
        onSelectMessage={(index) => {
          console.log("Navigate to message:", index);
        }}
      />
    </ScrollProvider>
  );
}

function useSearchShortcut(
  isInputFocused: boolean,
  isSearchOpen: boolean,
  setIsSearchOpen: (open: boolean) => void,
) {
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && isSearchOpen) {
        event.preventDefault();
        setIsSearchOpen(false);
        return;
      }

      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setIsSearchOpen(true);
      }
    };

    if (!isInputFocused) {
      window.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isInputFocused, isSearchOpen, setIsSearchOpen]);
}

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

const MESSAGE_EMPTY_ERROR = "Please enter a message before sending.";
const CONVERSATION_NOT_READY_ERROR =
  "Conversation is not ready yet. Please try again.";
const SOP_EMPTY_ERROR =
  "Please provide details with SOP enabled (message cannot be empty).";

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

const uploadAttachments = async ({
  conversationId,
  files,
  uploadFiles,
}: {
  conversationId: string;
  files: File[];
  uploadFiles: ReturnType<typeof useUploadFiles>["mutateAsync"];
}) => {
  if (files.length === 0) {
    return { skippedFiles: [], uploadedFiles: [] as string[] };
  }

  return uploadFiles({ conversationId, files });
};

const reportSkippedFiles = (skippedFiles: Array<{ reason?: string }>) => {
  skippedFiles.forEach((file) => {
    if (file.reason) {
      displayErrorToast(file.reason);
    }
  });
};

const buildPromptWithFiles = ({
  content,
  uploadedFiles,
  isSopMessage,
  t,
}: {
  content: string;
  uploadedFiles: string[];
  isSopMessage: boolean;
  t: ReturnType<typeof useTranslation>["t"];
}) => {
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
};

function useChatMessaging({
  events,
  selectedRepository,
  replayJson,
  send,
  conversationId,
  uploadFiles,
  t,
  setOptimisticUserMessage,
  triggerOptimisticSop,
  useSop,
}: {
  events: unknown[];
  selectedRepository: RootState["initialQuery"]["selectedRepository"];
  replayJson: RootState["initialQuery"]["replayJson"];
  send: ReturnType<typeof useWsClient>["send"];
  conversationId: string | undefined;
  uploadFiles: ReturnType<typeof useUploadFiles>["mutateAsync"];
  t: ReturnType<typeof useTranslation>["t"];
  setOptimisticUserMessage: (message: string | null) => void;
  triggerOptimisticSop: () => void;
  useSop: boolean;
}) {
  const [messageToSend, setMessageToSend] = React.useState<string | null>(null);
  const [lastUserMessage, setLastUserMessage] = React.useState<string | null>(
    null,
  );

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
      const allFiles = [...images, ...files];
      const validation = validateFiles(allFiles);

      if (!validation.isValid) {
        displayErrorToast(`Error: ${validation.errorMessage}`);
        return;
      }

      const imageUrls = await Promise.all(
        images.map((image) => convertImageToBase64(image)),
      );
      const timestamp = new Date().toISOString();
      const uploadResult = await uploadAttachments({
        conversationId: conversationId!,
        files,
        uploadFiles,
      });
      const skippedFiles =
        (uploadResult as any).skippedFiles ||
        (uploadResult as any).skipped_files ||
        [];
      const uploadedFiles =
        (uploadResult as any).uploadedFiles ||
        (uploadResult as any).uploaded_files ||
        [];

      reportSkippedFiles(skippedFiles);

      const prompt = buildPromptWithFiles({
        content: messageContent,
        uploadedFiles: uploadedFiles as string[],
        isSopMessage: useSop,
        t,
      });

      if (!prompt) {
        return;
      }

      send(createChatMessage(prompt, imageUrls, uploadedFiles, timestamp));
      setOptimisticUserMessage(messageContent);
      setMessageToSend(null);

      if (useSop) {
        try {
          displayErrorToast("Starting SOP...");
        } catch {
          /* ignore toast errors */
        }
        triggerOptimisticSop();
      }
    },
    [
      conversationId,
      events,
      replayJson,
      selectedRepository,
      send,
      setOptimisticUserMessage,
      t,
      triggerOptimisticSop,
      uploadFiles,
      useSop,
    ],
  );

  const handleAskAboutCode = React.useCallback((code: string) => {
    const question = `Can you explain this code?\n\n\`\`\`\n${code}\n\`\`\``;
    setMessageToSend(question);
  }, []);

  const handleRunCode = React.useCallback(
    (code: string, language: string) => {
      const message = `Please run this ${language} code:\n\n\`\`\`${language}\n${code}\n\`\`\``;
      handleSendMessage(message, [], []);
    },
    [handleSendMessage],
  );

  return {
    messageToSend,
    setMessageToSend,
    lastUserMessage,
    handleSendMessage,
    handleAskAboutCode,
    handleRunCode,
  } as const;
}

function ChatMainColumn({
  navigate,
  hitBottom,
  scrollDomToBottom,
  tasks,
  isTaskPanelOpen,
  toggleTaskPanel,
  scrollRef,
  onChatBodyScroll,
  isLoadingMessages,
  events,
  handleSendMessage,
  handleStop,
  messageToSend,
  setMessageToSend,
  curAgentState,
  showTechnicalDetails,
  handleAskAboutCode,
  handleRunCode,
  isWaitingForUserInput,
  hasSubstantiveAgentActions,
  optimisticUserMessage,
  useSop,
  setUseSop,
  optimisticSopStarting,
  isOrchestrating,
  errorMessage,
  parsedEvents,
  lastEvent,
  lastUserMessage,
  taskCount,
}: {
  navigate: ReturnType<typeof useNavigate>;
  hitBottom: boolean;
  scrollDomToBottom: () => void;
  tasks: ReturnType<typeof useTasks>["tasks"];
  isTaskPanelOpen: boolean;
  toggleTaskPanel: () => void;
  scrollRef: React.RefObject<HTMLDivElement | null>;
  onChatBodyScroll: (element: HTMLDivElement) => void;
  isLoadingMessages: boolean;
  events: unknown[];
  handleSendMessage: (content: string, images: File[], files: File[]) => void;
  handleStop: () => void;
  messageToSend: string | null;
  setMessageToSend: React.Dispatch<React.SetStateAction<string | null>>;
  curAgentState: AgentState;
  showTechnicalDetails: boolean;
  handleAskAboutCode: (code: string) => void;
  handleRunCode: (code: string, language: string) => void;
  isWaitingForUserInput: boolean;
  hasSubstantiveAgentActions: boolean;
  optimisticUserMessage: string | null;
  useSop: boolean;
  setUseSop: (value: boolean) => void;
  optimisticSopStarting: boolean;
  isOrchestrating: boolean;
  errorMessage: string | null;
  parsedEvents: ReturnType<typeof useWsClient>["parsedEvents"];
  lastEvent: unknown;
  lastUserMessage: string | null;
  taskCount: number;
}) {
  return (
    <div className="flex flex-col bg-black relative overflow-hidden transition-all duration-300 w-full">
      <ChatHeader
        navigate={navigate}
        hitBottom={hitBottom}
        scrollDomToBottom={scrollDomToBottom}
      />

      <TaskPanel
        tasks={tasks}
        isOpen={isTaskPanelOpen}
        onToggle={toggleTaskPanel}
      />

      <ChatMessagesSection
        scrollRef={scrollRef}
        onChatBodyScroll={onChatBodyScroll}
        isLoadingMessages={isLoadingMessages}
        events={events}
        setMessageToSend={setMessageToSend}
        curAgentState={curAgentState}
        showTechnicalDetails={showTechnicalDetails}
        handleAskAboutCode={handleAskAboutCode}
        handleRunCode={handleRunCode}
        isWaitingForUserInput={isWaitingForUserInput}
        hasSubstantiveAgentActions={hasSubstantiveAgentActions}
        optimisticUserMessage={optimisticUserMessage}
        handleSendMessage={handleSendMessage}
      />

      <ChatControlsSection
        curAgentState={curAgentState}
        parsedEvents={parsedEvents}
        lastEvent={lastEvent}
        taskCount={taskCount}
        isOrchestrating={isOrchestrating}
        optimisticSopStarting={optimisticSopStarting}
        errorMessage={errorMessage}
        events={events}
        messageToSend={messageToSend}
        setMessageToSend={setMessageToSend}
        useSop={useSop}
        setUseSop={setUseSop}
        handleSendMessage={handleSendMessage}
        handleStop={handleStop}
        lastUserMessage={lastUserMessage}
      />
    </div>
  );
}

function ChatHeader({
  navigate,
  hitBottom,
  scrollDomToBottom,
}: {
  navigate: ReturnType<typeof useNavigate>;
  hitBottom: boolean;
  scrollDomToBottom: () => void;
}) {
  return (
    <div className="flex-shrink-0 relative">
      <div className="relative bg-black border-b border-violet-500/20">
        <div className="px-2 sm:px-3 md:px-4 lg:px-6 py-2 sm:py-3 md:py-4">
          <div className="flex items-center justify-between gap-1 sm:gap-2 min-w-0">
            <div className="flex items-center gap-1 sm:gap-2 min-w-0 flex-shrink-0">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="Go back to home"
                onClick={() => navigate("/")}
                className="h-8 w-8 p-1 rounded-lg hover:bg-violet-500/10 transition-all duration-200"
              >
                <ChevronLeft className="h-3.5 w-3.5 text-foreground-secondary" />
              </Button>

              <div className="min-w-0">
                <AgentControlBar />
              </div>
            </div>

            <div className="flex items-center justify-center min-w-0 flex-1 px-2">
              <div className="min-w-0 max-w-xs">
                <AgentStatusBar />
              </div>
            </div>

            <div className="flex items-center gap-1 sm:gap-1.5 flex-shrink-0">
              <div className="flex items-center gap-1" />
              <div
                className={cn(
                  "animate-scale-in transition-all duration-300 ml-1",
                  hitBottom ? "opacity-30 pointer-events-none" : "opacity-100",
                )}
              >
                <ScrollToBottomButton onClick={scrollDomToBottom} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatMessagesSection({
  scrollRef,
  onChatBodyScroll,
  isLoadingMessages,
  events,
  setMessageToSend,
  curAgentState,
  showTechnicalDetails,
  handleAskAboutCode,
  handleRunCode,
  isWaitingForUserInput,
  hasSubstantiveAgentActions,
  optimisticUserMessage,
  handleSendMessage,
}: {
  scrollRef: React.RefObject<HTMLDivElement | null>;
  onChatBodyScroll: (element: HTMLDivElement) => void;
  isLoadingMessages: boolean;
  events: unknown[];
  setMessageToSend: React.Dispatch<React.SetStateAction<string | null>>;
  curAgentState: AgentState;
  showTechnicalDetails: boolean;
  handleAskAboutCode: (code: string) => void;
  handleRunCode: (code: string, language: string) => void;
  isWaitingForUserInput: boolean;
  hasSubstantiveAgentActions: boolean;
  optimisticUserMessage: string | null;
  handleSendMessage: (content: string, images: File[], files: File[]) => void;
}) {
  return (
    <div
      ref={scrollRef}
      onScroll={(event) => onChatBodyScroll(event.currentTarget)}
      className="scrollbar-thin scrollbar-track-transparent scrollbar-thumb-violet-500/30 hover:scrollbar-thumb-violet-500/50 flex flex-col justify-start grow overflow-y-auto overflow-x-hidden px-2 sm:px-3 md:px-4 lg:px-6 py-3 sm:py-4 md:py-6 gap-3 sm:gap-4 fast-smooth-scroll relative bg-black"
    >
      {isLoadingMessages ? (
        <div className="relative z-10">
          <MessageSkeleton count={4} />
        </div>
      ) : (
        <div className="chat-messages-container space-y-2 relative z-10 flex flex-col items-start">
          {events.length === 0 ? (
            <div className="flex items-center justify-center min-h-[60vh] w-full">
              <EmptyState onSelectExample={setMessageToSend} />
            </div>
          ) : (
            <Messages
              messages={events as any}
              isAwaitingUserConfirmation={
                curAgentState === AgentState.AWAITING_USER_CONFIRMATION
              }
              showTechnicalDetails={showTechnicalDetails}
              onAskAboutCode={handleAskAboutCode}
              onRunCode={handleRunCode}
            />
          )}
        </div>
      )}

      {false &&
        isWaitingForUserInput &&
        hasSubstantiveAgentActions &&
        !optimisticUserMessage && (
          <div className="px-1 sm:px-2 py-3 sm:py-4">
            <div className="glass rounded-xl p-3 sm:p-4 border-grey-800/50 bg-gradient-to-br from-grey-950/60 to-grey-900/40 backdrop-blur-xl animate-slide-up">
              <ActionSuggestions
                onSuggestionsClick={(value) => handleSendMessage(value, [], [])}
              />
            </div>
          </div>
        )}
    </div>
  );
}

function ChatControlsSection({
  curAgentState,
  parsedEvents,
  lastEvent,
  taskCount,
  isOrchestrating,
  optimisticSopStarting,
  errorMessage,
  events,
  messageToSend,
  setMessageToSend,
  useSop,
  setUseSop,
  handleSendMessage,
  handleStop,
  lastUserMessage,
}: {
  curAgentState: AgentState;
  parsedEvents: ReturnType<typeof useWsClient>["parsedEvents"];
  lastEvent: unknown;
  taskCount: number;
  isOrchestrating: boolean;
  optimisticSopStarting: boolean;
  errorMessage: string | null;
  events: unknown[];
  messageToSend: string | null;
  setMessageToSend: React.Dispatch<React.SetStateAction<string | null>>;
  useSop: boolean;
  setUseSop: (value: boolean) => void;
  handleSendMessage: (content: string, images: File[], files: File[]) => void;
  handleStop: () => void;
  lastUserMessage: string | null;
}) {
  const showStatusIndicator = curAgentState === AgentState.RUNNING;
  const orchestrationMessage = getOrchestrationMessage({
    optimisticSopStarting,
    isOrchestrating,
  });
  const shouldShowSuggestions =
    events.length > 0 && !messageToSend && curAgentState === AgentState.INIT;
  const chatBoxMode = curAgentState === AgentState.RUNNING ? "stop" : "submit";
  const chatBoxDisabled =
    curAgentState === AgentState.LOADING ||
    curAgentState === AgentState.AWAITING_USER_CONFIRMATION;

  return (
    <div className="flex-shrink-0 relative">
      <div className="relative bg-transparent">
        <div className="px-2 sm:px-3 md:px-4 lg:px-6 py-2 space-y-2">
          <div className="flex items-center justify-center relative">
            <div className="absolute left-1/2 transform -translate-x-1/2">
              {showStatusIndicator && (
                <ChatStatusIndicator
                  parsedEvents={parsedEvents}
                  lastEvent={lastEvent}
                  taskCount={taskCount}
                />
              )}
            </div>
          </div>

          {orchestrationMessage}

          <ErrorBannerSection message={errorMessage} />

          {shouldShowSuggestions && (
            <SmartSuggestions
              onSelectSuggestion={setMessageToSend}
              context={{
                isEmpty: false,
              }}
              className="mb-4"
            />
          )}

          <InteractiveChatBox
            onSubmit={handleSendMessage}
            onStop={handleStop}
            isDisabled={chatBoxDisabled}
            mode={chatBoxMode}
            value={messageToSend ?? undefined}
            onChange={setMessageToSend}
            sopEnabled={useSop}
            onToggleSop={setUseSop}
            onEditLastMessage={() => lastUserMessage}
          />
        </div>
      </div>
    </div>
  );
}

function ErrorBannerSection({ message }: { message: string | null }) {
  if (!message) {
    return null;
  }

  return (
    <div className="animate-slide-down">
      <ErrorMessageBanner message={message} />
    </div>
  );
}

const getOrchestrationMessage = ({
  optimisticSopStarting,
  isOrchestrating,
}: {
  optimisticSopStarting: boolean;
  isOrchestrating: boolean;
}) => {
  if (!optimisticSopStarting && !isOrchestrating) {
    return null;
  }

  return (
    <div className="flex items-center justify-center mt-1">
      <div className="flex items-center gap-2 text-sm text-text-secondary">
        <LoadingSpinner size="small" />
        <span>
          {isOrchestrating
            ? "MetaSOP orchestration in progress"
            : "Starting MetaSOP…"}
        </span>
      </div>
    </div>
  );
};

function mapActionToStatusType(
  action: string,
):
  | "think"
  | "thinking"
  | "plan"
  | "run"
  | "write"
  | "edit"
  | "browse"
  | "read"
  | "message" {
  if (action === "write") return "write";
  if (action === "edit") return "edit";
  if (action === "run") return "run";
  if (action === "browse") return "browse";
  if (action === "read") return "read";
  if (action === "message") return "message";
  if (action === "task_tracking") return "plan";
  return "think";
}

function ChatStatusIndicator({
  parsedEvents,
  lastEvent,
  taskCount,
}: {
  parsedEvents: ReturnType<typeof useWsClient>["parsedEvents"];
  lastEvent: unknown;
  taskCount: number;
}) {
  if (parsedEvents.length === 0) {
    return <StatusIndicator type="think" />;
  }

  const latestEvent = parsedEvents[parsedEvents.length - 1];

  if (isTaskTrackingObservation(latestEvent)) {
    return (
      <StatusIndicator
        type="plan"
        message={`Agent updated the plan (${taskCount} tasks)`}
      />
    );
  }

  if (isForgeAction(latestEvent)) {
    return <StatusIndicator type={mapActionToStatusType(latestEvent.action)} />;
  }

  if (isForgeAction(lastEvent)) {
    return <StatusIndicator type={mapActionToStatusType(lastEvent.action)} />;
  }

  return <StatusIndicator type="think" />;
}
