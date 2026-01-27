import { beforeEach, describe, expect, it, vi } from "vitest";
import ObservationType from "#/types/observation-type";
import type { ObservationMessage } from "#/types/message";
import { AgentState } from "#/types/agent-state";

const dispatchMock = vi.hoisted(() => vi.fn());
const setUrlMock = vi.hoisted(() => vi.fn(() => ({ type: "browser/setUrl" })));
const appendOutputMock = vi.hoisted(() =>
  vi.fn(() => ({ type: "terminal/append" })),
);
const setCurrentAgentStateMock = vi.hoisted(() =>
  vi.fn(() => ({ type: "agent/setState" })),
);
const startStreamMock = vi.hoisted(() =>
  vi.fn(() => ({ type: "stream/start" })),
);
const appendStreamChunkMock = vi.hoisted(() =>
  vi.fn(() => ({ type: "stream/chunk" })),
);
const completeStreamMock = vi.hoisted(() =>
  vi.fn(() => ({ type: "stream/complete" })),
);

vi.mock("#/state/browser-slice", () => ({
  setUrl: setUrlMock,
}));

vi.mock("#/state/command-slice", () => ({
  appendOutput: appendOutputMock,
}));

vi.mock("#/state/agent-slice", () => ({
  setCurrentAgentState: setCurrentAgentStateMock,
}));

vi.mock("#/store/streaming-slice", () => ({
  startStream: startStreamMock,
  appendStreamChunk: appendStreamChunkMock,
  completeStream: completeStreamMock,
}));

vi.mock("#/store", () => ({
  default: {
    dispatch: dispatchMock,
  },
}));

describe("handleObservationMessage", () => {
  let handleObservationMessage: typeof import("#/services/observations").handleObservationMessage;

  const makeMessage = (
    overrides: Partial<ObservationMessage>,
  ): ObservationMessage =>
    ({
      observation: "",
      id: 1,
      cause: 0,
      content: "",
      message: "",
      timestamp: "",
      ...overrides,
      extras: {
        metadata: {},
        error_id: "",
        hidden: false,
        ...(overrides.extras ?? {}),
      },
    }) as ObservationMessage;

  beforeEach(async () => {
    vi.resetModules();
    dispatchMock.mockClear();
    setUrlMock.mockClear();
    appendOutputMock.mockClear();
    setCurrentAgentStateMock.mockClear();
    startStreamMock.mockClear();
    appendStreamChunkMock.mockClear();
    completeStreamMock.mockClear();

    ({ handleObservationMessage } = await import("#/services/observations"));
  });

  it("streams command output when observation is RUN", () => {
    const message = makeMessage({
      observation: ObservationType.RUN,
      id: 8,
      content: "log",
    });

    handleObservationMessage(message);

    expect(startStreamMock).toHaveBeenCalledWith({ id: "8", type: "terminal" });
    expect(appendStreamChunkMock).toHaveBeenCalledWith({
      id: "8",
      chunk: "log",
    });
    expect(completeStreamMock).toHaveBeenCalledWith("8");
    expect(appendOutputMock).toHaveBeenCalledWith("log");
    expect(dispatchMock).toHaveBeenCalledTimes(4);
  });

  it("skips hidden command output", () => {
    const message = makeMessage({
      observation: ObservationType.RUN,
      extras: { hidden: true, metadata: {}, error_id: "" },
    });

    handleObservationMessage(message);

    expect(startStreamMock).not.toHaveBeenCalled();
    expect(appendOutputMock).not.toHaveBeenCalled();
  });

  it("dispatches agent state changes", () => {
    const message = makeMessage({
      observation: ObservationType.AGENT_STATE_CHANGED,
      extras: { metadata: {}, error_id: "", agent_state: AgentState.ERROR },
    });

    handleObservationMessage(message);
    expect(setCurrentAgentStateMock).toHaveBeenCalledWith(AgentState.ERROR);
  });

  it("handles browser observations and respects hidden flag for string handlers", () => {
    const visibleMessage = makeMessage({
      observation: ObservationType.BROWSE,
      extras: { metadata: {}, error_id: "", url: "https://example.com" },
    });

    handleObservationMessage(visibleMessage);
    expect(setUrlMock).toHaveBeenCalledWith("https://example.com");
    expect(setUrlMock).toHaveBeenCalledTimes(2); // enum + string handler

    const hiddenMessage = makeMessage({
      observation: ObservationType.BROWSE,
      extras: {
        metadata: {},
        error_id: "",
        hidden: true,
        url: "https://hidden",
      },
    });
    setUrlMock.mockClear();

    handleObservationMessage(hiddenMessage);
    expect(setUrlMock).toHaveBeenCalledWith("https://hidden");
    expect(setUrlMock).toHaveBeenCalledTimes(1); // string handler skipped when hidden
  });

  it("ignores observations without special handlers", () => {
    dispatchMock.mockClear();
    const noopTypes: ObservationType[] = [
      ObservationType.READ,
      ObservationType.EDIT,
      ObservationType.THINK,
      ObservationType.NULL,
      ObservationType.RECALL,
      ObservationType.ERROR,
      ObservationType.MCP,
      ObservationType.TASK_TRACKING,
    ];

    noopTypes.forEach((type) => {
      handleObservationMessage(
        makeMessage({
          observation: type,
          extras: { metadata: {}, error_id: "" },
        }),
      );
    });

    expect(dispatchMock).not.toHaveBeenCalled();
  });
});
