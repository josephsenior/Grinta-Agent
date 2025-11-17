import { renderHook, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { store, displayErrorToastMock, generateAgentStateChangeEventMock } = vi.hoisted(() => ({
  store: {
    events: [] as Array<Record<string, any>>,
    send: vi.fn(),
  },
  displayErrorToastMock: vi.fn(),
  generateAgentStateChangeEventMock: vi.fn(),
}));

vi.mock("#/context/ws-client-provider", () => ({
  useWsClient: () => ({
    get events() {
      return store.events;
    },
    get send() {
      return store.send;
    },
  }),
}));

vi.mock("#/utils/custom-toast-handlers", () => ({
  displayErrorToast: displayErrorToastMock,
}));

vi.mock("#/services/agent-state-service", () => ({
  generateAgentStateChangeEvent: generateAgentStateChangeEventMock,
}));

import { AgentState } from "#/types/agent-state";
import { useHandleWSEvents } from "#/hooks/use-handle-ws-events";

describe("useHandleWSEvents", () => {
  beforeEach(() => {
    store.events = [];
    store.send.mockClear();
    displayErrorToastMock.mockClear();
    generateAgentStateChangeEventMock.mockClear();
  });

  const render = () => renderHook(() => useHandleWSEvents());

  it("does nothing when there are no events", () => {
    store.events = [];
    render();

    expect(displayErrorToastMock).not.toHaveBeenCalled();
    expect(store.send).not.toHaveBeenCalled();
  });

  it("shows session expired toast for 401 errors", () => {
    store.events = [{ error: true, message: "Expired", error_code: 401 }];

    render();

    expect(displayErrorToastMock).toHaveBeenCalledWith("Session expired.");
    expect(store.send).not.toHaveBeenCalled();
  });

  it("shows string error value", () => {
    store.events = [{ error: "Something went wrong", message: "Ignored" }];

    render();

    expect(displayErrorToastMock).toHaveBeenCalledWith("Something went wrong");
  });

  it("falls back to message when error is boolean", () => {
    store.events = [{ error: true, message: "Fallback message" }];

    render();

    expect(displayErrorToastMock).toHaveBeenCalledWith("Fallback message");
  });

  it("pauses agent when max iterations reached", () => {
    const pauseEvent = { type: "error", message: "Agent reached maximum iterations" };
    const pauseAction = { type: "agent", payload: AgentState.PAUSED };
    generateAgentStateChangeEventMock.mockReturnValue(pauseAction);
    store.events = [pauseEvent];

    render();

    expect(generateAgentStateChangeEventMock).toHaveBeenCalledWith(AgentState.PAUSED);
    expect(store.send).toHaveBeenCalledWith(pauseAction);
  });

  it("responds to subsequent events on rerender", () => {
    const { rerender } = render();

    act(() => {
      store.events = [{ error: true, message: "first" }];
      rerender();
    });

    expect(displayErrorToastMock).toHaveBeenLastCalledWith("first");

    act(() => {
      store.events = [
        { error: true, message: "placeholder" },
        { error: true, message: "ignored", error_code: 401 },
      ];
      rerender();
    });

    expect(displayErrorToastMock).toHaveBeenLastCalledWith("Session expired.");

    act(() => {
      generateAgentStateChangeEventMock.mockReturnValueOnce({ pause: true });
      store.events = [{ type: "error", message: "Agent reached maximum steps" }];
      rerender();
    });

    expect(store.send).toHaveBeenCalledWith({ pause: true });
  });
});
