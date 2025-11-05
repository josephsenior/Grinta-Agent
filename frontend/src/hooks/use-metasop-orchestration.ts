import { useState, useEffect, useCallback } from "react";
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

interface MetaSOPEvent {
  type: "metasop_step_start" | "metasop_step_complete" | "metasop_step_failed";
  step_id: string;
  role: string;
  artifact?: any;
  error?: string;
}

/**
 * Hook to track MetaSOP orchestration progress from WebSocket events
 * Listens for MetaSOP-specific events and updates orchestration state
 */
export function useMetaSOPOrchestration() {
  const { parsedEvents } = useWsClient();
  const [steps, setSteps] = useState<OrchestrationStep[]>([]);
  const [isOrchestrating, setIsOrchestrating] = useState(false);

  // Debug current state
  // useEffect(() => {
  //   console.log("MetaSOP Hook - Current state:", {
  //     isOrchestrating,
  //     stepsCount: steps.length,
  //     steps: steps.map((s) => ({
  //       id: s.step_id,
  //       role: s.role,
  //       status: s.status,
  //     })),
  //   });
  // }, [isOrchestrating, steps]);

  // Listen for MetaSOP events in the parsed events stream
  useEffect(() => {
    if (!parsedEvents || parsedEvents.length === 0) return;

    const latestEvent = parsedEvents[parsedEvents.length - 1];

    // Debug logging for MetaSOP events
    // console.log("MetaSOP Hook - Latest event:", {
    //   event: latestEvent,
    //   hasMessage: "message" in latestEvent,
    //   message: "message" in latestEvent ? latestEvent.message : null,
    //   hasObservation: "observation" in latestEvent,
    //   observation:
    //     "observation" in latestEvent ? latestEvent.observation : null,
    //   eventType:
    //     "action" in latestEvent
    //       ? latestEvent.action
    //       : "type" in latestEvent
    //         ? latestEvent.type
    //         : "unknown",
    // });

    // Check for StatusUpdate events (MetaSOP status updates)
    if (isStatusUpdate(latestEvent)) {
      const { message } = latestEvent;
      // console.log("MetaSOP Hook - StatusUpdate event:", {
      //   type: latestEvent.type,
      //   message,
      // });

      // Start orchestration
      if (message.includes("MetaSOP orchestration started")) {
        // console.log("MetaSOP: Orchestration started", { message });
        setIsOrchestrating(true);
        setSteps([]);
      }

      // End orchestration
      if (
        message.includes("MetaSOP orchestration completed") ||
        message.includes("MetaSOP finished successfully") ||
        message.includes("MetaSOP failed")
      ) {
        // console.log("MetaSOP: Orchestration ended", { message });
        setIsOrchestrating(false);
      }

      // Parse step events from MetaSOP messages
      const stepEventMatch = message.match(
        /step:(\S+)\s+role:([^:]+)\s+status:(\S+)(?:\s+retries:(\d+))?/i,
      );

      if (stepEventMatch) {
        const [, stepId, role, status, retries] = stepEventMatch;
        // console.log("MetaSOP: Step event detected", {
        //   stepId,
        //   role,
        //   status,
        //   retries,
        //   message,
        // });

        const stepInfo: OrchestrationStep = {
          step_id: stepId,
          role: role.trim(),
          status: status as "pending" | "running" | "success" | "failed",
          timestamp: new Date().toISOString(),
        };

        setSteps((prev) => {
          const existing = prev.find((s) => s.step_id === stepInfo.step_id);
          if (existing) {
            return prev.map((s) =>
              s.step_id === stepInfo.step_id ? { ...stepInfo } : s,
            );
          }
          return [...prev, stepInfo];
        });
      }

      // Parse artifact events
      const artifactMatch = message.match(
        /artifact:(\S+)\s+step:(\S+)\s+type:(\S+)/i,
      );

      if (artifactMatch) {
        const [, artifactHash, stepId, artifactType] = artifactMatch;
        // console.log("MetaSOP: Artifact event detected", {
        //   artifactHash,
        //   stepId,
        //   artifactType,
        // });

        // Find the most recently executed step to attach the artifact
        const executedStep = parsedEvents
          .slice()
          .reverse()
          .find((event) => {
            if (isStatusUpdate(event) && typeof event.message === "string") {
              const stepMatch = event.message.match(
                /step:(\S+)\s+role:([^:]+)\s+status:(\S+)/i,
              );
              return stepMatch && stepMatch[3] === "executed";
            }
            return false;
          });

        if (executedStep && isStatusUpdate(executedStep)) {
          const stepMatch = executedStep.message.match(
            /step:(\S+)\s+role:([^:]+)\s+status:(\S+)/i,
          );
          if (stepMatch) {
            const [, artifactStepId] = stepMatch;

            setSteps((prev) =>
              prev.map((step) =>
                step.step_id === artifactStepId
                  ? {
                      ...step,
                      artifact: {
                        hash: artifactHash,
                        type: artifactType,
                        timestamp: new Date().toISOString(),
                      },
                      artifact_hash: artifactHash,
                    }
                  : step,
              ),
            );
          }
        }
      }
    }

    // Check if it's a MetaSOP-related message
    // The backend sends these as user or agent messages with specific patterns
    if ("message" in latestEvent && typeof latestEvent.message === "string") {
      const { message } = latestEvent;
      
      // Debug: Log all messages to see what we're receiving
      // if (message.includes("step:") || message.includes("role:") || message.includes("status:")) {
      //   console.log("MetaSOP: Potential step message detected:", message);
      // }

      // Detect orchestration start
      if (
        message.includes("MetaSOP") &&
        (message.includes("orchestration started") ||
          message.includes("Running SOP:"))
      ) {
        // MetaSOP orchestration started
        setIsOrchestrating(true);
        setSteps([]);
      }

      // Detect step events: "step:pm_spec role:Product Manager status:executed retries:0"
      const stepEventMatch = message.match(
        /step:(\S+)\s+role:([^:]+)\s+status:(\S+)(?:\s+retries:(\d+))?/i,
      );
      if (stepEventMatch) {
        const [, stepId, role, status, retries] = stepEventMatch;
        // console.log("MetaSOP: Step event detected", {
        //   stepId,
        //   role,
        //   status,
        //   retries,
        //   message,
        // });
        setSteps((prev) => {
          // Check if step already exists
          const existing = prev.find((s) => s.step_id === stepId);
          if (existing) {
            // Update existing step
            return prev.map((s) =>
              s.step_id === stepId
                ? {
                    ...s,
                    status: status as
                      | "pending"
                      | "running"
                      | "success"
                      | "failed",
                    timestamp: new Date().toISOString(),
                  }
                : s,
            );
          }
          // Add new step
          return [
            ...prev,
            {
              step_id: stepId,
              role,
              status: status as "pending" | "running" | "success" | "failed",
              timestamp: new Date().toISOString(),
            },
          ];
        });
      }

      // Detect step completion with artifact
      // Look for JSON artifacts in observations or actions
      if (
        message.includes("Artifact produced") ||
        message.includes("Step completed") ||
        message.includes("status:executed")
      ) {
        // Try to extract JSON from the message
        try {
          const jsonMatch = message.match(/```json\s*([\s\S]*?)\s*```/);
          if (jsonMatch) {
            const artifact = JSON.parse(jsonMatch[1]);

            // Find the most recent step that was just executed to add artifact
            setSteps((prev) => {
              const executedStepIndex = prev.findIndex(
                (s) => s.status === "success",
              );
              if (executedStepIndex >= 0) {
                const updated = [...prev];
                updated[executedStepIndex] = {
                  ...updated[executedStepIndex],
                  artifact,
                };
                return updated;
              }
              return prev;
            });
          }
        } catch (error) {
          // Not JSON, skip
        }
      }

      // Detect step failure
      if (
        message.includes("Step failed") ||
        message.includes("Error in step")
      ) {
        setSteps((prev) => {
          const runningStepIndex = prev.findIndex(
            (s) => s.status === "running",
          );
          if (runningStepIndex >= 0) {
            const updated = [...prev];
            updated[runningStepIndex] = {
              ...updated[runningStepIndex],
              status: "failed",
              error: message,
            };
            return updated;
          }
          return prev;
        });
      }

      // Detect orchestration end
      if (
        message.includes("Orchestration complete") ||
        message.includes("All steps completed") ||
        message.includes("MetaSOP finished successfully") ||
        message.includes("MetaSOP failed")
      ) {
        setIsOrchestrating(false);
        // Mark any remaining running steps as success
        setSteps((prev) =>
          prev.map((s) =>
            s.status === "running" ? { ...s, status: "success" as const } : s,
          ),
        );
      }
    }

    // Also check for specific observation types (if backend sends structured events)
    if (
      "observation" in latestEvent &&
      typeof latestEvent.observation === "string"
    ) {
      // Check for custom MetaSOP observation types
      // @ts-expect-error - metasop_step is a custom observation type not in the enum yet
      if (latestEvent.observation === "metasop_step") {
        const extras = (latestEvent as any).extras || {};
        const stepInfo: OrchestrationStep = {
          step_id: extras.step_id || "unknown",
          role: extras.role || "Unknown",
          status: extras.status || "pending",
          artifact: extras.artifact,
          artifact_hash: extras.artifact_hash,
          timestamp: new Date().toISOString(),
        };

        setSteps((prev) => {
          const existing = prev.find((s) => s.step_id === stepInfo.step_id);
          if (existing) {
            return prev.map((s) =>
              s.step_id === stepInfo.step_id ? { ...stepInfo } : s,
            );
          }
          return [...prev, stepInfo];
        });
      }
    }
  }, [parsedEvents]);

  const clearSteps = useCallback(() => {
    setSteps([]);
    setIsOrchestrating(false);
  }, []);

  return {
    steps,
    isOrchestrating,
    clearSteps,
    hasSteps: steps.length > 0,
  };
}
