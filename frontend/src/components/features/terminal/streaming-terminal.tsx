import React, {
  useEffect,
  useRef,
  useState,
  useMemo,
  useCallback,
} from "react";
import { Copy, Check, Terminal as TerminalIcon } from "lucide-react";
import { useSelector } from "react-redux";
import { RootState } from "#/store";
import { logger } from "#/utils/logger";
import {
  selectIsStreaming,
  selectStreamingEnabled,
  selectStreamContent,
} from "#/state/streaming-slice";

interface StreamingTerminalProps {
  eventId?: string;
  streamId?: string;
  content?: string;
  exitCode?: number;
  command?: string;
  onComplete?: () => void;
  className?: string;
}

function useStreamingTerminalController({
  eventId,
  streamId,
  content,
  exitCode,
  onComplete,
}: StreamingTerminalProps) {
  const resolvedEventId = eventId || streamId || "";
  const terminalRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [displayedContent, setDisplayedContent] = useState("");
  const [isCopied, setIsCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  const resolvedContentFromStore = useSelector((state: RootState) =>
    resolvedEventId ? selectStreamContent(state, resolvedEventId) : "",
  );

  const resolvedContent = content ?? resolvedContentFromStore;
  const isStreaming = useSelector((state: RootState) =>
    resolvedEventId ? selectIsStreaming(state, resolvedEventId) : false,
  );
  const streamingEnabled = useSelector((state: RootState) =>
    selectStreamingEnabled(state),
  );

  useEffect(() => {
    if (!streamingEnabled || !isStreaming) {
      setDisplayedContent(resolvedContent);
      return;
    }

    if (!resolvedContent || resolvedContent.length === 0) {
      setDisplayedContent("");
      return;
    }

    setDisplayedContent(resolvedContent);

    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [resolvedContent, isStreaming, streamingEnabled, onComplete]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(displayedContent || "");
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (error) {
      logger.error("Failed to copy:", error);
    }
  }, [displayedContent]);

  const exitCodeColor = useMemo(() => {
    if (exitCode === undefined) {
      return "text-foreground-secondary";
    }
    return exitCode === 0
      ? "text-[var(--text-success)]"
      : "text-[var(--text-danger)]";
  }, [exitCode]);

  const lineCount = useMemo(
    () => (displayedContent ? displayedContent.split("\n").length : 0),
    [displayedContent],
  );

  const isLongOutput = lineCount > 8;
  const maxHeight = isExpanded ? "32rem" : "12rem";

  const toggleExpand = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  return {
    terminalRef: terminalRef as React.RefObject<HTMLDivElement>,
    contentRef: contentRef as React.RefObject<HTMLDivElement>,
    displayedContent,
    isCopied,
    isExpanded,
    exitCodeColor,
    lineCount,
    isLongOutput,
    maxHeight,
    isStreaming,
    handleCopy,
    toggleExpand,
  };
}

function StreamingTerminalHeader({
  command,
  exitCode,
  exitCodeColor,
  lineCount,
  isLongOutput,
  isExpanded,
  onToggleExpand,
  onCopy,
  isCopied,
}: {
  command?: string;
  exitCode?: number;
  exitCodeColor: string;
  lineCount: number;
  isLongOutput: boolean;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onCopy: () => void;
  isCopied: boolean;
}) {
  return (
    <div className="terminal-header flex items-center justify-between px-3 py-2 bg-(--bg-elevated) border-b border-(--border-primary)">
      <div className="flex items-center gap-2">
        <TerminalIcon className="w-3.5 h-3.5 text-(--text-success)" />
        <span className="ml-2 text-xs text-(--text-primary)">
          Terminal Output
        </span>
        {command && (
          <>
            <span className="text-(--text-success) font-mono text-xs">
              $
            </span>
            <code className="text-xs text-(--text-tertiary) font-mono truncate max-w-[300px]">
              {command}
            </code>
          </>
        )}
        {exitCode !== undefined && (
          <span className={`text-xs font-mono ${exitCodeColor} ml-2`}>
            {exitCode}
          </span>
        )}
        {lineCount > 0 && (
          <span className="text-[10px] text-(--text-tertiary) ml-2">
            {lineCount} {lineCount === 1 ? "line" : "lines"}
          </span>
        )}
      </div>

      <div className="flex items-center gap-1">
        {isLongOutput && (
          <button
            type="button"
            onClick={onToggleExpand}
            className="px-2 py-0.5 text-[10px] text-(--text-tertiary) hover:text-(--text-primary) rounded transition-colors"
            title={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? "Collapse" : "Expand"}
          </button>
        )}

        <button
          type="button"
          onClick={onCopy}
          className="flex items-center gap-1 px-2 py-0.5 text-[10px] rounded transition-colors hover:bg-(--bg-tertiary)"
          title="Copy output"
        >
          {isCopied ? (
            <>
              <Check className="w-3 h-3 text-(--text-success)" />
              <span className="text-(--text-success)">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3 text-(--text-tertiary)" />
              <span className="text-(--text-tertiary)">Copy</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

function StreamingTerminalContent({
  contentRef,
  displayedContent,
  isStreaming,
  maxHeight,
}: {
  contentRef: React.RefObject<HTMLDivElement>;
  displayedContent: string;
  isStreaming: boolean;
  maxHeight: string;
}) {
  return (
    <div
      ref={contentRef}
      className="terminal-content px-3 py-2 overflow-y-auto font-mono text-xs leading-relaxed [scrollbar-gutter:stable] transition-[max-height] duration-200 ease-in-out"
      style={{
        maxHeight,
      }}
    >
      <pre className="whitespace-pre-wrap text-(--text-primary)">
        {displayedContent}
        {isStreaming && (
          <span className="inline-block w-1.5 h-3 bg-(--text-success) ml-1 animate-pulse" />
        )}
      </pre>
    </div>
  );
}

export function StreamingTerminal({
  eventId,
  streamId,
  content,
  exitCode,
  command,
  onComplete,
  className,
}: StreamingTerminalProps) {
  const controller = useStreamingTerminalController({
    eventId,
    streamId,
    content,
    exitCode,
    command,
    onComplete,
  });

  return (
    <div
      ref={controller.terminalRef}
      role="region"
      className={`streaming-terminal rounded-lg overflow-hidden border border-(--border-primary) bg-(--bg-primary) my-2 w-full ${controller.isStreaming ? "streaming" : ""} ${className ?? ""}`}
    >
      <StreamingTerminalHeader
        command={command}
        exitCode={exitCode}
        exitCodeColor={controller.exitCodeColor}
        lineCount={controller.lineCount}
        isLongOutput={controller.isLongOutput}
        isExpanded={controller.isExpanded}
        onToggleExpand={controller.toggleExpand}
        onCopy={controller.handleCopy}
        isCopied={controller.isCopied}
      />

      <StreamingTerminalContent
        contentRef={controller.contentRef}
        displayedContent={controller.displayedContent}
        isStreaming={controller.isStreaming}
        maxHeight={controller.maxHeight}
      />
    </div>
  );
}

export { useStreamingTerminalController };
