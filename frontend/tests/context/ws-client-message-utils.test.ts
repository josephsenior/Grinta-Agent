import { afterEach, describe, expect, it, vi } from "vitest";
import { AgentState } from "#/types/agent-state";
import type { Conversation } from "#/api/forge.types";
import type { ForgeParsedEvent } from "#/types/core";
import {
  extractServerReadyInfo,
  getDiffInvalidatePath,
  getEventId,
  getStatusErrorMessage,
  isMessageAction,
  shouldAppendParsedEvent,
  shouldInvalidateFileChanges,
  warnIfNullPayload,
} from "#/context/ws-client-message-utils";

const baseEvent = {
  id: 1,
  source: "agent" as const,
  message: "",
  timestamp: new Date().toISOString(),
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ws-client message utils", () => {
  it("extracts status error message from status update", () => {
    const statusUpdateEvent = {
      ...baseEvent,
      status_update: true,
      type: "error" as const,
      message: "Status failure",
    } as unknown as ForgeParsedEvent;

    expect(getStatusErrorMessage(statusUpdateEvent)).toBe("Status failure");
  });

  it("extracts status error message from agent state change", () => {
    const agentStateEvent = {
      ...baseEvent,
      observation: "agent_state_changed" as const,
      extras: {
        agent_state: AgentState.ERROR,
        reason: "Runtime crashed",
      },
    } as unknown as ForgeParsedEvent;

    expect(getStatusErrorMessage(agentStateEvent)).toBe("Runtime crashed");
  });

  it("returns undefined for non-error events", () => {
    const normalEvent = {
      ...baseEvent,
      action: "message" as const,
      args: {
        thought: "All good",
        image_urls: [],
        file_urls: [],
        wait_for_response: false,
      },
    } as unknown as ForgeParsedEvent;

    expect(getStatusErrorMessage(normalEvent)).toBeUndefined();
  });

  it("extracts server ready info from observation", () => {
    const readyEvent = {
      ...baseEvent,
      observation: "server_ready" as const,
      extras: {
        port: 8080,
        url: "http://localhost:8080",
        protocol: "http",
        health_status: "ready",
      },
    } as unknown as ForgeParsedEvent;

    expect(extractServerReadyInfo(readyEvent)).toEqual({
      port: 8080,
      url: "http://localhost:8080",
      protocol: "http",
      health_status: "ready",
    });
  });

  it("extracts server ready info from extras payload", () => {
    const readyExtrasEvent = {
      ...baseEvent,
      observation: "run" as const,
      extras: {
        server_ready: {
          port: 9000,
          url: "https://server",
          protocol: "https",
        },
      },
    } as unknown as ForgeParsedEvent;

    expect(extractServerReadyInfo(readyExtrasEvent)).toEqual({
      port: 9000,
      url: "https://server",
      protocol: "https",
      health_status: "unknown",
    });
  });

  it("detects message actions", () => {
    const messageEvent = {
      ...baseEvent,
      action: "message" as const,
      source: "agent" as const,
      type: "message" as const,
      args: {
        thought: "Hi",
        image_urls: null,
        file_urls: [],
        wait_for_response: false,
      },
    } as unknown as ForgeParsedEvent;

    expect(isMessageAction(messageEvent)).toBe(true);
  });

  it("identifies events that should be appended to parsed list", () => {
    const actionEvent = {
      ...baseEvent,
      action: "write" as const,
      args: {
        path: "file.ts",
        content: "console.log('a');",
        thought: "",
      },
    } as unknown as ForgeParsedEvent;

    expect(shouldAppendParsedEvent(actionEvent)).toBe(true);
  });

  it("detects file change invalidations", () => {
    const commandEvent = {
      ...baseEvent,
      action: "run" as const,
      args: {
        command: "npm test",
        thought: "",
        security_risk: "low",
        confirmation_state: "confirmed",
      },
    } as unknown as ForgeParsedEvent;

    const writeEvent = {
      ...baseEvent,
      action: "write" as const,
      args: {
        path: "src/index.ts",
        content: "export {}",
        thought: "",
      },
    } as unknown as ForgeParsedEvent;

    expect(shouldInvalidateFileChanges(commandEvent)).toBe(true);
    expect(shouldInvalidateFileChanges(writeEvent)).toBe(true);
  });

  it("normalizes diff invalidate path", () => {
    const conversation: Conversation = {
      conversation_id: "abc",
      title: "Test",
      selected_repository: "org/project",
      selected_branch: null,
      git_provider: null,
      last_updated_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      status: "RUNNING",
      runtime_status: null,
      url: null,
      session_api_key: null,
      pr_number: null,
    };

    const writeEvent = {
      ...baseEvent,
      action: "write" as const,
      args: {
        path: "/workspace/project/src/app.ts",
        content: "export {}",
        thought: "",
      },
    } as unknown as ForgeParsedEvent;

    expect(getDiffInvalidatePath(writeEvent, conversation)).toBe("src/app.ts");
  });

  it("warns when payload contains literal NULL", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const event = {
      ...baseEvent,
      message: "null",
    } as Record<string, unknown>;

    warnIfNullPayload(event);
    expect(warnSpy).toHaveBeenCalledTimes(1);
  });

  it("derives event id from record", () => {
    const id = getEventId({ id: 42 });
    expect(id).toBe("42");
  });
});
