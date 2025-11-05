import React from "react";
import posthog from "posthog-js";
import { useParams } from "react-router-dom";
import { ChevronLeft, Menu, X, Keyboard, Search, Bookmark } from "lucide-react";
import { TrajectoryActions } from "../trajectory/trajectory-actions";
import { AgentControlBar } from "#/components/features/controls/agent-control-bar";
import { AgentStatusBar } from "#/components/features/controls/agent-status-bar";
import { InteractiveChatBox } from "./interactive-chat-box";
import { isOpenHandsAction, isTaskTrackingObservation } from "#/types/core/guards";
import { FeedbackModal } from "../feedback/feedback-modal";
import { TypingIndicator } from "./typing-indicator";
import { Messages } from "./messages";
import { ActionSuggestions } from "./action-suggestions";
import { AgentState } from "#/types/agent-state";
import { SmartSuggestions } from "./smart-suggestions";
import { KeyboardShortcutsPanel } from "./keyboard-shortcuts-panel";
import { EmptyState } from "./empty-state";
import { MessageSkeleton } from "./message-skeleton";
import { ConversationSearch } from "./conversation-search";
import { ConversationBookmarks } from "./conversation-bookmarks";
import { MetaSOPOrchestrationPanel } from "./metasop/metasop-orchestration-panel";
import { OrchestrationSteps } from "./metasop/orchestration-steps";
import { ErrorMessageBanner } from "./error-message-banner";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { TaskPanel } from "../task-panel/task-panel";
import { StatusIndicator } from "./status-indicator";

// Custom hooks
import { useChatInterfaceState } from "./hooks/use-chat-interface-state";
import { useChatKeyboardShortcuts } from "./hooks/use-chat-keyboard-shortcuts";
import { useChatMessageHandlers } from "./hooks/use-chat-message-handlers";
import { useChatFeedbackActions } from "./hooks/use-chat-feedback-actions";
import { useFilteredEvents } from "./utils/use-filtered-events";

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

/**
 * Refactored ChatInterface component with improved separation of concerns
 * Uses custom hooks to manage complex state and side effects
 */
export function ChatInterfaceRefactored() {
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
    config,
    t,
    navigate,
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
    steps,
    isOrchestrating,
    hasSteps,
    optimisticUserMessage,
    errorMessage,
    setOptimisticUserMessage,
    getOptimisticUserMessage,
  } = useChatInterfaceState();

  // Keyboard shortcuts hook
  const { isSearchOpen, setIsSearchOpen, bookmarksHook } = useChatKeyboardShortcuts(
    isInputFocused,
    setShowShortcutsPanel
  );

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
    // Adapter: UI expects (files: File[]) => Promise<any>
    React.useCallback(
      async (files: File[]) => {
        if (!params?.conversationId) {
          return Promise.reject(new Error("missing conversationId"));
        }
        // uploadFiles is mutateAsync from useUploadFiles()
        return uploadFiles({ conversationId: params.conversationId, files });
      },
      [uploadFiles, params?.conversationId],
    ),
    params.conversationId
  );

  // Feedback and actions hook
  const {
    feedbackPolarity,
    setFeedbackPolarity,
    feedbackModalIsOpen,
    setFeedbackModalIsOpen,
    onClickShareFeedbackActionButton,
    onClickExportTrajectoryButton,
  } = useChatFeedbackActions();

  // Filtered events hook
  const events = useFilteredEvents(parsedEvents, showTechnicalDetails);

  // Entry point detection (use safe runtime checks instead of `any` casts)
  const hasRepo = !!(
    config && typeof config === "object" && "github_repo_url" in config && (config as Record<string, unknown>).github_repo_url
  );
  const hasReplay = !!(
    config && typeof config === "object" && "replay_json" in config && (config as Record<string, unknown>).replay_json
  );
  const entryPoint = getEntryPoint(hasRepo, hasReplay);

  // Render empty state if no events
  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <EmptyState onSelectExample={setMessageToSend} />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-background-primary">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleGoBack}
            className="flex items-center gap-2"
          >
            <ChevronLeft className="w-4 h-4" />
            {t("Go back")}
          </Button>
          
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsSearchOpen(true)}
              className="flex items-center gap-2"
            >
              <Search className="w-4 h-4" />
              <kbd className="px-1.5 py-0.5 text-xs bg-background-secondary rounded">
                ⌘K
              </kbd>
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => bookmarksHook.setIsOpen(true)}
              className="flex items-center gap-2"
            >
              <Bookmark className="w-4 h-4" />
              <kbd className="px-1.5 py-0.5 text-xs bg-background-secondary rounded">
                ⌘B
              </kbd>
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowShortcutsPanel(true)}
            className="flex items-center gap-2"
          >
            <Keyboard className="w-4 h-4" />
            <kbd className="px-1.5 py-0.5 text-xs bg-background-secondary rounded">
              ?
            </kbd>
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden"
          >
            {isMobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* Task Panel */}
      <TaskPanel
        tasks={tasks}
        isOpen={isTaskPanelOpen}
        onToggle={toggleTaskPanel}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Status Indicator */}
        {events.length > 0 && isTaskTrackingObservation(events[events.length - 1]) ? (
            <StatusIndicator
              type="plan"
              message={(() => {
                const e = events[events.length - 1];
                if (!e) return `Agent updated the plan (0 tasks)`;
                if (isTaskTrackingObservation(e)) {
                  const n = Array.isArray(e.extras?.task_list) ? e.extras!.task_list.length : 0;
                  return `Agent updated the plan (${n} tasks)`;
                }
                return `Agent updated the plan (0 tasks)`;
              })()}
            />
        ) : events.length > 0 && isOpenHandsAction(events[events.length - 1]) ? (
          // Narrow the event using the runtime guard so we can safely access `action`
          (() => {
            const last = events[events.length - 1];
            return isOpenHandsAction(last) ? (
              <TypingIndicator action={last.action} />
            ) : null;
          })()
        ) : null}

        {/* Messages Area */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 py-2"
          onScroll={(e) => onChatBodyScroll(e.currentTarget as HTMLElement)}
        >
          {isLoadingMessages ? (
            <MessageSkeleton />
          ) : (
            <Messages
              messages={events}
              isAwaitingUserConfirmation={isAwaitingUserConfirmation}
              showTechnicalDetails={showTechnicalDetails}
              onAskAboutCode={handleAskAboutCode}
              onRunCode={handleRunCode}
            />
          )}
        </div>

        {/* Suggestions */}
        <div className="px-4 py-2">
          <ActionSuggestions
            onSuggestionsClick={setMessageToSend}
          />
          <SmartSuggestions
            lastEvent={events[events.length - 1]}
            onSelectSuggestion={setMessageToSend}
          />
        </div>

        {/* Chat Input */}
        <div className="border-t border-border bg-background-primary">
          <InteractiveChatBox
            isDisabled={curAgentState === AgentState.LOADING}
            mode="submit"
            // InteractiveChatBox expects (message, images, files)
            // but our handler is (message, files, images) — adapt here
            onSubmit={(message: string, images: File[], files: File[]) =>
              handleSendMessage(message, files ?? [], images ?? [])
            }
            onStop={handleStop}
            value={messageToSend || ""}
            onChange={setMessageToSend}
            placeholder={t("Type a message...")}
            onFocus={() => setIsInputFocused(true)}
            onBlur={() => setIsInputFocused(false)}
          />
        </div>
      </div>

      {/* Modals and Panels */}
      {showShortcutsPanel && (
        <KeyboardShortcutsPanel
          isOpen={showShortcutsPanel}
          onClose={() => setShowShortcutsPanel(false)}
        />
      )}

      {isSearchOpen && (
        <ConversationSearch
          isOpen={isSearchOpen}
          onClose={() => setIsSearchOpen(false)}
          messages={events}
          onSelectMessage={(index: number) => {
            setIsSearchOpen(false);
            // Try to scroll to bottom for now; a future enhancement would
            // scroll to the exact message element.
            scrollDomToBottom();
          }}
        />
      )}

      {bookmarksHook.isOpen && (
        <ConversationBookmarks
          isOpen={bookmarksHook.isOpen}
          onClose={() => bookmarksHook.setIsOpen(false)}
          bookmarks={bookmarksHook.bookmarks}
          onSelectBookmark={(messageIndex: number) => {
            bookmarksHook.setIsOpen(false);
            // Jump to bottom for now; could scroll to messageIndex later
            scrollDomToBottom();
          }}
          onRemoveBookmark={(id: string) => bookmarksHook.removeBookmark(id)}
        />
      )}

      {showOrchestrationPanel && (
        <MetaSOPOrchestrationPanel
          isOpen={showOrchestrationPanel}
          onClose={() => setShowOrchestrationPanel(false)}
        />
      )}

      {feedbackModalIsOpen && (
        <FeedbackModal
          isOpen={feedbackModalIsOpen}
          onClose={() => setFeedbackModalIsOpen(false)}
          polarity={feedbackPolarity}
        />
      )}

      {/* Error Banner */}
      {errorMessage && (
        <ErrorMessageBanner
          message={errorMessage}
          onDismiss={() => {}}
        />
      )}

      {/* MetaSOP Steps */}
      {hasSteps && (
        <OrchestrationSteps
          steps={steps}
        />
      )}
    </div>
  );
}
