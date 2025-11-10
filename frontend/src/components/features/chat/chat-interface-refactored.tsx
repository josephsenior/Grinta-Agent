import React from "react";
import { useParams } from "react-router-dom";
import { ChevronLeft, Menu, X, Keyboard, Search, Bookmark } from "lucide-react";
import { InteractiveChatBox } from "./interactive-chat-box";
import { isForgeAction, isTaskTrackingObservation } from "#/types/core/guards";
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
import { TaskPanel } from "../task-panel/task-panel";
import { StatusIndicator } from "./status-indicator";

// Custom hooks
import { useChatInterfaceState } from "./hooks/use-chat-interface-state";
import { useChatKeyboardShortcuts } from "./hooks/use-chat-keyboard-shortcuts";
import { useChatMessageHandlers } from "./hooks/use-chat-message-handlers";
import { useChatFeedbackActions } from "./hooks/use-chat-feedback-actions";
import { useFilteredEvents } from "./utils/use-filtered-events";

type ChatEvent =
  ReturnType<typeof useFilteredEvents> extends Array<infer Item> ? Item : never;

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
    t,
    send,
    uploadFiles,
    scrollRef,
    scrollDomToBottom,
    onChatBodyScroll,
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
    steps,
    hasSteps,
    errorMessage,
    setOptimisticUserMessage,
  } = useChatInterfaceState();

  // Keyboard shortcuts hook
  const { isSearchOpen, setIsSearchOpen, bookmarksHook } =
    useChatKeyboardShortcuts(isInputFocused, setShowShortcutsPanel);

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
    params.conversationId,
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
  const lastEvent = events[events.length - 1] as ChatEvent | undefined;

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <EmptyState onSelectExample={setMessageToSend} />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-background-primary">
      <ChatHeader
        t={t}
        onGoBack={handleGoBack}
        onOpenSearch={() => setIsSearchOpen(true)}
        onOpenBookmarks={() => bookmarksHook.setIsOpen(true)}
        onOpenShortcuts={() => setShowShortcutsPanel(true)}
        isMobileMenuOpen={isMobileMenuOpen}
        onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
      />

      <TaskPanel
        tasks={tasks}
        isOpen={isTaskPanelOpen}
        onToggle={toggleTaskPanel}
      />

      <div className="flex-1 flex flex-col min-h-0">
        <ChatStatusBanner lastEvent={lastEvent} />

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
        />
      </div>

      <ChatOverlays
        events={events}
        showShortcutsPanel={showShortcutsPanel}
        closeShortcuts={() => setShowShortcutsPanel(false)}
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
  );
}

export default ChatInterfaceRefactored;

interface ChatHeaderProps {
  t: (key: string, options?: Record<string, unknown>) => string;
  onGoBack: () => void;
  onOpenSearch: () => void;
  onOpenBookmarks: () => void;
  onOpenShortcuts: () => void;
  isMobileMenuOpen: boolean;
  onToggleMobileMenu: () => void;
}

type BookmarksHookState = ReturnType<
  typeof useChatKeyboardShortcuts
>["bookmarksHook"];

type FeedbackPolarity = ReturnType<
  typeof useChatFeedbackActions
>["feedbackPolarity"];

type StepsState = ReturnType<typeof useChatInterfaceState>["steps"];

function ChatHeader({
  t,
  onGoBack,
  onOpenSearch,
  onOpenBookmarks,
  onOpenShortcuts,
  isMobileMenuOpen,
  onToggleMobileMenu,
}: ChatHeaderProps) {
  return (
    <div className="flex items-center justify-between p-4 border-b border-border">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={onGoBack}
          className="flex items-center gap-2"
        >
          <ChevronLeft className="w-4 h-4" />
          {t("Go back")}
        </Button>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onOpenSearch}
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
            onClick={onOpenBookmarks}
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
          onClick={onOpenShortcuts}
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
  );
}

function ChatStatusBanner({ lastEvent }: { lastEvent?: ChatEvent }) {
  if (!lastEvent) {
    return null;
  }

  if (isTaskTrackingObservation(lastEvent)) {
    return (
      <StatusIndicator
        type="plan"
        message={buildPlanUpdateMessage(lastEvent)}
      />
    );
  }

  if (isForgeAction(lastEvent)) {
    return <TypingIndicator action={lastEvent.action} />;
  }

  return null;
}

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
      className="flex-1 overflow-y-auto px-4 py-2"
      onScroll={(event) => onScroll(event.currentTarget)}
    >
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
  );
}

interface ChatSuggestionsSectionProps {
  lastEvent?: ChatEvent;
  onSelectSuggestion: (value: string) => void;
}

function ChatSuggestionsSection({
  lastEvent,
  onSelectSuggestion,
}: ChatSuggestionsSectionProps) {
  return (
    <div className="px-4 py-2">
      <ActionSuggestions onSuggestionsClick={onSelectSuggestion} />
      <SmartSuggestions
        lastEvent={lastEvent}
        onSelectSuggestion={onSelectSuggestion}
      />
    </div>
  );
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
}: ChatInputSectionProps) {
  return (
    <div className="border-t border-border bg-background-primary">
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
      />
    </div>
  );
}

interface ChatOverlaysProps {
  events: ChatEvent[];
  showShortcutsPanel: boolean;
  closeShortcuts: () => void;
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

function ChatOverlays({
  events,
  showShortcutsPanel,
  closeShortcuts,
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
      {showShortcutsPanel && (
        <KeyboardShortcutsPanel
          isOpen={showShortcutsPanel}
          onClose={closeShortcuts}
        />
      )}
      {isSearchOpen && (
        <ConversationSearch
          isOpen={isSearchOpen}
          onClose={closeSearch}
          messages={events}
          onSelectMessage={(_index: number) => {
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
          onSelectBookmark={(_messageIndex: number) => {
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

function buildPlanUpdateMessage(event: ChatEvent): string {
  if (!isTaskTrackingObservation(event)) {
    return "Agent updated the plan (0 tasks)";
  }

  const tasks = Array.isArray(event.extras?.task_list)
    ? event.extras?.task_list.length
    : 0;

  return `Agent updated the plan (${tasks} tasks)`;
}
