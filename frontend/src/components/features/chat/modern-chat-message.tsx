import React from "react";
import { Clock, CheckCircle2, AlertCircle, Copy, ThumbsUp, ThumbsDown, MoreHorizontal } from "lucide-react";
import { cn } from "#/utils/utils";
import { Card, CardContent } from "#/components/ui/card";
import { Button } from "#/components/ui/button";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";

type SenderType = "user" | "assistant" | "system";
type MessageStatus = "sending" | "sent" | "delivered" | "error";

interface ModernChatMessageProps {
  id: string;
  content: string;
  sender: SenderType;
  timestamp?: Date;
  status?: MessageStatus;
  isTyping?: boolean;
  onCopy?: (content: string) => void;
  onLike?: (id: string) => void;
  onDislike?: (id: string) => void;
  className?: string;
  showActions?: boolean;
}

const STATUS_ICON_CONFIG: Record<
  MessageStatus,
  { Icon: typeof Clock; className: string } | undefined
> = {
  sending: { Icon: Clock, className: "text-text-foreground-secondary animate-pulse" },
  sent: { Icon: CheckCircle2, className: "text-success-500" },
  delivered: { Icon: CheckCircle2, className: "text-success-500" },
  error: { Icon: AlertCircle, className: "text-danger-500" },
};

const SENDER_CONFIG: Record<
  SenderType,
  {
    label: string;
    typingEmoji: string;
    avatarEmoji: string;
    bubbleClassName: string;
    hoverGradientClassName: string;
    enableFeedback: boolean;
  }
> = {
  user: {
    label: "You",
    typingEmoji: "👤",
    avatarEmoji: "👤",
    bubbleClassName: "ml-auto max-w-[80%] bg-gradient-to-br from-accent-cyan/20 to-accent-green/20",
    hoverGradientClassName: "bg-gradient-to-r from-accent-cyan/5 to-accent-green/5",
    enableFeedback: false,
  },
  assistant: {
    label: "Forge AI",
    typingEmoji: "🤖",
    avatarEmoji: "🤖",
    bubbleClassName: "bg-gradient-to-br from-primary-500/10 to-primary-600/10",
    hoverGradientClassName: "bg-gradient-to-r from-primary-500/5 to-primary-600/5",
    enableFeedback: true,
  },
  system: {
    label: "System",
    typingEmoji: "⚙️",
    avatarEmoji: "⚙️",
    bubbleClassName: "bg-gradient-to-br from-accent-pink/10 to-accent-purple/10",
    hoverGradientClassName: "bg-gradient-to-r from-accent-pink/5 to-accent-purple/5",
    enableFeedback: false,
  },
};

const renderStatusIcon = (status: MessageStatus) => {
  const config = STATUS_ICON_CONFIG[status];
  if (!config) {
    return null;
  }

  const { Icon, className } = config;

  return <Icon className={cn("h-3 w-3", className)} />;
};

export function ModernChatMessage({
  id,
  content,
  sender,
  timestamp,
  status = "sent",
  isTyping = false,
  onCopy,
  onLike,
  onDislike,
  className,
  showActions = true,
}: ModernChatMessageProps) {
  const senderConfig = SENDER_CONFIG[sender];
  const statusIcon = renderStatusIcon(status);
  const copyContent =
    onCopy ?? ((text: string) => navigator.clipboard.writeText(text));

  const handleCopy = () => copyContent(content);

  if (isTyping) {
    return (
      <div className={cn("flex items-start gap-3 animate-fade-in", className)}>
        <div className="h-8 w-8 flex items-center justify-center">
          <div className="w-8 h-8 text-primary-500">
            {senderConfig.typingEmoji}
          </div>
        </div>
        <Card className="bg-background-glass backdrop-blur-xl border border-border-glass shadow-lg">
          <CardContent className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-medium text-text-primary">
                {senderConfig.label}
              </span>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse" />
                <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse delay-75" />
                <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse delay-150" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className={cn("flex items-start gap-3 animate-fade-in", className)}>
      {/* Avatar */}
      <div className="h-8 w-8 flex items-center justify-center flex-shrink-0">
        <div className="w-8 h-8 text-primary-500">
          {senderConfig.avatarEmoji}
        </div>
      </div>

      {/* Message Content */}
      <div className="flex-1 min-w-0 space-y-2">
        {/* Sender Info */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-primary">
            {senderConfig.label}
          </span>
          {timestamp && (
            <span className="text-xs text-text-foreground-secondary">
              <ClientFormattedDate
                iso={timestamp.toISOString()}
                options={{ hour: "2-digit", minute: "2-digit" }}
              />
            </span>
          )}
          {statusIcon}
        </div>

        {/* Message Bubble */}
        <Card
          className={cn(
            "group relative overflow-hidden transition-all duration-300",
            "bg-background-glass backdrop-blur-xl border border-border-glass",
            "shadow-lg hover:shadow-xl",
            senderConfig.bubbleClassName,
          )}
        >
          {/* Animated Background */}
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <div
              className={cn(
                "absolute inset-0",
                senderConfig.hoverGradientClassName,
              )}
            />
          </div>

          <CardContent className="relative p-4">
            {/* Message Text */}
            <div className="prose prose-invert max-w-none">
              <p className="text-text-primary leading-relaxed whitespace-pre-wrap">
                {content}
              </p>
            </div>

            {/* Message Actions */}
            {showActions && (
              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleCopy}
                    className="h-7 w-7 text-text-foreground-secondary hover:text-text-primary hover:bg-background-glass/50"
                  >
                    <Copy className="h-3 w-3" />
                  </Button>

                  {senderConfig.enableFeedback && (
                    <>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onLike?.(id)}
                        className="h-7 w-7 text-text-foreground-secondary hover:text-success-500 hover:bg-success-500/10"
                      >
                        <ThumbsUp className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onDislike?.(id)}
                        className="h-7 w-7 text-text-foreground-secondary hover:text-danger-500 hover:bg-danger-500/10"
                      >
                        <ThumbsDown className="h-3 w-3" />
                      </Button>
                    </>
                  )}

                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-text-foreground-secondary hover:text-text-primary hover:bg-background-glass/50"
                  >
                    <MoreHorizontal className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
