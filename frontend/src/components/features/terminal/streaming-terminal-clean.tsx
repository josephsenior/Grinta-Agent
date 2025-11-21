import React from "react";
import { Copy, Check, Terminal as TerminalIcon } from "lucide-react";
import { useStreamingTerminalController } from "./streaming-terminal";

interface StreamingTerminalProps {
  eventId?: string;
  streamId?: string;
  content?: string;
  exitCode?: number;
  command?: string;
  onComplete?: () => void;
  className?: string;
}

// Helper components - defined before use
function StreamingTerminalCleanHeader({
  command,
  exitCode,
  exitCodeColor,
  exitCodeSymbol,
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
  exitCodeSymbol: string;
  lineCount: number;
  isLongOutput: boolean;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onCopy: () => void;
  isCopied: boolean;
}) {
  return (
    <div className="terminal-header flex items-center justify-between px-3 py-1.5 bg-[#1a1a1a] border-b border-border/30">
      <div className="flex items-center gap-2">
        <TerminalIcon className="w-3.5 h-3.5 text-green-500" />
        <span className="ml-2 text-xs text-foreground">Terminal Output</span>
        {command && (
          <>
            <span className="text-green-500 font-mono text-xs">$</span>
            <code className="text-xs text-foreground-secondary font-mono truncate max-w-[300px]">
              {command}
            </code>
          </>
        )}
        {exitCode !== undefined && (
          <span className={`text-xs font-mono ${exitCodeColor} ml-2`}>
            {exitCodeSymbol} {exitCode}
          </span>
        )}
        {lineCount > 0 && (
          <span className="text-[10px] text-foreground-secondary/50 ml-2">
            {lineCount} {lineCount === 1 ? "line" : "lines"}
          </span>
        )}
      </div>

      <div className="flex items-center gap-1">
        {isLongOutput && (
          <button
            type="button"
            onClick={onToggleExpand}
            className="px-2 py-0.5 text-[10px] text-foreground-secondary hover:text-foreground rounded transition-colors"
            title={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? "Collapse" : "Expand"}
          </button>
        )}

        <button
          type="button"
          onClick={onCopy}
          className="flex items-center gap-1 px-2 py-0.5 text-[10px] rounded transition-colors hover:bg-background-tertiary/50"
          title="Copy output"
        >
          {isCopied ? (
            <>
              <Check className="w-3 h-3 text-green-500" />
              <span className="text-green-500">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3 text-foreground-secondary" />
              <span className="text-foreground-secondary">Copy</span>
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
      className="terminal-content px-3 py-2 overflow-y-auto font-mono text-xs leading-relaxed"
      style={{
        maxHeight,
        scrollbarGutter: "stable",
        transition: "max-height 0.2s ease-in-out",
      }}
    >
      <pre className="whitespace-pre-wrap text-foreground-secondary/90">
        {displayedContent}
        {isStreaming && (
          <span className="inline-block w-1.5 h-3 bg-green-500 ml-1 animate-pulse" />
        )}
      </pre>
    </div>
  );
}

export function StreamingTerminalClean({
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

  const exitCodeSymbol = (() => {
    if (exitCode === undefined) return "";
    if (exitCode === 0) return "✓";
    return "✗";
  })();

  return (
    <div
      ref={controller.terminalRef}
      role="region"
      className={`streaming-terminal rounded-lg overflow-hidden border border-border/40 bg-[#0a0a0a] my-2 shadow-lg w-full ${controller.isStreaming ? "streaming" : ""} ${className ?? ""}`}
    >
      <StreamingTerminalCleanHeader
        command={command}
        exitCode={exitCode}
        exitCodeColor={controller.exitCodeColor}
        exitCodeSymbol={exitCodeSymbol}
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
