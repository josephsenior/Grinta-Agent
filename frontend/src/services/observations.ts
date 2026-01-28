import { setCurrentAgentState } from "#/state/agent-slice";
import { setUrl } from "#/state/browser-slice";
import store from "#/store";
import { ObservationMessage } from "#/types/message";
import { appendOutput } from "#/state/command-slice";
import ObservationType from "#/types/observation-type";
import { AgentState } from "#/types/agent-state";
import { setCurStatusMessage } from "#/state/status-slice";
import {
  startStream,
  appendStreamChunk,
  completeStream,
} from "#/store/streaming-slice";

// Helper function to handle browser-related observations
function handleBrowserObservation(message: ObservationMessage) {
  // Only track URL for agent navigation sync with InteractiveBrowser
  if (message.extras?.url) {
    store.dispatch(setUrl(message.extras.url));
  }
  // Note: Screenshots are no longer displayed - agent Playwright actions
  // still work, but we don't clutter the UI with static snapshots
}

// Helper function to handle command output (NO MORE TRUNCATION!)
function handleCommandOutput(message: ObservationMessage) {
  if (message.extras.hidden) {
    return;
  }

  const { content } = message;
  const eventId = String(message.id);

  // Enable streaming for terminal output
  store.dispatch(
    startStream({
      id: eventId,
      type: "terminal",
    }),
  );

  // Add content to stream (will be displayed progressively by StreamingTerminal)
  store.dispatch(
    appendStreamChunk({
      id: eventId,
      chunk: content,
    }),
  );

  // Mark stream as complete
  store.dispatch(completeStream(eventId));

  // Also append to terminal output store for compatibility
  store.dispatch(appendOutput(content));
}

// Helper function to handle agent state changes
function handleAgentStateChange(message: ObservationMessage) {
  const state = message.extras.agent_state as AgentState;
  store.dispatch(setCurrentAgentState(state));

  // If entering error state, also update the status message
  if (state === AgentState.ERROR) {
    store.dispatch(
      setCurStatusMessage({
        type: "error",
        message: String(message.content || message.message || message.extras.reason || "An error occurred"),
        status_update: true,
      }),
    );
  }
}

// Helper function to handle error observations
function handleErrorObservation(message: ObservationMessage) {
  store.dispatch(setCurrentAgentState(AgentState.ERROR));
  
  // Try to parse structured error data from content
  let errorMessage = message.content || message.message || "An error occurred";
  let errorData: unknown = null;
  
  // Check if content is JSON with user-friendly error format
  if (message.content) {
    try {
      const parsed = JSON.parse(message.content);
      if (parsed && typeof parsed === "object" && "title" in parsed && "message" in parsed) {
        errorData = parsed;
        errorMessage = parsed.message || parsed.title || errorMessage;
      }
    } catch {
      // Not JSON, use as-is
    }
  }
  
  store.dispatch(
    setCurStatusMessage({
      type: "error",
      message: errorMessage,
      status_update: true,
      errorData: errorData, // Include structured error data if available
    }),
  );
}

// Main observation handler using a strategy pattern
const observationHandlers = {
  [ObservationType.RUN]: handleCommandOutput,
  [ObservationType.BROWSE]: handleBrowserObservation,
  [ObservationType.BROWSE_INTERACTIVE]: handleBrowserObservation,
  [ObservationType.AGENT_STATE_CHANGED]: handleAgentStateChange,
  // These observation types don't need special handling
  [ObservationType.READ]: () => {},
  [ObservationType.EDIT]: () => {},
  [ObservationType.THINK]: () => {},
  [ObservationType.NULL]: () => {},
  [ObservationType.RECALL]: () => {},
  [ObservationType.ERROR]: handleErrorObservation,
  [ObservationType.MCP]: () => {},
  [ObservationType.TASK_TRACKING]: () => {},
};

// String-based observation handlers for backward compatibility
const stringObservationHandlers = {
  browse: handleBrowserObservation,
  browse_interactive: handleBrowserObservation,
};

export function handleObservationMessage(message: ObservationMessage) {
  // Handle enum-based observations
  const enumHandler =
    observationHandlers[
      message.observation as keyof typeof observationHandlers
    ];
  if (enumHandler) {
    enumHandler(message);
  }

  // Handle string-based observations if not hidden
  if (!message.extras?.hidden) {
    const stringHandler =
      stringObservationHandlers[
        message.observation as keyof typeof stringObservationHandlers
      ];
    if (stringHandler) {
      stringHandler(message);
    }
  }
}
