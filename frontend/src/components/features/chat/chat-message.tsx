import React from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { CircleUser } from "lucide-react";
import { code } from "../markdown/code";
import { enhancedCode } from "../markdown/enhanced-code";
import { cn } from "#/utils/utils";
import { ul, ol } from "../markdown/list";
import { CopyToClipboardButton } from "#/components/shared/buttons/copy-to-clipboard-button";
import { anchor } from "../markdown/anchor";
import { OpenHandsSourceType } from "#/types/core/base";
import { paragraph } from "../markdown/paragraph";
import { TooltipButton } from "#/components/shared/buttons/tooltip-button";
import { MessageReactions } from "./message-reactions";

interface ChatMessageProps {
  type: OpenHandsSourceType;
  message: string;
  messageId?: string | number;
  actions?: Array<{
    icon: React.ReactNode;
    onClick: () => void;
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
    label: string;
    count: number;
    userReacted: boolean;
  }>;
  // New props for turn-based grouping
  hideAvatar?: boolean;
  compactMode?: boolean;
}

export const ChatMessage = React.memo(function ChatMessage({
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
  hideAvatar = false,
  compactMode = false,
}: React.PropsWithChildren<ChatMessageProps>) {
  const [isHovering, setIsHovering] = React.useState(false);
  const [isCopy, setIsCopy] = React.useState(false);
  // Ensure message is always a string; treat literal "NULL" (server artifact) as empty
  const safeMessage =
    message == null || String(message).toUpperCase() === "NULL"
      ? ""
      : String(message);
  const [displayed, setDisplayed] = React.useState(animate ? "" : safeMessage);
  // Start with empty so first-time animate=true will trigger the reveal
  const lastMessageRef = React.useRef<string>("");

  React.useEffect(() => {
    // If animate is disabled, always display full message
    if (!animate) {
      setDisplayed(safeMessage);
      lastMessageRef.current = safeMessage;
      // Return a no-op cleanup so the hook always returns a function
      return () => {
        /* noop */
      };
    }

    // If message changed, start animation
    if (lastMessageRef.current !== safeMessage) {
      // Handle empty message immediately
      if (safeMessage.length === 0) {
        setDisplayed("");
        lastMessageRef.current = safeMessage;
        // Return a no-op cleanup to keep return consistent
        return () => {
          /* noop */
        };
      }

      setDisplayed("");
      const totalChars = safeMessage.length;
      let idx = 0;
      const speed = 1; // ms per char - ChatGPT-style instant streaming (was 5ms)
      const intervalId = window.setInterval(() => {
        idx += 1;
        setDisplayed(safeMessage.slice(0, idx));
        if (idx >= totalChars) {
          window.clearInterval(intervalId);
          // Only mark as the last message after the animation finishes so
          // re-renders during animation don't prevent the animation from
          // restarting when appropriate.
          lastMessageRef.current = safeMessage;
        }
      }, speed);

      // Always return a cleanup function (consistent-return rule)
      return () => {
        try {
          window.clearInterval(intervalId);
        } catch (_) {
          /* ignore */
        }
      };
    }

    // Ensure consistent-return: always return a cleanup function
    // eslint-disable-next-line react-hooks/exhaustive-deps
    return () => {
      /* noop */
    };
  }, [animate, message]);

  const handleCopyToClipboard = async () => {
    await navigator.clipboard.writeText(message);
    setIsCopy(true);
  };

  React.useEffect(() => {
    let timeout: number | undefined;

    if (isCopy) {
      timeout = window.setTimeout(() => {
        setIsCopy(false);
      }, 2000);
    }

    return () => {
      if (timeout !== undefined) {
        window.clearTimeout(timeout);
      }
    };
  }, [isCopy]);

  return (
    <div
      className={cn(
        "w-full flex items-start gap-3",  /* Increased gap for better spacing */
        type === "user" ? "justify-end" : "justify-start",
        compactMode ? "mt-2" : "mt-4",  /* More generous spacing */
        "animate-message-enter",  /* Smooth entrance animation */
      )}
    >
      {/* Agent avatar - Simple logo on LEFT for agent */}
      {type === "agent" && !hideAvatar && (
        <div
          aria-label="Agent"
          className="shrink-0 w-8 h-8 flex items-center justify-center"
        >
          <img 
            src="/agent-icon.png?v=2" 
            alt="Forge Agent" 
            className="w-8 h-8 object-contain"
          />
        </div>
      )}
      
      {/* Spacer when avatar is hidden to maintain alignment */}
      {type === "agent" && hideAvatar && (
        <div className="shrink-0 w-2" aria-hidden="true" />
      )}

      <article
        data-testid={`${type}-message`}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
        className={cn(
          "chat-bubble",
          "group relative w-fit max-w-[85%]",
          "flex flex-col gap-1",
          // Clean, minimal styling like bolt.new
          compactMode ? "px-2 py-1" : "px-3 py-2",
          // Apply violet-themed chat bubble styles
          type === "user" && [
            "chat-bubble-user",
            "text-foreground",
            "rounded-lg",
          ],
          type === "agent" && [
            "chat-bubble-agent",
            "text-foreground",
            "rounded-lg",
          ],
        )}
      >
        <div
          className={cn(
            "absolute -top-2.5 -right-2.5 z-10",
            // Smooth fade-in on hover (Cursor-style)
            "transition-all duration-200 ease-out",
            !isHovering ? "opacity-0 pointer-events-none scale-95" : "opacity-100 scale-100 flex",
            "items-center gap-1.5",
            // Premium glass card for action buttons
            "bg-background-elevated/95 backdrop-blur-md",
            "border border-border-primary/50",
            "rounded-xl px-1.5 py-1.5",
            "shadow-lg shadow-black/20",
          )}
        >
          {actions?.map((action, index) => {
            const k = action.tooltip
              ? `${String(action.tooltip)}-${index}`
              : `action-${index}`;
            return action.tooltip ? (
              <TooltipButton
                key={k}
                tooltip={action.tooltip}
                ariaLabel={action.tooltip}
                placement="top"
              >
                <button
                  type="button"
                  onClick={action.onClick}
                  className="p-2 cursor-pointer rounded-lg bg-transparent hover:bg-brand-500/15 text-text-tertiary hover:text-brand-500 transition-all duration-200 active:scale-95"
                  aria-label={`Action ${index + 1}`}
                >
                  {action.icon}
                </button>
              </TooltipButton>
            ) : (
              <button
                key={k}
                type="button"
                onClick={action.onClick}
                className="p-2 cursor-pointer rounded-lg bg-transparent hover:bg-brand-500/15 text-text-tertiary hover:text-brand-500 transition-all duration-200 active:scale-95"
                aria-label={`Action ${index + 1}`}
              >
                {action.icon}
              </button>
            );
          })}

          <CopyToClipboardButton
            isHidden={!isHovering}
            isDisabled={isCopy}
            onClick={handleCopyToClipboard}
            mode={isCopy ? "copied" : "copy"}
          />
        </div>

        <div
          className={cn(
            "text-[15px]",  /* Cursor-level font size (15px) */
            "leading-[1.7]",  /* Enhanced line height */
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
                  ? enhancedCode(onAskAboutCode, onRunCode)
                  : code,
              ul,
              ol,
              a: anchor,
              p: paragraph,
            }}
            remarkPlugins={[remarkGfm, remarkBreaks]}
          >
            {displayed}
          </Markdown>
        </div>
        {children}

        {/* Message Reactions - Only for agent messages */}
        {type === "agent" && messageId && onReact && (
          <div className="mt-2">
            <MessageReactions
              messageId={messageId}
              reactions={reactions}
              onReact={onReact}
              compact
            />
          </div>
        )}
      </article>

      {/* User avatar - Custom icon on RIGHT for user messages */}
      {type === "user" && !hideAvatar && (
        <div
          aria-label="You"
          className="shrink-0 w-8 h-8 flex items-center justify-center"
        >
          <img 
            src="/user-icon.png?v=1" 
            alt="User" 
            className="w-8 h-8 object-contain"
          />
        </div>
      )}
    </div>
  );
});
