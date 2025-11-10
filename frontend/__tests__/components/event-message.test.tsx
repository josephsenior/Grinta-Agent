import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils";
import { EventMessage, looksLikeShell } from "#/components/features/chat/event-message";
import { AgentState } from "#/types/agent-state";
import { MicroagentStatus } from "#/types/microagent-status";
import { ActionSecurityRisk } from "#/state/security-analyzer-slice";

vi.mock("#/hooks/query/use-config", () => ({
  useConfig: () => ({
    data: { APP_MODE: "saas" },
  }),
}));

vi.mock("#/hooks/query/use-feedback-exists", () => ({
  useFeedbackExists: (eventId: number | undefined) => ({
    data: { exists: false },
    isLoading: false,
  }),
}));

const wsClientMock = {
  hydratedEventIds: new Set<string>(),
  parsedEvents: [] as Array<Record<string, unknown>>,
  send: vi.fn(),
};

vi.mock("#/context/ws-client-provider", () => ({
  useWsClient: () => wsClientMock,
}));

describe("EventMessage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  beforeEach(() => {
    wsClientMock.hydratedEventIds = new Set<string>();
    wsClientMock.parsedEvents = [];
    wsClientMock.send = vi.fn();
  });

  const createStreamingState = () => ({
    activeStreams: {},
    chunks: {},
    progress: {},
    currentOperation: null,
    streams: {},
    enableStreaming: true,
    streamSpeed: 16,
  });

  it("should render LikertScale for finish action when it's the last message", () => {
    const finishEvent = {
      id: 123,
      source: "agent" as const,
      action: "finish" as const,
      args: {
        final_thought: "Task completed successfully",
        outputs: {},
        thought: "Task completed successfully",
      },
      message: "Task completed successfully",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={finishEvent}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
      />,
    );

    expect(screen.getByLabelText("Rate 1 star")).toBeInTheDocument();
    expect(screen.getByLabelText("Rate 5 stars")).toBeInTheDocument();
  });

  it("should render LikertScale for assistant message when it's the last message", () => {
    const assistantMessageEvent = {
      id: 456,
      source: "agent" as const,
      action: "message" as const,
      args: {
        thought: "I need more information to proceed.",
        image_urls: null,
        file_urls: [],
        wait_for_response: true,
      },
      message: "I need more information to proceed.",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={assistantMessageEvent}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
      />,
    );

    expect(screen.getByLabelText("Rate 1 star")).toBeInTheDocument();
    expect(screen.getByLabelText("Rate 5 stars")).toBeInTheDocument();
  });

  it("should render LikertScale for error observation when it's the last message", () => {
    const errorEvent = {
      id: 789,
      source: "user" as const,
      observation: "error" as const,
      content: "An error occurred",
      extras: {
        error_id: "test-error-123",
      },
      message: "An error occurred",
      timestamp: new Date().toISOString(),
      cause: 123,
    };

    renderWithProviders(
      <EventMessage
        event={errorEvent}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
      />,
    );

    expect(screen.getByLabelText("Rate 1 star")).toBeInTheDocument();
    expect(screen.getByLabelText("Rate 5 stars")).toBeInTheDocument();
  });

  it("should NOT render LikertScale when not the last message", () => {
    const finishEvent = {
      id: 101,
      source: "agent" as const,
      action: "finish" as const,
      args: {
        final_thought: "Task completed successfully",
        outputs: {},
        thought: "Task completed successfully",
      },
      message: "Task completed successfully",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={finishEvent}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage={false}
        isInLast10Actions={false}
      />,
    );

    expect(screen.queryByLabelText("Rate 1 star")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Rate 5 stars")).not.toBeInTheDocument();
  });

  it("should render LikertScale for error observation when in last 10 actions but not last message", () => {
    const errorEvent = {
      id: 999,
      source: "user" as const,
      observation: "error" as const,
      content: "An error occurred",
      extras: {
        error_id: "test-error-456",
      },
      message: "An error occurred",
      timestamp: new Date().toISOString(),
      cause: 123,
    };

    renderWithProviders(
      <EventMessage
        event={errorEvent}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage={false}
        isInLast10Actions
      />,
    );

    expect(screen.getByLabelText("Rate 1 star")).toBeInTheDocument();
    expect(screen.getByLabelText("Rate 5 stars")).toBeInTheDocument();
  });

  it("should NOT render LikertScale for error observation when not in last 10 actions", () => {
    const errorEvent = {
      id: 888,
      source: "user" as const,
      observation: "error" as const,
      content: "An error occurred",
      extras: {
        error_id: "test-error-789",
      },
      message: "An error occurred",
      timestamp: new Date().toISOString(),
      cause: 123,
    };

    renderWithProviders(
      <EventMessage
        event={errorEvent}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage={false}
        isInLast10Actions={false}
      />,
    );

    expect(screen.queryByLabelText("Rate 1 star")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Rate 5 stars")).not.toBeInTheDocument();
  });

  it("renders error observation details when expanded", () => {
    const errorEvent = {
      id: 321,
      source: "user" as const,
      observation: "error" as const,
      content: "Detailed failure message",
      extras: {
        error_id: "CHAT_INTERFACE$AGENT_ERROR_MESSAGE",
      },
      cause: 1,
      message: "Detailed failure message",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={errorEvent}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
      />,
    );

    const toggle = screen.getByRole("button", { name: "Show error details" });
    fireEvent.click(toggle);
    expect(screen.getByText("Detailed failure message")).toBeInTheDocument();
  });

  it("renders streaming chunk agent message", async () => {
    const streamingEvent = {
      id: 654,
      source: "agent" as const,
      action: "streaming_chunk" as const,
      args: {
        chunk: "Partial response...",
        accumulated: "Partial response...",
        is_final: false,
      },
      message: "",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={streamingEvent}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.LOADING },
          streaming: {
            activeStreams: {},
            chunks: {
              "654": ["Partial response..."],
            },
            progress: {},
            currentOperation: null,
            streams: {},
            enableStreaming: true,
            streamSpeed: 16,
          },
        },
      },
    );

    expect(await screen.findByText(/Partial response/)).toBeInTheDocument();
  });

  it("renders file write action with created badge", () => {
    const fileWriteEvent = {
      id: 789,
      source: "agent" as const,
      action: "write" as const,
      args: {
        path: "src/new-file.ts",
        content: "console.log('Hello');",
        thought: "Creating new file",
      },
      message: "",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={fileWriteEvent}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.LOADING },
        },
      },
    );

    expect(screen.getByText("src/new-file.ts")).toBeInTheDocument();
    expect(screen.getByText("Created")).toBeInTheDocument();
  });

  it("renders file edit action with modified badge", () => {
    const fileEditEvent = {
      id: 778,
      source: "agent" as const,
      action: "edit" as const,
      args: {
        path: "src/existing-file.ts",
        content: "export const value = 42;",
        thought: "Updating file",
        security_risk: ActionSecurityRisk.LOW,
      },
      message: "",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={fileEditEvent}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.LOADING },
        },
      },
    );

    expect(screen.getByText("src/existing-file.ts")).toBeInTheDocument();
    expect(screen.getByText("Modified")).toBeInTheDocument();
  });

  it("should render run observation with streaming terminal output", () => {
    const runEvent = {
      id: 901,
      source: "agent" as const,
      observation: "run" as const,
      content: "npm install react",
      extras: {
        command: "npm install react",
        exit_code: 0,
      },
      cause: 900,
      message: "",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={runEvent as any}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.LOADING },
          streaming: createStreamingState(),
        },
      },
    );

    expect(screen.getByText("Terminal Output")).toBeInTheDocument();
    expect(screen.getAllByText("npm install react")).toHaveLength(2);
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("should render generic event details when technical details are shown", () => {
    const genericEvent = {
      id: 902,
      source: "agent" as const,
      observation: "custom" as const,
      title: "Deployment Status",
      content: "Deployment succeeded",
      extras: {},
      cause: 901,
      message: "",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={genericEvent as any}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
        showTechnicalDetails
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.LOADING },
          streaming: createStreamingState(),
        },
      },
    );

    expect(screen.getByText("Deployment Status")).toBeInTheDocument();
  });

  it("should render attachments and microagent status indicator for assistant message", () => {
    const assistantMessageEvent = {
      id: 903,
      source: "agent" as const,
      action: "message" as const,
      args: {
        thought: "Showing attachments",
        message: "Please review the attachments.",
        image_urls: ["https://example.com/image.png"],
        file_urls: ["report.pdf"],
        wait_for_response: false,
      },
      message: "Please review the attachments.",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={assistantMessageEvent}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
        microagentStatus={MicroagentStatus.COMPLETED}
        microagentConversationId="conversation-123"
        microagentPRUrl="https://example.com/pr"
        actions={[]}
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.LOADING },
          streaming: createStreamingState(),
        },
      },
    );

    expect(screen.getAllByTestId("image-preview")).toHaveLength(1);
    expect(screen.getByTestId("file-item")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "MICROAGENT$VIEW_YOUR_PR" }),
    ).toHaveAttribute("href", "https://example.com/pr");
  });

  it("should render streaming code artifact when agent is running", () => {
    const fileEditEvent = {
      id: 904,
      source: "agent" as const,
      action: "edit" as const,
      args: {
        path: "src/stream-file.ts",
        content: "export const value = 1;",
        thought: "Update the default export",
        security_risk: ActionSecurityRisk.LOW,
      },
      message: "",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={fileEditEvent}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.RUNNING },
          streaming: createStreamingState(),
        },
      },
    );

    expect(screen.getByText("src/stream-file.ts")).toBeInTheDocument();
    expect(screen.getByText(/Streaming$/)).toBeInTheDocument();
    expect(screen.getByText("Editing")).toBeInTheDocument();
  });

  it("should not render when technical details are hidden for non-critical events", () => {
    const hiddenEvent = {
      id: 905,
      source: "agent" as const,
      observation: "null" as const,
      content: "",
      extras: {},
      cause: 904,
      message: "",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={hiddenEvent as any}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions={false}
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.LOADING },
          streaming: createStreamingState(),
        },
      },
    );

    expect(screen.queryByTestId("agent-message")).toBeNull();
    expect(screen.queryByTestId("user-message")).toBeNull();
  });

  it("should render paired thought content when an action includes a thought", () => {
    const pairedThoughtEvent = {
      id: 906,
      source: "agent" as const,
      action: "write" as const,
      args: {
        thought: "Summarize the latest changes",
        path: "src/summary.txt",
        content: "Summary content",
      },
      message: "",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={pairedThoughtEvent}
        hasObservationPair
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
        actions={[]}
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.LOADING },
          streaming: createStreamingState(),
        },
      },
    );

    expect(screen.getByText("Summarize the latest changes")).toBeInTheDocument();
  });

  it("should render microagent indicator for paired actions without thoughts", () => {
    const pairedIndicatorEvent = {
      id: 907,
      source: "agent" as const,
      action: "write" as const,
      args: {
        path: "src/file.ts",
        content: "const value = 1;",
        thought: "",
      },
      message: "",
      timestamp: new Date().toISOString(),
    };

    renderWithProviders(
      <EventMessage
        event={pairedIndicatorEvent}
        hasObservationPair
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
        microagentStatus={MicroagentStatus.WAITING}
        actions={[]}
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.LOADING },
          streaming: createStreamingState(),
        },
      },
    );

    expect(screen.getByText("MICROAGENT$STATUS_WAITING")).toBeInTheDocument();
  });

  it("should render reject observations with their message content", () => {
    const rejectObservation = {
      id: 908,
      source: "agent" as const,
      observation: "user_rejected" as const,
      content: "I cannot proceed without credentials.",
      message: "",
      timestamp: new Date().toISOString(),
      extras: {},
      cause: 1,
    };

    renderWithProviders(
      <EventMessage
        event={rejectObservation}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
        showTechnicalDetails
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.LOADING },
          streaming: createStreamingState(),
        },
      },
    );

    const rejectMessage = screen.getByTestId("agent-message");
    expect(rejectMessage).toHaveTextContent(
      "I cannot proceed without credentials.",
    );
  });

  it("should render MCP observations with their title and details", () => {
    const mcpObservation = {
      id: 909,
      source: "agent" as const,
      observation: "mcp" as const,
      title: "Tool Invocation",
      content: "Executed external tool successfully.",
      message: "",
      timestamp: new Date().toISOString(),
      extras: {
        name: "external_tool",
        arguments: { key: "value" },
      },
      cause: 1,
    };

    renderWithProviders(
      <EventMessage
        event={mcpObservation}
        hasObservationPair={false}
        isAwaitingUserConfirmation
        isLastMessage
        isInLast10Actions
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.LOADING },
          streaming: createStreamingState(),
        },
      },
    );

    expect(screen.getByText("Tool Invocation")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Tool Invocation"));
    expect(screen.getByText("MCP_OBSERVATION$ARGUMENTS")).toBeInTheDocument();
    expect(screen.getByText("MCP_OBSERVATION$OUTPUT")).toBeInTheDocument();
  });

  it("should process task tracking observations", () => {
    const taskTrackingObservation = {
      id: 910,
      source: "agent" as const,
      observation: "task_tracking" as const,
      content: "",
      message: "",
      timestamp: new Date().toISOString(),
      extras: {
        command: "plan",
        task_list: [
          { id: "1", title: "Review code", status: "in_progress" },
          { id: "2", title: "Update tests", status: "todo" },
        ],
      },
      cause: 1,
    };

    renderWithProviders(
      <EventMessage
        event={taskTrackingObservation as any}
        hasObservationPair={false}
        isAwaitingUserConfirmation={false}
        isLastMessage
        isInLast10Actions
      />,
      {
        preloadedState: {
          agent: { curAgentState: AgentState.LOADING },
          streaming: createStreamingState(),
        },
      },
    );

    // The component returns null, but reaching this point exercises the task tracking branch.
    expect(screen.queryByText("Review code")).toBeNull();
  });
});

describe("looksLikeShell", () => {
  it("detects shell-like commands", () => {
    expect(looksLikeShell("npm install")).toBe(true);
    expect(looksLikeShell("git clone https://example.com")).toBe(true);
    expect(looksLikeShell("cd /app && ls")).toBe(true);
    expect(looksLikeShell("Ran npm test")).toBe(true);
  });

  it("returns false for non-shell content", () => {
    expect(looksLikeShell("Hello world")).toBe(false);
    expect(looksLikeShell("This is just plain text")).toBe(false);
    expect(looksLikeShell(null)).toBe(false);
  });
});
