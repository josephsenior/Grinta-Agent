import React, { useRef, useEffect } from "react";
import { useParams } from "react-router-dom";
import { ChevronLeft, Search } from "lucide-react";
import { gsap } from "gsap";
import { InteractiveChatBox } from "./interactive-chat-box";
import { isForgeAction } from "#/types/core/guards";
import { TypingIndicator } from "./typing-indicator";
import { Messages } from "./messages";
import { AgentState } from "#/types/agent-state";
import { SmartSuggestions } from "./smart-suggestions";
import { EmptyState } from "./empty-state";
import { MessageSkeleton } from "./message-skeleton";
import { ConversationSearch } from "./conversation-search";
import { ErrorMessageBanner } from "./error-message-banner";
import { ConnectionStatusBanner } from "./connection-status-banner";
import { Button } from "#/components/ui/button";
import { StatusIndicator } from "./status-indicator";
import { AgentControlBar } from "#/components/features/controls/agent-control-bar";
import { AgentStatusBar } from "#/components/features/controls/agent-status-bar";
import { ScrollToBottomButton } from "#/components/shared/buttons/scroll-to-bottom-button";
import { ScrollProvider } from "#/context/scroll-context";
import { cn } from "#/utils/utils";
import { useGSAPFadeIn, useGSAPSlideIn } from "#/hooks/use-gsap-animations";

// Custom hooks
import { useChatInterfaceState } from "./hooks/use-chat-interface-state";
import { useWsStatus } from "#/context/ws-client-provider";
import { useChatKeyboardShortcuts } from "./hooks/use-chat-keyboard-shortcuts";
import { useChatMessageHandlers } from "./hooks/use-chat-message-handlers";
import { useFilteredEvents } from "./utils/use-filtered-events";

type ChatEvent =
  ReturnType<typeof useFilteredEvents> extends Array<infer Item> ? Item : never;

interface ChatHeaderProps {
  onGoBack: () => void;
  onOpenSearch: () => void;
  hitBottom?: boolean;
  scrollDomToBottom?: () => void;
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
}

interface ChatOverlaysProps {
  events: ChatEvent[];
  isSearchOpen: boolean;
  closeSearch: () => void;
  scrollDomToBottom: () => void;
  errorMessage: string | null;
}

function ChatHeader({
  onGoBack,
  onOpenSearch,
  hitBottom = false,
  scrollDomToBottom,
}: ChatHeaderProps) {
  const headerRef = useGSAPFadeIn<HTMLDivElement>({
    delay: 0.1,
    duration: 0.5,
  });

  return (
    <div
      ref={headerRef}
      className="shrink-0 relative bg-(--bg-primary) border-b border-(--border-primary)"
    >
      <div className="w-full max-w-full px-4 sm:px-6 py-3">
        <div className="flex items-center justify-between gap-2 min-w-0">
          <div className="flex items-center gap-2 min-w-0 shrink-0">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="Go back"
              onClick={onGoBack}
              className="h-8 w-8 p-1 hover:bg-(--bg-tertiary) text-(--text-secondary)"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>

            <div className="min-w-0">
              <AgentControlBar />
            </div>

            <div className="hidden md:flex items-center gap-1 ml-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={onOpenSearch}
                className="h-8 px-2 text-xs text-(--text-secondary) hover:bg-(--bg-tertiary) hover:text-(--text-primary)"
                title="Search (Ctrl+K)"
              >
                <Search className="w-3.5 h-3.5 mr-1.5" />
                <span className="hidden lg:inline">Search</span>
              </Button>
            </div>
          </div>

          <div className="flex items-center justify-center min-w-0 flex-1 px-2">
            <div className="min-w-0 max-w-xs">
              <AgentStatusBar />
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            {scrollDomToBottom && (
              <div
                className={cn(
                  "transition-all duration-300",
                  hitBottom ? "opacity-30 pointer-events-none" : "opacity-100",
                )}
              >
                <ScrollToBottomButton onClick={scrollDomToBottom} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatStatusBanner({
  lastEvent,
}: {
  lastEvent?: ChatEvent;
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
  }, [lastEvent]);

  if (!lastEvent) {
    return null;
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
      className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 relative bg-(--bg-primary)"
      onScroll={(event) => onScroll(event.currentTarget)}
    >
      <div className="w-full max-w-full">
        {isLoadingMessages ? (
          <MessageSkeleton />
        ) : (
          <Messages
            messages={events}
            isAwaitingUserConfirmation={isAwaitingUserConfirmation}
            showTechnicalDetails={showTechnicalDetails}
            onAskAboutCode={onAskAboutCode}
            onRunCode={onRunCode}
            scrollContainerRef={scrollRef}
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
    <div ref={suggestionsRef} className="px-4 sm:px-6 py-3">
      <div className="w-full max-w-full">
        <SmartSuggestions
          lastEvent={lastEvent}
          onSelectSuggestion={onSelectSuggestion}
        />
      </div>
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
}: ChatInputSectionProps) {
  const { webSocketStatus } = useWsStatus();
  const inputRef = useGSAPSlideIn<HTMLDivElement>({
    direction: "up",
    distance: 30,
    duration: 0.5,
    delay: 0.2,
  });

  // Allow input when connecting or disconnected so users can still interact
  // Only disable when agent is actively loading or running
  const isDisabled = 
    (curAgentState === AgentState.LOADING && webSocketStatus === "CONNECTED") ||
    curAgentState === AgentState.RUNNING;

  return (
    <div
      ref={inputRef}
      className="shrink-0 relative bg-(--bg-primary) border-t border-(--border-primary)"
    >
      <div className="w-full px-4 sm:px-6 py-4">
        <InteractiveChatBox
          isDisabled={isDisabled}
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
    </div>
  );
}

function ChatOverlays({
  events,
  isSearchOpen,
  closeSearch,
  scrollDomToBottom,
  errorMessage,
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
      {errorMessage && (
        <ErrorMessageBanner message={errorMessage ?? ""} onDismiss={() => {}} />
      )}
    </>
  );
}

/**
 * Merged ChatInterface component focusing on:
 * - Refactored architecture (custom hooks) for better separation of concerns
 * - Core features: Chat, Files, and Terminal
 * - Enhanced features: Keyboard shortcuts, Smart suggestions
 */
export function ChatInterface() {
  const params = useParams<{ conversationId: string }>();

  // Main state management hook
  const {
    curAgentState,
    isAwaitingUserConfirmation,
    parsedEvents,
    isLoadingMessages,
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
    messageToSend,
    setMessageToSend,
    setLastUserMessage,
    isInputFocused,
    setIsInputFocused,
    showTechnicalDetails,
    errorMessage,
    setOptimisticUserMessage,
    selectedRepository,
    replayJson,
  } = useChatInterfaceState();

  // Keyboard shortcuts hook
  const { isSearchOpen, setIsSearchOpen } =
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
  );

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
        <div className="h-full flex relative overflow-hidden bg-(--bg-primary)">
          <div className="flex flex-col relative overflow-hidden transition-all duration-300 w-full">
            <ChatHeader
              onGoBack={handleGoBack}
              onOpenSearch={() => setIsSearchOpen(true)}
              hitBottom={hitBottom}
              scrollDomToBottom={scrollDomToBottom}
            />

            {/* Background Pattern for empty state */}
            <div className="flex-1 min-h-0 relative">
              <div className="absolute inset-0 opacity-[0.02] pointer-events-none" />
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
            />
          </div>
        </div>
      </ScrollProvider>
    );
  }

  return (
    <ScrollProvider value={scrollProviderValue}>
      <div className="h-full flex relative overflow-hidden bg-(--bg-primary)">
        <div className="flex flex-col relative overflow-hidden transition-all duration-300 w-full">
          <ChatHeader
            onGoBack={handleGoBack}
            onOpenSearch={() => setIsSearchOpen(true)}
            hitBottom={hitBottom}
            scrollDomToBottom={scrollDomToBottom}
          />

          <ConnectionStatusBanner />

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
            isSearchOpen={isSearchOpen}
            closeSearch={() => setIsSearchOpen(false)}
            scrollDomToBottom={scrollDomToBottom}
            errorMessage={errorMessage}
          />
        </div>
      </div>
    </ScrollProvider>
  );
}

export default ChatInterface;
