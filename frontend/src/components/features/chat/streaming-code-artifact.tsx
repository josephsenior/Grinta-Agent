import React, { useEffect, useState, useCallback } from "react";
import {
  Copy,
  Check,
  FileCode,
  Code2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Card, CardContent, CardHeader } from "#/components/ui/card";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";
import { cn } from "#/utils/utils";
import { LazyMonaco } from "#/components/shared/lazy-monaco";

interface StreamingCodeArtifactProps {
  filePath: string;
  language: string;
  code: string;
  action?: "create" | "edit" | "delete";
  onCopy?: () => void;
  onApply?: () => void;
  className?: string;
  eventId: string;
  isStreaming?: boolean;
}

/**
 * StreamingCodeArtifact - Real-time token-by-token file streaming component
 *
 * Features:
 * - Token-by-token streaming of file content
 * - Beautiful card layout with file path header
 * - Syntax highlighting via Monaco Editor
 * - Copy entire file button
 * - Apply changes button (optional)
 * - Collapsible for long code
 * - Action badge (create/edit/delete)
 * - Streaming progress indicator
 */
export function StreamingCodeArtifact({
  filePath,
  language,
  code,
  action = "create",
  onCopy,
  onApply,
  className,
  eventId,
  isStreaming = true,
}: StreamingCodeArtifactProps) {
  const streaming = useCodeStreaming({ code, isStreaming });
  const copyController = useCodeCopy({ code, onCopy });
  const [isCollapsed, setIsCollapsed] = useState(false);
  const headerMeta = buildHeaderMeta({
    action,
    language,
    displayedCode: streaming.displayedCode,
    code,
  });
  const actionBadge = getActionBadge(action);

  return (
    <Card
      className={cn(
        "streaming-code-artifact my-4 overflow-hidden",
        "bg-gradient-to-br from-background-elevated to-background-surface",
        "border border-border-secondary shadow-xl shadow-primary-500/5",
        "transition-all duration-300 hover:shadow-2xl hover:shadow-primary-500/10",
        isStreaming && "border-brand-500/30 shadow-brand-500/10",
        className,
      )}
    >
      <StreamingCodeHeader
        filePath={filePath}
        headerMeta={headerMeta}
        actionBadge={actionBadge}
        isStreaming={isStreaming}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
        copyController={copyController}
        onApply={onApply}
      />

      {/* Code Content */}
      {!isCollapsed && (
        <CardContent className="p-0">
          <div className="max-h-[500px] overflow-auto">
            <LazyMonaco
              value={streaming.displayedCode}
              language={language}
              height={`${Math.min(headerMeta.lineCount * 19 + 20, 500)}px`}
              options={{
                readOnly: true,
                minimap: { enabled: headerMeta.totalLineCount > 50 },
                scrollBeyondLastLine: false,
                fontSize: 13,
                lineNumbers: "on",
                glyphMargin: false,
                folding: true,
                lineDecorationsWidth: 0,
                lineNumbersMinChars: 3,
                renderLineHighlight: "none",
                scrollbar: {
                  vertical: "auto",
                  horizontal: "auto",
                  useShadows: false,
                },
                padding: { top: 12, bottom: 12 },
              }}
            />
            {/* Streaming cursor */}
            {isStreaming && streaming.displayedCode.length < code.length && (
              <div className="absolute bottom-2 right-2">
                <div className="w-2 h-2 bg-brand-500 rounded-full animate-pulse" />
              </div>
            )}
          </div>
        </CardContent>
      )}

      {/* Footer (collapsed state) */}
      {isCollapsed && (
        <CardContent className="px-4 py-3 bg-background-surface/50">
          <p className="text-xs text-foreground-muted italic">
            Code collapsed ({headerMeta.totalLineCount} lines)
            {isStreaming && ` · ${headerMeta.progressLabel}`}
          </p>
        </CardContent>
      )}
    </Card>
  );
}

function useCodeStreaming({
  code,
  isStreaming,
}: {
  code: string;
  isStreaming: boolean;
}) {
  const [displayedCode, setDisplayedCode] = useState("");

  useEffect(() => {
    if (!isStreaming) {
      setDisplayedCode(code);
      return;
    }

    if (code.length === 0) {
      setDisplayedCode("");
      return;
    }

    let currentIndex = 0;
    const interval = setInterval(() => {
      currentIndex += 1;
      setDisplayedCode(code.slice(0, currentIndex));

      if (currentIndex >= code.length) {
        clearInterval(interval);
      }
    }, 10);

    return () => clearInterval(interval);
  }, [code, isStreaming]);

  return {
    displayedCode,
  } as const;
}

function useCodeCopy({ code, onCopy }: { code: string; onCopy?: () => void }) {
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setIsCopied(true);
      onCopy?.();
      setTimeout(() => setIsCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  }, [code, onCopy]);

  return {
    isCopied,
    handleCopy,
  } as const;
}

function buildHeaderMeta({
  action,
  language,
  displayedCode,
  code,
}: {
  action: StreamingCodeArtifactProps["action"];
  language: string;
  displayedCode: string;
  code: string;
}) {
  const lineCount = displayedCode.split("\n").length;
  const totalLineCount = code.split("\n").length;
  const isLongCode = totalLineCount > 50;
  const progress = displayedCode.length / Math.max(code.length, 1);

  return {
    language,
    lineCount,
    totalLineCount,
    isLongCode,
    progress,
    progressLabel: `${Math.round(progress * 100)}% complete`,
  } as const;
}

function getActionBadge(action: StreamingCodeArtifactProps["action"]) {
  const actionColors = {
    create: "bg-success-500/10 text-success-500 border-success-500/30",
    edit: "bg-warning-500/10 text-warning-500 border-warning-500/30",
    delete: "bg-error-500/10 text-error-500 border-error-500/30",
  } as const;

  const actionLabels = {
    create: "Creating",
    edit: "Editing",
    delete: "Deleting",
  } as const;

  return {
    className: actionColors[action as keyof typeof actionColors],
    label: actionLabels[action as keyof typeof actionLabels],
  } as const;
}

function StreamingCodeHeader({
  filePath,
  headerMeta,
  actionBadge,
  isStreaming,
  isCollapsed,
  onToggleCollapse,
  copyController,
  onApply,
}: {
  filePath: string;
  headerMeta: ReturnType<typeof buildHeaderMeta>;
  actionBadge: ReturnType<typeof getActionBadge>;
  isStreaming: boolean;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  copyController: ReturnType<typeof useCodeCopy>;
  onApply?: () => void;
}) {
  const { isCopied, handleCopy } = copyController;

  return (
    <CardHeader className="px-4 py-3 bg-background-tertiary border-b border-border-secondary">
      <div className="flex items-center justify-between gap-3">
        <StreamingCodeFileInfo
          filePath={filePath}
          headerMeta={headerMeta}
          isStreaming={isStreaming}
          actionBadge={actionBadge}
        />

        <StreamingCodeHeaderActions
          headerMeta={headerMeta}
          isCollapsed={isCollapsed}
          isStreaming={isStreaming}
          isCopied={isCopied}
          onToggleCollapse={onToggleCollapse}
          onCopy={handleCopy}
          onApply={onApply}
        />
      </div>

      {isStreaming && <StreamingCodeProgress progress={headerMeta.progress} />}
    </CardHeader>
  );
}

function StreamingCodeFileInfo({
  filePath,
  headerMeta,
  isStreaming,
  actionBadge,
}: {
  filePath: string;
  headerMeta: ReturnType<typeof buildHeaderMeta>;
  isStreaming: boolean;
  actionBadge: ReturnType<typeof getActionBadge>;
}) {
  return (
    <div className="flex items-center gap-3 min-w-0 flex-1">
      <FileCode
        className={cn(
          "w-4 h-4 flex-shrink-0",
          isStreaming ? "text-violet-500 animate-pulse" : "text-primary-500",
        )}
      />
      <div className="min-w-0 flex-1">
        <p
          className="text-sm font-mono text-foreground truncate"
          title={filePath}
        >
          {filePath}
        </p>
        <p className="text-xs text-foreground-secondary mt-0.5">
          {headerMeta.lineCount}/{headerMeta.totalLineCount}{" "}
          {headerMeta.totalLineCount === 1 ? "line" : "lines"} ·{" "}
          {headerMeta.language}
          {isStreaming && " · Streaming"}
        </p>
      </div>

      <Badge
        variant="outline"
        className={cn(
          "text-xs font-medium flex-shrink-0",
          actionBadge.className,
          isStreaming && "animate-pulse",
        )}
      >
        {actionBadge.label}
      </Badge>
    </div>
  );
}

function StreamingCodeHeaderActions({
  headerMeta,
  isCollapsed,
  isStreaming,
  isCopied,
  onToggleCollapse,
  onCopy,
  onApply,
}: {
  headerMeta: ReturnType<typeof buildHeaderMeta>;
  isCollapsed: boolean;
  isStreaming: boolean;
  isCopied: boolean;
  onToggleCollapse: () => void;
  onCopy: () => void;
  onApply?: () => void;
}) {
  return (
    <div className="flex items-center gap-2 flex-shrink-0">
      {headerMeta.isLongCode && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onToggleCollapse}
          className="h-8 px-2 text-xs"
        >
          {isCollapsed ? (
            <>
              <ChevronDown className="w-3.5 h-3.5 mr-1" />
              Expand
            </>
          ) : (
            <>
              <ChevronUp className="w-3.5 h-3.5 mr-1" />
              Collapse
            </>
          )}
        </Button>
      )}

      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onCopy}
        className="h-8 px-3 text-xs"
      >
        {isCopied ? (
          <>
            <Check className="w-3.5 h-3.5 mr-1.5 text-success-500" />
            <span className="text-success-500">Copied!</span>
          </>
        ) : (
          <>
            <Copy className="w-3.5 h-3.5 mr-1.5" />
            Copy
          </>
        )}
      </Button>

      {onApply && !isStreaming && (
        <Button
          type="button"
          variant="default"
          size="sm"
          onClick={onApply}
          className="h-8 px-3 text-xs bg-primary-500 hover:bg-primary-600"
        >
          <Code2 className="w-3.5 h-3.5 mr-1.5" />
          Apply
        </Button>
      )}
    </div>
  );
}

function StreamingCodeProgress({ progress }: { progress: number }) {
  return (
    <div className="mt-3 flex items-center gap-2">
      <div className="flex-1 h-1 bg-background-surface rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-brand-500 to-accent-cyan transition-all duration-300 ease-out"
          style={{ width: `${Math.round(progress * 100)}%` }}
        />
      </div>
      <span className="text-xs text-foreground-muted font-mono">
        {Math.round(progress * 100)}%
      </span>
    </div>
  );
}
