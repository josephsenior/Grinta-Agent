import { Editor, Monaco } from "@monaco-editor/react";
import React from "react";
import { editor as editor_t } from "monaco-editor";
import { Copy, Check, FileText, ChevronRight } from "lucide-react";
import { GitChangeStatus } from "#/api/open-hands.types";
import { getLanguageFromPath } from "#/utils/get-language-from-path";
import { cn } from "#/utils/utils";
import { useGitDiff } from "#/hooks/query/use-get-diff";
// import FileIcon from "#/components/ui/file-icon";

interface LoadingSpinnerProps {
  className?: string;
}

// TODO: Move out of this file and replace the current spinner with this one
function LoadingSpinner({ className }: LoadingSpinnerProps) {
  return (
    <div className="flex items-center justify-center">
      <div
        className={cn(
          "animate-spin rounded-full border-4 border-border border-t-brand-500",
          className,
        )}
        role="status"
        aria-label="Loading"
      />
    </div>
  );
}

const STATUS_MAP: Record<GitChangeStatus, string> = {
  A: "A",
  D: "D",
  M: "M",
  R: "R",
  U: "U",
};

export interface FileDiffViewerProps {
  path: string;
  type: GitChangeStatus;
  expanded?: boolean;
  onToggle?: (expanded: boolean) => void;
}

export function FileDiffViewer({ path, type }: FileDiffViewerProps) {
  const editorRef = React.useRef<editor_t.IStandaloneCodeEditor | null>(null);
  const [copied, setCopied] = React.useState(false);
  const [lineCount, setLineCount] = React.useState(0);

  const isDeleted = type === "D";

  const filePath = React.useMemo(() => {
    if (type === "R") {
      const parts = path.split(/\s+/).slice(1);
      return parts[parts.length - 1];
    }
    return path;
  }, [path, type]);

  const {
    data: diff,
    isLoading,
    isSuccess,
  } = useGitDiff({
    filePath,
    type,
    enabled: !!filePath && typeof filePath === 'string' && filePath.trim().length > 0,
  });

  // Calculate line count
  React.useEffect(() => {
    if (isSuccess && diff) {
      const content = isDeleted ? diff.original : diff.modified;
      if (content) {
        setLineCount(content.split("\n").length);
      }
    }
  }, [isSuccess, diff, isDeleted]);

  const handleCopyPath = async () => {
    try {
      await navigator.clipboard.writeText(filePath);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Silently handle error
    }
  };

  // Generate breadcrumbs from file path
  const breadcrumbs = React.useMemo(() => {
    if (!filePath || typeof filePath !== 'string') {
      return [];
    }
    return filePath.split("/");
  }, [filePath]);

  const beforeMount = (monaco: Monaco) => {
    monaco.editor.defineTheme("bolt-theme", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "comment", foreground: "6A9955" },
        { token: "keyword", foreground: "C586C0" },
        { token: "string", foreground: "CE9178" },
        { token: "number", foreground: "B5CEA8" },
        { token: "type", foreground: "4EC9B0" },
        { token: "function", foreground: "DCDCAA" },
      ],
      colors: {
        "editor.background": "#0A0A0A",
        "editor.foreground": "#D4D4D4",
        "editor.lineHighlightBackground": "#1A1A1A",
        "editorLineNumber.foreground": "#6E6E6E",
        "editorLineNumber.activeForeground": "#A0A0A0",
        "editor.selectionBackground": "#264F78",
        "editorCursor.foreground": "#AEAFAD",
        "editorWhitespace.foreground": "#3B3B3B",
      },
    });
  };

  const handleEditorDidMount = (editor: editor_t.IStandaloneCodeEditor) => {
    editorRef.current = editor;
  };

  // Show modified content, or original if deleted
  const content = isDeleted ? diff?.original : diff?.modified;

  const status = (type === "U" ? STATUS_MAP.A : STATUS_MAP[type]) || "?";

  return (
    <div
      data-testid="file-diff-viewer-outer"
      className="w-full h-full flex flex-col"
    >
      {/* Enhanced header with breadcrumbs and actions */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-background-secondary">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-[10px] font-semibold text-foreground-secondary flex-shrink-0">
            {status}
          </span>

          {/* File Icon */}
          <div className="flex-shrink-0">
            <div className="w-4 h-4 bg-background-tertiary rounded text-xs flex items-center justify-center text-foreground-secondary">
              📄
            </div>
          </div>

          {/* Breadcrumbs */}
          <div className="flex items-center gap-1 text-xs text-foreground-secondary overflow-hidden">
            {breadcrumbs.map((crumb, index) => (
              <React.Fragment key={index}>
                {index > 0 && (
                  <ChevronRight className="w-3 h-3 text-foreground-secondary/50 flex-shrink-0" />
                )}
                <span
                  className={cn(
                    "truncate",
                    index === breadcrumbs.length - 1
                      ? "text-foreground font-medium"
                      : "text-foreground-secondary",
                  )}
                >
                  {crumb}
                </span>
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {lineCount > 0 && (
            <span className="text-[10px] text-foreground-secondary flex items-center gap-1">
              <FileText className="w-3 h-3" />
              {lineCount} lines
            </span>
          )}
          <button
            onClick={handleCopyPath}
            className="p-1 rounded text-foreground-secondary hover:text-violet-500 hover:bg-background-tertiary transition-all duration-150"
            title="Copy file path"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-success-500" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* Simple text editor */}
      <div className="flex-1 min-h-0">
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <LoadingSpinner className="w-6 h-6" />
          </div>
        )}
        {isSuccess && (
          <Editor
            data-testid="file-viewer"
            className="w-full h-full"
            language={getLanguageFromPath(filePath)}
            value={content || ""}
            theme="bolt-theme"
            onMount={handleEditorDidMount}
            beforeMount={beforeMount}
            options={{
              readOnly: true,
              scrollBeyondLastLine: false,
              minimap: { enabled: false },
              automaticLayout: true,
              scrollbar: {
                alwaysConsumeMouseWheel: false,
                vertical: "auto",
                horizontal: "auto",
              },
              lineNumbers: "on",
              renderLineHighlight: "line",
              fontSize: 12,
              fontFamily:
                "IBM Plex Mono, Menlo, Monaco, Courier New, monospace",
              padding: { top: 12, bottom: 12 },
              renderWhitespace: "none",
              glyphMargin: false,
              folding: true,
              lineDecorationsWidth: 0,
              lineNumbersMinChars: 3,
            }}
          />
        )}
      </div>
    </div>
  );
}
