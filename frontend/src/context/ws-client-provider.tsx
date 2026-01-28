import React from "react";
import { flushSync } from "react-dom";
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
import { useOptimisticUserMessage } from "#/hooks/use-optimistic-user-message";
import { useWSErrorMessage } from "#/hooks/use-ws-error-message";
import Forge from "#/api/forge";
import { logger } from "#/utils/logger";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { AgentState } from "#/types/agent-state";

export type WebSocketStatus = "CONNECTING" | "CONNECTED" | "DISCONNECTED";

// Helper narrow types to avoid casting to `any` in several runtime checks
type MaybeProcess = { env?: Record<string, string | undefined> };
type MaybeImportMeta = { env?: Record<string, unknown> };
type WindowWithPlaywright = Window & { __Forge_PLAYWRIGHT?: boolean };

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

function detectPlaywrightRun(): boolean {
  const hasProcessFlag =
    typeof process !== "undefined" &&
    (process as MaybeProcess).env?.PLAYWRIGHT === "1";
  const hasViteFlag = Boolean(
    (import.meta as MaybeImportMeta).env?.VITE_PLAYWRIGHT_STUB,
  );
  const windowFlag =
    typeof window !== "undefined" &&
    (window as WindowWithPlaywright).__Forge_PLAYWRIGHT === true;

  return Boolean(hasProcessFlag || hasViteFlag || windowFlag);
}

function shouldEstablishConnection(
  conversation: { status?: string; runtime_status?: unknown } | undefined,
  isPlaywright: boolean,
): boolean {
  if (isPlaywright) {
    return true;
  }

  if (!conversation) {
    return false;
  }

  const status = conversation.status?.toUpperCase();

  // Allow connection for active conversations (handle both uppercase and lowercase)
  if (status === "RUNNING" || status === "STARTING") {
    return true;
  }

  // Allow connection if runtime_status exists (runtime is available)
  if (conversation.runtime_status) {
    return true;
  }

  // Allow connection for stopped conversations - WebSocket connection is needed
  // to initialize/restart the runtime, so we should attempt connection even if stopped
  if (status === "STOPPED") {
    return true;
  }

  // For ERROR status, still allow connection - the WebSocket might help recover
  if (status === "ERROR") {
    return true;
  }

  // For other statuses or undefined, be more permissive - allow connection attempts
  // The backend will reject if it's truly not allowed
  return true;
}

function disconnectExistingSocket(ref: React.MutableRefObject<Socket | null>) {
  const socket = ref.current;
  if (socket?.connected) {
    socket.disconnect();
  }
}

function buildSocketQuery({
  conversationId,
  conversation,
  providers,
  lastEvent,
}: {
  conversationId: string;
  conversation: { session_api_key?: string | null } | undefined;
  providers: unknown;
  lastEvent: Record<string, unknown> | null;
}): Record<string, unknown> {
  const latestEventId = (lastEvent as { id?: unknown } | null)?.id ?? -1;
  const query: Record<string, unknown> = {
    latest_event_id: latestEventId,
    conversation_id: conversationId,
    providers_set: providers,
  };

  if (conversation?.session_api_key) {
    query.session_api_key = conversation.session_api_key;
  }

  return query;
}

function resolveSocketTarget(
  conversation: { url?: string | null } | undefined,
): { baseUrl: string; socketPath: string } {
  if (conversation?.url && !conversation.url.startsWith("/")) {
    try {
      const url = new URL(conversation.url);
      const prefix = url.pathname.split("/api/conversations")[0] || "/";
      const sanitized = prefix.replace(/\/$/, "");
      return {
        baseUrl: url.origin,
        socketPath: `${sanitized}/socket.io`,
      };
    } catch {
      // Fall through to env/proxy-based resolution
    }
  }

  // Prefer explicit backend URL from env, otherwise use current origin so that
  // dev proxy and production hosts behave correctly. This avoids hardcoding
  // `localhost:3000` which breaks when backend runs on a different port.
  const envBase =
    (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined) ||
    (import.meta.env.VITE_BACKEND_HOST as string | undefined);

  let baseUrl: string;
  if (envBase && envBase.includes("://")) {
    baseUrl = envBase;
  } else if (envBase) {
    // allow host:port form in env (no protocol)
    if (typeof window !== "undefined" && window.location) {
      baseUrl = `${window.location.protocol}//${envBase}`;
    } else {
      baseUrl = `http://${envBase}`;
    }
  } else if (typeof window !== "undefined" && window.location) {
    baseUrl = window.location.origin;
  } else {
    // Default to backend port used by the local Python server
    baseUrl = "http://localhost:3000";
  }

  return { baseUrl, socketPath: "/socket.io" };
}

function createSocketConnection({
  baseUrl,
  socketPath,
  query,
}: {
  baseUrl: string | null;
  socketPath: string;
  query: Record<string, unknown>;
}): Socket {
  // Check if this is a local connection
  const isLocal = 
    baseUrl?.includes("localhost") || 
    baseUrl?.includes("127.0.0.1") ||
    (typeof window !== "undefined" && window.location.hostname === "localhost");

  return io(baseUrl ?? undefined, {
    // For local connections, use websocket directly (skip polling)
    // For remote connections, allow fallback to polling
    transports: isLocal ? ["websocket"] : ["websocket", "polling"],
    path: socketPath,
    query,
    // Local connections should be much faster - reduce timeout
    timeout: isLocal ? 2000 : 20000, // 2 seconds for local, 20 for remote
    reconnection: true,
    reconnectionDelay: isLocal ? 100 : 1000, // Faster reconnection for local
    reconnectionAttempts: 5,
    forceNew: true,
    // Skip upgrade process for local - connect directly with websocket
    upgrade: !isLocal, // Only upgrade for remote connections
    autoConnect: true,
    rememberUpgrade: !isLocal, // Don't remember upgrade for local
  });
}

function createSyntheticPlaywrightEvents(conversationId: string) {
  const timestamp = new Date().toISOString();
  return [
    {
      id: "pw-agent-state",
      source: "system",
      message: "AWAITING_USER_INPUT",
      timestamp,
      observation: "agent_state_change",
      content: "",
      extras: { agent_state: "AWAITING_USER_INPUT" },
    },
    {
      id: "pw-session-ready",
      source: "system",
      message: "SESSION_READY",
      timestamp,
      observation: "session_ready",
      content: "SESSION_READY",
      extras: { conversation_id: conversationId },
    },
  ] as Record<string, unknown>[];
}

function extractTrajectoryMessageCandidate(item: Record<string, unknown>) {
  const messageProp = getProp(item, "message");
  const contentProp = getProp(item, "content");
  const argsProp = getProp(item, "args") as Record<string, unknown> | undefined;

  const candidates = [
    typeof messageProp === "string" ? messageProp : undefined,
    typeof contentProp === "string" ? contentProp : undefined,
    typeof argsProp?.content === "string" ? argsProp.content : undefined,
    typeof argsProp?.command === "string" ? argsProp.command : undefined,
  ];

  return candidates.find((value): value is string => Boolean(value));
}

function logTrajectoryNullCandidate(item: Record<string, unknown>) {
  try {
    const candidate = extractTrajectoryMessageCandidate(item);
    if (!candidate) {
      return;
    }

    if (candidate.toUpperCase() === "NULL") {
      logger.warn("Trajectory contains literal 'NULL'", {
        id: getProp(item, "id"),
        item,
      });
    }
  } catch (error) {
    // ignore logging failures
  }
}

function extractTrajectoryId(item: Record<string, unknown>): string {
  const rawId = getProp(item, "id");
  if (typeof rawId === "string" && rawId.trim().length > 0) {
    return rawId;
  }
  if (typeof rawId === "number" && Number.isFinite(rawId)) {
    return String(rawId);
  }
  return Math.random().toString(36).slice(2, 9);
}

function markItemAsHydrated(
  item: Record<string, unknown>,
  hydratedIds: Set<string>,
  id: string,
) {
  try {
    // eslint-disable-next-line no-param-reassign
    (item as Record<string, unknown>).__hydrated = true;
  } catch (error) {
    // ignore if flag cannot be set
  }
  hydratedIds.add(id);
}

function isTrajectoryCandidate(item: Record<string, unknown>): boolean {
  return (
    "id" in item && "source" in item && "message" in item && "timestamp" in item
  );
}

function mergeTrajectoryEvents(
  prev: (ForgeAction | ForgeObservation)[],
  trajectory: unknown[],
  hydratedIds: Set<string>,
): (ForgeAction | ForgeObservation)[] {
  const existingIds = new Set(
    prev.map((event) => String(getProp(event, "id") ?? "")),
  );
  const merged = [...prev];

  for (const rawItem of trajectory) {
    const item = rawItem as Record<string, unknown>;
    if (item && typeof item === "object") {
      logTrajectoryNullCandidate(item);
      const id = extractTrajectoryId(item);
      if (!existingIds.has(id)) {
        markItemAsHydrated(item, hydratedIds, id);
        if (isTrajectoryCandidate(item)) {
          if (
            isForgeAction(item as unknown) ||
            isForgeObservation(item as unknown)
          ) {
            merged.push(item as unknown as ForgeParsedEvent);
            existingIds.add(id);
          } else {
            logger.debug("Skipping non-event trajectory item", { id, item });
          }
        } else {
          logger.debug("Skipping incomplete trajectory item", { id, item });
        }
      }
    } else {
      logger.debug("Skipping non-object trajectory item", { item });
    }
  }

  return merged;
}

async function hydrateTrajectoryState({
  conversationId,
  setParsedEvents,
  hydratedEventIdsRef,
}: {
  conversationId: string;
  setParsedEvents: React.Dispatch<
    React.SetStateAction<(ForgeAction | ForgeObservation)[]>
  >;
  hydratedEventIdsRef: React.MutableRefObject<Set<string>>;
}) {
  try {
    const resp = await Forge.getTrajectory(conversationId);
    const trajectory = resp?.trajectory ?? [];
    if (!Array.isArray(trajectory) || trajectory.length === 0) {
      return;
    }

    setParsedEvents((prev) =>
      mergeTrajectoryEvents(prev, trajectory, hydratedEventIdsRef.current),
    );
  } catch (error) {
    // Ignore trajectory hydration failures - UI can still operate with live socket
    // no-op
  }
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
    const lastEventId = lastEventRef.current?.id ?? -1;
    try {
      const resp = await Forge.getTrajectory(conversationId);
      const trajectory = resp?.trajectory ?? [];
      const missedEvents = trajectory.filter((item) => {
        const eventId = Number(getProp(item, "id") ?? -1);
        return Number.isFinite(eventId) && eventId > Number(lastEventId);
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

  return () => {
    socket.off("reconnect", reconnectHandler);
    socket.off("connect", handleConnect);
    socket.off("forge_event", handleMessage);
    socket.off("connect_error", handleError);
    socket.off("connect_failed", handleError);
    socket.off("disconnect", handleDisconnect);
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
    import("#/state/agent-slice").then(
      ({ getCurrentAgentState, setCurrentAgentState }) => {
        import("#/store").then(({ default: store }) => {
          const currentState = getCurrentAgentState(store.getState());
          // Only recover if currently in ERROR state
          if (currentState === AgentState.ERROR) {
            // Recover from ERROR state when WebSocket reconnects
            store.dispatch(setCurrentAgentState(AgentState.LOADING));
          }
        });
      },
    );
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
      setEvents((prevEvents) => [...prevEvents, event]);
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
      flushSync(() => {
        setParsedEvents((prevEvents) => {
          const existingIds = new Set(
            prevEvents.map(
              (existing) =>
                getEventId(existing as unknown as Record<string, unknown>) ??
                "",
            ),
          );

          if (existingIds.has(eventId)) {
            return prevEvents;
          }

          return [...prevEvents, event as ForgeAction | ForgeObservation];
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

  function handleMessage(event: Record<string, unknown>) {
    warnIfNullPayload(event);
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
    setWebSocketStatus("CONNECTING");

    // 🔄 CRITICAL FIX: Reset agent state when switching conversations
    // This prevents ERROR state from persisting across conversations
    import("#/state/agent-slice").then(({ setCurrentAgentState }) => {
      import("#/store").then(({ default: store }) => {
        import("#/types/agent-state").then(({ AgentState }) => {
          // New conversation - reset agent state
          store.dispatch(setCurrentAgentState(AgentState.LOADING));
        });
      });
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
      const socket = createSocketConnection({ baseUrl, socketPath, query });
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

    return () => {
      teardown?.();
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

  const value = React.useMemo<UseWsClient>(
    () => ({
      webSocketStatus,
      isLoadingMessages: messageRateHandler.isUnderThreshold,
      events,
      parsedEvents,
      hydratedEventIds: hydratedEventIdsRef.current,
      send,
    }),
    [
      webSocketStatus,
      messageRateHandler.isUnderThreshold,
      events,
      parsedEvents,
      send,
    ],
  );

  return (
    <WsClientContext.Provider value={value}>
      {children}
    </WsClientContext.Provider>
  );
}

export function useWsClient() {
  return React.useContext(WsClientContext);
}
