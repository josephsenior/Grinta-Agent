import React, { useEffect, useState } from "react";
import { Copy, Check, FileCode, Code2, ChevronDown, ChevronUp } from "lucide-react";
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
  const [isCopied, setIsCopied] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [displayedCode, setDisplayedCode] = useState("");
  
  // Streaming effect - character by character
  useEffect(() => {
    if (!isStreaming) {
      setDisplayedCode(code);
      return;
    }
    
    // Handle empty code
    if (code.length === 0) {
      setDisplayedCode("");
      return;
    }
    
    // Character-by-character streaming
    let currentIndex = 0;
    const interval = setInterval(() => {
      currentIndex += 1;
      setDisplayedCode(code.slice(0, currentIndex));
      
      if (currentIndex >= code.length) {
        clearInterval(interval);
      }
    }, 10); // 100 chars/second for faster file streaming
    
    return () => clearInterval(interval);
  }, [code, isStreaming]);
  
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code); // Always copy the full code
      setIsCopied(true);
      onCopy?.();
      setTimeout(() => setIsCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  };
  
  const actionColors = {
    create: "bg-success-500/10 text-success-500 border-success-500/30",
    edit: "bg-warning-500/10 text-warning-500 border-warning-500/30",
    delete: "bg-error-500/10 text-error-500 border-error-500/30",
  };
  
  const actionLabels = {
    create: "Creating",
    edit: "Editing", 
    delete: "Deleting",
  };
  
  const lineCount = displayedCode.split("\n").length;
  const totalLineCount = code.split("\n").length;
  const isLongCode = totalLineCount > 50;
  
  return (
    <Card
      className={cn(
        "streaming-code-artifact my-4 overflow-hidden",
        "bg-gradient-to-br from-background-elevated to-background-surface",
        "border border-border-secondary shadow-xl shadow-primary-500/5",
        "transition-all duration-300 hover:shadow-2xl hover:shadow-primary-500/10",
        isStreaming && "border-brand-500/30 shadow-brand-500/10",
        className
      )}
    >
      {/* Header */}
      <CardHeader className="px-4 py-3 bg-background-tertiary border-b border-border-secondary">
        <div className="flex items-center justify-between gap-3">
          {/* File Info */}
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <FileCode className={cn(
              "w-4 h-4 flex-shrink-0",
              isStreaming ? "text-violet-500 animate-pulse" : "text-primary-500"
            )} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-mono text-foreground truncate" title={filePath}>
                {filePath}
              </p>
              <p className="text-xs text-foreground-secondary mt-0.5">
                {lineCount}/{totalLineCount} {totalLineCount === 1 ? "line" : "lines"} · {language}
                {isStreaming && " · Streaming"}
              </p>
            </div>
            
            {/* Action Badge */}
            <Badge
              variant="outline"
              className={cn(
                "text-xs font-medium flex-shrink-0",
                actionColors[action],
                isStreaming && "animate-pulse"
              )}
            >
              {actionLabels[action]}
            </Badge>
          </div>
          
          {/* Actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Collapse Button (for long code) */}
            {isLongCode && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsCollapsed(!isCollapsed)}
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
            
            {/* Copy Button */}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleCopy}
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
            
            {/* Apply Button (optional) */}
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
        </div>
        
        {/* Streaming Progress Bar */}
        {isStreaming && (
          <div className="mt-3 flex items-center gap-2">
            <div className="flex-1 h-1 bg-background-surface rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-brand-500 to-accent-cyan transition-all duration-300 ease-out"
                style={{ width: `${(displayedCode.length / code.length) * 100}%` }}
              />
            </div>
            <span className="text-xs text-foreground-muted font-mono">
              {Math.round((displayedCode.length / code.length) * 100)}%
            </span>
          </div>
        )}
      </CardHeader>
      
      {/* Code Content */}
      {!isCollapsed && (
        <CardContent className="p-0">
          <div className="max-h-[500px] overflow-auto">
            <LazyMonaco
              value={displayedCode}
              language={language}
              height={`${Math.min(lineCount * 19 + 20, 500)}px`}
              options={{
                readOnly: true,
                minimap: { enabled: totalLineCount > 50 },
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
            {isStreaming && displayedCode.length < code.length && (
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
            Code collapsed ({totalLineCount} lines)
            {isStreaming && ` · ${Math.round((displayedCode.length / code.length) * 100)}% complete`}
          </p>
        </CardContent>
      )}
    </Card>
  );
}
