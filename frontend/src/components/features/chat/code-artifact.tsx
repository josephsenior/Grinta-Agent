import React, { useState } from "react";
import { useTranslation } from "react-i18next";
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
import { logger } from "#/utils/logger";

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
  const { t } = useTranslation();
  const [isCopied, setIsCopied] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setIsCopied(true);
      onCopy?.();
      setTimeout(() => setIsCopied(false), 2000);
    } catch (error) {
      logger.error("Failed to copy:", error);
    }
  };

  const actionColors = {
    create:
      "bg-[var(--text-success)]/10 text-[var(--text-success)] border-[var(--text-success)]/30",
    edit: "bg-[var(--border-accent)]/10 text-[var(--border-accent)] border-[var(--border-accent)]/30",
    delete:
      "bg-[var(--text-danger)]/10 text-[var(--text-danger)] border-[var(--text-danger)]/30",
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
        "bg-[var(--bg-elevated)]",
        "border border-[var(--border-primary)]",
        "transition-all duration-200",
        className,
      )}
    >
      {/* Header */}
      <CardHeader className="px-4 py-2.5 bg-[var(--bg-tertiary)] border-b border-[var(--border-primary)]">
        <div className="flex items-center justify-between gap-3">
          {/* File Info */}
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <FileCode className="w-4 h-4 text-[var(--text-success)] flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <p
                className="text-sm font-mono text-[var(--text-primary)] truncate"
                title={filePath}
              >
                {filePath}
              </p>
              <p className="text-xs text-[var(--text-tertiary)] mt-0.5">
                {lineCount} {lineCount === 1 ? "line" : "lines"} · {language}
              </p>
            </div>

            {/* Action Badge */}
            <Badge
              variant="outline"
              className={cn(
                "text-xs font-medium flex-shrink-0",
                actionColors[action],
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
                    {t("chat.codeArtifact.expand", "Expand")}
                  </>
                ) : (
                  <>
                    <ChevronUp className="w-3.5 h-3.5 mr-1" />
                    {t("chat.codeArtifact.collapse", "Collapse")}
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
                  <Check className="w-3.5 h-3.5 mr-1.5 text-[var(--text-success)]" />
                  <span className="text-[var(--text-success)]">
                    {t("chat.codeArtifact.copied", "Copied!")}
                  </span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 mr-1.5" />
                  {t("chat.codeArtifact.copy", "Copy")}
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
                className="h-8 px-3 text-xs bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed] hover:brightness-110 text-white"
              >
                <Code2 className="w-3.5 h-3.5 mr-1.5" />
                {t("chat.codeArtifact.apply", "Apply")}
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
            {t(
              "chat.codeArtifact.collapsed",
              "Code collapsed ({{count}} lines)",
              {
                count: lineCount,
              },
            )}
          </p>
        </CardContent>
      )}
    </Card>
  );
}
