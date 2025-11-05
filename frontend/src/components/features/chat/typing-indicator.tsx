import { Terminal, FileEdit, Brain, Code, Search, Loader2, ListTodo } from "lucide-react";
import { cn } from "#/utils/utils";

interface TypingIndicatorProps {
  action?: "run" | "write" | "edit" | "think" | "browse" | "read" | "plan" | string;
}

// Map actions to human-readable text and icons (bolt.diy style)
const ACTION_MAP: Record<string, { text: string; icon: React.ReactNode; color: string }> = {
  run: {
    text: "Running command",
    icon: <Terminal className="w-3.5 h-3.5" />,
    color: "text-success-500",
  },
  write: {
    text: "Writing file",
    icon: <FileEdit className="w-3.5 h-3.5" />,
    color: "text-violet-500",
  },
  edit: {
    text: "Editing file",
    icon: <Code className="w-3.5 h-3.5" />,
    color: "text-violet-500",
  },
  read: {
    text: "Reading file",
    icon: <Search className="w-3.5 h-3.5" />,
    color: "text-primary-500",
  },
  browse: {
    text: "Browsing",
    icon: <Search className="w-3.5 h-3.5" />,
    color: "text-primary-500",
  },
  think: {
    text: "Thinking",
    icon: <Brain className="w-3.5 h-3.5" />,
    color: "text-accent-purple",
  },
  plan: {
    text: "Agent updated the plan",
    icon: <ListTodo className="w-3.5 h-3.5" />,
    color: "text-violet-500",
  },
  message: {
    text: "Responding",
    icon: <Brain className="w-3.5 h-3.5" />,
    color: "text-accent-purple",
  },
};

export function TypingIndicator({ action }: TypingIndicatorProps) {
  const actionInfo = action ? ACTION_MAP[action] || ACTION_MAP.think : ACTION_MAP.think;

  return (
    <div className="flex items-center gap-2 bg-background-secondary/50 backdrop-blur-sm px-4 py-2 rounded-xl border border-border-subtle">
      {/* Icon with pulse animation */}
      <div className={cn("animate-pulse", actionInfo.color)}>
        {actionInfo.icon}
      </div>

      {/* Action text */}
      <span className="text-sm text-text-secondary font-medium">
        {actionInfo.text}
      </span>

      {/* Animated dots (bolt.diy style) */}
      <div className="flex items-center space-x-1">
        <span
          className="w-1 h-1 bg-foreground-secondary rounded-full animate-[bounce_0.6s_infinite]"
          style={{ animationDelay: "0ms" }}
        />
        <span
          className="w-1 h-1 bg-foreground-secondary rounded-full animate-[bounce_0.6s_infinite]"
          style={{ animationDelay: "150ms" }}
        />
        <span
          className="w-1 h-1 bg-foreground-secondary rounded-full animate-[bounce_0.6s_infinite]"
          style={{ animationDelay: "300ms" }}
        />
      </div>
    </div>
  );
}
