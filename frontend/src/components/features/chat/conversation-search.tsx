import React from "react";
import { useTranslation } from "react-i18next";
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
import { ForgeAction, ForgeObservation } from "#/types/core";
import { isUserMessage, isAssistantMessage } from "#/types/core/guards";
import ClientTimeDelta from "#/components/shared/client-time-delta";
import { useConversationSearch } from "./conversation-search/hooks/use-conversation-search";
import { SearchFilter } from "./conversation-search/types";

interface ConversationSearchProps {
  isOpen: boolean;
  onClose: () => void;
  messages: (ForgeAction | ForgeObservation)[];
  onSelectMessage: (messageIndex: number) => void;
}

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

export function ConversationSearch({
  isOpen,
  onClose,
  messages,
  onSelectMessage,
}: ConversationSearchProps) {
  const { t } = useTranslation();
  const [query, setQuery] = React.useState("");
  const [filter, setFilter] = React.useState<SearchFilter>("all");

  const results = useConversationSearch({ messages, query, filter });

  const handleSelectResult = (result: { index: number }) => {
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
            {t("chat.search.title", "Search Conversation")}
          </DialogTitle>
        </DialogHeader>

        <div className="px-6 pt-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-foreground-secondary" />
            <input
              type="text"
              placeholder={t("chat.search.placeholder", "Search messages...")}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              // eslint-disable-next-line jsx-a11y/no-autofocus
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
                type="button"
                onClick={() => setQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-foreground-secondary hover:text-text-primary"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

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

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {query && results.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Search className="h-12 w-12 text-text-foreground-secondary opacity-50 mb-3" />
              <p className="text-sm font-medium text-text-primary mb-1">
                {t("chat.search.noResults", "No results found")}
              </p>
              <p className="text-xs text-text-foreground-secondary">
                {t(
                  "chat.search.tryDifferent",
                  "Try different keywords or filters",
                )}
              </p>
            </div>
          )}

          {!query && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Search className="h-12 w-12 text-text-foreground-secondary opacity-50 mb-3" />
              <p className="text-sm font-medium text-text-primary mb-1">
                {t(
                  "chat.search.searchConversation",
                  "Search your conversation",
                )}
              </p>
              <p className="text-xs text-text-foreground-secondary">
                {t(
                  "chat.search.typeToSearch",
                  "Type to search through all messages",
                )}
              </p>
            </div>
          )}

          {results.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-text-foreground-secondary mb-3">
                {t("chat.search.foundResults", "Found {{count}} {{results}}", {
                  count: results.length,
                  results: results.length === 1 ? "result" : "results",
                })}
              </p>
              {results.map((result) => (
                <button
                  key={result.index}
                  type="button"
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

        <div className="px-6 py-3 border-t border-border-glass text-xs text-text-foreground-secondary text-center">
          {t("chat.search.pressToClose", "Press")}{" "}
          <kbd className="px-1.5 py-0.5 rounded bg-background-surface border border-border-glass">
            {t("chat.search.escKey", "Esc")}
          </kbd>{" "}
          {t("chat.search.toClose", "to close")}
        </div>
      </DialogContent>
    </Dialog>
  );
}
