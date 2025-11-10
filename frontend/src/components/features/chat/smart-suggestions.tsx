import React from "react";
import {
  Sparkles,
  Code,
  FileText,
  Bug,
  Zap,
  Search,
  GitBranch,
  Terminal,
  BookOpen,
  Lightbulb,
  Eye,
  Play,
  Globe,
  Edit,
  TestTube,
} from "lucide-react";
import { Button } from "#/components/ui/button";
import { Card } from "#/components/ui/card";
import { cn } from "#/utils/utils";
import { ForgeEvent } from "#/types/core/base";
import { isForgeAction } from "#/types/core/guards";

interface Suggestion {
  id: string;
  icon: React.ReactNode;
  label: string;
  prompt: string;
  category: "code" | "debug" | "docs" | "general";
}

interface SmartSuggestionsProps {
  onSelectSuggestion: (prompt: string) => void;
  context?: {
    hasCode?: boolean;
    hasErrors?: boolean;
    isEmpty?: boolean;
    recentTopics?: string[];
  };
  className?: string;
  lastEvent?: ForgeEvent; // For context-aware suggestions (bolt.diy style)
}

const GENERAL_SUGGESTIONS: Suggestion[] = [
  {
    id: "explain-project",
    icon: <BookOpen className="h-4 w-4" />,
    label: "Explain this project",
    prompt: "Can you explain the structure and purpose of this project?",
    category: "general",
  },
  {
    id: "create-feature",
    icon: <Sparkles className="h-4 w-4" />,
    label: "Create a new feature",
    prompt: "Help me create a new feature. What should it do?",
    category: "code",
  },
  {
    id: "write-tests",
    icon: <FileText className="h-4 w-4" />,
    label: "Write tests",
    prompt: "Help me write comprehensive tests for this code",
    category: "code",
  },
  {
    id: "optimize-code",
    icon: <Zap className="h-4 w-4" />,
    label: "Optimize performance",
    prompt: "Analyze and optimize the performance of this code",
    category: "code",
  },
];

const CODE_SUGGESTIONS: Suggestion[] = [
  {
    id: "refactor",
    icon: <Code className="h-4 w-4" />,
    label: "Refactor code",
    prompt: "Help me refactor this code to follow best practices",
    category: "code",
  },
  {
    id: "add-comments",
    icon: <FileText className="h-4 w-4" />,
    label: "Add documentation",
    prompt: "Add comprehensive comments and documentation to this code",
    category: "docs",
  },
  {
    id: "security-review",
    icon: <Search className="h-4 w-4" />,
    label: "Security review",
    prompt: "Review this code for security vulnerabilities and suggest fixes",
    category: "code",
  },
];

const DEBUG_SUGGESTIONS: Suggestion[] = [
  {
    id: "fix-bug",
    icon: <Bug className="h-4 w-4" />,
    label: "Fix this bug",
    prompt: "Help me debug and fix this issue",
    category: "debug",
  },
  {
    id: "analyze-error",
    icon: <Terminal className="h-4 w-4" />,
    label: "Analyze error",
    prompt: "Analyze this error and suggest a solution",
    category: "debug",
  },
  {
    id: "add-logging",
    icon: <FileText className="h-4 w-4" />,
    label: "Add logging",
    prompt: "Add appropriate logging to help debug this code",
    category: "debug",
  },
];

const EMPTY_STATE_SUGGESTIONS: Suggestion[] = [
  {
    id: "start-project",
    icon: <GitBranch className="h-4 w-4" />,
    label: "Start new project",
    prompt: "Help me set up a new project. What technology stack should I use?",
    category: "general",
  },
  {
    id: "learn-feature",
    icon: <Lightbulb className="h-4 w-4" />,
    label: "Learn something",
    prompt: "Teach me about a programming concept or technology",
    category: "general",
  },
  {
    id: "review-code",
    icon: <Search className="h-4 w-4" />,
    label: "Review my code",
    prompt: "Review my codebase and suggest improvements",
    category: "code",
  },
  {
    id: "generate-boilerplate",
    icon: <Code className="h-4 w-4" />,
    label: "Generate boilerplate",
    prompt: "Generate boilerplate code for a common pattern",
    category: "code",
  },
];

// Context-aware suggestions based on last agent action (bolt.diy inspired)
const getContextAwareSuggestions = (lastEvent?: ForgeEvent): Suggestion[] => {
  if (!lastEvent || !isForgeAction(lastEvent)) {
    return [];
  }

  const { action } = lastEvent;

  // If agent wrote a file
  if (action === "write") {
    const filePath = lastEvent.args?.path || "file";
    return [
      {
        id: "view-file",
        icon: <Eye className="h-4 w-4" />,
        label: "View file",
        prompt: `Show me the contents of ${filePath}`,
        category: "code",
      },
      {
        id: "make-changes",
        icon: <Edit className="h-4 w-4" />,
        label: "Make changes",
        prompt: `I want to make some changes to ${filePath}`,
        category: "code",
      },
      {
        id: "test-it",
        icon: <Play className="h-4 w-4" />,
        label: "Test it",
        prompt: "Run tests to verify this code works correctly",
        category: "code",
      },
    ];
  }

  // If agent ran a command
  if (action === "run") {
    return [
      {
        id: "check-output",
        icon: <Terminal className="h-4 w-4" />,
        label: "Check output",
        prompt: "Show me the detailed output of that command",
        category: "debug",
      },
      {
        id: "try-again",
        icon: <Zap className="h-4 w-4" />,
        label: "Try again",
        prompt: "Run that command again with different parameters",
        category: "debug",
      },
      {
        id: "debug",
        icon: <Bug className="h-4 w-4" />,
        label: "Debug",
        prompt: "Help me debug any issues with this command",
        category: "debug",
      },
    ];
  }

  // If agent edited a file
  if (action === "edit") {
    const filePath = lastEvent.args?.path || "file";
    return [
      {
        id: "view-changes",
        icon: <Eye className="h-4 w-4" />,
        label: "View changes",
        prompt: `Show me what changed in ${filePath}`,
        category: "code",
      },
      {
        id: "test-changes",
        icon: <TestTube className="h-4 w-4" />,
        label: "Test changes",
        prompt: "Test the changes to make sure everything works",
        category: "code",
      },
      {
        id: "revert",
        icon: <GitBranch className="h-4 w-4" />,
        label: "Revert",
        prompt: `Revert the changes to ${filePath}`,
        category: "code",
      },
    ];
  }

  // If agent browsed/created app
  if (action === "browse" || action === "browse_interactive") {
    return [
      {
        id: "open-browser",
        icon: <Globe className="h-4 w-4" />,
        label: "Open browser",
        prompt: "Open the app in the browser tab",
        category: "general",
      },
      {
        id: "ui-changes",
        icon: <Edit className="h-4 w-4" />,
        label: "Make UI changes",
        prompt: "I want to change the user interface",
        category: "code",
      },
      {
        id: "test-app",
        icon: <Play className="h-4 w-4" />,
        label: "Test app",
        prompt: "Let's test the application functionality",
        category: "code",
      },
    ];
  }

  return [];
};

export function SmartSuggestions({
  onSelectSuggestion,
  context = {},
  className,
  lastEvent,
}: SmartSuggestionsProps) {
  const [isVisible, setIsVisible] = React.useState(true);

  const getSuggestions = (): Suggestion[] => {
    // First, try context-aware suggestions based on last action
    const contextAware = getContextAwareSuggestions(lastEvent);
    if (contextAware.length > 0) {
      // Show 3 context-aware + 1 general suggestion
      return [...contextAware.slice(0, 3), GENERAL_SUGGESTIONS[0]];
    }

    // Fallback to original context-based logic
    if (context.isEmpty) {
      return EMPTY_STATE_SUGGESTIONS;
    }

    if (context.hasErrors) {
      return [...DEBUG_SUGGESTIONS, ...CODE_SUGGESTIONS.slice(0, 2)];
    }

    if (context.hasCode) {
      return [...CODE_SUGGESTIONS, ...GENERAL_SUGGESTIONS.slice(0, 2)];
    }

    return GENERAL_SUGGESTIONS;
  };

  const suggestions = getSuggestions();

  if (!isVisible) return null;

  return (
    <Card
      className={cn(
        "bg-black border border-violet-500/20 p-2 animate-slide-up",
        className,
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-violet-500" />
          <h3 className="text-xs font-medium text-violet-400">Quick Actions</h3>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsVisible(false)}
          className="h-5 w-5 p-0 text-text-foreground-secondary hover:text-violet-400"
        >
          ✕
        </Button>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {suggestions.slice(0, 3).map((suggestion) => (
          <Button
            key={suggestion.id}
            variant="ghost"
            size="sm"
            onClick={() => {
              onSelectSuggestion(suggestion.prompt);
              setIsVisible(false);
            }}
            className={cn(
              "h-auto py-1.5 px-2.5 text-left",
              "bg-black hover:bg-violet-500/10",
              "border border-violet-500/20 hover:border-violet-500/40",
              "text-text-secondary hover:text-violet-400",
              "transition-all duration-200",
            )}
          >
            <span className="flex items-center gap-1.5">
              <span className="flex-shrink-0 text-violet-500 scale-75">
                {suggestion.icon}
              </span>
              <span className="text-xs font-medium">{suggestion.label}</span>
            </span>
          </Button>
        ))}
      </div>
    </Card>
  );
}
