import React, { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Sparkles, Settings, Trash2, Download, Share2 } from "lucide-react";
import { cn } from "#/utils/utils";
import { Button } from "#/components/ui/button";
import { ScrollArea } from "#/components/ui/scroll-area";
import { ModernChatInput } from "./modern-chat-input";
import { ModernChatMessage } from "./modern-chat-message";

interface Message {
  id: string;
  content: string;
  sender: "user" | "assistant" | "system";
  timestamp: Date;
  status?: "sending" | "sent" | "delivered" | "error";
}

interface ModernChatInterfaceProps {
  messages?: Message[];
  isTyping?: boolean;
  onSendMessage?: (message: string) => void;
  onStop?: () => void;
  onClearChat?: () => void;
  onExportChat?: () => void;
  onShareChat?: () => void;
  className?: string;
  showQuickActions?: boolean;
  showHeader?: boolean;
  title?: string;
  subtitle?: string;
}

export function ModernChatInterface({
  messages = [],
  isTyping = false,
  onSendMessage,
  onStop,
  onClearChat,
  onExportChat,
  onShareChat,
  className,
  showQuickActions = true,
  showHeader = true,
  title = "Forge Pro AI",
  subtitle = "Your intelligent coding assistant",
}: ModernChatInterfaceProps) {
  const { t } = useTranslation();
  const [inputValue, setInputValue] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSendMessage = (message: string) => {
    if (message.trim() && onSendMessage) {
      onSendMessage(message);
      setInputValue("");
    }
  };

  const handleQuickAction = (action: string) => {
    setInputValue(action);
    if (onSendMessage) {
      onSendMessage(action);
      setInputValue("");
    }
  };

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
    // You could add a toast notification here
  };

  const handleLike = (messageId: string) => {
    // Handle like functionality
    console.log("Liked message:", messageId);
  };

  const handleDislike = (messageId: string) => {
    // Handle dislike functionality
    console.log("Disliked message:", messageId);
  };

  return (
    <div
      className={cn(
        "flex flex-col h-full bg-gradient-to-br from-background-surface via-background-DEFAULT to-background-elevated",
        className,
      )}
    >
      {/* Header */}
      {showHeader && (
        <div className="flex-shrink-0 relative">
          {/* Background gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-r from-primary-500/5 via-transparent to-accent-pink/5" />

          {/* Glass morphism header */}
          <div className="relative backdrop-blur-xl bg-background-glass border-b border-border-glass">
            <div className="px-4 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
                    <Sparkles className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <h1 className="text-lg font-semibold text-text-primary">
                      {title}
                    </h1>
                    <p className="text-sm text-text-secondary">{subtitle}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={onShareChat}
                    className="h-9 w-9 text-text-foreground-secondary hover:text-text-primary hover:bg-primary-500/10"
                  >
                    <Share2 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={onExportChat}
                    className="h-9 w-9 text-text-foreground-secondary hover:text-text-primary hover:bg-primary-500/10"
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={onClearChat}
                    className="h-9 w-9 text-text-foreground-secondary hover:text-danger-500 hover:bg-danger-500/10"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-9 w-9 text-text-foreground-secondary hover:text-text-primary hover:bg-primary-500/10"
                  >
                    <Settings className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 min-h-0 relative">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-[0.02] pointer-events-none">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_80%,_rgba(189,147,249,0.1)_0%,_transparent_50%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,_rgba(139,233,253,0.05)_0%,_transparent_50%)]" />
        </div>

        <ScrollArea className="h-full" ref={scrollAreaRef}>
          <div className="p-4 space-y-6">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="h-16 w-16 rounded-full bg-gradient-to-br from-primary-500/20 to-accent-pink/20 flex items-center justify-center mb-4">
                  <Sparkles className="h-8 w-8 text-primary-500" />
                </div>
                <h3 className="text-xl font-semibold text-text-primary mb-2">
                  Welcome to Forge AI
                </h3>
                <p className="text-text-secondary max-w-md">
                  Start a conversation by typing a message below. I can help you
                  with coding, debugging, and much more!
                </p>
              </div>
            ) : (
              messages.map((message) => (
                <ModernChatMessage
                  key={message.id}
                  id={message.id}
                  content={message.content}
                  sender={message.sender}
                  timestamp={message.timestamp}
                  status={message.status}
                  onCopy={handleCopy}
                  onLike={handleLike}
                  onDislike={handleDislike}
                />
              ))
            )}

            {/* Typing Indicator */}
            {isTyping && (
              <ModernChatMessage
                id="typing"
                content=""
                sender="assistant"
                timestamp={new Date()}
                isTyping
              />
            )}

            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 relative">
        {/* Background gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-background-surface/80 via-background-DEFAULT/60 to-transparent" />

        {/* Glass morphism container */}
        <div className="relative backdrop-blur-xl bg-background-glass border-t border-border-glass">
          <div className="p-4">
            <ModernChatInput
              value={inputValue}
              onChange={setInputValue}
              onSubmit={handleSendMessage}
              onStop={onStop}
              disabled={isTyping}
              button={isTyping ? "stop" : "submit"}
              showQuickActions={showQuickActions && messages.length === 0}
              onQuickAction={handleQuickAction}
              placeholder="Type your message here..."
              className="w-full"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
