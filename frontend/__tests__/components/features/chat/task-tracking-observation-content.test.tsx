import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TaskTrackingObservationContent } from "#/components/features/chat/task-tracking-observation-content";
import { TaskTrackingObservation } from "#/types/core/observations";

const updateTasksMock = vi.fn();

vi.mock("#/context/task-context", () => ({
  useTasks: () => ({
    updateTasks: updateTasksMock,
  }),
}));

describe("TaskTrackingObservationContent", () => {
  const mockEvent: TaskTrackingObservation = {
    id: 123,
    timestamp: "2024-01-01T00:00:00Z",
    source: "agent",
    observation: "task_tracking",
    content: "Task tracking operation completed successfully",
    cause: 122,
    message: "Task tracking operation completed successfully",
    extras: {
      command: "plan",
      task_list: [
        {
          id: "task-1",
          title: "Implement feature A",
          status: "todo",
          notes: "This is a test task",
        },
        {
          id: "task-2",
          title: "Fix bug B",
          status: "in_progress",
        },
        {
          id: "task-3",
          title: "Deploy to production",
          status: "done",
          notes: "Completed successfully",
        },
      ],
    },
  };

  beforeEach(() => {
    updateTasksMock.mockClear();
  });

  it("renders nothing", () => {
    const { container } = render(
      <TaskTrackingObservationContent event={mockEvent} />,
    );

    expect(container.firstChild).toBeNull();
  });

  it("updates tasks when command is 'plan' and tasks exist", () => {
    render(<TaskTrackingObservationContent event={mockEvent} />);

    expect(updateTasksMock).toHaveBeenCalledWith([
      { id: "task-1", title: "Implement feature A", status: "todo" },
      { id: "task-2", title: "Fix bug B", status: "in_progress" },
      { id: "task-3", title: "Deploy to production", status: "done" },
    ]);
  });

  it("does not update tasks when command is not 'plan'", () => {
    const eventWithoutPlan = {
      ...mockEvent,
      extras: {
        ...mockEvent.extras,
        command: "view",
      },
    };

    render(<TaskTrackingObservationContent event={eventWithoutPlan} />);

    expect(updateTasksMock).not.toHaveBeenCalled();
  });

  it("does not update tasks when task list is empty", () => {
    const eventWithEmptyTasks = {
      ...mockEvent,
      extras: {
        ...mockEvent.extras,
        task_list: [],
      },
    };

    render(<TaskTrackingObservationContent event={eventWithEmptyTasks} />);

    expect(updateTasksMock).not.toHaveBeenCalled();
  });

  it("sanitizes malformed task entries", () => {
    const malformedEvent = {
      ...mockEvent,
      extras: {
        ...mockEvent.extras,
        task_list: [
          null,
          { id: 123, title: 456, status: "unknown" },
        ],
      },
    } as TaskTrackingObservation;

    render(<TaskTrackingObservationContent event={malformedEvent} />);

    expect(updateTasksMock).toHaveBeenCalledWith([
      { id: "", title: "", status: "todo" },
      { id: "123", title: "456", status: "todo" },
    ]);
  });
});
