import React from "react";
import { Editor } from "@monaco-editor/react";
import { editor as editor_t } from "monaco-editor";
import { Copy, Check, FileText, Zap } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "#/utils/utils";
import { getLanguageFromPath } from "#/utils/get-language-from-path";
import { logger } from "#/utils/logger";

interface StreamingFileViewerProps {
  path: string;
  content: string;
  isStreaming?: boolean;
  className?: string;
}

export function StreamingFileViewer({
  path,
  content,
  isStreaming = false,
  className,
}: StreamingFileViewerProps) {
  const { t } = useTranslation();
  const editorRef = React.useRef<editor_t.IStandaloneCodeEditor | null>(null);
  const [copied, setCopied] = React.useState(false);
  const [lineCount, setLineCount] = React.useState(0);

  const language = getLanguageFromPath(path);
  const fileName = path.split("/").pop() || path;

  // Update editor content when streaming content changes
  React.useEffect(() => {
    if (editorRef.current && content !== undefined) {
      editorRef.current.setValue(content);
      // Scroll to bottom for streaming content
      if (isStreaming) {
        editorRef.current.revealLine(
          editorRef.current.getModel()?.getLineCount() || 1,
        );
      }
    }
  }, [content, isStreaming]);

  const handleEditorDidMount = (editor: editor_t.IStandaloneCodeEditor) => {
    editorRef.current = editor;

    // Configure editor for streaming content
    editor.updateOptions({
      readOnly: true,
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      lineNumbers: "on",
      folding: false,
      automaticLayout: true,
    });

    // Update line count when content changes
    const model = editor.getModel();
    if (model) {
      setLineCount(model.getLineCount());

      // Listen for content changes to update line count
      const disposable = model.onDidChangeContent(() => {
        setLineCount(model.getLineCount());
      });

      // Cleanup on unmount
      return () => disposable.dispose();
    }

    // Return undefined if no model
    return undefined;
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      logger.error("Failed to copy to clipboard:", err);
    }
  };

  return (
    <div
      className={cn("h-full flex flex-col bg-background-primary", className)}
    >
      {/* Header */}
      <div className="flex-none border-b border-border bg-background-secondary">
        <div className="flex items-center justify-between px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <FileText className="w-4 h-4 text-violet-500" />
            <span className="text-sm font-medium text-foreground truncate">
              {fileName}
            </span>
            {isStreaming && (
              <div className="flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-violet-500 animate-pulse" />
                <span className="text-xs text-violet-500 font-medium">
                  {t("streamingFileViewer.streaming", "Streaming")}
                </span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-foreground-secondary">
              {t("streamingFileViewer.lineCount", "{{count}} lines", {
                count: lineCount,
              })}
            </span>
            <button
              type="button"
              onClick={copyToClipboard}
              className="flex items-center gap-1.5 px-2 py-1 text-xs text-foreground-secondary hover:text-foreground hover:bg-background-tertiary rounded transition-colors"
              title="Copy to clipboard"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-success-500" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        </div>
      </div>

      {/* Streaming indicator */}
      {isStreaming && (
        <div className="flex-none px-4 py-1.5 bg-brand-500/10 border-b border-brand-500/20">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-brand-500 rounded-full animate-pulse" />
            <span className="text-xs text-violet-500 font-medium">
              Generating content in real-time...
            </span>
          </div>
        </div>
      )}

      {/* Editor */}
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          language={language}
          value={content}
          onMount={handleEditorDidMount}
          theme="vs-dark"
          options={{
            readOnly: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            lineNumbers: "on",
            folding: false,
            automaticLayout: true,
            padding: { top: 16, bottom: 16 },
            fontSize: 14,
            fontFamily: "Menlo, Monaco, 'Courier New', monospace",
          }}
        />
      </div>
    </div>
  );
}
