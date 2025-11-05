import React from "react";
import { MessageSquare, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "#/utils/utils";
import { Button } from "#/components/ui/button";

interface MessageThreadIndicatorProps {
  threadId?: string;
  isFirstInThread?: boolean;
  isLastInThread?: boolean;
  threadSize?: number;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;
}

export function MessageThreadIndicator({
  threadId,
  isFirstInThread = false,
  isLastInThread = false,
  threadSize = 1,
  isCollapsed = false,
  onToggleCollapse,
  className,
}: MessageThreadIndicatorProps) {
  // Don't show indicator if no thread
  if (!threadId || threadSize <= 1) return null;

  return (
    <div className={cn("relative", className)}>
      {/* Thread line connector */}
      <div
        className={cn(
          "absolute left-0 w-0.5 bg-gradient-to-b from-primary-500/30 to-primary-500/10",
          isFirstInThread ? "top-0" : "-top-4",
          isLastInThread ? "bottom-1/2" : "bottom-0",
        )}
      />

      {/* Thread indicator badge */}
      {isFirstInThread && (
        <div className="flex items-center gap-2 mb-2 ml-3">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-primary-500/10 border border-primary-500/20">
            <MessageSquare className="h-3 w-3 text-primary-500" />
            <span className="text-xs font-medium text-primary-500">
              Thread ({threadSize})
            </span>
          </div>

          {/* Collapse/Expand button */}
          {onToggleCollapse && threadSize > 2 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleCollapse}
              className="h-6 px-2 text-xs rounded-full hover:bg-primary-500/10"
              title={isCollapsed ? "Expand thread" : "Collapse thread"}
            >
              {isCollapsed ? (
                <>
                  <ChevronDown className="h-3 w-3 mr-1" />
                  Expand
                </>
              ) : (
                <>
                  <ChevronUp className="h-3 w-3 mr-1" />
                  Collapse
                </>
              )}
            </Button>
          )}
        </div>
      )}

      {/* Connection dot */}
      <div
        className={cn(
          "absolute left-[-3px] w-2 h-2 rounded-full",
          "bg-primary-500 border-2 border-background",
          isFirstInThread ? "top-2" : "top-1/2 -translate-y-1/2",
        )}
      />
    </div>
  );
}

// Hook to manage message threading
export function useMessageThreading(
  messages: Array<{
    id?: string | number;
    source?: string;
    [key: string]: unknown;
  }>,
) {
  const [collapsedThreads, setCollapsedThreads] = React.useState<Set<string>>(
    new Set(),
  );

  // Group messages into threads based on source (user/agent) alternation
  const threads = React.useMemo(() => {
    const threadMap = new Map<string, number[]>();
    let currentThread: number[] = [];
    let lastSource: string | undefined;
    let threadId = 0;

    messages.forEach((message, index) => {
      const source = message.source || "unknown";

      // Start new thread if source changes
      if (source !== lastSource && currentThread.length > 0) {
        if (currentThread.length > 1) {
          threadMap.set(`thread-${threadId}`, currentThread);
        }
        currentThread = [];
        threadId++;
      }

      currentThread.push(index);
      lastSource = source;
    });

    // Add last thread
    if (currentThread.length > 1) {
      threadMap.set(`thread-${threadId}`, currentThread);
    }

    return threadMap;
  }, [messages]);

  const toggleThreadCollapse = React.useCallback((threadId: string) => {
    setCollapsedThreads((prev) => {
      const next = new Set(prev);
      if (next.has(threadId)) {
        next.delete(threadId);
      } else {
        next.add(threadId);
      }
      return next;
    });
  }, []);

  const getThreadInfo = React.useCallback(
    (messageIndex: number) => {
      for (const [threadId, indices] of threads.entries()) {
        if (indices.includes(messageIndex)) {
          const firstIndex = indices[0];
          const lastIndex = indices[indices.length - 1];
          return {
            threadId,
            isFirstInThread: messageIndex === firstIndex,
            isLastInThread: messageIndex === lastIndex,
            threadSize: indices.length,
            isCollapsed: collapsedThreads.has(threadId),
            onToggleCollapse: () => toggleThreadCollapse(threadId),
          };
        }
      }
      return {
        threadId: undefined,
        isFirstInThread: false,
        isLastInThread: false,
        threadSize: 1,
        isCollapsed: false,
        onToggleCollapse: undefined,
      };
    },
    [threads, collapsedThreads, toggleThreadCollapse],
  );

  const shouldShowMessage = React.useCallback(
    (messageIndex: number) => {
      const threadInfo = getThreadInfo(messageIndex);
      if (!threadInfo.threadId || !threadInfo.isCollapsed) return true;

      // Show first and last message of collapsed thread
      return threadInfo.isFirstInThread || threadInfo.isLastInThread;
    },
    [getThreadInfo],
  );

  return {
    getThreadInfo,
    shouldShowMessage,
    collapsedThreads,
  };
}
