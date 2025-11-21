import { useReducer, useEffect, useCallback, useState } from "react";
import { useWsClient } from "#/context/ws-client-provider";
import { isStatusUpdate } from "#/types/core/guards";

export interface OrchestrationStep {
  step_id: string;
  role: string;
  status: "pending" | "running" | "success" | "failed";
  artifact?: any;
  artifact_hash?: string;
  error?: string;
  timestamp?: string;
}

// MetaSOPEvent interface for type safety when working with MetaSOP events
export interface MetaSOPEvent {
  type: "metasop_step_start" | "metasop_step_complete" | "metasop_step_failed";
  step_id: string;
  role: string;
  artifact?: any;
  artifact_hash?: string;
  error?: string;
  timestamp?: string;
  message?: string;
  observation?: "metasop_step";
  extras?: {
    step_id?: string;
    role?: string;
    status?: "pending" | "running" | "success" | "failed";
    artifact?: any;
    artifact_hash?: string;
  };
}

type MetaSopAction =
  | { type: "RESET" }
  | { type: "UPSERT_STEP"; payload: OrchestrationStep }
  | {
      type: "ATTACH_ARTIFACT_REFERENCE";
      payload: {
        stepId: string;
        artifact: { hash: string; type: string; timestamp: string };
      };
    }
  | { type: "ATTACH_ARTIFACT_DATA"; payload: { artifact: unknown } }
  | { type: "FAIL_RUNNING_STEP"; payload: { error: string } }
  | { type: "MARK_RUNNING_SUCCESS" };

// Helper functions defined before they're used
function getLatestEvent(events: unknown[] | undefined) {
  if (!Array.isArray(events) || events.length === 0) {
    return undefined;
  }
  return events[events.length - 1];
}

function extractMetaSopMessage(event: unknown): string | null {
  // Type guard for status update events
  if (isStatusUpdate(event) && typeof event.message === "string") {
    return event.message;
  }

  // Type guard for MetaSOP events
  if (
    event &&
    typeof event === "object" &&
    "message" in event &&
    typeof event.message === "string"
  ) {
    return event.message;
  }

  return null;
}

function extractMetaSopObservation(event: unknown): OrchestrationStep | null {
  // Type guard for MetaSOP observation events
  if (!event || typeof event !== "object") {
    return null;
  }

  const metaSopEvent = event as Partial<MetaSOPEvent>;
  if (metaSopEvent.observation !== "metasop_step") {
    return null;
  }

  const extras = metaSopEvent.extras || {};
  return {
    step_id: extras.step_id || metaSopEvent.step_id || "unknown",
    role: extras.role || metaSopEvent.role || "Unknown",
    status: extras.status || "pending",
    artifact: extras.artifact || metaSopEvent.artifact,
    artifact_hash: extras.artifact_hash || metaSopEvent.artifact_hash,
    timestamp: metaSopEvent.timestamp || new Date().toISOString(),
  };
}

function isOrchestrationStartMessage(message: string): boolean {
  return (
    message.includes("MetaSOP orchestration started") ||
    message.includes("Running SOP:")
  );
}

function isOrchestrationEndMessage(message: string): boolean {
  return (
    message.includes("MetaSOP orchestration completed") ||
    message.includes("MetaSOP finished successfully") ||
    message.includes("MetaSOP failed") ||
    message.includes("Orchestration complete") ||
    message.includes("All steps completed")
  );
}

function parseStepEvent(message: string) {
  const match = message.match(/step:(\S+)\s+role:([^:]+)\s+status:(\S+)/i);
  if (!match) {
    return null;
  }

  const [, stepId, role, status] = match;
  return {
    step_id: stepId,
    role: role.trim(),
    status: status.toLowerCase() as OrchestrationStep["status"],
  };
}

function parseArtifactReference(message: string) {
  const match = message.match(/artifact:(\S+)\s+step:(\S+)\s+type:(\S+)/i);
  if (!match) {
    return null;
  }

  const [, artifactHash, stepId, artifactType] = match;
  return { artifactHash, stepId, artifactType };
}

function findMostRecentExecutedStepId(events: unknown[] | undefined) {
  if (!Array.isArray(events)) {
    return undefined;
  }

  for (let i = events.length - 1; i >= 0; i -= 1) {
    const event = events[i];
    if (isStatusUpdate(event) && typeof event.message === "string") {
      const match = event.message.match(
        /step:(\S+)\s+role:([^:]+)\s+status:(\S+)/i,
      );
      if (match && match[3] === "executed") {
        return match[1];
      }
    }
  }

  return undefined;
}

function parseArtifactJson(message: string) {
  const jsonMatch = message.match(/```json\s*([\s\S]*?)\s*```/i);
  if (!jsonMatch) {
    return null;
  }

  try {
    return JSON.parse(jsonMatch[1]);
  } catch (error) {
    return null;
  }
}

function isStepFailureMessage(message: string): boolean {
  return message.includes("Step failed") || message.includes("Error in step");
}

function upsertStep(state: OrchestrationStep[], payload: OrchestrationStep) {
  const index = state.findIndex((step) => step.step_id === payload.step_id);
  if (index >= 0) {
    const updated = [...state];
    updated[index] = { ...payload };
    return updated;
  }
  return [...state, payload];
}

function attachArtifactData(state: OrchestrationStep[], artifact: unknown) {
  const updated = [...state];
  for (let i = updated.length - 1; i >= 0; i -= 1) {
    if (updated[i].status === "success") {
      updated[i] = {
        ...updated[i],
        artifact,
      };
      break;
    }
  }
  return updated;
}

function failRunningStep(state: OrchestrationStep[], error: string) {
  const updated = [...state];
  const index = updated.findIndex((step) => step.status === "running");
  if (index >= 0) {
    updated[index] = {
      ...updated[index],
      status: "failed",
      error,
      timestamp: new Date().toISOString(),
    };
  }
  return updated;
}

const META_SOP_REDUCER_HANDLERS: {
  [Type in MetaSopAction["type"]]: (
    state: OrchestrationStep[],
    action: Extract<MetaSopAction, { type: Type }>,
  ) => OrchestrationStep[];
} = {
  RESET: () => [],
  UPSERT_STEP: (state, action) => upsertStep(state, action.payload),
  ATTACH_ARTIFACT_REFERENCE: (state, action) =>
    state.map((step) =>
      step.step_id === action.payload.stepId
        ? {
            ...step,
            artifact: action.payload.artifact,
            artifact_hash: action.payload.artifact.hash,
          }
        : step,
    ),
  ATTACH_ARTIFACT_DATA: (state, action) =>
    attachArtifactData(state, action.payload.artifact),
  FAIL_RUNNING_STEP: (state, action) =>
    failRunningStep(state, action.payload.error),
  MARK_RUNNING_SUCCESS: (state) =>
    state.map((step) =>
      step.status === "running"
        ? {
            ...step,
            status: "success",
            timestamp: new Date().toISOString(),
          }
        : step,
    ),
};

function metaSopReducer(
  state: OrchestrationStep[],
  action: MetaSopAction,
): OrchestrationStep[] {
  const handler = META_SOP_REDUCER_HANDLERS[action.type];
  if (!handler) {
    return state;
  }
  return handler(state, action as any);
}

function handleMetaSopMessage(
  message: string,
  context: {
    dispatch: React.Dispatch<MetaSopAction>;
    setIsOrchestrating: (value: boolean) => void;
    parsedEvents: unknown[] | undefined;
  },
): void {
  if (isOrchestrationStartMessage(message)) {
    context.setIsOrchestrating(true);
    context.dispatch({ type: "RESET" });
    return;
  }

  if (isOrchestrationEndMessage(message)) {
    context.setIsOrchestrating(false);
    context.dispatch({ type: "MARK_RUNNING_SUCCESS" });
    return;
  }

  const stepEvent = parseStepEvent(message);
  if (stepEvent) {
    context.dispatch({
      type: "UPSERT_STEP",
      payload: {
        ...stepEvent,
        timestamp: new Date().toISOString(),
      },
    });
    return;
  }

  const artifactReference = parseArtifactReference(message);
  if (artifactReference) {
    const executedStepId = findMostRecentExecutedStepId(context.parsedEvents);
    if (executedStepId) {
      context.dispatch({
        type: "ATTACH_ARTIFACT_REFERENCE",
        payload: {
          stepId: executedStepId,
          artifact: {
            hash: artifactReference.artifactHash,
            type: artifactReference.artifactType,
            timestamp: new Date().toISOString(),
          },
        },
      });
    }
    return;
  }

  const artifactData = parseArtifactJson(message);
  if (artifactData) {
    context.dispatch({
      type: "ATTACH_ARTIFACT_DATA",
      payload: { artifact: artifactData },
    });
    return;
  }

  if (isStepFailureMessage(message)) {
    context.dispatch({
      type: "FAIL_RUNNING_STEP",
      payload: { error: message },
    });
  }
}

export function useMetaSOPOrchestration() {
  const { parsedEvents } = useWsClient();
  const [steps, dispatch] = useReducer(metaSopReducer, []);
  const [isOrchestrating, setIsOrchestrating] = useState(false);

  useEffect(() => {
    const latestEvent = getLatestEvent(parsedEvents);
    if (!latestEvent) {
      return;
    }

    const message = extractMetaSopMessage(latestEvent);
    if (message) {
      handleMetaSopMessage(message, {
        dispatch,
        setIsOrchestrating,
        parsedEvents,
      });
    }

    const observationStep = extractMetaSopObservation(latestEvent);
    if (observationStep) {
      dispatch({ type: "UPSERT_STEP", payload: observationStep });
    }
  }, [parsedEvents]);

  const clearSteps = useCallback(() => {
    dispatch({ type: "RESET" });
    setIsOrchestrating(false);
  }, []);

  return {
    steps,
    isOrchestrating,
    clearSteps,
    hasSteps: steps.length > 0,
  };
}
