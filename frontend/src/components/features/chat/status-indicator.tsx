import React from "react";
import {
  ListTodo,
  Brain,
  Terminal,
  FileEdit,
  Code,
  Search,
  Workflow,
  Loader2,
} from "lucide-react";
import { cn } from "#/utils/utils";
import { logger } from "#/utils/logger";

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
    | "message"
    | "sop"
    | "orchestrating";
  message?: string;
  className?: string;
}

const STATUS_MAP = {
  think: {
    icon: <Brain className="w-3.5 h-3.5" />,
    text: "Thinking",
    color: "text-[var(--text-success)]",
  },
  thinking: {
    icon: <Brain className="w-3.5 h-3.5" />,
    text: "Thinking",
    color: "text-[var(--text-success)]",
  },
  message: {
    icon: <Brain className="w-3.5 h-3.5" />,
    text: "Responding",
    color: "text-[var(--text-success)]",
  },
  plan: {
    icon: <ListTodo className="w-3.5 h-3.5" />,
    text: "Agent updated the plan",
    color: "text-[var(--border-accent)]",
  },
  run: {
    icon: <Terminal className="w-3.5 h-3.5" />,
    text: "Running command",
    color: "text-[var(--text-success)]",
  },
  write: {
    icon: <FileEdit className="w-3.5 h-3.5" />,
    text: "Writing file",
    color: "text-[var(--border-accent)]",
  },
  edit: {
    icon: <Code className="w-3.5 h-3.5" />,
    text: "Editing file",
    color: "text-[var(--border-accent)]",
  },
  browse: {
    icon: <Search className="w-3.5 h-3.5" />,
    text: "Browsing",
    color: "text-[var(--text-success)]",
  },
  read: {
    icon: <Search className="w-3.5 h-3.5" />,
    text: "Reading file",
    color: "text-[var(--text-success)]",
  },
  sop: {
    icon: <Workflow className="w-3.5 h-3.5" />,
    text: "Starting SOP orchestration",
    color: "text-[var(--border-accent)]",
  },
  orchestrating: {
    icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
    text: "Orchestrating",
    color: "text-[var(--border-accent)]",
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
    logger.warn(`Unknown status type: ${type}`);
    return null;
  }

  const displayText = message || status.text;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-primary)]",
        className,
      )}
    >
      <div className={cn("flex-shrink-0", status.color)}>{status.icon}</div>
      <span className="text-sm text-[var(--text-primary)] font-medium whitespace-nowrap">
        {displayText}
      </span>
    </div>
  );
}
