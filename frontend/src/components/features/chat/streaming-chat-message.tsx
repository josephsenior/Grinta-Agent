import React from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { streamingCode } from "../markdown/streaming-code";
import { cn } from "#/utils/utils";
import { ul, ol } from "../markdown/list";
import { CopyToClipboardButton } from "#/components/shared/buttons/copy-to-clipboard-button";
import { anchor } from "../markdown/anchor";
import { ForgeSourceType } from "#/types/core/base";
import { paragraph } from "../markdown/paragraph";
import { TooltipButton } from "#/components/shared/buttons/tooltip-button";
import { logger } from "#/utils/logger";

interface StreamingChatMessageProps {
  type: ForgeSourceType;
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

// Helper functions and hooks (defined before main component)

const getSenderLabel = (type: ForgeSourceType) =>
  type === "agent" ? "Assistant" : "You";

const getContainerClassName = ({
  type,
  animate,
}: {
  type: ForgeSourceType;
  animate: boolean;
}) =>
  cn(
    "group relative flex gap-2 p-4 rounded-xl transition-all duration-200",
    animate && "animate-in slide-in-from-bottom-2 fade-in-0 duration-500",
    type === "agent" && "bg-background-secondary border border-border",
    type === "user" && "bg-brand-500/5 border border-brand-500/20",
  );

function renderChatIcon(type: ForgeSourceType) {
  const iconSrc =
    type === "agent"
      ? { src: "/agent-icon.png?v=2", alt: "Forge Agent" }
      : { src: "/user-icon.png?v=1", alt: "User" };

  return (
    <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center">
      <img
        src={iconSrc.src}
        alt={iconSrc.alt}
        className="w-8 h-8 object-contain"
      />
    </div>
  );
}

const buildMarkdownComponents = ({
  onAskAboutCode,
  onRunCode,
  isStreaming,
  streamingSpeed,
  streamingInterval,
}: {
  onAskAboutCode?: (code: string) => void;
  onRunCode?: (code: string, language: string) => void;
  isStreaming: boolean;
  streamingSpeed: number;
  streamingInterval: number;
}) => ({
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
});

function StreamingIndicator() {
  return (
    <div className="flex items-center gap-1">
      <div className="w-1 h-1 bg-primary-500 rounded-full animate-pulse" />
      <div className="w-1 h-1 bg-primary-500 rounded-full animate-pulse delay-100" />
      <div className="w-1 h-1 bg-primary-500 rounded-full animate-pulse delay-200" />
    </div>
  );
}

function renderActionButtons({
  actions,
  messageId,
}: {
  actions?: StreamingChatMessageProps["actions"];
  messageId?: string | number;
}) {
  if (!actions || actions.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-1">
      {actions.map((action, index) => {
        const key = `${messageId}-action-${index}`;
        const ariaLabel = action.tooltip || `Action ${index + 1}`;

        if (action.disabled) {
          return (
            <TooltipButton
              key={key}
              tooltip={action.tooltip || ""}
              ariaLabel={ariaLabel}
              className="p-1.5 cursor-not-allowed rounded-lg bg-background-tertiary/30 border border-border text-foreground-secondary opacity-50"
            >
              {action.icon}
            </TooltipButton>
          );
        }

        return (
          <button
            key={key}
            type="button"
            onClick={action.onClick}
            className="p-1.5 cursor-pointer rounded-lg bg-primary-500/15 backdrop-blur-sm border border-primary-500/30 hover:bg-primary-500/25 hover:border-primary-500/50 transition-all duration-200 shadow-md hover:shadow-lg"
            aria-label={ariaLabel}
          >
            {action.icon}
          </button>
        );
      })}
    </div>
  );
}

const useReactionHandler = ({
  onReact,
  messageId,
}: {
  onReact?: (messageId: string | number, reactionId: string) => void;
  messageId?: string | number;
}) =>
  React.useCallback(
    (reactionId: string) => {
      if (onReact && messageId) {
        onReact(messageId, reactionId);
      }
    },
    [messageId, onReact],
  );

function useCopyController(message: string) {
  const [isHovering, setIsHovering] = React.useState(false);
  const [isCopy, setIsCopy] = React.useState(false);

  const handleCopyToClipboard = React.useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message);
      setIsCopy(true);
      setTimeout(() => setIsCopy(false), 2000);
    } catch (error) {
      logger.error("Failed to copy to clipboard:", error);
    }
  }, [message]);

  return {
    isHovering,
    setIsHovering,
    isCopy,
    handleCopyToClipboard,
  } as const;
}

function useStreamingMessage({
  message,
  isStreaming,
  streamingDelay,
  streamingInterval,
  streamingSpeed,
}: {
  message: string;
  isStreaming: boolean;
  streamingDelay: number;
  streamingInterval: number;
  streamingSpeed: number;
}) {
  const [displayedMessage, setDisplayedMessage] = React.useState("");
  const [isComplete, setIsComplete] = React.useState(!isStreaming);
  const intervalRef = React.useRef<NodeJS.Timeout | null>(null);
  const delayTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  React.useEffect(() => {
    if (!isStreaming) {
      setDisplayedMessage(message);
      setIsComplete(true);
      return () => {};
    }

    const clearTimers = () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (delayTimeoutRef.current) clearTimeout(delayTimeoutRef.current);
    };

    clearTimers();

    delayTimeoutRef.current = setTimeout(() => {
      intervalRef.current = setInterval(() => {
        setDisplayedMessage((previous) => {
          const nextLength = Math.min(
            previous.length + streamingSpeed,
            message.length,
          );
          const nextMessage = message.slice(0, nextLength);

          if (nextLength >= message.length) {
            setIsComplete(true);
            clearTimers();
          }

          return nextMessage;
        });
      }, streamingInterval);
    }, streamingDelay);

    return clearTimers;
  }, [message, isStreaming, streamingSpeed, streamingInterval, streamingDelay]);

  return { displayedMessage, isComplete } as const;
}

function MessageHeader({
  type,
  isStreamingComplete,
  actions,
  isCopy,
  isHovering,
  handleCopyToClipboard,
  messageId,
}: {
  type: ForgeSourceType;
  isStreamingComplete: boolean;
  actions?: StreamingChatMessageProps["actions"];
  isCopy: boolean;
  isHovering: boolean;
  handleCopyToClipboard: () => void;
  messageId?: string | number;
}) {
  return (
    <div className="flex items-center justify-between mb-2">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-foreground">
          {getSenderLabel(type)}
        </span>
        {!isStreamingComplete && <StreamingIndicator />}
      </div>

      <div className="flex items-center gap-2">
        {renderActionButtons({
          actions,
          messageId,
        })}
        <CopyToClipboardButton
          isHidden={!isHovering}
          isDisabled={isCopy}
          onClick={handleCopyToClipboard}
          mode={isCopy ? "copied" : "copy"}
        />
      </div>
    </div>
  );
}

function MessageBody({
  type,
  streaming,
  onAskAboutCode,
  onRunCode,
  isStreaming,
  streamingSpeed,
  streamingInterval,
}: {
  type: ForgeSourceType;
  streaming: ReturnType<typeof useStreamingMessage>;
  onAskAboutCode?: (code: string) => void;
  onRunCode?: (code: string, language: string) => void;
  isStreaming: boolean;
  streamingSpeed: number;
  streamingInterval: number;
}) {
  return (
    <div
      className={cn(
        "text-sm",
        type === "agent" && "text-foreground",
        type === "user" && "text-foreground",
      )}
    >
      <Markdown
        components={buildMarkdownComponents({
          onAskAboutCode,
          onRunCode,
          isStreaming,
          streamingSpeed,
          streamingInterval,
        })}
        remarkPlugins={[remarkGfm, remarkBreaks]}
      >
        {streaming.displayedMessage}
      </Markdown>
      {!streaming.isComplete && (
        <span className="inline-block w-0.5 h-4 bg-primary-500 ml-0.5 animate-pulse" />
      )}
    </div>
  );
}

function ChildrenContainer({ children }: React.PropsWithChildren) {
  if (!children) {
    return null;
  }

  return <div className="mt-3">{children}</div>;
}

function ReactionButtons({
  reactions,
  onReact,
}: {
  reactions?: StreamingChatMessageProps["reactions"];
  onReact: (reactionId: string) => void;
}) {
  if (!reactions || reactions.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 mt-3">
      {reactions.map((reaction) => (
        <button
          type="button"
          key={reaction.id}
          onClick={() => onReact(reaction.id)}
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
  );
}

// Main exported component
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
  const streaming = useStreamingMessage({
    message,
    isStreaming,
    streamingDelay,
    streamingInterval,
    streamingSpeed,
  });
  const { isHovering, setIsHovering, isCopy, handleCopyToClipboard } =
    useCopyController(message);
  const handleReaction = useReactionHandler({ onReact, messageId });
  const icon = renderChatIcon(type);
  const containerClassName = getContainerClassName({ type, animate });

  return (
    <div
      className={containerClassName}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {icon}

      <div className="flex-1 min-w-0">
        <MessageHeader
          type={type}
          isStreamingComplete={streaming.isComplete}
          actions={actions}
          isCopy={isCopy}
          isHovering={isHovering}
          handleCopyToClipboard={handleCopyToClipboard}
          messageId={messageId}
        />

        <MessageBody
          type={type}
          streaming={streaming}
          onAskAboutCode={onAskAboutCode}
          onRunCode={onRunCode}
          isStreaming={isStreaming}
          streamingSpeed={streamingSpeed}
          streamingInterval={streamingInterval}
        />

        <ReactionButtons reactions={reactions} onReact={handleReaction} />

        <ChildrenContainer>{children}</ChildrenContainer>
      </div>
    </div>
  );
}
