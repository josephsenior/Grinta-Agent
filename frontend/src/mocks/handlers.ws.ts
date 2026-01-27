import { delay, WebSocketHandler, ws } from "msw";
import { toSocketIo } from "@mswjs/socket.io-binding";
import { AgentState } from "#/types/agent-state";
import { InitConfig } from "#/types/core/variances";
import { SESSION_HISTORY } from "./session-history.mock";
import {
  generateAgentStateChangeObservation,
  emitMessages,
  emitAssistantMessage,
} from "./mock-ws-helpers";

const isInitConfig = (data: unknown): data is InitConfig =>
  typeof data === "object" &&
  data !== null &&
  "action" in data &&
  data.action === "initialize";

const chat = ws.link(`ws://${window?.location.host}/socket.io`);

export const handlers: WebSocketHandler[] = [
  chat.addEventListener("connection", (connection) => {
    const io = toSocketIo(connection);
    // @ts-expect-error - accessing private property for testing purposes
    const { url }: { url: URL } = io.client.connection;
    const conversationId = url.searchParams.get("conversation_id");

    io.client.emit("connect");

    // Emit initial session messages and an agent-state change so the
    // frontend can transition out of loading state quickly. Previously we
    // only emitted these when conversation_id was present; that occasionally
    // caused the app to wait for socket events and time out in Playwright
    // runs. Emitting unconditionally is safe for tests and keeps behavior
    // deterministic.
    // Emit initial agent-state immediately so the frontend can transition
    // out of loading state quickly during tests. Also emit a deterministic
    // SESSION_READY observation which Playwright tests can rely on to
    // consider the session ready for navigation. This reduces races where
    // navigation occurs before the app considers the session initialized.
    if (conversationId && SESSION_HISTORY["1"]) {
      emitMessages(io, SESSION_HISTORY["1"]);
    }

    // Agent state change to indicate ready for user input
    io.client.emit(
      "forge_event",
      generateAgentStateChangeObservation(AgentState.AWAITING_USER_INPUT),
    );

    // Deterministic session-ready observation (test-only semantic)
    io.client.emit("forge_event", {
      id: 99999,
      source: "system",
      message: "SESSION_READY",
      timestamp: new Date().toISOString(),
      observation: "session_ready",
      content: "SESSION_READY",
      extras: { conversation_id: conversationId },
    });

    io.client.on("forge_user_action", async (_, data) => {
      if (isInitConfig(data)) {
        io.client.emit(
          "forge_event",
          generateAgentStateChangeObservation(AgentState.INIT),
        );
      } else {
        io.client.emit(
          "forge_event",
          generateAgentStateChangeObservation(AgentState.RUNNING),
        );

        await delay(2500);
        emitAssistantMessage(io, "Hello!");

        io.client.emit(
          "forge_event",
          generateAgentStateChangeObservation(AgentState.AWAITING_USER_INPUT),
        );
      }
    });
  }),
];
