import React from "react";
import {
  Bookmark,
  BookmarkCheck,
  Calendar,
  User,
  Bot,
  ChevronRight,
  Star,
  Trash2,
} from "lucide-react";
import ClientTimeDelta from "#/components/shared/ClientTimeDelta";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "#/components/ui/dialog";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";
import { cn } from "#/utils/utils";

interface BookmarkedMessage {
  id: string;
  messageIndex: number;
  content: string;
  timestamp: Date;
  source: "user" | "agent";
  label?: string;
}

interface ConversationBookmarksProps {
  isOpen: boolean;
  onClose: () => void;
  bookmarks: BookmarkedMessage[];
  onSelectBookmark: (messageIndex: number) => void;
  onRemoveBookmark: (id: string) => void;
}

export function ConversationBookmarks({
  isOpen,
  onClose,
  bookmarks,
  onSelectBookmark,
  onRemoveBookmark,
}: ConversationBookmarksProps) {
  const [hoveredId, setHoveredId] = React.useState<string | null>(null);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Bookmark className="h-5 w-5" />
            Bookmarked Messages
            <Badge variant="outline" className="ml-auto">
              {bookmarks.length}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-4">
          {bookmarks.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Bookmark className="h-12 w-12 text-text-foreground-secondary opacity-50 mb-3" />
              <p className="text-sm font-medium text-text-primary mb-1">
                No bookmarks yet
              </p>
              <p className="text-xs text-text-foreground-secondary max-w-xs">
                Click the bookmark icon on any message to save it for quick
                access later
              </p>
            </div>
          )}

          {bookmarks.length > 0 && (
            <div className="space-y-2">
              {bookmarks.map((bookmark) => (
                <div
                  key={bookmark.id}
                  className={cn(
                    "relative p-3 rounded-lg transition-all duration-200",
                    "bg-background-surface/50 hover:bg-primary-500/5",
                    "border border-border-glass hover:border-primary-500/40",
                    "group",
                  )}
                  onMouseEnter={() => setHoveredId(bookmark.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  <button
                    onClick={() => onSelectBookmark(bookmark.messageIndex)}
                    className="w-full text-left"
                  >
                    <div className="flex items-start gap-3">
                      {/* Icon */}
                      <div
                        className={cn(
                          "flex-shrink-0 p-1.5 rounded-lg",
                          bookmark.source === "user"
                            ? "bg-accent-cyan/10 text-accent-cyan"
                            : "bg-primary-500/10 text-primary-500",
                        )}
                      >
                        {bookmark.source === "user" ? (
                          <User className="h-3 w-3" />
                        ) : (
                          <Bot className="h-3 w-3" />
                        )}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium text-text-primary">
                            {bookmark.source === "user" ? "You" : "Assistant"}
                          </span>
                          <span className="text-xs text-text-foreground-secondary flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            <ClientTimeDelta dateIso={bookmark.timestamp} />
                          </span>
                          {bookmark.label && (
                            <Badge
                              variant="outline"
                              className="text-xs px-1.5 py-0 h-4 bg-primary-500/10 border-primary-500/30 text-primary-500"
                            >
                              <Star className="h-2.5 w-2.5 mr-1" />
                              {bookmark.label}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-text-secondary line-clamp-2">
                          {bookmark.content}
                        </p>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <ChevronRight className="h-4 w-4 text-text-foreground-secondary group-hover:text-primary-500 transition-colors" />
                      </div>
                    </div>
                  </button>

                  {/* Delete button - shown on hover */}
                  {hoveredId === bookmark.id && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemoveBookmark(bookmark.id);
                      }}
                      className="absolute top-2 right-2 h-6 w-6 p-0 hover:bg-error-500/20 hover:text-error-500 text-text-foreground-secondary"
                      title="Remove bookmark"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border-glass pt-3 text-xs text-text-foreground-secondary text-center">
          {bookmarks.length > 0 && (
            <p>Click any bookmark to jump to that message</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Hook to manage bookmarks
export function useConversationBookmarks() {
  const [bookmarks, setBookmarks] = React.useState<BookmarkedMessage[]>(() => {
    try {
      const saved = localStorage.getItem("Forge.bookmarks");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [isOpen, setIsOpen] = React.useState(false);

  // Save to localStorage whenever bookmarks change
  React.useEffect(() => {
    try {
      localStorage.setItem("Forge.bookmarks", JSON.stringify(bookmarks));
    } catch (e) {
      console.error("Failed to save bookmarks:", e);
    }
  }, [bookmarks]);

  const addBookmark = React.useCallback(
    (
      messageIndex: number,
      content: string,
      source: "user" | "agent",
      label?: string,
    ) => {
      const newBookmark: BookmarkedMessage = {
        id: `bookmark-${Date.now()}-${messageIndex}`,
        messageIndex,
        content: content.slice(0, 200), // Limit content length
        timestamp: new Date(),
        source,
        label,
      };

      setBookmarks((prev) => {
        // Don't add duplicate bookmarks for the same message index
        if (prev.some((b) => b.messageIndex === messageIndex)) {
          return prev;
        }
        return [...prev, newBookmark];
      });
    },
    [],
  );

  const removeBookmark = React.useCallback((id: string) => {
    setBookmarks((prev) => prev.filter((b) => b.id !== id));
  }, []);

  const isBookmarked = React.useCallback(
    (messageIndex: number) =>
      bookmarks.some((b) => b.messageIndex === messageIndex),
    [bookmarks],
  );

  const toggleBookmark = React.useCallback(
    (messageIndex: number, content: string, source: "user" | "agent") => {
      const existing = bookmarks.find((b) => b.messageIndex === messageIndex);
      if (existing) {
        removeBookmark(existing.id);
      } else {
        addBookmark(messageIndex, content, source);
      }
    },
    [bookmarks, addBookmark, removeBookmark],
  );

  return {
    bookmarks,
    isOpen,
    setIsOpen,
    addBookmark,
    removeBookmark,
    isBookmarked,
    toggleBookmark,
  };
}

// Bookmark button component for messages
interface BookmarkButtonProps {
  messageIndex: number;
  isBookmarked: boolean;
  onToggle: () => void;
  className?: string;
}

export function BookmarkButton({
  messageIndex,
  isBookmarked,
  onToggle,
  className,
}: BookmarkButtonProps) {
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
      className={cn(
        "h-6 w-6 p-0 rounded-lg transition-all duration-200",
        isBookmarked
          ? "text-primary-500 hover:text-primary-600"
          : "text-text-foreground-secondary hover:text-primary-500",
        className,
      )}
      title={isBookmarked ? "Remove bookmark" : "Add bookmark"}
    >
      {isBookmarked ? (
        <BookmarkCheck className="h-3.5 w-3.5" />
      ) : (
        <Bookmark className="h-3.5 w-3.5" />
      )}
    </Button>
  );
}
