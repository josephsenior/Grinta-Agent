import React from "react";
import {
  CheckCircle2,
  Circle,
  Clock,
  ChevronDown,
  ChevronUp,
  ListTodo,
} from "lucide-react";
import { cn } from "#/utils/utils";

interface Task {
  id: string;
  title: string;
  status: "todo" | "in_progress" | "done" | "cancelled";
  notes?: string;
}

interface TaskPanelProps {
  tasks: Task[];
  isOpen: boolean;
  onToggle: () => void;
}

export function TaskPanel({ tasks, isOpen, onToggle }: TaskPanelProps) {
  const todoCount = tasks.filter((task) => task.status === "todo").length;
  const inProgressCount = tasks.filter(
    (task) => task.status === "in_progress",
  ).length;
  const doneCount = tasks.filter((task) => task.status === "done").length;
  const totalCount = tasks.length;
  const progress = totalCount > 0 ? (doneCount / totalCount) * 100 : 0;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "todo":
        return <Circle className="w-3.5 h-3.5 text-text-tertiary" />;
      case "in_progress":
        return <Clock className="w-3.5 h-3.5 text-warning-500" />;
      case "done":
        return <CheckCircle2 className="w-3.5 h-3.5 text-success-500" />;
      default:
        return <Circle className="w-3.5 h-3.5 text-text-tertiary" />;
    }
  };

  const getStatusClassName = (status: string) => {
    switch (status) {
      case "todo":
        return "text-text-secondary";
      case "in_progress":
        return "text-warning-500";
      case "done":
        return "text-success-500 line-through opacity-60";
      default:
        return "text-text-secondary";
    }
  };

  // Hide completely when there are no tasks
  if (tasks.length === 0) {
    return null;
  }

  return (
    <div className="w-full border-b border-border bg-background-secondary/50 backdrop-blur-sm">
      {/* Compact Header - Always Visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-background-tertiary/50 transition-colors"
      >
        <ListTodo className="w-3.5 h-3.5 text-violet-500 flex-shrink-0" />

        {/* Inline Progress Info */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-xs font-medium text-text-primary whitespace-nowrap">
            Tasks {doneCount}/{totalCount}
          </span>

          {/* Compact Progress Bar */}
          <div className="flex-1 min-w-[80px] max-w-[200px] h-1 bg-background-tertiary rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-brand-500 to-success-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>

          <span className="text-[10px] text-text-tertiary whitespace-nowrap">
            {Math.round(progress)}%
          </span>
        </div>

        {/* Status Counts - More Compact */}
        <div className="flex items-center gap-2 text-[10px] flex-shrink-0">
          <div className="flex items-center gap-0.5">
            <Clock className="w-3 h-3 text-warning-500" />
            <span className="text-text-tertiary">{inProgressCount}</span>
          </div>
          <div className="flex items-center gap-0.5">
            <Circle className="w-3 h-3 text-text-tertiary" />
            <span className="text-text-tertiary">{todoCount}</span>
          </div>
        </div>

        {/* Toggle Icon */}
        {isOpen ? (
          <ChevronUp className="w-3.5 h-3.5 text-text-secondary flex-shrink-0" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-text-secondary flex-shrink-0" />
        )}
      </button>

      {/* Expandable Task List */}
      {isOpen && (
        <div
          className="px-3 pb-2 overflow-y-auto animate-fade-in"
          style={{ maxHeight: "320px" }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-1.5">
            {tasks.map((task, index) => (
              <div
                key={task.id}
                className={cn(
                  "p-1.5 rounded border transition-all duration-200",
                  task.status === "done"
                    ? "bg-success-500/5 border-success-500/20"
                    : task.status === "in_progress"
                      ? "bg-warning-500/5 border-warning-500/20"
                      : "bg-background-tertiary/30 border-border-subtle",
                )}
              >
                <div className="flex items-start gap-1.5">
                  <div className="mt-0.5">{getStatusIcon(task.status)}</div>
                  <div className="flex-1 min-w-0">
                    <p
                      className={cn(
                        "text-[11px] font-medium leading-tight",
                        getStatusClassName(task.status),
                      )}
                    >
                      <span className="text-text-tertiary mr-1">
                        {index + 1}.
                      </span>
                      {task.title}
                    </p>
                    {task.notes && (
                      <p className="text-[9px] text-text-tertiary mt-0.5 italic leading-tight">
                        {task.notes}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
