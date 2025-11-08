import React from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { code } from "../markdown/code";
import { enhancedCode } from "../markdown/enhanced-code";
import { cn } from "#/utils/utils";
import { ul, ol } from "../markdown/list";
import { CopyToClipboardButton } from "#/components/shared/buttons/copy-to-clipboard-button";
import { anchor } from "../markdown/anchor";
import { ForgeSourceType } from "#/types/core/base";
import { paragraph } from "../markdown/paragraph";
import { TooltipButton } from "#/components/shared/buttons/tooltip-button";
import { MessageReactions } from "./message-reactions";

interface ChatMessageProps {
  type: ForgeSourceType;
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

  const safeMessage = React.useMemo(() => sanitizeMessage(message), [message]);
  const displayed = useAnimatedMessage({ message: safeMessage, animate });
  const copyState = useCopyFeedback(message);
  const layout = useChatMessageLayout({
    type,
    hideAvatar,
    messageId,
    onReact,
  });

  return (
    <div
      className={cn(
        "w-full flex items-start gap-3",
        type === "user" ? "justify-end" : "justify-start",
        compactMode ? "mt-2" : "mt-4",
        "animate-message-enter",
      )}
    >
      {layout.showAgentAvatar && <ChatMessageAvatar type="agent" />}
      {layout.showAgentSpacer && <div className="shrink-0 w-2" aria-hidden="true" />}

      <article
        data-testid={`${type}-message`}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
        className={cn(
          "chat-bubble",
          "group relative w-fit max-w-[85%]",
          "flex flex-col gap-1",
          compactMode ? "px-2 py-1" : "px-3 py-2",
          type === "user" && ["chat-bubble-user", "text-foreground", "rounded-lg"],
          type === "agent" && ["chat-bubble-agent", "text-foreground", "rounded-lg"],
        )}
      >
        <ChatMessageActions
          actions={actions}
          isHovering={isHovering}
          copyState={copyState}
        />

        <ChatMessageBody
          type={type}
          displayed={displayed}
          onAskAboutCode={onAskAboutCode}
          onRunCode={onRunCode}
        />

        {children}

        {layout.showReactions && (
          <div className="mt-2">
            <MessageReactions
              messageId={messageId!}
              reactions={reactions}
              onReact={onReact}
              compact
            />
          </div>
        )}
      </article>

      {layout.showUserAvatar && <ChatMessageAvatar type="user" />}
    </div>
  );
});

function useChatMessageLayout({
  type,
  hideAvatar,
  messageId,
  onReact,
}: {
  type: ForgeSourceType;
  hideAvatar: boolean;
  messageId?: string | number;
  onReact?: ChatMessageProps["onReact"];
}) {
  return React.useMemo(() => {
    const isAgent = type === "agent";
    const isUser = type === "user";

    return {
      showAgentAvatar: isAgent && !hideAvatar,
      showAgentSpacer: isAgent && hideAvatar,
      showUserAvatar: isUser && !hideAvatar,
      showReactions: Boolean(isAgent && messageId && onReact),
    };
  }, [type, hideAvatar, messageId, onReact]);
}

function ChatMessageAvatar({ type }: { type: ForgeSourceType }) {
  if (type === "agent") {
    return (
      <div aria-label="Agent" className="shrink-0 w-8 h-8 flex items-center justify-center">
        <img src="/agent-icon.png?v=2" alt="Forge Agent" className="w-8 h-8 object-contain" />
      </div>
    );
  }

  return (
    <div aria-label="You" className="shrink-0 w-8 h-8 flex items-center justify-center">
      <img src="/user-icon.png?v=1" alt="User" className="w-8 h-8 object-contain" />
    </div>
  );
}

function ChatMessageActions({
  actions,
  isHovering,
  copyState,
}: {
  actions?: ChatMessageProps["actions"];
  isHovering: boolean;
  copyState: CopyFeedback;
}) {
  const hasActions = (actions?.length ?? 0) > 0;

  if (!hasActions && !copyState.canCopy) {
    return null;
  }

  return (
    <div
      className={cn(
        "absolute -top-2.5 -right-2.5 z-10",
        "transition-all duration-200 ease-out",
        !isHovering ? "opacity-0 pointer-events-none scale-95" : "opacity-100 scale-100 flex",
        "items-center gap-1.5",
        "bg-background-elevated/95 backdrop-blur-md",
        "border border-border-primary/50",
        "rounded-xl px-1.5 py-1.5",
        "shadow-lg shadow-black/20",
      )}
    >
      {actions?.map((action, index) => (
        <ChatMessageActionButton key={getActionKey(action, index)} action={action} index={index} />
      ))}
      {copyState.canCopy && (
        <CopyToClipboardButton
          isHidden={!isHovering}
          isDisabled={copyState.isCopying}
          onClick={copyState.handleCopy}
          mode={copyState.isCopying ? "copied" : "copy"}
        />
      )}
    </div>
  );
}

function ChatMessageActionButton({
  action,
  index,
}: {
  action: NonNullable<ChatMessageProps["actions"]>[number];
  index: number;
}) {
  const commonProps = {
    type: "button" as const,
    onClick: action.onClick,
    className:
      "p-2 cursor-pointer rounded-lg bg-transparent hover:bg-brand-500/15 text-text-tertiary hover:text-brand-500 transition-all duration-200 active:scale-95",
    "aria-label": `Action ${index + 1}`,
  };

  if (action.tooltip) {
    return (
      <TooltipButton tooltip={action.tooltip} ariaLabel={action.tooltip} placement="top">
        <button {...commonProps}>{action.icon}</button>
      </TooltipButton>
    );
  }

  return <button {...commonProps}>{action.icon}</button>;
}

function ChatMessageBody({
  type,
  displayed,
  onAskAboutCode,
  onRunCode,
}: {
  type: ForgeSourceType;
  displayed: string;
  onAskAboutCode?: (code: string) => void;
  onRunCode?: (code: string, language: string) => void;
}) {
  return (
    <div
      className={cn(
        "text-[15px]",
        "leading-[1.7]",
        type === "agent" && "text-foreground",
        type === "user" && "text-foreground",
      )}
      style={{ whiteSpace: "normal", wordBreak: "break-word" }}
    >
      <Markdown
        components={{
          code: onAskAboutCode || onRunCode ? enhancedCode(onAskAboutCode, onRunCode) : code,
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
  );
}

function useAnimatedMessage({
  message,
  animate,
}: {
  message: string;
  animate: boolean;
}) {
  const [displayed, setDisplayed] = React.useState(animate ? "" : message);
  const lastMessageRef = React.useRef<string>("");

  React.useEffect(() => {
    if (!animate) {
      setDisplayed(message);
      lastMessageRef.current = message;
      return () => {
        /* noop */
      };
    }

    if (lastMessageRef.current !== message) {
      if (message.length === 0) {
        setDisplayed("");
        lastMessageRef.current = message;
        return () => {
          /* noop */
        };
      }

      setDisplayed("");
      const totalChars = message.length;
      let idx = 0;
      const speed = 1;
      const intervalId = window.setInterval(() => {
        idx += 1;
        setDisplayed(message.slice(0, idx));
        if (idx >= totalChars) {
          window.clearInterval(intervalId);
          lastMessageRef.current = message;
        }
      }, speed);

      return () => {
        window.clearInterval(intervalId);
      };
    }

    return () => {
      /* noop */
    };
  }, [animate, message]);

  return displayed;
}

type CopyFeedback = {
  isCopying: boolean;
  handleCopy: () => void;
  canCopy: boolean;
};

function useCopyFeedback(message: string | undefined): CopyFeedback {
  const [isCopying, setIsCopying] = React.useState(false);

  const handleCopy = React.useCallback(async () => {
    if (!message) {
      return;
    }
    try {
      await navigator.clipboard.writeText(message);
      setIsCopying(true);
    } catch {
      /* ignore clipboard errors */
    }
  }, [message]);

  React.useEffect(() => {
    if (!isCopying) {
      return;
    }

    const timeout = window.setTimeout(() => {
      setIsCopying(false);
    }, 2000);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [isCopying]);

  return {
    isCopying,
    handleCopy,
    canCopy: Boolean(message) && message.toUpperCase() !== "NULL",
  };
}

function sanitizeMessage(message: string | undefined): string {
  if (message == null) {
    return "";
  }

  const normalized = String(message);
  return normalized.toUpperCase() === "NULL" ? "" : normalized;
}

function getActionKey(action: NonNullable<ChatMessageProps["actions"]>[number], index: number) {
  return action.tooltip ? `${String(action.tooltip)}-${index}` : `action-${index}`;
}
