import React, { useEffect } from "react";
import { TaskTrackingObservation } from "#/types/core/observations";
import { useTasks } from "#/context/task-context";
import { StatusIndicator } from "./status-indicator";

interface TaskTrackingObservationContentProps {
  event: TaskTrackingObservation;
}

export function TaskTrackingObservationContent({
  event,
}: TaskTrackingObservationContentProps) {
  const { updateTasks } = useTasks();

  const extras = event.extras ?? {};
  const command = typeof extras.command === "string" ? extras.command : undefined;
  const rawTaskList = Array.isArray(extras.task_list) ? extras.task_list : [];
  const shouldShowTaskList = command === "plan" && rawTaskList.length > 0;

  // Update the task context when task list changes
  useEffect(() => {
    if (shouldShowTaskList) {
      try {
        const safeTasks = (rawTaskList ?? []).map((it) => {
          if (typeof it === "object" && it !== null) {
            const rec = it as Record<string, unknown>;
            const id = String(rec["id"] ?? "");
            const title = String(rec["title"] ?? "");
            const statusRaw = String(rec["status"] ?? "todo");
            const status = (["todo", "in_progress", "done", "cancelled"].includes(statusRaw) ? statusRaw : "todo") as "todo" | "in_progress" | "done" | "cancelled";
            return { id, title, status };
          }
          return { id: "", title: "", status: "todo" as const };
        });
        updateTasks(safeTasks);
      } catch {
        // ignore malformed extras
      }
    }
  }, [shouldShowTaskList, extras, updateTasks]);

  // Don't render anything - we'll show it in the typing indicator area instead
  return null;
}
