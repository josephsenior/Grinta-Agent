import React from "react";
import {
  ListTodo,
  Brain,
  Terminal,
  FileEdit,
  Code,
  Search,
} from "lucide-react";
import { cn } from "#/utils/utils";

interface StatusIndicatorProps {
  type:
    | "think"
    | "thinking"
    | "plan"
    | "run"
    | "write"
    | "edit"
    | "browse"
    | "read"
    | "message";
  message?: string;
  className?: string;
}

const STATUS_MAP = {
  think: {
    icon: <Brain className="w-3.5 h-3.5" />,
    text: "Thinking",
    color: "text-accent-purple",
  },
  thinking: {
    icon: <Brain className="w-3.5 h-3.5" />,
    text: "Thinking",
    color: "text-accent-purple",
  },
  message: {
    icon: <Brain className="w-3.5 h-3.5" />,
    text: "Responding",
    color: "text-accent-purple",
  },
  plan: {
    icon: <ListTodo className="w-3.5 h-3.5" />,
    text: "Agent updated the plan",
    color: "text-violet-500",
  },
  run: {
    icon: <Terminal className="w-3.5 h-3.5" />,
    text: "Running command",
    color: "text-success-500",
  },
  write: {
    icon: <FileEdit className="w-3.5 h-3.5" />,
    text: "Writing file",
    color: "text-violet-500",
  },
  edit: {
    icon: <Code className="w-3.5 h-3.5" />,
    text: "Editing file",
    color: "text-violet-500",
  },
  browse: {
    icon: <Search className="w-3.5 h-3.5" />,
    text: "Browsing",
    color: "text-primary-500",
  },
  read: {
    icon: <Search className="w-3.5 h-3.5" />,
    text: "Reading file",
    color: "text-primary-500",
  },
};

export function StatusIndicator({
  type,
  message,
  className,
}: StatusIndicatorProps) {
  const status = STATUS_MAP[type];

  // Guard against undefined status
  if (!status) {
    console.warn(`Unknown status type: ${type}`);
    return null;
  }

  const displayText = message || status.text;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-background-secondary/50 backdrop-blur-sm border border-border-subtle",
        className,
      )}
    >
      <div className={cn("flex-shrink-0", status.color)}>{status.icon}</div>
      <span className="text-sm text-text-primary font-medium whitespace-nowrap">
        {displayText}
      </span>
    </div>
  );
}
