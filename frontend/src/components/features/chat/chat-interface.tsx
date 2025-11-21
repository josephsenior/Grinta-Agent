import React, { useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { ChevronLeft, Menu, X, Search, Bookmark } from "lucide-react";
import { gsap } from "gsap";
import { InteractiveChatBox } from "./interactive-chat-box";
import { isForgeAction, isTaskTrackingObservation } from "#/types/core/guards";
import { FeedbackModal } from "../feedback/feedback-modal";
import { TrajectoryActions } from "../trajectory/trajectory-actions";
import { useConfig } from "#/hooks/query/use-config";
import { TypingIndicator } from "./typing-indicator";
import { Messages } from "./messages";
import { ActionSuggestions } from "./action-suggestions";
import { AgentState } from "#/types/agent-state";
import { SmartSuggestions } from "./smart-suggestions";
import { EmptyState } from "./empty-state";
import { MessageSkeleton } from "./message-skeleton";
import { ConversationSearch } from "./conversation-search";
import { ConversationBookmarks } from "./conversation-bookmarks";
import { MetaSOPOrchestrationPanel } from "./metasop/metasop-orchestration-panel";
import { OrchestrationSteps } from "./metasop/orchestration-steps";
import { ErrorMessageBanner } from "./error-message-banner";
import { Button } from "#/components/ui/button";
import { TaskPanel } from "../task-panel/task-panel";
import { StatusIndicator } from "./status-indicator";
import { AgentControlBar } from "#/components/features/controls/agent-control-bar";
import { AgentStatusBar } from "#/components/features/controls/agent-status-bar";
import { ScrollToBottomButton } from "#/components/shared/buttons/scroll-to-bottom-button";
import { RepositoryGuidesPanel } from "./repository-guides-panel";
import { ScrollProvider } from "#/context/scroll-context";
import { cn } from "#/utils/utils";
import { useGSAPFadeIn, useGSAPSlideIn } from "#/hooks/use-gsap-animations";

// Custom hooks
import { useChatInterfaceState } from "./hooks/use-chat-interface-state";
import { useChatKeyboardShortcuts } from "./hooks/use-chat-keyboard-shortcuts";
import { useChatMessageHandlers } from "./hooks/use-chat-message-handlers";
import { useChatFeedbackActions } from "./hooks/use-chat-feedback-actions";
import { useFilteredEvents } from "./utils/use-filtered-events";

type ChatEvent =
  ReturnType<typeof useFilteredEvents> extends Array<infer Item> ? Item : never;

interface ChatHeaderProps {
  onGoBack: () => void;
  onOpenSearch: () => void;
  onOpenBookmarks: () => void;
  isMobileMenuOpen: boolean;
  onToggleMobileMenu: () => void;
  onPositiveFeedback: () => void;
  onNegativeFeedback: () => void;
  onExportTrajectory: () => void;
  isSaasMode?: boolean;
  hitBottom?: boolean;
  scrollDomToBottom?: () => void;
}

type BookmarksHookState = ReturnType<
  typeof useChatKeyboardShortcuts
>["bookmarksHook"];

type FeedbackPolarity = ReturnType<
  typeof useChatFeedbackActions
>["feedbackPolarity"];

type StepsState = ReturnType<typeof useChatInterfaceState>["steps"];

interface ChatMessagesSectionProps {
  scrollRef: React.RefObject<HTMLDivElement | null>;
  onScroll: (element: HTMLElement) => void;
  events: ChatEvent[];
  isLoadingMessages: boolean;
  isAwaitingUserConfirmation: boolean;
  showTechnicalDetails: boolean;
  onAskAboutCode: (code: string) => void;
  onRunCode: (code: string, language: string) => void;
}

interface ChatSuggestionsSectionProps {
  lastEvent?: ChatEvent;
  onSelectSuggestion: (value: string) => void;
}

interface ChatInputSectionProps {
  curAgentState: AgentState;
  handleSendMessage: (message: string, files: File[], images: File[]) => void;
  handleStop: () => void;
  messageToSend: string | null;
  onChangeMessage: (value: string) => void;
  onFocus: () => void;
  onBlur: () => void;
  t: (key: string, options?: Record<string, unknown>) => string;
  useSop?: boolean;
  setUseSop?: (value: boolean) => void;
}

interface ChatOverlaysProps {
  events: ChatEvent[];
  isSearchOpen: boolean;
  closeSearch: () => void;
  bookmarksHook: BookmarksHookState;
  scrollDomToBottom: () => void;
  showOrchestrationPanel: boolean;
  closeOrchestrationPanel: () => void;
  feedbackModalIsOpen: boolean;
  closeFeedbackModal: () => void;
  feedbackPolarity: FeedbackPolarity;
  errorMessage: string | null;
  hasSteps: boolean;
  steps: StepsState;
}

function buildPlanUpdateMessage(event: ChatEvent): string {
  if (!isTaskTrackingObservation(event)) {
    return "Agent updated the plan (0 tasks)";
  }

  const tasks = Array.isArray(event.extras?.task_list)
    ? event.extras?.task_list.length
    : 0;

  return `Agent updated the plan (${tasks} tasks)`;
}

function ChatHeader({
  onGoBack,
  onOpenSearch,
  onOpenBookmarks,
  isMobileMenuOpen,
  onToggleMobileMenu,
  onPositiveFeedback,
  onNegativeFeedback,
  onExportTrajectory,
  isSaasMode = false,
  hitBottom = false,
  scrollDomToBottom,
}: ChatHeaderProps) {
  const { t } = useTranslation();
  const headerRef = useGSAPFadeIn<HTMLDivElement>({
    delay: 0.1,
    duration: 0.5,
  });

  return (
    <div ref={headerRef} className="flex-shrink-0 relative">
      {/* Background gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-primary-500/5 via-transparent to-accent-pink/5" />

      {/* Glass morphism header */}
      <div
        className="relative backdrop-blur-xl border-b"
        style={{
          backgroundColor: "var(--glass-bg)",
          borderColor: "var(--border-glass)",
        }}
      >
        <div className="px-2 sm:px-3 md:px-4 lg:px-6 py-2 sm:py-3 md:py-4">
          <div className="flex items-center justify-between gap-1 sm:gap-2 min-w-0">
            <div className="flex items-center gap-1 sm:gap-2 min-w-0 flex-shrink-0">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="Go back to home"
                onClick={onGoBack}
                className="h-8 w-8 p-1 rounded-lg hover:bg-violet-500/10 transition-all duration-200"
              >
                <ChevronLeft className="h-3.5 w-3.5 text-foreground-secondary" />
              </Button>

              <div className="min-w-0">
                <AgentControlBar />
              </div>

              <div className="hidden md:flex items-center gap-2 ml-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onOpenSearch}
                  className="flex items-center gap-2"
                >
                  <Search className="w-4 h-4" />
                  <kbd className="px-1.5 py-0.5 text-xs bg-background-secondary rounded">
                    {t("chat.shortcuts.search", "⌘K")}
                  </kbd>
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onOpenBookmarks}
                  className="flex items-center gap-2"
                >
                  <Bookmark className="w-4 h-4" />
                  <kbd className="px-1.5 py-0.5 text-xs bg-background-secondary rounded">
                    {t("chat.shortcuts.bookmarks", "⌘B")}
                  </kbd>
                </Button>
              </div>
            </div>

            <div className="flex items-center justify-center min-w-0 flex-1 px-2">
              <div className="min-w-0 max-w-xs">
                <AgentStatusBar />
              </div>
            </div>

            <div className="flex items-center gap-1 sm:gap-1.5 flex-shrink-0">
              {!isSaasMode && (
                <TrajectoryActions
                  onPositiveFeedback={onPositiveFeedback}
                  onNegativeFeedback={onNegativeFeedback}
                  onExportTrajectory={onExportTrajectory}
                  isSaasMode={isSaasMode}
                />
              )}
              {scrollDomToBottom && (
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
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={onToggleMobileMenu}
                className="md:hidden"
              >
                {isMobileMenuOpen ? (
                  <X className="w-4 h-4" />
                ) : (
                  <Menu className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatStatusBanner({
  lastEvent,
  optimisticSopStarting,
  isOrchestrating,
}: {
  lastEvent?: ChatEvent;
  optimisticSopStarting?: boolean;
  isOrchestrating?: boolean;
}) {
  const bannerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!bannerRef.current) return;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      gsap.set(bannerRef.current, { opacity: 1, y: 0 });
      return;
    }

    // Animate in when banner appears
    gsap.fromTo(
      bannerRef.current,
      { opacity: 0, y: -20 },
      { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" },
    );
  }, [lastEvent, optimisticSopStarting, isOrchestrating]);

  // Show SOP status indicators first (highest priority)
  if (isOrchestrating) {
    return (
      <div ref={bannerRef}>
        <StatusIndicator type="orchestrating" />
      </div>
    );
  }

  if (optimisticSopStarting) {
    return (
      <div ref={bannerRef}>
        <StatusIndicator type="sop" />
      </div>
    );
  }

  if (!lastEvent) {
    return null;
  }

  if (isTaskTrackingObservation(lastEvent)) {
    return (
      <div ref={bannerRef}>
        <StatusIndicator
          type="plan"
          message={buildPlanUpdateMessage(lastEvent)}
        />
      </div>
    );
  }

  if (isForgeAction(lastEvent)) {
    return (
      <div ref={bannerRef}>
        <TypingIndicator action={lastEvent.action} />
      </div>
    );
  }

  return null;
}

function ChatMessagesSection({
  scrollRef,
  onScroll,
  events,
  isLoadingMessages,
  isAwaitingUserConfirmation,
  showTechnicalDetails,
  onAskAboutCode,
  onRunCode,
}: ChatMessagesSectionProps) {
  return (
    <div
      ref={scrollRef as React.RefObject<HTMLDivElement>}
      className="flex-1 overflow-y-auto px-4 py-2 relative"
      onScroll={(event) => onScroll(event.currentTarget)}
    >
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-[0.02] pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_80%,_rgba(189,147,249,0.1)_0%,_transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,_rgba(139,233,253,0.05)_0%,_transparent_50%)]" />
      </div>

      <div className="relative z-10">
        {isLoadingMessages ? (
          <MessageSkeleton />
        ) : (
          <Messages
            messages={events}
            isAwaitingUserConfirmation={isAwaitingUserConfirmation}
            showTechnicalDetails={showTechnicalDetails}
            onAskAboutCode={onAskAboutCode}
            onRunCode={onRunCode}
          />
        )}
      </div>
    </div>
  );
}

function ChatSuggestionsSection({
  lastEvent,
  onSelectSuggestion,
}: ChatSuggestionsSectionProps) {
  const suggestionsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!suggestionsRef.current) return;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      gsap.set(suggestionsRef.current, { opacity: 1, y: 0 });
      return;
    }

    // Fade in and slide up when suggestions appear
    gsap.fromTo(
      suggestionsRef.current,
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, duration: 0.5, ease: "power2.out", delay: 0.1 },
    );
  }, [lastEvent]);

  return (
    <div ref={suggestionsRef} className="px-4 py-2">
      <ActionSuggestions onSuggestionsClick={onSelectSuggestion} />
      <SmartSuggestions
        lastEvent={lastEvent}
        onSelectSuggestion={onSelectSuggestion}
      />
    </div>
  );
}

function ChatInputSection({
  curAgentState,
  handleSendMessage,
  handleStop,
  messageToSend,
  onChangeMessage,
  onFocus,
  onBlur,
  t,
  useSop,
  setUseSop,
}: ChatInputSectionProps) {
  const inputRef = useGSAPSlideIn<HTMLDivElement>({
    direction: "up",
    distance: 30,
    duration: 0.5,
    delay: 0.2,
  });

  return (
    <div ref={inputRef} className="flex-shrink-0 relative">
      {/* Background gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-background-surface/80 via-background-DEFAULT/60 to-transparent" />

      {/* Glass morphism container */}
      <div
        className="relative backdrop-blur-xl border-t"
        style={{
          backgroundColor: "var(--glass-bg)",
          borderColor: "var(--border-glass)",
        }}
      >
        <InteractiveChatBox
          isDisabled={curAgentState === AgentState.LOADING}
          mode="submit"
          onSubmit={(message: string, images: File[], files: File[]) =>
            handleSendMessage(message, files ?? [], images ?? [])
          }
          onStop={handleStop}
          value={messageToSend ?? ""}
          onChange={onChangeMessage}
          placeholder={t("Type a message...")}
          onFocus={onFocus}
          onBlur={onBlur}
          sopEnabled={useSop}
          onToggleSop={setUseSop}
        />
      </div>
    </div>
  );
}

function ChatOverlays({
  events,
  isSearchOpen,
  closeSearch,
  bookmarksHook,
  scrollDomToBottom,
  showOrchestrationPanel,
  closeOrchestrationPanel,
  feedbackModalIsOpen,
  closeFeedbackModal,
  feedbackPolarity,
  errorMessage,
  hasSteps,
  steps,
}: ChatOverlaysProps) {
  return (
    <>
      {isSearchOpen && (
        <ConversationSearch
          isOpen={isSearchOpen}
          onClose={closeSearch}
          messages={events}
          onSelectMessage={() => {
            closeSearch();
            scrollDomToBottom();
          }}
        />
      )}
      {bookmarksHook.isOpen && (
        <ConversationBookmarks
          isOpen={bookmarksHook.isOpen}
          onClose={() => bookmarksHook.setIsOpen(false)}
          bookmarks={bookmarksHook.bookmarks}
          onSelectBookmark={() => {
            bookmarksHook.setIsOpen(false);
            scrollDomToBottom();
          }}
          onRemoveBookmark={(id: string) => bookmarksHook.removeBookmark(id)}
        />
      )}
      {showOrchestrationPanel && (
        <MetaSOPOrchestrationPanel
          isOpen={showOrchestrationPanel}
          onClose={closeOrchestrationPanel}
        />
      )}
      {feedbackModalIsOpen && (
        <FeedbackModal
          isOpen={feedbackModalIsOpen}
          onClose={closeFeedbackModal}
          polarity={feedbackPolarity}
        />
      )}
      {errorMessage && (
        <ErrorMessageBanner message={errorMessage ?? ""} onDismiss={() => {}} />
      )}{" "}
      {hasSteps && <OrchestrationSteps steps={steps} />}
    </>
  );
}

/**
 * Merged ChatInterface component combining the best of both implementations:
 * - Refactored architecture (custom hooks) for better separation of concerns
 * - All features from original: AgentControlBar, AgentStatusBar, RepositoryGuidesPanel, ScrollProvider, SOP support
 * - Enhanced features from refactored: TrajectoryActions, Keyboard shortcuts, Bookmarks, Smart suggestions
 */
export function ChatInterface() {
  const params = useParams<{ conversationId: string }>();

  // Main state management hook
  const {
    curAgentState,
    isAwaitingUserConfirmation,
    parsedEvents,
    isLoadingMessages,
    tasks,
    isTaskPanelOpen,
    toggleTaskPanel,
    t,
    send,
    uploadFiles,
    scrollRef,
    scrollDomToBottom,
    onChatBodyScroll,
    hitBottom,
    autoScroll,
    setAutoScroll,
    setHitBottom,
    isMobileMenuOpen,
    setIsMobileMenuOpen,
    messageToSend,
    setMessageToSend,
    setLastUserMessage,
    isInputFocused,
    setIsInputFocused,
    showOrchestrationPanel,
    setShowOrchestrationPanel,
    showTechnicalDetails,
    steps,
    hasSteps,
    errorMessage,
    setOptimisticUserMessage,
    selectedRepository,
    replayJson,
    useSop,
    setUseSop,
    triggerOptimisticSop,
    optimisticSopStarting,
    isOrchestrating,
  } = useChatInterfaceState();

  // Keyboard shortcuts hook
  const { isSearchOpen, setIsSearchOpen, bookmarksHook } =
    useChatKeyboardShortcuts(isInputFocused);

  // Message handling hooks
  const {
    handleSendMessage,
    handleStop,
    handleAskAboutCode,
    handleRunCode,
    handleGoBack,
  } = useChatMessageHandlers(
    send,
    setOptimisticUserMessage,
    setMessageToSend,
    setLastUserMessage,
    // Adapter: UI expects (variables: { conversationId: string; files: File[] }) => Promise<any>
    React.useCallback(
      async (variables: { conversationId: string; files: File[] }) =>
        // uploadFiles is mutateAsync from useUploadFiles()
        uploadFiles(variables),
      [uploadFiles, params?.conversationId],
    ),
    params?.conversationId,
    parsedEvents,
    selectedRepository,
    replayJson,
    useSop,
    triggerOptimisticSop,
  );

  // Feedback and actions hook
  const {
    feedbackPolarity,
    feedbackModalIsOpen,
    setFeedbackModalIsOpen,
    onClickShareFeedbackActionButton,
    onClickExportTrajectoryButton,
  } = useChatFeedbackActions();

  // Get config for SaaS mode check
  const { data: config } = useConfig();
  const isSaasMode = config?.APP_MODE === "saas";

  // Filtered events hook
  const events = useFilteredEvents(parsedEvents, showTechnicalDetails);
  const lastEvent = events[events.length - 1] as ChatEvent | undefined;

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

  if (events.length === 0) {
    return (
      <ScrollProvider value={scrollProviderValue}>
        <div className="h-full flex relative overflow-hidden bg-gradient-to-br from-background-surface via-background-DEFAULT to-background-elevated">
          <div className="flex flex-col relative overflow-hidden transition-all duration-300 w-full">
            <ChatHeader
              onGoBack={handleGoBack}
              onOpenSearch={() => setIsSearchOpen(true)}
              onOpenBookmarks={() => bookmarksHook.setIsOpen(true)}
              isMobileMenuOpen={isMobileMenuOpen}
              onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              onPositiveFeedback={() =>
                onClickShareFeedbackActionButton("positive")
              }
              onNegativeFeedback={() =>
                onClickShareFeedbackActionButton("negative")
              }
              onExportTrajectory={onClickExportTrajectoryButton}
              isSaasMode={isSaasMode}
              hitBottom={hitBottom}
              scrollDomToBottom={scrollDomToBottom}
            />

            {/* Background Pattern for empty state */}
            <div className="flex-1 min-h-0 relative">
              <div className="absolute inset-0 opacity-[0.02] pointer-events-none">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_80%,_rgba(189,147,249,0.1)_0%,_transparent_50%)]" />
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,_rgba(139,233,253,0.05)_0%,_transparent_50%)]" />
              </div>
              <div className="relative z-10 flex items-center justify-center min-h-[60vh]">
                <EmptyState onSelectExample={setMessageToSend} />
              </div>
            </div>

            <ChatInputSection
              curAgentState={curAgentState}
              handleSendMessage={handleSendMessage}
              handleStop={handleStop}
              messageToSend={messageToSend}
              onChangeMessage={setMessageToSend}
              onFocus={() => setIsInputFocused(true)}
              onBlur={() => setIsInputFocused(false)}
              t={t}
              useSop={useSop}
              setUseSop={setUseSop}
            />
          </div>
        </div>
      </ScrollProvider>
    );
  }

  return (
    <ScrollProvider value={scrollProviderValue}>
      <div className="h-full flex relative overflow-hidden bg-gradient-to-br from-background-surface via-background-DEFAULT to-background-elevated">
        <div className="flex flex-col relative overflow-hidden transition-all duration-300 w-full">
          <ChatHeader
            onGoBack={handleGoBack}
            onOpenSearch={() => setIsSearchOpen(true)}
            onOpenBookmarks={() => bookmarksHook.setIsOpen(true)}
            isMobileMenuOpen={isMobileMenuOpen}
            onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            onPositiveFeedback={() =>
              onClickShareFeedbackActionButton("positive")
            }
            onNegativeFeedback={() =>
              onClickShareFeedbackActionButton("negative")
            }
            onExportTrajectory={onClickExportTrajectoryButton}
            isSaasMode={isSaasMode}
            hitBottom={hitBottom}
            scrollDomToBottom={scrollDomToBottom}
          />

          <RepositoryGuidesPanel />

          <TaskPanel
            tasks={tasks}
            isOpen={isTaskPanelOpen}
            onToggle={toggleTaskPanel}
          />

          <div className="flex-1 flex flex-col min-h-0">
            <ChatStatusBanner
              lastEvent={lastEvent}
              optimisticSopStarting={optimisticSopStarting}
              isOrchestrating={isOrchestrating}
            />

            <ChatMessagesSection
              scrollRef={scrollRef}
              onScroll={onChatBodyScroll}
              events={events}
              isLoadingMessages={isLoadingMessages}
              isAwaitingUserConfirmation={isAwaitingUserConfirmation}
              showTechnicalDetails={showTechnicalDetails}
              onAskAboutCode={handleAskAboutCode}
              onRunCode={handleRunCode}
            />

            <ChatSuggestionsSection
              lastEvent={lastEvent}
              onSelectSuggestion={setMessageToSend}
            />

            <ChatInputSection
              curAgentState={curAgentState}
              handleSendMessage={handleSendMessage}
              handleStop={handleStop}
              messageToSend={messageToSend}
              onChangeMessage={setMessageToSend}
              onFocus={() => setIsInputFocused(true)}
              onBlur={() => setIsInputFocused(false)}
              t={t}
              useSop={useSop}
              setUseSop={setUseSop}
            />
          </div>

          <ChatOverlays
            events={events}
            isSearchOpen={isSearchOpen}
            closeSearch={() => setIsSearchOpen(false)}
            bookmarksHook={bookmarksHook}
            scrollDomToBottom={scrollDomToBottom}
            showOrchestrationPanel={showOrchestrationPanel}
            closeOrchestrationPanel={() => setShowOrchestrationPanel(false)}
            feedbackModalIsOpen={feedbackModalIsOpen}
            closeFeedbackModal={() => setFeedbackModalIsOpen(false)}
            feedbackPolarity={feedbackPolarity}
            errorMessage={errorMessage}
            hasSteps={hasSteps}
            steps={steps}
          />
        </div>
      </div>
    </ScrollProvider>
  );
}

export default ChatInterface;
