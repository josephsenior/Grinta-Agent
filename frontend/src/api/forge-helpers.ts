/**
 * Shared helpers and state used across Forge API service modules.
 *
 * Extracted from the monolithic ForgeClient class so that domain-specific
 * service files (file-service, git-service, etc.) can access URL builders
 * and conversation state without circular dependencies.
 */

import { AxiosHeaders } from "axios";
import { Conversation } from "#/api/forge.types";
import { ConversationStatus } from "#/types/conversation-status";
import { RuntimeStatus } from "#/types/runtime-status";
import { getAPIBase, CURRENT_API_VERSION } from "#/config/api-config";

// ---------------------------------------------------------------------------
// Module-level conversation state (singleton, matches prior static field)
// ---------------------------------------------------------------------------

let currentConversation: Conversation | null = null;

export function getCurrentConversation(): Conversation | null {
  return currentConversation;
}

export function setCurrentConversation(c: Conversation | null): void {
  currentConversation = c;
}

// ---------------------------------------------------------------------------
// URL helpers
// ---------------------------------------------------------------------------

/** Versioned API base, e.g. `/api/v1` */
export function getBase(): string {
  return getAPIBase(CURRENT_API_VERSION);
}

/**
 * Returns the appropriate URL for a conversation endpoint.
 * If the conversation has a custom URL, it is used; otherwise falls back to
 * the local API base.
 */
export function getConversationUrl(conversationId: string): string {
  if (
    currentConversation?.conversation_id === conversationId &&
    currentConversation.url
  ) {
    return currentConversation.url;
  }
  return `${getBase()}/conversations/${conversationId}`;
}

/**
 * Build headers needed for authenticated conversation requests.
 */
export function getConversationHeaders(): AxiosHeaders {
  const headers = new AxiosHeaders();
  const sessionApiKey = currentConversation?.session_api_key;
  if (sessionApiKey) {
    headers.set("X-Session-API-Key", sessionApiKey);
  }
  return headers;
}

// ---------------------------------------------------------------------------
// Normalisation / error helpers
// ---------------------------------------------------------------------------

export function normalizeConversation(conversation: Conversation): Conversation {
  const statusRaw = conversation.status;
  const status = (
    typeof statusRaw === "string" ? statusRaw.toUpperCase() : statusRaw
  ) as ConversationStatus;

  const runtimeStatusRaw = conversation.runtime_status;
  const runtimeStatus = (
    typeof runtimeStatusRaw === "string"
      ? runtimeStatusRaw.toUpperCase()
      : runtimeStatusRaw
  ) as RuntimeStatus | null;

  return {
    ...conversation,
    status,
    runtime_status: runtimeStatus,
  };
}

/**
 * Safely extract a user-friendly error message from unknown error values.
 */
export function safeErrorMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err instanceof Error) return err.message;
  if (typeof err === "object" && err !== null) {
    const e = err as Record<string, unknown>;
    const resp = e.response as Record<string, unknown> | undefined;
    const data = resp?.data as Record<string, unknown> | undefined;
    const errorStr = data?.error;
    if (typeof errorStr === "string") return errorStr;
    const msg = e.message;
    if (typeof msg === "string") return msg;
  }
  return "";
}
