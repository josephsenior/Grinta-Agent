import React, { Suspense } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";

import { useConversationId } from "#/hooks/use-conversation-id";
import { clearTerminal } from "#/state/command-slice";
import { useEffectOnce } from "#/hooks/use-effect-once";
import { useConversationConfig } from "#/hooks/query/use-conversation-config";

import {
  Orientation,
  ResizablePanel,
} from "#/components/layout/resizable-panel";

import { useActiveConversation } from "#/hooks/query/use-active-conversation";
import { useSettings } from "#/hooks/query/use-settings";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { useDocumentTitleFromState } from "#/hooks/use-document-title-from-state";
import { useAutoNavigateToApp } from "#/hooks/use-auto-navigate-to-app";
import Forge from "#/api/forge";
import { ConversationSubscriptionsProvider } from "#/context/conversation-subscriptions-provider";
import { ConversationTabs } from "#/components/features/conversation/conversation-tabs";
import { logger } from "#/utils/logger";

// Lazy load heavy conversation components for better performance
const ChatInterface = React.lazy(() =>
  import("../components/features/chat/chat-interface").then((m) => ({
    default: m.ChatInterface,
  })),
);
const WsClientProvider = React.lazy(() =>
  import("#/context/ws-client-provider").then((m) => ({
    default: m.WsClientProvider,
  })),
);
const EventHandler = React.lazy(() =>
  import("../wrapper/event-handler").then((m) => ({ default: m.EventHandler })),
);

function AppContent() {
  useConversationConfig();
  const { data: settings } = useSettings();
  const { conversationId } = useConversationId();
  const { data: conversation, isFetched, refetch } = useActiveConversation();

  const dispatch = useDispatch();
  const navigate = useNavigate();

  const [isMobile, setIsMobile] = React.useState(
    typeof window !== "undefined" ? window.innerWidth < 768 : false,
  );

  // Linter: keep settings referenced in dev to avoid unused-var warnings
  React.useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      // Reference settings in dev builds to avoid unused variable warnings
      // and provide a tiny debug hook for manual inspection.
      logger.debug("dev settings:", settings);
    }
  }, [settings]);

  // Set the document title to the conversation title when available
  useDocumentTitleFromState();
  useAutoNavigateToApp();

  React.useEffect(() => {
    if (isFetched && !conversation) {
      displayErrorToast(
        "This conversation does not exist, or you do not have permission to access it.",
      );
      navigate("/conversations");
    } else if (conversation?.status === "STOPPED") {
      // start the conversation if the state is stopped on initial load
      Forge.startConversation(conversation.conversation_id)
        .then(() => refetch())
        .catch((err) => {
          logger.error("Failed to start conversation:", err);
          displayErrorToast(
            "Failed to start conversation. Please check your LLM settings and API key.",
          );
        });
    }
  }, [conversation?.conversation_id, isFetched]);

  React.useEffect(() => {
    dispatch(clearTerminal());
  }, [conversationId]);

  useEffectOnce(() => {
    dispatch(clearTerminal());
  });

  React.useEffect(() => {
    function handleResize() {
      setIsMobile(window.innerWidth < 768);
    }
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  function renderMain() {
    if (isMobile) {
      return (
        <div className="flex flex-col grow overflow-hidden h-full">
          <div className="flex-1 overflow-hidden">
            <Suspense
              fallback={
                <div className="h-full bg-[var(--bg-elevated)] animate-pulse" />
              }
            >
              <ChatInterface />
            </Suspense>
          </div>
          <div className="h-1/2 border-t border-[var(--border-primary)]">
            <ConversationTabs />
          </div>
        </div>
      );
    }

    return (
      <ResizablePanel
        orientation={Orientation.HORIZONTAL}
        className="grow h-full min-h-0 min-w-0"
        initialSize={450}
        firstClassName="overflow-hidden bg-[var(--bg-primary)] min-h-0 border-r border-[var(--border-primary)]"
        secondClassName="flex flex-col overflow-hidden min-h-0 bg-[var(--bg-primary)]"
        firstChild={
          <Suspense
            fallback={
              <div className="h-full bg-[var(--bg-elevated)] animate-pulse" />
            }
          >
            <ChatInterface />
          </Suspense>
        }
        secondChild={<ConversationTabs />}
      />
    );
  }

  return (
    <Suspense
      fallback={
        <div className="h-full bg-background-secondary animate-pulse rounded-lg" />
      }
    >
      <WsClientProvider conversationId={conversationId}>
        <ConversationSubscriptionsProvider>
          <Suspense
            fallback={
              <div className="h-full bg-background-secondary animate-pulse rounded-lg" />
            }
          >
            <EventHandler>
              <div
                data-testid="app-route"
                className="flex flex-col h-full w-full"
              >
                <div className="flex h-full overflow-hidden min-h-0 max-h-full">
                  {renderMain()}
                </div>
              </div>
            </EventHandler>
          </Suspense>
        </ConversationSubscriptionsProvider>
      </WsClientProvider>
    </Suspense>
  );
}

function App() {
  return <AppContent />;
}

export default App;
