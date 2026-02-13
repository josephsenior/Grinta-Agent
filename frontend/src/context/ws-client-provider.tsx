/**
 * Canonical WebSocket provider — the single owner of the Socket.IO
 * connection, event stream, and parsed events for a conversation.
 *
 * All components that need real-time data should consume either
 * `useWsStatus()` (connection state) or `useWsEvents()` (event list).
 *
 * NOTE: conversation-subscriptions-provider.tsx is deprecated and
 * should be removed once integration tests confirm no side-effects.
 */
import React, { startTransition } from "react";
import { io, Socket } from "socket.io-client";
import { useQueryClient } from "@tanstack/react-query";
import EventLogger from "#/utils/event-logger";
import { handleAssistantMessage } from "#/services/actions";
import { showChatError, trackError } from "#/utils/error-handler";
import { useRate } from "#/hooks/use-rate";
import { ForgeParsedEvent } from "#/types/core";
import { ForgeAction } from "#/types/core/actions";
import { useUserProviders } from "#/hooks/use-user-providers";
import { useActiveConversation } from "#/hooks/query/use-active-conversation";
import { ForgeObservation } from "#/types/core/observations";
import {
  isErrorObservation,
  isForgeAction,
  isForgeEvent,
  isForgeObservation,
  isAgentStateChangeObservation,
  isUserMessage,
} from "#/types/core/guards";
import {
  extractServerReadyInfo,
  getDiffInvalidatePath,
  getEventId,
  getProp,
  getStatusErrorMessage,
  isMessageAction,
  shouldAppendParsedEvent,
  shouldInvalidateFileChanges,
  warnIfNullPayload,
} from "./ws-client-message-utils";
import { normalizeForgeEvent, compactStreamingChunks } from "#/utils/event-normalization";
import { useOptimisticUserMessage } from "#/hooks/use-optimistic-user-message";
import { useWSErrorMessage } from "#/hooks/use-ws-error-message";
import Forge from "#/api/forge";
import { logger } from "#/utils/logger";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { AgentState } from "#/types/agent-state";

// Extracted utilities
import {
  detectPlaywrightRun,
  shouldEstablishConnection,
  disconnectExistingSocket,
  buildSocketQuery,
  resolveSocketTarget,
  createSocketConnection,
  createSyntheticPlaywrightEvents,
} from "./ws-client-connection";
import {
  extractTrajectoryMessageCandidate,
  logTrajectoryNullCandidate,
  extractTrajectoryId,
  markItemAsHydrated,
  isTrajectoryCandidate,
  mergeTrajectoryEvents,
  hydrateTrajectoryState,
} from "./ws-client-trajectory";

export type WebSocketStatus = "CONNECTING" | "CONNECTED" | "DISCONNECTED";

const hasValidMessageProperty = (obj: unknown): obj is { message: string } =>
  typeof obj === "object" &&
  obj !== null &&
  "message" in obj &&
  typeof obj.message === "string";

interface UseWsClient {
  webSocketStatus: WebSocketStatus;
  isLoadingMessages: boolean;
  events: Record<string, unknown>[];
  parsedEvents: (ForgeAction | ForgeObservation)[];
  hydratedEventIds: Set<string>;
  send: (event: Record<string, unknown>) => void;
}

/**
 * Stable context — only changes on connection status transitions.
 * Most components only need `send` and `webSocketStatus`.
 */
interface WsStatusContext {
  webSocketStatus: WebSocketStatus;
  isLoadingMessages: boolean;
  hydratedEventIds: Set<string>;
  send: (event: Record<string, unknown>) => void;
}

/**
 * Volatile context — changes on every WebSocket message.
 * Only components rendering the event list should consume this.
 */
interface WsEventsContext {
  events: Record<string, unknown>[];
  parsedEvents: (ForgeAction | ForgeObservation)[];
}

const WsStatusCtx = React.createContext<WsStatusContext>({
  webSocketStatus: "DISCONNECTED",
  isLoadingMessages: true,
  hydratedEventIds: new Set<string>(),
  send: () => {
    throw new Error("not connected");
  },
});

const WsEventsCtx = React.createContext<WsEventsContext>({
  events: [],
  parsedEvents: [],
});

// Legacy unified context kept for backward-compat; delegates to the split contexts.
const WsClientContext = React.createContext<UseWsClient>({
  webSocketStatus: "DISCONNECTED",
  isLoadingMessages: true,
  events: [],
  parsedEvents: [],
  hydratedEventIds: new Set<string>(),
  send: () => {
    throw new Error("not connected");
  },
});

interface WsClientProviderProps {
  conversationId: string;
}

function registerSocketHandlers({
  socket,
  conversationId,
  handleConnect,
  handleMessage,
  handleError,
  handleDisconnect,
  lastEventRef,
  setWebSocketStatus,
}: {
  socket: Socket;
  conversationId: string;
  handleConnect: () => void;
  handleMessage: (event: Record<string, unknown>) => void;
  handleError: (data: unknown) => void;
  handleDisconnect: (data: unknown) => void;
  lastEventRef: React.MutableRefObject<Record<string, unknown> | null>;
  setWebSocketStatus: (status: WebSocketStatus) => void;
}): () => void {
  const reconnectHandler = async () => {
    const lastEventId = Number(lastEventRef.current?.id ?? -1);
    try {
      // Pass sinceId to fetch only events we missed during disconnect
      const resp = await Forge.getTrajectory(conversationId, {
        sinceId: lastEventId >= 0 ? lastEventId : undefined,
      });
      const trajectory = resp?.trajectory ?? [];
      const missedEvents = trajectory.filter((item) => {
        const eventId = Number(getProp(item, "id") ?? -1);
        return Number.isFinite(eventId) && eventId > lastEventId;
      });

      if (missedEvents.length > 0) {
        missedEvents.forEach((item) => {
          handleMessage(item as Record<string, unknown>);
        });
      }
    } catch (error) {
      EventLogger.error(
        `Failed to recover missed events on reconnect: ${String(error)}`,
      );
    }

    setWebSocketStatus("CONNECTED");
  };

  socket.on("reconnect", reconnectHandler);
  socket.on("connect", handleConnect);
  socket.on("forge_event", handleMessage);
  socket.on("connect_error", handleError);
  socket.on("connect_failed", handleError);
  socket.on("disconnect", handleDisconnect);

  // Track reconnection attempts for status feedback
  const reconnectAttemptHandler = (attempt: number) => {
    setWebSocketStatus("CONNECTING");
    if (attempt > 3) {
      EventLogger.warning(
        `WebSocket reconnection attempt ${attempt} — backoff active`,
      );
    }
  };
  socket.io.on("reconnect_attempt", reconnectAttemptHandler);

  return () => {
    socket.off("reconnect", reconnectHandler);
    socket.off("connect", handleConnect);
    socket.off("forge_event", handleMessage);
    socket.off("connect_error", handleError);
    socket.off("connect_failed", handleError);
    socket.off("disconnect", handleDisconnect);
    socket.io.off("reconnect_attempt", reconnectAttemptHandler);
    socket.disconnect();
  };
}

function setupPlaywrightSocket({
  conversationId,
  handleMessage,
  sioRef,
  setWebSocketStatus,
}: {
  conversationId: string;
  handleMessage: (event: Record<string, unknown>) => void;
  sioRef: React.MutableRefObject<Socket | null>;
  setWebSocketStatus: (status: WebSocketStatus) => void;
}) {
  const noopSocket = {
    connected: true,
    emit: () => undefined,
    off: () => undefined,
    on: () => undefined,
    disconnect: () => undefined,
  } as unknown as Socket;

  // eslint-disable-next-line no-param-reassign
  sioRef.current = noopSocket;
  setWebSocketStatus("CONNECTED");

  const syntheticEvents = createSyntheticPlaywrightEvents(conversationId);
  setTimeout(() => {
    try {
      syntheticEvents.forEach((event) => handleMessage(event));
    } catch (error) {
      logger.warn("Playwright synthetic ws events failed", error);
    }
  }, 0);

  try {
    if (
      typeof window !== "undefined" &&
      typeof window.dispatchEvent === "function"
    ) {
      window.dispatchEvent(new CustomEvent("Forge:open-conversation-panel"));
    }
  } catch (error) {
    // ignore errors in test environment
  }
}

export function updateStatusWhenErrorMessagePresent(data: unknown) {
  const isObject = (val: unknown): val is object =>
    !!val && typeof val === "object";
  const isString = (val: unknown): val is string => typeof val === "string";
  if (isObject(data) && "message" in data && isString(data.message)) {
    if (data.message === "websocket error" || data.message === "timeout") {
      return;
    }
    let msgId: string | undefined;
    let metadata: Record<string, unknown> = {};

    if ("data" in data && isObject(data.data)) {
      if ("msg_id" in data.data && isString(data.data.msg_id)) {
        msgId = data.data.msg_id;
      }
      metadata = data.data as Record<string, unknown>;
    }

    showChatError({
      message: data.message,
      source: "websocket",
      metadata,
      msgId,
    });
  }
}

// Maximum number of raw / parsed events kept in memory per conversation.
// Older events are dropped from the front when exceeded.
const MAX_WS_EVENTS = 5_000;

export function WsClientProvider({
  conversationId,
  children,
}: React.PropsWithChildren<WsClientProviderProps>) {
  const { removeOptimisticUserMessage } = useOptimisticUserMessage();
  const { setErrorMessage, removeErrorMessage } = useWSErrorMessage();
  const queryClient = useQueryClient();
  const sioRef = React.useRef<Socket | null>(null);
  const [webSocketStatus, setWebSocketStatus] =
    React.useState<WebSocketStatus>("DISCONNECTED");
  const [events, setEvents] = React.useState<Record<string, unknown>[]>([]);
  const [parsedEvents, setParsedEvents] = React.useState<
    (ForgeAction | ForgeObservation)[]
  >([]);
  const hydratedEventIdsRef = React.useRef<Set<string>>(new Set());
  /** O(1) dedupe index — avoids rebuilding a Set on every incoming event. */
  const seenEventIdsRef = React.useRef<Set<string>>(new Set());
  /** Counter for events evicted due to MAX_WS_EVENTS cap (dev telemetry). */
  const evictedCountRef = React.useRef<number>(0);
  const lastEventRef = React.useRef<Record<string, unknown> | null>(null);
  const connectingTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);
  const { providers } = useUserProviders();

  const messageRateHandler = useRate({ threshold: 50 }); // Reduced from 250ms to 50ms for faster rendering
  const { data: conversation, refetch: refetchConversation } =
    useActiveConversation();

  const invalidateFileChangeQueries = React.useCallback(
    (event: ForgeParsedEvent) => {
      queryClient.invalidateQueries(
        {
          queryKey: ["file_changes", conversationId],
        },
        { cancelRefetch: false },
      );

      const diffPath = getDiffInvalidatePath(event, conversation);
      if (diffPath) {
        queryClient.invalidateQueries({
          queryKey: ["file_diff", conversationId, diffPath],
        });
      }
    },
    [queryClient, conversationId, conversation],
  );

  function send(event: Record<string, unknown>) {
    if (!sioRef.current) {
      EventLogger.error("WebSocket is not connected.");
      return;
    }
    sioRef.current.emit("forge_user_action", event);
  }

  function handleConnect() {
    setWebSocketStatus("CONNECTED");
    removeErrorMessage();
    // Clear any connecting timeout when successfully connected
    if (connectingTimeoutRef.current) {
      clearTimeout(connectingTimeoutRef.current);
      connectingTimeoutRef.current = null;
    }

    // 🔄 CRITICAL FIX: Auto-recover from ERROR state when WebSocket connects
    // This handles cases where runtime becomes available after being down
    Promise.all([
      import("#/state/agent-slice"),
      import("#/store"),
    ])
      .then(([{ getCurrentAgentState, setCurrentAgentState }, { default: store }]) => {
        const currentState = getCurrentAgentState(store.getState());
        // Only recover if currently in ERROR state
        if (currentState === AgentState.ERROR) {
          // Recover from ERROR state when WebSocket reconnects
          store.dispatch(setCurrentAgentState(AgentState.LOADING));
        }
      })
      .catch((error) => {
        logger.error("Failed to recover agent state:", error);
      });
  }

  const updateLastEventRefFromEvent = React.useCallback(
    (event: Record<string, unknown>) => {
      const maybeId = getProp(event, "id");
      if (typeof maybeId === "string" && !Number.isNaN(parseInt(maybeId, 10))) {
        lastEventRef.current = event;
      }
    },
    [],
  );

  const appendEvent = React.useCallback(
    (event: Record<string, unknown>) => {
      setEvents((prevEvents) => {
        const next = [...prevEvents, event];
        return next.length > MAX_WS_EVENTS
          ? next.slice(next.length - MAX_WS_EVENTS)
          : next;
      });
      updateLastEventRefFromEvent(event);
    },
    [setEvents, updateLastEventRefFromEvent],
  );

  const handleForgeStatusError = React.useCallback(
    (event: ForgeParsedEvent) => {
      const statusErrorMessage = getStatusErrorMessage(event);
      if (!statusErrorMessage) {
        return false;
      }

      // Show error prominently in chat with user-friendly formatting
      showChatError({
        message: statusErrorMessage,
        source: "chat",
        metadata: { msgId: event.id, event },
        rawError: event,
      });

      trackError({
        message: statusErrorMessage,
        source: "chat",
        metadata: { msgId: event.id },
        rawError: event,
      });
      setErrorMessage(statusErrorMessage);
      return true;
    },
    [setErrorMessage],
  );

  const appendParsedEventIfNeeded = React.useCallback(
    (event: ForgeParsedEvent) => {
      if (!shouldAppendParsedEvent(event)) {
        return;
      }

      const eventId =
        getEventId(event as unknown as Record<string, unknown>) ?? "";

      // O(1) dedupe via persistent Set ref — no per-event array scan.
      if (seenEventIdsRef.current.has(eventId)) {
        return;
      }
      seenEventIdsRef.current.add(eventId);

      startTransition(() => {
        setParsedEvents((prevEvents) => {
          let next = [...prevEvents, event as ForgeAction | ForgeObservation];

          // When approaching the cap, compact streaming chunks first
          // to reclaim slots before falling back to dropping oldest events.
          if (next.length > MAX_WS_EVENTS) {
            next = compactStreamingChunks(next) as typeof next;
          }

          if (next.length > MAX_WS_EVENTS) {
            const evictCount = next.length - MAX_WS_EVENTS;
            evictedCountRef.current += evictCount;

            // Log eviction telemetry at warn-level so it's visible during
            // long sessions without being spammy (only fires on actual evict).
            if (evictedCountRef.current % 500 === 0 || evictCount > 100) {
              EventLogger.warning(
                `Event eviction: dropped ${evictCount} oldest events ` +
                  `(total evicted: ${evictedCountRef.current})`,
              );
            }

            // Remove evicted IDs from the dedupe index to prevent unbounded
            // growth.  Only the retained tail is still "seen".
            const evicted = next.slice(0, evictCount);
            for (const ev of evicted) {
              const id =
                getEventId(ev as unknown as Record<string, unknown>) ?? "";
              seenEventIdsRef.current.delete(id);
            }

            next = next.slice(evictCount);
          }

          return next;
        });
      });
    },
    [setParsedEvents],
  );

  const dispatchServerReadyIfPresent = React.useCallback(
    (event: ForgeParsedEvent) => {
      const serverReadyInfo = extractServerReadyInfo(event);
      if (!serverReadyInfo) {
        return;
      }

      window.dispatchEvent(
        new CustomEvent("Forge:server-ready", { detail: serverReadyInfo }),
      );
    },
    [],
  );

  const applyObservationEffects = React.useCallback(
    (event: ForgeParsedEvent) => {
      if (isErrorObservation(event)) {
        trackError({
          message: event.message,
          source: "chat",
          metadata: { msgId: event.id },
        });
        
        // Try to extract user-friendly error from content (may be JSON)
        let errorToDisplay: unknown = event.message;
        if (event.content) {
          try {
            const parsed = JSON.parse(event.content);
            if (parsed && typeof parsed === "object" && "title" in parsed) {
              errorToDisplay = parsed; // Use structured error
            }
          } catch {
            // Not JSON, use message as-is
            errorToDisplay = event.content || event.message;
          }
        }
        
        displayErrorToast(errorToDisplay);
      } else if (isAgentStateChangeObservation(event)) {
        // Handled by handleObservationMessage in handleAssistantMessage
      } else {
        removeErrorMessage();
      }
    },
    [removeErrorMessage],
  );

  const applyEventSideEffects = React.useCallback(
    (event: ForgeParsedEvent) => {
      applyObservationEffects(event);

      if (isUserMessage(event)) {
        removeOptimisticUserMessage();
      }

      if (isMessageAction(event)) {
        messageRateHandler.record(Date.now());
      }

      if (shouldInvalidateFileChanges(event)) {
        invalidateFileChangeQueries(event);
      }
    },
    [
      applyObservationEffects,
      invalidateFileChangeQueries,
      messageRateHandler,
      removeOptimisticUserMessage,
    ],
  );

  function handleMessage(raw: Record<string, unknown>) {
    // Centralised normalization — guarantees id, timestamp, source, message
    // invariants and sanitizes literal "NULL" strings.
    const event = normalizeForgeEvent(raw);

    handleAssistantMessage(event);

    if (!isForgeEvent(event)) {
      appendEvent(event);
      return;
    }

    if (handleForgeStatusError(event)) {
      return;
    }

    appendParsedEventIfNeeded(event);
    dispatchServerReadyIfPresent(event);
    applyEventSideEffects(event);
    appendEvent(event);
  }

  function handleDisconnect(data: unknown) {
    setWebSocketStatus("DISCONNECTED");
    const sio = sioRef.current;
    if (!sio) {
      return;
    }
    sio.io.opts.query = sio.io.opts.query || {};
    sio.io.opts.query.latest_event_id = lastEventRef.current?.id;
    updateStatusWhenErrorMessagePresent(data);

    setErrorMessage(hasValidMessageProperty(data) ? data.message : "");
  }

  function handleError(data: unknown) {
    setWebSocketStatus("DISCONNECTED");
    updateStatusWhenErrorMessagePresent(data);

    // Extract user-friendly error if available
    const errorMessage = hasValidMessageProperty(data)
      ? data.message
      : "An unknown error occurred on the WebSocket connection.";

    // Show error prominently in chat
    showChatError({
      message: errorMessage,
      source: "websocket",
      metadata:
        typeof data === "object" && data !== null
          ? (data as Record<string, unknown>)
          : {},
      rawError: data,
    });

    setErrorMessage(errorMessage);

    // check if something went wrong with the conversation.
    refetchConversation();
  }

  React.useEffect(() => {
    lastEventRef.current = null;

    // reset events when conversationId changes
    setEvents([]);
    setParsedEvents([]);
    hydratedEventIdsRef.current.clear();
    seenEventIdsRef.current.clear();
    evictedCountRef.current = 0;
    setWebSocketStatus("CONNECTING");

    // 🔄 CRITICAL FIX: Reset agent state when switching conversations
    // This prevents ERROR state from persisting across conversations
    Promise.all([
      import("#/state/agent-slice"),
      import("#/store"),
      import("#/types/agent-state"),
    ])
      .then(([{ setCurrentAgentState }, { default: store }, { AgentState }]) => {
        // New conversation - reset agent state
        store.dispatch(setCurrentAgentState(AgentState.LOADING));
      })
      .catch((error) => {
        logger.error("Failed to reset agent state:", error);
      });
  }, [conversationId]);

  React.useEffect(() => {
    if (!conversationId) {
      throw new Error("No conversation ID provided");
    }

    const isPlaywright = detectPlaywrightRun();
    if (
      !shouldEstablishConnection(
        conversation as
          | { status?: string; runtime_status?: unknown }
          | undefined,
        isPlaywright,
      )
    ) {
      return () => undefined;
    }

    disconnectExistingSocket(sioRef);
    setWebSocketStatus("CONNECTING");

    // Clear any existing timeout
    if (connectingTimeoutRef.current) {
      clearTimeout(connectingTimeoutRef.current);
      connectingTimeoutRef.current = null;
    }

    // Add timeout for connecting state - show error if takes too long
    connectingTimeoutRef.current = setTimeout(() => {
      setWebSocketStatus((currentStatus) => {
        if (currentStatus === "CONNECTING") {
          setErrorMessage(
            "Connection timeout. Please check your internet connection and try refreshing the page."
          );
          return "DISCONNECTED";
        }
        return currentStatus;
      });
      connectingTimeoutRef.current = null;
    }, 120000); // 2 minutes timeout

    const query = buildSocketQuery({
      conversationId,
      conversation: conversation as
        | { session_api_key?: string | null }
        | undefined,
      providers,
      lastEvent: lastEventRef.current,
    });

    let teardown: (() => void) | undefined;
    if (isPlaywright) {
      setupPlaywrightSocket({
        conversationId,
        handleMessage,
        sioRef,
        setWebSocketStatus,
      });
    } else {
      const { baseUrl, socketPath } = resolveSocketTarget(
        conversation as { url?: string | null } | undefined,
      );
      const socket = createSocketConnection({
        baseUrl,
        socketPath,
        query,
        sessionApiKey: (conversation as any)?.session_api_key,
      });
      sioRef.current = socket;
      teardown = registerSocketHandlers({
        socket,
        conversationId,
        handleConnect,
        handleMessage,
        handleError,
        handleDisconnect,
        lastEventRef,
        setWebSocketStatus,
      });
    }

    hydrateTrajectoryState({
      conversationId,
      setParsedEvents,
      hydratedEventIdsRef,
    });

    return () => {
      if (connectingTimeoutRef.current) {
        clearTimeout(connectingTimeoutRef.current);
        connectingTimeoutRef.current = null;
      }
      if (teardown) {
        teardown();
      }
    };
  }, [
    conversationId,
    conversation?.url,
    conversation?.status,
    conversation?.runtime_status,
    providers,
  ]);

  React.useEffect(
    () => () => {
      const sio = sioRef.current;
      if (sio) {
        sio.off("disconnect", handleDisconnect);
        sio.disconnect();
      }
    },
    [],
  );

  // Stable context — only changes on connection transitions
  const statusValue = React.useMemo<WsStatusContext>(
    () => ({
      webSocketStatus,
      isLoadingMessages: messageRateHandler.isUnderThreshold,
      hydratedEventIds: hydratedEventIdsRef.current,
      send,
    }),
    [webSocketStatus, messageRateHandler.isUnderThreshold, send],
  );

  // Volatile context — changes on every event
  const eventsValue = React.useMemo<WsEventsContext>(
    () => ({ events, parsedEvents }),
    [events, parsedEvents],
  );

  // Legacy unified value for backward-compat (useWsClient)
  const value = React.useMemo<UseWsClient>(
    () => ({ ...statusValue, ...eventsValue }),
    [statusValue, eventsValue],
  );

  return (
    <WsStatusCtx.Provider value={statusValue}>
      <WsEventsCtx.Provider value={eventsValue}>
        <WsClientContext.Provider value={value}>
          {children}
        </WsClientContext.Provider>
      </WsEventsCtx.Provider>
    </WsStatusCtx.Provider>
  );
}

/**
 * Full context — re-renders on every WS event.
 * Prefer `useWsStatus()` or `useWsEvents()` for better performance.
 */
export function useWsClient() {
  return React.useContext(WsClientContext);
}

/**
 * Stable hook — only re-renders on connection status changes.
 * Use when you only need `send`, `webSocketStatus`, or `isLoadingMessages`.
 */
export function useWsStatus() {
  return React.useContext(WsStatusCtx);
}

/**
 * Volatile hook — re-renders on every WebSocket message.
 * Use only when you need the events/parsedEvents arrays.
 */
export function useWsEvents() {
  return React.useContext(WsEventsCtx);
}
