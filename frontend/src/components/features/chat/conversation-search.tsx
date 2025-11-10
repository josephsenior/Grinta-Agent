import React from "react";
import {
  Search,
  X,
  MessageSquare,
  Calendar,
  User,
  Bot,
  ChevronRight,
  Filter,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "#/components/ui/dialog";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";
import { cn } from "#/utils/utils";
import { ForgeAction } from "#/types/core/actions";
import { ForgeObservation } from "#/types/core/observations";
import { isUserMessage, isAssistantMessage } from "#/types/core/guards";

import ClientTimeDelta from "#/components/shared/ClientTimeDelta";

interface ConversationSearchProps {
  isOpen: boolean;
  onClose: () => void;
  messages: (ForgeAction | ForgeObservation)[];
  onSelectMessage: (messageIndex: number) => void;
}

interface SearchResult {
  index: number;
  message: ForgeAction | ForgeObservation;
  snippet: string;
  timestamp?: Date;
  matchScore: number;
}

type SearchFilter = "all" | "user" | "agent" | "code" | "errors";

function highlightText(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;

  const parts = text.split(new RegExp(`(${query})`, "gi"));
  return parts.map((part, index) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <mark
        key={index}
        className="bg-primary-500/30 text-primary-500 font-medium rounded px-0.5"
      >
        {part}
      </mark>
    ) : (
      part
    ),
  );
}

const STRING_FIELDS: Array<keyof ForgeAction | keyof ForgeObservation> = [
  "message",
  "content",
  "observation",
];

const extractStringField = (message: ForgeAction | ForgeObservation) => {
  for (const field of STRING_FIELDS) {
    if (field in message && typeof (message as any)[field] === "string") {
      return (message as any)[field] as string;
    }
  }

  return null;
};

const extractArgsText = (args: unknown): string | null => {
  if (!args) {
    return null;
  }

  if (typeof args === "string") {
    return args;
  }

  if (
    typeof args === "object" &&
    "thought" in (args as Record<string, unknown>)
  ) {
    const { thought } = args as Record<string, unknown>;
    return thought != null ? String(thought) : "";
  }

  return null;
};

function getMessageText(message: ForgeAction | ForgeObservation): string {
  const stringField = extractStringField(message);
  if (stringField !== null) {
    return stringField;
  }

  if ("args" in message) {
    const argsText = extractArgsText(message.args);
    if (argsText !== null) {
      return argsText;
    }
  }

  return JSON.stringify(message);
}

export function ConversationSearch({
  isOpen,
  onClose,
  messages,
  onSelectMessage,
}: ConversationSearchProps) {
  const [query, setQuery] = React.useState("");
  const [filter, setFilter] = React.useState<SearchFilter>("all");
  const [results, setResults] = React.useState<SearchResult[]>([]);

  // Search logic
  React.useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    const searchQuery = query.toLowerCase();
    const searchResults: SearchResult[] = [];

    messages.forEach((message, index) => {
      // Apply filter
      if (filter === "user" && !isUserMessage(message)) return;
      if (filter === "agent" && !isAssistantMessage(message)) return;

      const text = getMessageText(message);
      const lowerText = text.toLowerCase();

      // Check if message matches query
      if (lowerText.includes(searchQuery)) {
        // Calculate match score
        const exactMatch = lowerText === searchQuery;
        const startsWithMatch = lowerText.startsWith(searchQuery);
        const wordMatch = lowerText
          .split(/\s+/)
          .some((word) => word === searchQuery);

        let matchScore = 1;
        if (exactMatch) matchScore = 100;
        else if (startsWithMatch) matchScore = 80;
        else if (wordMatch) matchScore = 60;
        else matchScore = 40;

        // Create snippet with context
        const matchIndex = lowerText.indexOf(searchQuery);
        const snippetStart = Math.max(0, matchIndex - 50);
        const snippetEnd = Math.min(
          text.length,
          matchIndex + searchQuery.length + 50,
        );
        let snippet = text.slice(snippetStart, snippetEnd);

        if (snippetStart > 0) snippet = `...${snippet}`;
        if (snippetEnd < text.length) snippet += "...";

        searchResults.push({
          index,
          message,
          snippet,
          timestamp: message.timestamp
            ? new Date(message.timestamp)
            : undefined,
          matchScore,
        });
      }
    });

    // Sort by match score
    searchResults.sort((a, b) => b.matchScore - a.matchScore);
    setResults(searchResults.slice(0, 50)); // Limit to 50 results
  }, [query, filter, messages]);

  const handleSelectResult = (result: SearchResult) => {
    onSelectMessage(result.index);
    onClose();
  };

  const getFilterCount = (filterType: SearchFilter): number => {
    if (filterType === "all") return messages.length;
    if (filterType === "user") return messages.filter(isUserMessage).length;
    if (filterType === "agent")
      return messages.filter(isAssistantMessage).length;
    return 0;
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl max-h-[80vh] flex flex-col p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-border-glass">
          <DialogTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Search Conversation
          </DialogTitle>
        </DialogHeader>

        {/* Search Input */}
        <div className="px-6 pt-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-foreground-secondary" />
            <input
              type="text"
              placeholder="Search messages..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
              className={cn(
                "w-full pl-10 pr-10 py-3 rounded-lg",
                "bg-background-surface border border-border-glass",
                "text-text-primary placeholder:text-text-foreground-secondary",
                "focus:outline-none focus:ring-2 focus:ring-primary-500/50",
                "text-sm",
              )}
            />
            {query && (
              <button
                onClick={() => setQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-foreground-secondary hover:text-text-primary"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            <Filter className="h-3 w-3 text-text-foreground-secondary" />
            {(["all", "user", "agent"] as SearchFilter[]).map((filterType) => (
              <Button
                key={filterType}
                variant="outline"
                size="sm"
                onClick={() => setFilter(filterType)}
                className={cn(
                  "h-7 px-2 text-xs rounded-full transition-all duration-200",
                  filter === filterType
                    ? "bg-primary-500/20 border-primary-500/40 text-primary-500"
                    : "bg-background-surface/50 border-border-glass text-text-foreground-secondary",
                )}
              >
                {filterType === "user" && <User className="h-3 w-3 mr-1" />}
                {filterType === "agent" && <Bot className="h-3 w-3 mr-1" />}
                {filterType === "all" && (
                  <MessageSquare className="h-3 w-3 mr-1" />
                )}
                {filterType.charAt(0).toUpperCase() + filterType.slice(1)}
                <Badge
                  variant="outline"
                  className="ml-1.5 px-1 py-0 h-4 text-xs bg-background-surface/50"
                >
                  {getFilterCount(filterType)}
                </Badge>
              </Button>
            ))}
          </div>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {query && results.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Search className="h-12 w-12 text-text-foreground-secondary opacity-50 mb-3" />
              <p className="text-sm font-medium text-text-primary mb-1">
                No results found
              </p>
              <p className="text-xs text-text-foreground-secondary">
                Try different keywords or filters
              </p>
            </div>
          )}

          {!query && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Search className="h-12 w-12 text-text-foreground-secondary opacity-50 mb-3" />
              <p className="text-sm font-medium text-text-primary mb-1">
                Search your conversation
              </p>
              <p className="text-xs text-text-foreground-secondary">
                Type to search through all messages
              </p>
            </div>
          )}

          {results.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-text-foreground-secondary mb-3">
                Found {results.length}{" "}
                {results.length === 1 ? "result" : "results"}
              </p>
              {results.map((result) => (
                <button
                  key={result.index}
                  onClick={() => handleSelectResult(result)}
                  className={cn(
                    "w-full text-left p-3 rounded-lg transition-all duration-200",
                    "bg-background-surface/50 hover:bg-primary-500/5",
                    "border border-border-glass hover:border-primary-500/40",
                    "group",
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={cn(
                        "flex-shrink-0 p-1.5 rounded-lg",
                        isUserMessage(result.message)
                          ? "bg-accent-cyan/10 text-accent-cyan"
                          : "bg-primary-500/10 text-primary-500",
                      )}
                    >
                      {isUserMessage(result.message) ? (
                        <User className="h-3 w-3" />
                      ) : (
                        <Bot className="h-3 w-3" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium text-text-primary">
                          {isUserMessage(result.message) ? "You" : "Assistant"}
                        </span>
                        {result.timestamp && (
                          <span className="text-xs text-text-foreground-secondary flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            <ClientTimeDelta dateIso={result.timestamp} />
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-text-secondary line-clamp-2">
                        {highlightText(result.snippet, query)}
                      </p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-text-foreground-secondary group-hover:text-primary-500 transition-colors flex-shrink-0" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border-glass text-xs text-text-foreground-secondary text-center">
          Press{" "}
          <kbd className="px-1.5 py-0.5 rounded bg-background-surface border border-border-glass">
            Esc
          </kbd>{" "}
          to close
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Hook for keyboard shortcut
export function useConversationSearch() {
  const [isOpen, setIsOpen] = React.useState(false);

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen(true);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return { isOpen, setIsOpen };
}
