import { useSelector } from "react-redux";
import React from "react";
import posthog from "posthog-js";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ChevronLeft, Menu, X, Search } from "lucide-react";
import { I18nKey } from "#/i18n/declaration";
import { convertImageToBase64 } from "#/utils/convert-image-to-base-64";
import { AgentControlBar } from "#/components/features/controls/agent-control-bar";
import { AgentStatusBar } from "#/components/features/controls/agent-status-bar";
import { createChatMessage } from "#/services/chat-service";
import { InteractiveChatBox } from "./interactive-chat-box";
import { RootState } from "#/store";
import { AgentState } from "#/types/agent-state";
import { isOpenHandsAction, isTaskTrackingObservation } from "#/types/core/guards";
import { generateAgentStateChangeEvent } from "#/services/agent-state-service";
import { FeedbackModal } from "../feedback/feedback-modal";
import { useScrollToBottom } from "#/hooks/use-scroll-to-bottom";
import { TypingIndicator } from "./typing-indicator";
import { useWsClient } from "#/context/ws-client-provider";
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
import { useGetTrajectory } from "#/hooks/mutation/use-get-trajectory";
import { downloadTrajectory } from "#/utils/download-trajectory";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { useOptimisticUserMessage } from "#/hooks/use-optimistic-user-message";
import { useWSErrorMessage } from "#/hooks/use-ws-error-message";
import { ErrorMessageBanner } from "./error-message-banner";
import { shouldRenderEvent } from "./event-content-helpers/should-render-event";
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
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const { tasks, isTaskPanelOpen, toggleTaskPanel } = useTasks();

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

  const [feedbackPolarity, setFeedbackPolarity] = React.useState<
    "positive" | "negative"
  >("positive");
  const [feedbackModalIsOpen, setFeedbackModalIsOpen] = React.useState(false);
  const [messageToSend, setMessageToSend] = React.useState<string | null>(null);
  const [lastUserMessage, setLastUserMessage] = React.useState<string | null>(
    null,
  );
  // Advanced features disabled for beta launch
  // const [showShortcutsPanel, setShowShortcutsPanel] = React.useState(false);
  const [isInputFocused, setIsInputFocused] = React.useState(false);
  const { isOpen: isSearchOpen, setIsOpen: setIsSearchOpen } =
    useConversationSearch();
  // const bookmarksHook = useConversationBookmarks();
  
  // Keyboard shortcuts disabled for beta
  // useKeyboardShortcuts(() => setShowShortcutsPanel(true), isInputFocused);

  // Beta launch: Only search keyboard shortcut enabled
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K for search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen(true);
      }
      
      // Escape to close search
      if (e.key === 'Escape') {
        if (isSearchOpen) setIsSearchOpen(false);
      }
    };

    if (!isInputFocused) {
      window.addEventListener('keydown', handleKeyDown);
    }
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isInputFocused, isSearchOpen]);
  // Orchestration panel disabled for beta
  const showOrchestrationPanel = false;
  // const [showOrchestrationPanel, setShowOrchestrationPanel] = React.useState(false);
  
  // Technical details hardcoded to false for beta launch
  // Post-beta: Re-enable with proper UI controls (not console-accessible)
  const showTechnicalDetails = false;

  // MetaSOP orchestration hook - always active to listen for events
  const { steps, isOrchestrating, hasSteps } = useMetaSOPOrchestration();

  // Optimistic MetaSOP indicator: show immediately after sending sop: message
  const [optimisticSopStarting, setOptimisticSopStarting] = React.useState(false);
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
  const [useSop, setUseSop] = React.useState<boolean>(() => {
    try {
      return localStorage.getItem("openhands.useSop") === "1";
    } catch {
      return false;
    }
  });

  React.useEffect(() => {
    try {
      localStorage.setItem("openhands.useSop", useSop ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [useSop]);

  const { selectedRepository, replayJson } = useSelector(
    (state: RootState) => state.initialQuery,
  );
  const params = useParams();
  const { mutate: getTrajectory } = useGetTrajectory();
  const { mutateAsync: uploadFiles } = useUploadFiles();

  const optimisticUserMessage = getOptimisticUserMessage();
  const errorMessage = getErrorMessage();

  // Filter events based on shouldRenderEvent and showTechnicalDetails
  const events = React.useMemo(() => {
    const baseFiltered = parsedEvents.filter(shouldRenderEvent);
    
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
          isOpenHandsAction(event) &&
          event.source === "agent" &&
          event.action !== "system",
      ),
    [parsedEvents],
  );

  const handleSendMessage = async (
    content: string,
    originalImages: File[],
    originalFiles: File[],
  ) => {
    // Prevent empty messages, which can cause backend 400s and block MetaSOP
    if (!content || content.trim().length === 0) {
      displayErrorToast("Please enter a message before sending.");
      return;
    }
    // Track last user message for quick edit feature (↑ key)
    setLastUserMessage(content);

    // Create mutable copies of the arrays
    const images = [...originalImages];
    const files = [...originalFiles];
    if (events.length === 0) {
      posthog.capture("initial_query_submitted", {
        entry_point: getEntryPoint(
          selectedRepository !== null,
          replayJson !== null,
        ),
        query_character_length: content.length,
        replay_json_size: replayJson?.length,
      });
    } else {
      posthog.capture("user_message_sent", {
        session_message_count: events.length,
        current_message_length: content.length,
      });
    }

    // Validate file sizes before any processing
    const allFiles = [...images, ...files];
    const validation = validateFiles(allFiles);

    if (!validation.isValid) {
      displayErrorToast(`Error: ${validation.errorMessage}`);
      return; // Stop processing if validation fails
    }

    const promises = images.map((image) => convertImageToBase64(image));
    const imageUrls = await Promise.all(promises);

    const timestamp = new Date().toISOString();

    const { skipped_files: skippedFiles, uploaded_files: uploadedFiles } =
      files.length > 0
        ? await uploadFiles({ conversationId: params.conversationId!, files })
        : { skipped_files: [], uploaded_files: [] };

    skippedFiles.forEach((f) => displayErrorToast(f.reason));

    // Prefix with sop: when SOP mode is enabled for MetaSOP orchestration
    const isSopMessage = useSop;
    if (isSopMessage && content.trim().length === 0) {
      displayErrorToast(
        "Please provide details with SOP enabled (message cannot be empty).",
      );
      return;
    }
    const contentToSend = isSopMessage ? `sop:${content}` : content;

    const filePrompt = `${t("CHAT_INTERFACE$AUGMENTED_PROMPT_FILES_TITLE")}: ${uploadedFiles.join("\n\n")}`;
    const prompt =
      uploadedFiles.length > 0
        ? `${contentToSend}\n\n${filePrompt}`
        : contentToSend;

    send(createChatMessage(prompt, imageUrls, uploadedFiles, timestamp));
    setOptimisticUserMessage(content);
    setMessageToSend(null);

    // Immediately reflect SOP starting state in UI
      if (isSopMessage) {
      // Notify user explicitly
      try {
          // Best-effort toast; ignore failures
          displayErrorToast("Starting SOP...");
      } catch {}
      try {
        // Prefer success/info style if available
        // eslint-disable-next-line @typescript-eslint/no-var-requires
      } catch {}
      // Use a minimal inline + header indicator regardless
      setOptimisticSopStarting(true);
      // Clear any previous timer
      if (optimisticTimerRef.current) {
        window.clearTimeout(optimisticTimerRef.current);
      }
      // Fallback timeout in case backend is slow to emit events
      optimisticTimerRef.current = window.setTimeout(() => {
        setOptimisticSopStarting(false);
        optimisticTimerRef.current = null;
      }, 8000);
    }
  };

  // Code action handlers for inline code blocks
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

  const handleStop = () => {
    posthog.capture("stop_button_clicked");
    send(generateAgentStateChangeEvent(AgentState.STOPPED));
  };

  const onClickShareFeedbackActionButton = async (
    polarity: "positive" | "negative",
  ) => {
    setFeedbackModalIsOpen(true);
    setFeedbackPolarity(polarity);
  };

  const onClickExportTrajectoryButton = () => {
    if (!params.conversationId) {
      displayErrorToast(t(I18nKey.CONVERSATION$DOWNLOAD_ERROR));
      return;
    }

    getTrajectory(params.conversationId, {
      onSuccess: async (data) => {
        await downloadTrajectory(
          params.conversationId ?? t(I18nKey.CONVERSATION$UNKNOWN),
          data.trajectory,
        );
      },
      onError: () => {
        displayErrorToast(t(I18nKey.CONVERSATION$DOWNLOAD_ERROR));
      },
    });
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

  const lastEvent = parsedEvents.length > 0 ? parsedEvents[parsedEvents.length - 1] : null;

  // Map OpenHands action strings to the StatusIndicator `type` union
  const mapActionToStatusType = (
    action: string | undefined,
  ): "think" | "thinking" | "plan" | "run" | "write" | "edit" | "browse" | "read" | "message" => {
    if (!action) return "think";
    switch (action) {
      case "task_tracking":
        return "plan";
      case "message":
        return "message";
      case "think":
      case "thinking":
        return "thinking";
      case "write":
      case "file_write":
        return "write";
      case "edit":
        return "edit";
      case "run":
      case "run_ipython":
        return "run";
      case "read":
      case "browse":
      case "browse_interactive":
        return "read";
      default:
        return "think";
    }
  };

  const taskCount = isTaskTrackingObservation(lastEvent)
    ? (lastEvent.extras?.task_list?.length ?? 0)
    : 0;

  return (
    <ScrollProvider value={scrollProviderValue}>
      <div className="h-full flex relative overflow-hidden bg-black">
        {/* Main Chat Column */}
        <div
          className={cn(
            "flex flex-col bg-black relative overflow-hidden transition-all duration-300",
            showOrchestrationPanel ? "flex-1 w-0" : "w-full",
          )}
        >
          {/* Pure black background */}

          {/* Responsive Chat Header */}
          <div className="flex-shrink-0 relative">
            {/* Glass morphism effect */}
            <div className="relative bg-black border-b border-violet-500/20">
              <div className="px-2 sm:px-3 md:px-4 lg:px-6 py-2 sm:py-3 md:py-4">
                {/* Responsive Header Layout */}
                <div className="flex items-center justify-between gap-1 sm:gap-2 min-w-0">
                  {/* Left Section - Navigation and Controls */}
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

                  {/* Center Section - Agent Status */}
                  <div className="flex items-center justify-center min-w-0 flex-1 px-2">
                    <div className="min-w-0 max-w-xs">
                      <AgentStatusBar />
                    </div>
                  </div>

                  {/* Right Section - Actions */}
                  <div className="flex items-center gap-1 sm:gap-1.5 flex-shrink-0">
                    {/* Mobile Menu Button */}
                    {/* Mobile menu button removed per user request */}

                    {/* Desktop Actions - Compact */}
                    <div className="flex items-center gap-1">
                      {/* TrajectoryActions removed per user request */}

                      {/* BETA UI SIMPLIFICATION: Hidden buttons for cleaner interface */}
                      {/* Search, Bookmarks, Technical Details, Keyboard Shortcuts, and Orchestration buttons */}
                      {/* These can still be accessed via keyboard shortcuts (Ctrl+K for search, etc.) */}
                      {/* Uncomment below to restore buttons for post-beta release */}
                      
                      {/* Search Button with Keyboard Shortcut Hint */}
                      {/* <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => setIsSearchOpen(true)}
                        className={cn(
                          "h-8 px-2 rounded-lg hover:bg-violet-500/10 transition-all duration-200",
                          "flex items-center gap-1.5"
                        )}
                        title="Search conversation (Ctrl+K)"
                      >
                        <Search className="h-3.5 w-3.5 text-foreground-secondary" />
                        <kbd className="hidden md:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] font-medium bg-background-tertiary/50 border border-border-subtle rounded">
                          <span className="text-text-tertiary">⌘</span>
                          <span className="text-text-secondary">K</span>
                        </kbd>
                      </Button> */}

                      {/* Bookmarks Button */}
                    </div>

                    {/* Scroll to Bottom Button */}
                    <div
                      className={cn(
                        "animate-scale-in transition-all duration-300 ml-1",
                        hitBottom
                          ? "opacity-30 pointer-events-none"
                          : "opacity-100",
                      )}
                    >
                      <ScrollToBottomButton onClick={scrollDomToBottom} />
                    </div>
                  </div>
                </div>

                {/* Mobile Menu Dropdown */}
                {isMobileMenuOpen && (
                  <div className="sm:hidden mt-3 pt-3 border-t border-border-glass animate-slide-down">
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-text-secondary">
                          Actions
                        </span>
                        <div className="flex items-center gap-2">
                          <ScrollToBottomButton onClick={scrollDomToBottom} />
                        </div>
                      </div>

                      {/* TrajectoryActions removed per user request */}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Task Panel Bar - Top of Conversation */}
          <TaskPanel
            tasks={tasks}
            isOpen={isTaskPanelOpen}
            onToggle={toggleTaskPanel}
          />

          {/* Responsive Messages Area */}
          <div
            ref={scrollRef}
            onScroll={(e) => onChatBodyScroll(e.currentTarget)}
            className="scrollbar-thin scrollbar-track-transparent scrollbar-thumb-violet-500/30 hover:scrollbar-thumb-violet-500/50 flex flex-col justify-start grow overflow-y-auto overflow-x-hidden px-2 sm:px-3 md:px-4 lg:px-6 py-3 sm:py-4 md:py-6 gap-3 sm:gap-4 fast-smooth-scroll relative bg-black"
          >
            {/* Pure black background */}

            {isLoadingMessages && (
              <div className="relative z-10">
                <MessageSkeleton count={4} />
              </div>
            )}

            {!isLoadingMessages && (
              <div className="chat-messages-container space-y-2 relative z-10 flex flex-col items-start">
                {events.length === 0 ? (
                  <div className="flex items-center justify-center min-h-[60vh] w-full">
                    <EmptyState onSelectExample={setMessageToSend} />
                  </div>
                ) : (
                  <Messages
                    messages={events}
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
                      onSuggestionsClick={(value) =>
                        handleSendMessage(value, [], [])
                      }
                    />
                  </div>
                </div>
              )}
          </div>

          {/* Responsive Chat Controls */}
          <div className="flex-shrink-0 relative">
            {/* Glass morphism container */}
            <div className="relative bg-transparent">
              <div className="px-2 sm:px-3 md:px-4 lg:px-6 py-2 space-y-2">
                {/* Typing Indicator (centered, action-aware) */}
                <div className="flex items-center justify-center relative">
                  <div className="absolute left-1/2 transform -translate-x-1/2">
                    {curAgentState === AgentState.RUNNING && (
                      <div className="animate-fade-in">
                        {/* Show consistent status indicator for all actions */}
                        {parsedEvents.length > 0 && isTaskTrackingObservation(parsedEvents[parsedEvents.length - 1]) ? (
                          <StatusIndicator
                            type="plan"
                            message={`Agent updated the plan (${taskCount} tasks)`}
                          />
                        ) : parsedEvents.length > 0 && isOpenHandsAction(parsedEvents[parsedEvents.length - 1]) ? (
                          // If the last event is an OpenHands action, narrow and map its action to a supported StatusIndicator type
                          ((): React.ReactElement | null => {
                            if (isOpenHandsAction(lastEvent)) {
                              return <StatusIndicator type={mapActionToStatusType(lastEvent.action)} />;
                            }
                            return null;
                          })()
                        ) : (
                          <StatusIndicator type="think" />
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {(optimisticSopStarting || isOrchestrating) && (
                  <div className="flex items-center justify-center mt-1">
                    <div className="flex items-center gap-2 text-sm text-text-secondary">
                      <LoadingSpinner size="small" />
                      <span>
                        {isOrchestrating ? "MetaSOP orchestration in progress" : "Starting MetaSOP…"}
                      </span>
                    </div>
                  </div>
                )}

                {/* Enhanced Error Banner */}
                {errorMessage && (
                  <div className="animate-slide-down">
                    <ErrorMessageBanner message={errorMessage} />
                  </div>
                )}

                {/* Smart Suggestions - Context-aware (hide if empty state shown) */}
                {events.length > 0 &&
                  !messageToSend &&
                  curAgentState === AgentState.INIT && (
                    <SmartSuggestions
                      onSelectSuggestion={setMessageToSend}
                      context={{
                        isEmpty: false,
                      }}
                      className="mb-4"
                    />
                  )}

                {/* Enhanced Chat Input */}
                <InteractiveChatBox
                  onSubmit={handleSendMessage}
                  onStop={handleStop}
                  isDisabled={
                    curAgentState === AgentState.LOADING ||
                    curAgentState === AgentState.AWAITING_USER_CONFIRMATION
                  }
                  mode={
                    curAgentState === AgentState.RUNNING ? "stop" : "submit"
                  }
                  value={messageToSend ?? undefined}
                  onChange={setMessageToSend}
                  sopEnabled={useSop}
                  onToggleSop={setUseSop}
                  onEditLastMessage={() => lastUserMessage}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Orchestration Diagram Panel - Disabled for beta launch */}
      </div>

      {/* Enhanced Feedback Modal */}
      {config?.APP_MODE !== "saas" && (
        <div className="animate-scale-in">
          <FeedbackModal
            isOpen={feedbackModalIsOpen}
            onClose={() => setFeedbackModalIsOpen(false)}
            polarity={feedbackPolarity}
          />
        </div>
      )}

      {/* Advanced features disabled for beta launch */}
      
      {/* Conversation Search - Keep this one, it's useful */}
      <ConversationSearch
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        messages={events}
        onSelectMessage={(index) => {
          console.log("Navigate to message:", index);
        }}
      />
    </ScrollProvider>
  );
}
