import { setCurrentAgentState } from "#/state/agent-slice";
import { setUrl } from "#/state/browser-slice";
import store from "#/store";
import { ObservationMessage } from "#/types/message";
import { appendOutput } from "#/state/command-slice";
import { appendJupyterOutput } from "#/state/jupyter-slice";
import ObservationType from "#/types/observation-type";
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

// Helper function to handle Jupyter output
function handleJupyterOutput(message: ObservationMessage) {
  store.dispatch(
    appendJupyterOutput({
      content: message.content,
      imageUrls: Array.isArray(message.extras?.image_urls)
        ? message.extras.image_urls
        : undefined,
    }),
  );
}

// Helper function to handle agent state changes
function handleAgentStateChange(message: ObservationMessage) {
  store.dispatch(setCurrentAgentState(message.extras.agent_state));
}

// Main observation handler using a strategy pattern
const observationHandlers = {
  [ObservationType.RUN]: handleCommandOutput,
  [ObservationType.RUN_IPYTHON]: handleJupyterOutput,
  [ObservationType.BROWSE]: handleBrowserObservation,
  [ObservationType.BROWSE_INTERACTIVE]: handleBrowserObservation,
  [ObservationType.AGENT_STATE_CHANGED]: handleAgentStateChange,
  // These observation types don't need special handling
  [ObservationType.DELEGATE]: () => {},
  [ObservationType.READ]: () => {},
  [ObservationType.EDIT]: () => {},
  [ObservationType.THINK]: () => {},
  [ObservationType.NULL]: () => {},
  [ObservationType.RECALL]: () => {},
  [ObservationType.ERROR]: () => {},
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
