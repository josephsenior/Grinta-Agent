import React from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { CircleUser } from "lucide-react";
import { streamingCode } from "../markdown/streaming-code";
import { cn } from "#/utils/utils";
import { ul, ol } from "../markdown/list";
import { CopyToClipboardButton } from "#/components/shared/buttons/copy-to-clipboard-button";
import { anchor } from "../markdown/anchor";
import { OpenHandsSourceType } from "#/types/core/base";
import { paragraph } from "../markdown/paragraph";
import { TooltipButton } from "#/components/shared/buttons/tooltip-button";

interface StreamingChatMessageProps {
  type: OpenHandsSourceType;
  message: string;
  messageId?: string | number;
  actions?: Array<{
    icon: React.ReactNode;
    onClick: () => void;
    disabled?: boolean;
    tooltip?: string;
  }>;
  animate?: boolean;
  onAskAboutCode?: (code: string) => void;
  onRunCode?: (code: string, language: string) => void;
  onReact?: (messageId: string | number, reactionId: string) => void;
  reactions?: Array<{
    id: string;
    emoji: string;
    icon: React.ReactNode;
    count: number;
    userReacted: boolean;
  }>;
  isStreaming?: boolean;
  streamingSpeed?: number;
  streamingInterval?: number;
  streamingDelay?: number;
}

export function StreamingChatMessage({
  type,
  message,
  messageId,
  children,
  actions,
  animate = false,
  onAskAboutCode,
  onRunCode,
  onReact,
  reactions,
  isStreaming = false,
  streamingSpeed = 2,
  streamingInterval = 30,
  streamingDelay = 0,
}: React.PropsWithChildren<StreamingChatMessageProps>) {
  const [displayedMessage, setDisplayedMessage] = React.useState("");
  const [isComplete, setIsComplete] = React.useState(!isStreaming);
  const [isHovering, setIsHovering] = React.useState(false);
  const [isCopy, setIsCopy] = React.useState(false);
  const intervalRef = React.useRef<NodeJS.Timeout | null>(null);
  const delayTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  // Handle streaming effect
  React.useEffect(() => {
    if (!isStreaming) {
      setDisplayedMessage(message);
      setIsComplete(true);
      return;
    }

    // Clear any existing intervals/timeouts
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (delayTimeoutRef.current) clearTimeout(delayTimeoutRef.current);

    // Start streaming after delay
    delayTimeoutRef.current = setTimeout(() => {
      intervalRef.current = setInterval(() => {
        setDisplayedMessage((prev) => {
          const nextLength = Math.min(
            prev.length + streamingSpeed,
            message.length,
          );
          const nextMessage = message.slice(0, nextLength);

          if (nextLength >= message.length) {
            setIsComplete(true);
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
            }
          }

          return nextMessage;
        });
      }, streamingInterval);
    }, streamingDelay);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (delayTimeoutRef.current) clearTimeout(delayTimeoutRef.current);
    };
  }, [message, isStreaming, streamingSpeed, streamingInterval, streamingDelay]);

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(message);
      setIsCopy(true);
      setTimeout(() => setIsCopy(false), 2000);
    } catch (err) {
      console.error("Failed to copy to clipboard:", err);
    }
  };

  const handleReaction = (reactionId: string) => {
    if (onReact && messageId) {
      onReact(messageId, reactionId);
    }
  };

  const renderIcon = () => {
    if (type === "agent") {
      return (
        <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center">
          <img 
            src="/agent-icon.png?v=2" 
            alt="Forge Agent" 
            className="w-8 h-8 object-contain"
          />
        </div>
      );
    }

    return (
      <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center">
        <img 
          src="/user-icon.png?v=1" 
          alt="User" 
          className="w-8 h-8 object-contain"
        />
      </div>
    );
  };

  return (
    <div
      className={cn(
        "group relative flex gap-2 p-4 rounded-xl transition-all duration-200",
        animate && "animate-in slide-in-from-bottom-2 fade-in-0 duration-500",
        type === "agent" &&
          "bg-background-secondary border border-border",
        type === "user" &&
          "bg-brand-500/5 border border-brand-500/20",
      )}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {renderIcon()}

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground">
              {type === "agent" ? "Assistant" : "You"}
            </span>
            {!isComplete && (
              <div className="flex items-center gap-1">
                <div className="w-1 h-1 bg-primary-500 rounded-full animate-pulse" />
                <div className="w-1 h-1 bg-primary-500 rounded-full animate-pulse delay-100" />
                <div className="w-1 h-1 bg-primary-500 rounded-full animate-pulse delay-200" />
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Action buttons */}
            {actions && actions.length > 0 && (
              <div className="flex items-center gap-1">
                {actions.map((action, index) => {
                  const k = `${messageId}-action-${index}`;
                  return action.disabled ? (
                    <TooltipButton
                      key={k}
                      tooltip={action.tooltip || ""}
                      ariaLabel={action.tooltip || `Action ${index + 1}`}
                      className="p-1.5 cursor-not-allowed rounded-lg bg-background-tertiary/30 border border-border text-foreground-secondary opacity-50"
                    >
                      {action.icon}
                    </TooltipButton>
                  ) : (
                    <button
                      key={k}
                      type="button"
                      onClick={action.onClick}
                      className="p-1.5 cursor-pointer rounded-lg bg-primary-500/15 backdrop-blur-sm border border-primary-500/30 hover:bg-primary-500/25 hover:border-primary-500/50 transition-all duration-200 shadow-md hover:shadow-lg"
                      aria-label={`Action ${index + 1}`}
                    >
                      {action.icon}
                    </button>
                  );
                })}
              </div>
            )}

            {/* Copy button */}
            <CopyToClipboardButton
              isHidden={!isHovering}
              isDisabled={isCopy}
              onClick={handleCopyToClipboard}
              mode={isCopy ? "copied" : "copy"}
            />
          </div>
        </div>

        <div
          className={cn(
            "text-sm",
            type === "agent" && "text-foreground",
            type === "user" && "text-foreground",
          )}
          style={{
            whiteSpace: "normal",
            wordBreak: "break-word",
          }}
        >
          <Markdown
            components={{
              code:
                onAskAboutCode || onRunCode
                  ? streamingCode(
                      onAskAboutCode,
                      onRunCode,
                      isStreaming,
                      streamingSpeed,
                      streamingInterval,
                    )
                  : streamingCode(
                      undefined,
                      undefined,
                      isStreaming,
                      streamingSpeed,
                      streamingInterval,
                    ),
              ul,
              ol,
              a: anchor,
              p: paragraph,
            }}
            remarkPlugins={[remarkGfm, remarkBreaks]}
          >
            {displayedMessage}
          </Markdown>
          {!isComplete && (
            <span className="inline-block w-0.5 h-4 bg-primary-500 ml-0.5 animate-pulse" />
          )}
        </div>

        {/* Reactions */}
        {reactions && reactions.length > 0 && (
          <div className="flex items-center gap-2 mt-3">
            {reactions.map((reaction) => (
              <button
                key={reaction.id}
                onClick={() => handleReaction(reaction.id)}
                className={cn(
                  "flex items-center gap-1 px-2 py-1 rounded-full text-xs transition-all duration-200",
                  reaction.userReacted
                    ? "bg-brand-500/20 border border-brand-500/30 text-violet-500"
                    : "bg-background-tertiary border border-border text-foreground-secondary hover:bg-background-tertiary/70 hover:border-border-hover hover:text-foreground",
                )}
              >
                <span className="text-sm">{reaction.emoji}</span>
                <span>{reaction.count}</span>
              </button>
            ))}
          </div>
        )}

        {/* Children content */}
        {children && <div className="mt-3">{children}</div>}
      </div>
    </div>
  );
}
