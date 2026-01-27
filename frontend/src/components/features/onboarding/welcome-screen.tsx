import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  MessageSquare,
  Sparkles,
  Code,
  Zap,
  ArrowRight,
  X,
  Command,
  Keyboard,
} from "lucide-react";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { displayErrorToast } from "#/utils/custom-toast-handlers";

interface WelcomeScreenProps {
  onDismiss?: () => void;
  isNewUser?: boolean;
  className?: string;
}

const QUICK_START_EXAMPLES = [
  {
    icon: Code,
    title: "Build a feature",
    description: "Create a REST API endpoint with authentication",
    prompt:
      "Help me build a REST API endpoint with JWT authentication for user registration and login.",
    color: "text-[var(--text-accent)]",
    bg: "bg-[var(--text-accent)]/10",
  },
  {
    icon: Sparkles,
    title: "Fix a bug",
    description: "Debug and resolve runtime errors",
    prompt: "I'm getting a runtime error. Can you help me debug and fix it?",
    color: "text-[var(--text-danger)]",
    bg: "bg-[var(--text-danger)]/10",
  },
  {
    icon: Zap,
    title: "Refactor code",
    description: "Improve code quality and maintainability",
    prompt:
      "Help me refactor this code to make it more maintainable and follow best practices.",
    color: "text-[var(--border-accent)]",
    bg: "bg-[var(--border-accent)]/10",
  },
];

export function WelcomeScreen({
  onDismiss,
  isNewUser = false,
  className,
}: WelcomeScreenProps) {
  const navigate = useNavigate();
  const [selectedExample, setSelectedExample] = useState<number | null>(null);
  const { mutate: createConversation, isPending } = useCreateConversation();

  const handleStartConversation = (prompt?: string) => {
    createConversation(
      {},
      {
        onSuccess: (response) => {
          navigate(`/conversations/${response.conversation_id}`, {
            state: { initialMessage: prompt },
          });
        },
        onError: (error) => {
          displayErrorToast(error);
        },
      },
    );
  };

  return (
    <div
      className={cn(
        "flex-1 flex items-center justify-center p-8 bg-[var(--bg-primary)]",
        className,
      )}
    >
      <div className="w-full max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10 space-y-4">
          {isNewUser && (
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--text-accent)]/10 border border-[var(--text-accent)]/20 text-[var(--text-accent)] text-[10px] font-bold uppercase tracking-wider mb-4">
              <Sparkles className="w-3 h-3" />
              Welcome to Forge
            </div>
          )}
          <h1 className="text-4xl font-bold text-[var(--text-primary)] tracking-tight">
            {isNewUser ? "Welcome to Forge" : "Start a new conversation"}
          </h1>
          <p className="text-[var(--text-tertiary)] text-lg max-w-xl mx-auto font-medium">
            {isNewUser
              ? "Your AI-powered development assistant. Build, debug, and refactor code with intelligent agents."
              : "Choose a quick start example or type your own message to begin."}
          </p>
        </div>

        {/* Quick Start Examples */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-10">
          {QUICK_START_EXAMPLES.map((example, index) => {
            const Icon = example.icon;
            const isSelected = selectedExample === index;
            return (
              <button
                key={index}
                type="button"
                onClick={() => {
                  setSelectedExample(index);
                  handleStartConversation(example.prompt);
                }}
                disabled={isPending}
                className={cn(
                  "group relative p-5 rounded-xl border transition-all duration-300 text-left overflow-hidden",
                  "bg-[var(--bg-secondary)] border-[var(--border-primary)] shadow-sm",
                  "hover:border-[var(--border-accent)] hover:bg-[var(--bg-tertiary)] hover:-translate-y-1 hover:shadow-md",
                  isSelected &&
                    "border-[var(--border-accent)] bg-[var(--bg-elevated)]",
                  isPending && "opacity-50 cursor-not-allowed",
                )}
              >
                <div className="flex flex-col gap-4">
                  <div
                    className={cn(
                      "w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-110",
                      example.bg,
                    )}
                  >
                    <Icon className={cn("w-5 h-5", example.color)} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-bold text-[var(--text-primary)] mb-1 flex items-center gap-2">
                      {example.title}
                      <ArrowRight className="w-3 h-3 text-[var(--text-tertiary)] opacity-0 -translate-x-2 transition-all group-hover:opacity-100 group-hover:translate-x-0" />
                    </h3>
                    <p className="text-xs text-[var(--text-tertiary)] leading-relaxed line-clamp-2">
                      {example.description}
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Quick Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button
            onClick={() => handleStartConversation()}
            disabled={isPending}
            className="bg-[var(--color-brand-600)] text-white hover:bg-[var(--color-brand-500)] px-8 py-3 rounded-xl font-bold transition-all duration-200 shadow-md hover:shadow-lg hover:-translate-y-0.5"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Start Empty Conversation
          </Button>
        </div>

        {/* Keyboard Shortcuts Hint */}
        {!isNewUser && (
          <div className="mt-8 pt-8 border-t border-[var(--border-primary)]">
            <div className="flex items-center justify-center gap-6 text-xs text-[var(--text-tertiary)]">
              <div className="flex items-center gap-2">
                <Command className="w-3 h-3" />
                <span>Press</span>
                <kbd className="px-2 py-1 bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded text-[var(--text-primary)] font-mono">
                  Ctrl+P
                </kbd>
                <span>for commands</span>
              </div>
              <div className="flex items-center gap-2">
                <Keyboard className="w-3 h-3" />
                <span>Press</span>
                <kbd className="px-2 py-1 bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded text-[var(--text-primary)] font-mono">
                  Ctrl+N
                </kbd>
                <span>for new conversation</span>
              </div>
            </div>
          </div>
        )}

        {/* Dismiss Button */}
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="absolute top-4 right-4 p-2 rounded hover:bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
