import React from "react";
import {
  Bot,
  User,
  Sparkles,
  Clock,
  CheckCircle2,
  AlertCircle,
  Copy,
  ThumbsUp,
  ThumbsDown,
  MoreHorizontal,
} from "lucide-react";
import { cn } from "#/utils/utils";
import { Card, CardContent } from "#/components/ui/card";
import { Avatar, AvatarFallback } from "#/components/ui/avatar";
import { Button } from "#/components/ui/button";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";

interface ModernChatMessageProps {
  id: string;
  content: string;
  sender: "user" | "assistant" | "system";
  timestamp?: Date;
  status?: "sending" | "sent" | "delivered" | "error";
  isTyping?: boolean;
  onCopy?: (content: string) => void;
  onLike?: (id: string) => void;
  onDislike?: (id: string) => void;
  className?: string;
  showActions?: boolean;
}

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
  const isUser = sender === "user";
  const isAssistant = sender === "assistant";
  const isSystem = sender === "system";

  const getStatusIcon = () => {
    switch (status) {
      case "sending":
        return <Clock className="h-3 w-3 text-text-foreground-secondary animate-pulse" />;
      case "sent":
        return <CheckCircle2 className="h-3 w-3 text-success-500" />;
      case "delivered":
        return <CheckCircle2 className="h-3 w-3 text-success-500" />;
      case "error":
        return <AlertCircle className="h-3 w-3 text-danger-500" />;
      default:
        return null;
    }
  };

  const getSenderIcon = () => {
    if (isUser) return <User className="h-4 w-4" />;
    if (isAssistant) return <Bot className="h-4 w-4" />;
    return <Sparkles className="h-4 w-4" />;
  };

  const getSenderName = () => {
    if (isUser) return "You";
    if (isAssistant) return "OpenHands AI";
    return "System";
  };

  const getSenderInitials = () => {
    if (isUser) return "U";
    if (isAssistant) return "AI";
    return "S";
  };

  const handleCopy = () => {
    if (onCopy) {
      onCopy(content);
    } else {
      navigator.clipboard.writeText(content);
    }
  };

  if (isTyping) {
    return (
      <div className={cn("flex items-start gap-3 animate-fade-in", className)}>
        <div className="h-8 w-8 flex items-center justify-center">
          <div className="w-8 h-8 text-primary-500">
            {isUser ? "👤" : "🤖"}
          </div>
        </div>
        <Card className="bg-background-glass backdrop-blur-xl border border-border-glass shadow-lg">
          <CardContent className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-medium text-text-primary">
                {getSenderName()}
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
          {isUser ? "👤" : isAssistant ? "🤖" : "⚙️"}
        </div>
      </div>

      {/* Message Content */}
      <div className="flex-1 min-w-0 space-y-2">
        {/* Sender Info */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-primary">
            {getSenderName()}
          </span>
          {timestamp && (
            <span className="text-xs text-text-foreground-secondary">
              <ClientFormattedDate
                iso={timestamp.toISOString()}
                options={{ hour: "2-digit", minute: "2-digit" }}
              />
            </span>
          )}
          {getStatusIcon()}
        </div>

        {/* Message Bubble */}
        <Card
          className={cn(
            "group relative overflow-hidden transition-all duration-300",
            "bg-background-glass backdrop-blur-xl border border-border-glass",
            "shadow-lg hover:shadow-xl",
            isUser &&
              "ml-auto max-w-[80%] bg-gradient-to-br from-accent-cyan/20 to-accent-green/20",
            isAssistant &&
              "bg-gradient-to-br from-primary-500/10 to-primary-600/10",
            isSystem &&
              "bg-gradient-to-br from-accent-pink/10 to-accent-purple/10",
          )}
        >
          {/* Animated Background */}
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <div
              className={cn(
                "absolute inset-0",
                isUser &&
                  "bg-gradient-to-r from-accent-cyan/5 to-accent-green/5",
                isAssistant &&
                  "bg-gradient-to-r from-primary-500/5 to-primary-600/5",
                isSystem &&
                  "bg-gradient-to-r from-accent-pink/5 to-accent-purple/5",
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

                  {isAssistant && (
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
