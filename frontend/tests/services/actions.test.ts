import { beforeEach, describe, expect, it, vi } from "vitest";
import ActionType from "#/types/action-type";

const trackErrorMock = vi.hoisted(() => vi.fn());
const appendSecurityAnalyzerInputMock = vi.hoisted(() =>
  vi.fn(() => ({ type: "security/append" })),
);
const setCurStatusMessageMock = vi.hoisted(() =>
  vi.fn(() => ({ type: "status/set" })),
);
const setMetricsMock = vi.hoisted(() => vi.fn(() => ({ type: "metrics/set" })));
const appendInputMock = vi.hoisted(() =>
  vi.fn(() => ({ type: "terminal/input" })),
);
const appendJupyterInputMock = vi.hoisted(() =>
  vi.fn(() => ({ type: "jupyter/input" })),
);
const dispatchMock = vi.hoisted(() => vi.fn());
const invalidateQueriesMock = vi.hoisted(() => vi.fn());
const handleObservationMessageMock = vi.hoisted(() => vi.fn());

vi.mock("#/utils/error-handler", () => ({
  trackError: trackErrorMock,
}));

vi.mock("#/state/security-analyzer-slice", () => ({
  appendSecurityAnalyzerInput: appendSecurityAnalyzerInputMock,
}));

vi.mock("#/state/status-slice", () => ({
  setCurStatusMessage: setCurStatusMessageMock,
}));

vi.mock("#/state/metrics-slice", () => ({
  setMetrics: setMetricsMock,
}));

vi.mock("#/state/command-slice", () => ({
  appendInput: appendInputMock,
}));

vi.mock("#/state/jupyter-slice", () => ({
  appendJupyterInput: appendJupyterInputMock,
}));

vi.mock("#/query-client-config", () => ({
  queryClient: {
    invalidateQueries: invalidateQueriesMock,
  },
}));

vi.mock("#/services/observations", () => ({
  handleObservationMessage: handleObservationMessageMock,
}));

vi.mock("#/store", () => ({
  default: {
    dispatch: dispatchMock,
  },
}));

describe("services/actions", () => {
  let actionsModule: typeof import("#/services/actions");

  beforeEach(async () => {
    vi.resetModules();
    dispatchMock.mockClear();
    trackErrorMock.mockClear();
    appendSecurityAnalyzerInputMock.mockClear();
    setCurStatusMessageMock.mockClear();
    setMetricsMock.mockClear();
    appendInputMock.mockClear();
    appendJupyterInputMock.mockClear();
    invalidateQueriesMock.mockClear();
    handleObservationMessageMock.mockClear();

    actionsModule = await import("#/services/actions");
  });

  describe("handleActionMessage", () => {
    it("skips hidden actions", () => {
      actionsModule.handleActionMessage({
        action: ActionType.RUN,
        args: { hidden: true },
      } as any);

      expect(dispatchMock).not.toHaveBeenCalled();
      expect(appendInputMock).not.toHaveBeenCalled();
    });

    it("dispatches metrics when provided", () => {
      actionsModule.handleActionMessage({
        action: ActionType.MESSAGE,
        args: {},
        llm_metrics: {
          accumulated_cost: 1.25,
          max_budget_per_task: 5,
          accumulated_token_usage: { total_tokens: 10 },
        },
      } as any);

      expect(setMetricsMock).toHaveBeenCalledWith({
        cost: 1.25,
        max_budget_per_task: 5,
        usage: { total_tokens: 10 },
      });
      expect(dispatchMock).toHaveBeenCalledWith({ type: "metrics/set" });

      setMetricsMock.mockClear();
      dispatchMock.mockClear();

      actionsModule.handleActionMessage({
        action: ActionType.MESSAGE,
        args: {},
        llm_metrics: {},
      } as any);

      expect(setMetricsMock).toHaveBeenCalledWith({
        cost: null,
        max_budget_per_task: null,
        usage: null,
      });
      expect(dispatchMock).toHaveBeenCalledWith({ type: "metrics/set" });
    });

    it("forwards run commands to terminal and jupyter inputs", () => {
      actionsModule.handleActionMessage({
        action: ActionType.RUN,
        args: { command: "ls" },
      } as any);

      expect(appendInputMock).toHaveBeenCalledWith("ls");
      expect(dispatchMock).toHaveBeenCalledWith({ type: "terminal/input" });

      dispatchMock.mockClear();
      appendInputMock.mockClear();

      actionsModule.handleActionMessage({
        action: ActionType.RUN_IPYTHON,
        args: { code: "print(1)" },
      } as any);

      expect(appendJupyterInputMock).toHaveBeenCalledWith("print(1)");
      expect(dispatchMock).toHaveBeenCalledWith({ type: "jupyter/input" });
    });

    it("appends security analyzer input when security risk is present", () => {
      const msg = {
        action: ActionType.MESSAGE,
        args: { security_risk: true },
      } as any;

      actionsModule.handleActionMessage(msg);

      expect(appendSecurityAnalyzerInputMock).toHaveBeenCalledWith(msg);
      expect(dispatchMock).toHaveBeenCalledWith({ type: "security/append" });
    });
  });

  describe("handleStatusMessage", () => {
    it("invalidates conversation queries when title changes", () => {
      actionsModule.handleStatusMessage({
        status_update: true,
        type: "info",
        message: "123",
        conversation_title: "New Title",
      });

      expect(invalidateQueriesMock).toHaveBeenCalledWith({
        queryKey: ["user", "conversation", "123"],
      });
    });

    it("dispatches info status updates", () => {
      const message = {
        status_update: true,
        type: "info",
        message: "Loading",
      } as any;

      actionsModule.handleStatusMessage(message);
      expect(setCurStatusMessageMock).toHaveBeenCalledWith(message);
      expect(dispatchMock).toHaveBeenCalledWith({ type: "status/set" });
    });

    it("tracks errors for error status messages", () => {
      actionsModule.handleStatusMessage({
        status_update: true,
        type: "error",
        id: "abc",
        message: "Boom",
      } as any);

      expect(trackErrorMock).toHaveBeenCalledWith({
        message: "Boom",
        source: "chat",
        metadata: { msgId: "abc" },
      });
    });
  });

  describe("handleAssistantMessage", () => {
    it("routes to action handler", () => {
      appendInputMock.mockClear();
      actionsModule.handleAssistantMessage({
        action: ActionType.RUN,
        args: { command: "ls" },
      });

      expect(appendInputMock).toHaveBeenCalledWith("ls");
    });

    it("routes to observation handler", () => {
      const msg = { observation: "run" };
      actionsModule.handleAssistantMessage(msg);

      expect(handleObservationMessageMock).toHaveBeenCalledWith(msg);
    });

    it("routes to status handler", () => {
      invalidateQueriesMock.mockClear();
      actionsModule.handleAssistantMessage({
        type: "info",
        status_update: true,
        message: "123",
        conversation_title: "Title",
      });

      expect(invalidateQueriesMock).toHaveBeenCalledWith({
        queryKey: ["user", "conversation", "123"],
      });
    });

    it("treats objects with type strings as status messages", () => {
      setCurStatusMessageMock.mockClear();
      actionsModule.handleAssistantMessage({
        type: "info",
        message: "Loading",
      });

      expect(setCurStatusMessageMock).toHaveBeenCalledWith({
        type: "info",
        message: "Loading",
      });
    });

    it("ignores non-object payloads", () => {
      actionsModule.handleAssistantMessage(null);
      actionsModule.handleAssistantMessage(undefined);
      actionsModule.handleAssistantMessage("string");

      expect(handleObservationMessageMock).not.toHaveBeenCalled();
      expect(appendInputMock).not.toHaveBeenCalled();
      expect(invalidateQueriesMock).not.toHaveBeenCalled();
    });
  });
});
