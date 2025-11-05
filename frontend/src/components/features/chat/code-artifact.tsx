import React, { useState } from "react";
import { Copy, Check, FileCode, Code2, ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent, CardHeader } from "#/components/ui/card";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";
import { cn } from "#/utils/utils";
import { LazyMonaco } from "#/components/shared/lazy-monaco";

interface CodeArtifactProps {
  filePath: string;
  language: string;
  code: string;
  action?: "create" | "edit" | "delete";
  onCopy?: () => void;
  onApply?: () => void;
  className?: string;
}

/**
 * CodeArtifact - Claude-style code display component
 * 
 * Features:
 * - Beautiful card layout with file path header
 * - Syntax highlighting via Monaco Editor
 * - Copy entire file button
 * - Apply changes button (optional)
 * - Collapsible for long code
 * - Action badge (create/edit/delete)
 */
export function CodeArtifact({
  filePath,
  language,
  code,
  action = "create",
  onCopy,
  onApply,
  className,
}: CodeArtifactProps) {
  const [isCopied, setIsCopied] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
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
    create: "Created",
    edit: "Modified",
    delete: "Deleted",
  };
  
  const lineCount = code.split("\n").length;
  const isLongCode = lineCount > 50;
  
  return (
    <Card
      className={cn(
        "code-artifact my-4 overflow-hidden",
        "bg-gradient-to-br from-background-elevated to-background-surface",
        "border border-border-secondary shadow-xl shadow-primary-500/5",
        "transition-all duration-300 hover:shadow-2xl hover:shadow-primary-500/10",
        className
      )}
    >
      {/* Header */}
      <CardHeader className="px-4 py-3 bg-background-tertiary border-b border-border-secondary">
        <div className="flex items-center justify-between gap-3">
          {/* File Info */}
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <FileCode className="w-4 h-4 text-primary-500 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-mono text-foreground truncate" title={filePath}>
                {filePath}
              </p>
              <p className="text-xs text-foreground-secondary mt-0.5">
                {lineCount} {lineCount === 1 ? "line" : "lines"} · {language}
              </p>
            </div>
            
            {/* Action Badge */}
            <Badge
              variant="outline"
              className={cn(
                "text-xs font-medium flex-shrink-0",
                actionColors[action]
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
            {onApply && (
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
      </CardHeader>
      
      {/* Code Content */}
      {!isCollapsed && (
        <CardContent className="p-0">
          <div className="max-h-[500px] overflow-auto">
            <LazyMonaco
              value={code}
              language={language}
              height={`${Math.min(lineCount * 19 + 20, 500)}px`}
              options={{
                readOnly: true,
                minimap: { enabled: lineCount > 50 },
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
          </div>
        </CardContent>
      )}
      
      {/* Footer (collapsed state) */}
      {isCollapsed && (
        <CardContent className="px-4 py-3 bg-background-surface/50">
          <p className="text-xs text-foreground-muted italic">
            Code collapsed ({lineCount} lines)
          </p>
        </CardContent>
      )}
    </Card>
  );
}

