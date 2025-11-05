import React from "react";
import { ThumbsUp, ThumbsDown, Star, Check } from "lucide-react";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";

interface Reaction {
  id: string;
  emoji: string;
  icon: React.ReactNode;
  label: string;
  count: number;
  userReacted: boolean;
}

interface MessageReactionsProps {
  messageId: string | number;
  reactions?: Reaction[];
  onReact: (messageId: string | number, reactionId: string) => void;
  compact?: boolean;
  className?: string;
}

const DEFAULT_REACTIONS: Omit<Reaction, "count" | "userReacted">[] = [
  {
    id: "thumbs-up",
    emoji: "👍",
    icon: <ThumbsUp className="h-3 w-3" />,
    label: "Helpful",
  },
  {
    id: "thumbs-down",
    emoji: "👎",
    icon: <ThumbsDown className="h-3 w-3" />,
    label: "Not helpful",
  },
  {
    id: "star",
    emoji: "⭐",
    icon: <Star className="h-3 w-3" />,
    label: "Great!",
  },
  {
    id: "check",
    emoji: "✅",
    icon: <Check className="h-3 w-3" />,
    label: "Solved",
  },
];

export function MessageReactions({
  messageId,
  reactions,
  onReact,
  compact = false,
  className,
}: MessageReactionsProps) {
  const [isHovering, setIsHovering] = React.useState(false);
  const [showPicker, setShowPicker] = React.useState(false);

  // Merge default reactions with actual counts
  const displayReactions = React.useMemo(
    () =>
      DEFAULT_REACTIONS.map((defaultReaction) => {
        const existingReaction = reactions?.find(
          (r) => r.id === defaultReaction.id,
        );
        return {
          ...defaultReaction,
          count: existingReaction?.count || 0,
          userReacted: existingReaction?.userReacted || false,
        };
      }),
    [reactions],
  );

  const hasReactions = displayReactions.some((r) => r.count > 0);

  const handleReaction = (reactionId: string) => {
    onReact(messageId, reactionId);
    setShowPicker(false);
  };

  if (compact && !hasReactions) return null;

  return (
    <div
      className={cn("flex items-center gap-1 flex-wrap", className)}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => {
        setIsHovering(false);
        setShowPicker(false);
      }}
    >
      {/* Show existing reactions */}
      {displayReactions
        .filter((r) => r.count > 0)
        .map((reaction) => (
          <Button
            key={reaction.id}
            variant="ghost"
            size="sm"
            onClick={() => handleReaction(reaction.id)}
            className={cn(
              "h-6 px-2 gap-1 text-xs rounded-full transition-all duration-200",
              "bg-background-surface/50 hover:bg-background-surface",
              "border border-border-glass",
              reaction.userReacted && [
                "bg-primary-500/20 border-primary-500/40",
                "hover:bg-primary-500/30",
              ],
            )}
            title={reaction.label}
          >
            <span className="text-sm">{reaction.emoji}</span>
            {reaction.count > 0 && (
              <span
                className={cn(
                  "text-xs font-medium text-text-foreground-secondary",
                  reaction.userReacted && "text-primary-500",
                )}
              >
                {reaction.count}
              </span>
            )}
          </Button>
        ))}

      {/* Add reaction button (shown on hover or if picker is open) */}
      {(isHovering || showPicker || !compact) && (
        <div className="relative">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowPicker(!showPicker)}
            className={cn(
              "h-6 w-6 p-0 rounded-full transition-all duration-200",
              "bg-background-surface/50 hover:bg-primary-500/10",
              "border border-border-glass hover:border-primary-500/40",
              "text-text-foreground-secondary hover:text-primary-500",
              showPicker && "bg-primary-500/10 border-primary-500/40",
            )}
            title="Add reaction"
          >
            <span className="text-sm">+</span>
          </Button>

          {/* Reaction picker */}
          {showPicker && (
            <div
              className={cn(
                "absolute left-0 top-full mt-1 z-50",
                "flex items-center gap-1 p-1.5 rounded-lg",
                "bg-background-surface border border-border-glass shadow-lg",
                "animate-slide-up",
              )}
            >
              {displayReactions.map((reaction) => (
                <Button
                  key={reaction.id}
                  variant="ghost"
                  size="sm"
                  onClick={() => handleReaction(reaction.id)}
                  className={cn(
                    "h-8 w-8 p-0 rounded-lg transition-all duration-200",
                    "hover:bg-primary-500/10 hover:scale-110",
                    reaction.userReacted && "bg-primary-500/20",
                  )}
                  title={reaction.label}
                >
                  <span className="text-lg">{reaction.emoji}</span>
                </Button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Hook to manage reactions state
export function useMessageReactions() {
  const [reactions, setReactions] = React.useState<
    Map<string | number, Reaction[]>
  >(new Map());

  const handleReact = React.useCallback(
    (messageId: string | number, reactionId: string) => {
      setReactions((prev) => {
        const newReactions = new Map(prev);
        const messageReactions = newReactions.get(messageId) || [];

        const existingReactionIndex = messageReactions.findIndex(
          (r) => r.id === reactionId,
        );

        if (existingReactionIndex >= 0) {
          // Toggle user's reaction
          const existing = messageReactions[existingReactionIndex];
          if (existing.userReacted) {
            // Remove user's reaction
            messageReactions[existingReactionIndex] = {
              ...existing,
              count: Math.max(0, existing.count - 1),
              userReacted: false,
            };
          } else {
            // Add user's reaction
            messageReactions[existingReactionIndex] = {
              ...existing,
              count: existing.count + 1,
              userReacted: true,
            };
          }
        } else {
          // Add new reaction
          const defaultReaction = DEFAULT_REACTIONS.find(
            (r) => r.id === reactionId,
          );
          if (defaultReaction) {
            messageReactions.push({
              ...defaultReaction,
              count: 1,
              userReacted: true,
            });
          }
        }

        newReactions.set(messageId, messageReactions);
        return newReactions;
      });

      // TODO: Send reaction to backend
      // posthog.capture("message_reaction", { messageId, reactionId });
    },
    [],
  );

  const getReactions = React.useCallback(
    (messageId: string | number) => reactions.get(messageId) || [],
    [reactions],
  );

  return {
    reactions,
    handleReact,
    getReactions,
  };
}
