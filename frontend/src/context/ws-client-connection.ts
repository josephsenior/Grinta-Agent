/**
 * Socket.IO connection utilities extracted from ws-client-provider.
 *
 * Pure functions with no React dependency — safe to unit-test independently.
 */

import { io, Socket } from "socket.io-client";

// ── Playwright detection ───────────────────────────────────────────

type MaybeProcess = { env?: Record<string, string | undefined> };
type MaybeImportMeta = { env?: Record<string, unknown> };
type WindowWithPlaywright = Window & { __Forge_PLAYWRIGHT?: boolean };

export function detectPlaywrightRun(): boolean {
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

// ── Connection gating ──────────────────────────────────────────────

export function shouldEstablishConnection(
  conversation: { status?: string; runtime_status?: unknown } | undefined,
  isPlaywright: boolean,
): boolean {
  if (isPlaywright) return true;
  if (!conversation) return false;

  const status = conversation.status?.toUpperCase();

  if (
    status === "RUNNING" ||
    status === "STARTING" ||
    status === "STOPPED" ||
    status === "ERROR"
  )
    return true;
  if (conversation.runtime_status) return true;

  // Be permissive — the backend will reject if not allowed
  return true;
}

// ── Socket helpers ─────────────────────────────────────────────────

export function disconnectExistingSocket(
  ref: React.MutableRefObject<Socket | null>,
) {
  const socket = ref.current;
  if (socket?.connected) socket.disconnect();
}

export function buildSocketQuery({
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
  return query;
}

export function resolveSocketTarget(
  conversation: { url?: string | null } | undefined,
): { baseUrl: string; socketPath: string } {
  if (conversation?.url && !conversation.url.startsWith("/")) {
    try {
      const url = new URL(conversation.url);
      const prefix = url.pathname.split("/api/conversations")[0] || "/";
      const sanitized = prefix.replace(/\/$/, "");
      return { baseUrl: url.origin, socketPath: `${sanitized}/socket.io` };
    } catch {
      /* fall through */
    }
  }

  const envBase =
    (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined) ||
    (import.meta.env.VITE_BACKEND_HOST as string | undefined);

  let baseUrl: string;
  if (envBase && envBase.includes("://")) {
    baseUrl = envBase;
  } else if (envBase) {
    if (typeof window !== "undefined" && window.location) {
      baseUrl = `${window.location.protocol}//${envBase}`;
    } else {
      baseUrl = `http://${envBase}`;
    }
  } else if (typeof window !== "undefined" && window.location) {
    baseUrl = window.location.origin;
  } else {
    baseUrl = "http://localhost:3000";
  }

  return { baseUrl, socketPath: "/socket.io" };
}

export function createSocketConnection({
  baseUrl,
  socketPath,
  query,
  sessionApiKey,
}: {
  baseUrl: string | null;
  socketPath: string;
  query: Record<string, unknown>;
  sessionApiKey?: string | null;
}): Socket {
  const isLocal =
    baseUrl?.includes("localhost") ||
    baseUrl?.includes("127.0.0.1") ||
    (typeof window !== "undefined" && window.location.hostname === "localhost");

  return io(baseUrl ?? undefined, {
    transports: isLocal ? ["websocket"] : ["websocket", "polling"],
    path: socketPath,
    query,
    auth: {
      session_api_key: sessionApiKey,
    },
    timeout: isLocal ? 2000 : 20000,
    reconnection: true,
    reconnectionDelay: isLocal ? 100 : 1000,
    reconnectionDelayMax: 30_000, // exponential backoff caps at 30s
    reconnectionAttempts: Infinity, // never give up — long sessions need resilience
    forceNew: true,
    upgrade: !isLocal,
    autoConnect: true,
    rememberUpgrade: !isLocal,
  });
}

export function createSyntheticPlaywrightEvents(conversationId: string) {
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
