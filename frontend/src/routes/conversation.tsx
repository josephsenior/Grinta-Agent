import React, { Suspense } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";

import { useConversationId } from "#/hooks/use-conversation-id";
import { clearTerminal } from "#/state/command-slice";
import { useEffectOnce } from "#/hooks/use-effect-once";
import { clearJupyter } from "#/state/jupyter-slice";
import { useBatchFeedback } from "#/hooks/query/use-batch-feedback";
import { useConversationConfig } from "#/hooks/query/use-conversation-config";
import { useAutoNavigateToApp } from "#/hooks/use-auto-navigate-to-app";
import { TaskProvider } from "#/context/task-context";

import {
  Orientation,
  ResizablePanel,
} from "#/components/layout/resizable-panel";

import { useActiveConversation } from "#/hooks/query/use-active-conversation";
import { useSettings } from "#/hooks/query/use-settings";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { useDocumentTitleFromState } from "#/hooks/use-document-title-from-state";
import OpenHands from "#/api/open-hands";
import { useIsAuthed } from "#/hooks/query/use-is-authed";
import { ConversationSubscriptionsProvider } from "#/context/conversation-subscriptions-provider";
import { useUserProviders } from "#/hooks/use-user-providers";
import { ConversationTabs } from "#/components/features/conversation/conversation-tabs";

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
  const { data: isAuthed } = useIsAuthed();
  const { providers } = useUserProviders();

  // Fetch batch feedback data when conversation is loaded
  useBatchFeedback();
  
  // Auto-navigate to browser when servers start
  useAutoNavigateToApp();

  const dispatch = useDispatch();
  const navigate = useNavigate();

  // Linter: keep settings referenced in dev to avoid unused-var warnings
  React.useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      // Reference settings in dev builds to avoid unused variable warnings
      // and provide a tiny debug hook for manual inspection.
      // eslint-disable-next-line no-console
      console.debug("dev settings:", settings);
    }
  }, [settings]);

  // Set the document title to the conversation title when available
  useDocumentTitleFromState();

  const [width, setWidth] = React.useState(window.innerWidth);

  React.useEffect(() => {
    if (isFetched && !conversation && isAuthed) {
      displayErrorToast(
        "This conversation does not exist, or you do not have permission to access it.",
      );
      navigate("/");
    } else if (conversation?.status === "STOPPED") {
      // start the conversation if the state is stopped on initial load
      OpenHands.startConversation(conversation.conversation_id, providers).then(
        () => refetch(),
      );
    }
  }, [conversation?.conversation_id, isFetched, isAuthed, providers]);

  React.useEffect(() => {
    dispatch(clearTerminal());
    dispatch(clearJupyter());
  }, [conversationId]);

  useEffectOnce(() => {
    dispatch(clearTerminal());
    dispatch(clearJupyter());
  });

  function handleResize() {
    setWidth(window.innerWidth);
  }

  React.useEffect(() => {
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  function renderMain() {
    if (width <= 1024) {
      return (
        <div className="flex flex-col gap-3 w-full h-full min-h-0">
          <div className="rounded-xl overflow-hidden border border-border w-full bg-background-primary flex-1 min-h-0">
            <Suspense
              fallback={
                <div className="h-full bg-background-secondary animate-pulse rounded-lg" />
              }
            >
              <ChatInterface />
            </Suspense>
          </div>
          <div className="w-full flex-none min-h-0">
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
        firstClassName="overflow-hidden bg-background-primary min-h-0"
        secondClassName="flex flex-col overflow-hidden min-h-0"
        firstChild={
          <Suspense
            fallback={
              <div className="h-full bg-background-secondary animate-pulse rounded-lg" />
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
      fallback={<div className="h-full bg-background-secondary animate-pulse rounded-lg" />}
    >
      <TaskProvider>
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
                  className="flex flex-col h-full gap-3"
                >
                  <div className="flex h-full overflow-hidden min-h-0 max-h-full">
                    {renderMain()}
                  </div>

                  {/* Controls moved into ChatInterface header to preserve vertical space */}
                </div>
              </EventHandler>
            </Suspense>
          </ConversationSubscriptionsProvider>
        </WsClientProvider>
      </TaskProvider>
    </Suspense>
  );
}

function App() {
  return <AppContent />;
}

export default App;
