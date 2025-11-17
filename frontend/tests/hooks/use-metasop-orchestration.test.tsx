import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

const parsedEventsRef = { current: [] as any[] };

let statusId = 0;
const makeStatusEvent = (message: string) => ({
  status_update: true,
  type: "status",
  id: `status-${statusId++}`,
  message,
});

vi.mock("#/context/ws-client-provider", () => ({
  useWsClient: () => ({ parsedEvents: parsedEventsRef.current }),
}));

import {
  useMetaSOPOrchestration,
  OrchestrationStep,
} from "#/hooks/use-metasop-orchestration";

const DATE_NOW = new Date("2025-01-01T00:00:00.000Z");

describe("useMetaSOPOrchestration", () => {
  beforeEach(() => {
    parsedEventsRef.current = [];
    vi.useFakeTimers();
    vi.setSystemTime(DATE_NOW);
    statusId = 0;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("starts orchestration and resets steps", () => {
    const { result, rerender } = renderHook(() => useMetaSOPOrchestration());

    act(() => {
      parsedEventsRef.current = [
        makeStatusEvent("MetaSOP orchestration started"),
      ];
      rerender();
    });

    expect(result.current.isOrchestrating).toBe(true);
    expect(result.current.steps).toEqual([]);
  });

  it("marks running step success on orchestration completion", () => {
    const { result, rerender } = renderHook(() => useMetaSOPOrchestration());

    act(() => {
      parsedEventsRef.current = [
        makeStatusEvent("metasop step step:step-1 role:planner status:running"),
      ];
      rerender();
    });

    act(() => {
      parsedEventsRef.current = [
        ...parsedEventsRef.current,
        makeStatusEvent("MetaSOP orchestration completed"),
      ];
      rerender();
    });

    expect(result.current.isOrchestrating).toBe(false);
    return waitFor(() =>
      expect(result.current.steps.at(-1)?.status).toBe("success"),
    );
  });

  it("attaches artifact references and data", async () => {
    const { result, rerender } = renderHook(() => useMetaSOPOrchestration());

    act(() => {
      parsedEventsRef.current = [
        makeStatusEvent("metasop step step:step-1 role:planner status:executed"),
      ];
      rerender();
    });

    expect(result.current.steps).toHaveLength(1);
    expect(result.current.steps[0].status).toBe("executed");

    act(() => {
      parsedEventsRef.current = [
        ...parsedEventsRef.current,
        makeStatusEvent("artifact:hash123 step:step-1 type:json"),
      ];
      rerender();
    });

    await waitFor(() => expect(result.current.steps.at(-1)?.artifact_hash).toBe("hash123"));

    act(() => {
      parsedEventsRef.current = [
        ...parsedEventsRef.current,
        makeStatusEvent("metasop step step:step-1 role:planner status:success"),
      ];
      rerender();
    });

    act(() => {
      parsedEventsRef.current = [
        ...parsedEventsRef.current,
        makeStatusEvent("```json {\"result\":true} ```"),
      ];
      rerender();
    });

    await waitFor(() => {
      const step = result.current.steps.at(-1);
      expect(step?.artifact).toEqual({ result: true });
    });
  });

  it("ignores artifact reference when no executed step", () => {
    const { result, rerender } = renderHook(() => useMetaSOPOrchestration());

    act(() => {
      parsedEventsRef.current = [makeStatusEvent("artifact:hash123 step:step-1 type:json")];
      rerender();
    });

    expect(result.current.steps.at(-1)?.artifact_hash).toBeUndefined();
  });

  it("ignores invalid artifact json payloads", () => {
    const { result, rerender } = renderHook(() => useMetaSOPOrchestration());

    act(() => {
      parsedEventsRef.current = [
        makeStatusEvent("metasop step step:step-1 role:planner status:running"),
      ];
      rerender();
    });

    act(() => {
      parsedEventsRef.current = [
        ...parsedEventsRef.current,
        makeStatusEvent("metasop step step:step-1 role:planner status:executed"),
        makeStatusEvent("artifact:hash123 step:step-1 type:json"),
      ];
      rerender();
    });

    act(() => {
      parsedEventsRef.current = [
        ...parsedEventsRef.current,
        makeStatusEvent("```json invalid```"),
      ];
      rerender();
    });

    expect(result.current.steps.at(-1)?.artifact).not.toEqual({ result: true });
  });

  it("ignores non-metasop observations", () => {
    const { result, rerender } = renderHook(() => useMetaSOPOrchestration());

    act(() => {
      parsedEventsRef.current = [
        {
          observation: "other_step",
          extras: {
            step_id: "obs-2",
          },
        },
      ];
      rerender();
    });

    expect(result.current.steps).toHaveLength(0);
  });

  it("handles step failure messages", () => {
    const { result, rerender } = renderHook(() => useMetaSOPOrchestration());

    act(() => {
      parsedEventsRef.current = [
        makeStatusEvent("metasop step step:step-1 role:planner status:running"),
      ];
      rerender();
    });

    act(() => {
      parsedEventsRef.current = [
        ...parsedEventsRef.current,
        makeStatusEvent("Step failed due to timeout"),
      ];
      rerender();
    });

    return waitFor(() => {
      const step = result.current.steps.at(-1);
      expect(step?.status).toBe("failed");
      expect(step?.error).toContain("Step failed");
    });
  });

  it("extracts metasop observation events", () => {
    const { result, rerender } = renderHook(() => useMetaSOPOrchestration());

    act(() => {
      parsedEventsRef.current = [
        ...parsedEventsRef.current,
        {
          observation: "metasop_step",
          extras: {
            step_id: "obs-1",
            role: "observer",
            status: "pending",
            artifact: { foo: "bar" },
            artifact_hash: "hash",
          },
        },
      ];
      rerender();
    });

    return waitFor(() => {
      expect(result.current.steps).toHaveLength(1);
      expect(result.current.steps[0].step_id).toBe("obs-1");
    });
  });

  it("clearSteps resets state", () => {
    const { result, rerender } = renderHook(() => useMetaSOPOrchestration());

    act(() => {
      parsedEventsRef.current = [
        makeStatusEvent("metasop step step:step-1 role:planner status:running"),
      ];
      rerender();
    });

    act(() => {
      result.current.clearSteps();
    });

    expect(result.current.steps).toEqual([]);
    expect(result.current.isOrchestrating).toBe(false);
    expect(result.current.hasSteps).toBe(false);
  });
});
