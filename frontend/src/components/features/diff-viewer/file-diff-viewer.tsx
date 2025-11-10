import { Editor, Monaco } from "@monaco-editor/react";
import React from "react";
import { editor as editor_t } from "monaco-editor";
import { Copy, Check, FileText, ChevronRight } from "lucide-react";
import { GitChangeStatus } from "#/api/forge.types";
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
  const controller = useFileDiffController({ path, type });
  const { status } = controller;

  return (
    <div
      data-testid="file-diff-viewer-outer"
      className="w-full h-full flex flex-col"
    >
      {/* Enhanced header with breadcrumbs and actions */}
      <FileDiffHeader controller={controller} status={status} />

      {/* Simple text editor */}
      <div className="flex-1 min-h-0">
        {controller.isLoading && (
          <div className="flex items-center justify-center h-full">
            <LoadingSpinner className="w-6 h-6" />
          </div>
        )}

        {!controller.isLoading && controller.content && (
          <Editor
            beforeMount={controller.beforeMount}
            onMount={controller.handleEditorDidMount}
            value={controller.content}
            language={getLanguageFromPath(controller.filePath)}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              fontSize: 14,
              scrollBeyondLastLine: false,
              automaticLayout: true,
              scrollbar: {
                alwaysConsumeMouseWheel: false,
                vertical: "auto",
                horizontal: "auto",
              },
              lineNumbers: "on",
              renderLineHighlight: "line",
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

        {!controller.isLoading && !controller.content && (
          <div className="flex items-center justify-center h-full">
            <div className="text-sm text-foreground-secondary">
              No diff available
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function useFileDiffController({ path, type }: FileDiffViewerProps) {
  const editorRef = React.useRef<editor_t.IStandaloneCodeEditor | null>(null);
  const [copied, setCopied] = React.useState(false);
  const [lineCount, setLineCount] = React.useState(0);
  const isDeleted = type === "D";

  const filePath = React.useMemo(
    () => deriveFilePath(path, type),
    [path, type],
  );

  const diffQuery = useGitDiff({
    filePath,
    type,
    enabled: Boolean(filePath?.trim().length),
  });

  React.useEffect(() => {
    if (diffQuery.isSuccess && diffQuery.data) {
      const content = isDeleted
        ? diffQuery.data.original
        : diffQuery.data.modified;
      if (content) {
        setLineCount(content.split("\n").length);
      }
    }
  }, [diffQuery.isSuccess, diffQuery.data, isDeleted]);

  const handleCopyPath = React.useCallback(async () => {
    try {
      await navigator.clipboard.writeText(filePath);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // no-op
    }
  }, [filePath]);

  const breadcrumbs = React.useMemo(
    () => (filePath ? filePath.split("/") : []),
    [filePath],
  );

  const beforeMount = React.useCallback((monaco: Monaco) => {
    monaco.editor.defineTheme("bolt-theme", buildBoltTheme());
  }, []);

  const handleEditorDidMount = React.useCallback(
    (editor: editor_t.IStandaloneCodeEditor) => {
      editorRef.current = editor;
    },
    [],
  );

  const content = isDeleted
    ? diffQuery.data?.original
    : diffQuery.data?.modified;
  const status = (type === "U" ? STATUS_MAP.A : STATUS_MAP[type]) || "?";

  return {
    editorRef,
    copied,
    handleCopyPath,
    lineCount,
    breadcrumbs,
    beforeMount,
    handleEditorDidMount,
    content,
    isLoading: diffQuery.isLoading,
    filePath,
    status,
  };
}

function deriveFilePath(path: string, type: GitChangeStatus) {
  if (type === "R") {
    const parts = path.split(/\s+/).slice(1);
    return parts[parts.length - 1];
  }
  return path;
}

function buildBoltTheme() {
  return {
    base: "vs-dark" as const,
    inherit: true,
    rules: [
      { token: "comment", foreground: "6A9955" },
      { token: "keyword", foreground: "C586C0" },
      { token: "string", foreground: "CE9178" },
      { token: "number", foreground: "B5CEA8" },
      { token: "type", foreground: "4EC9B0" },
      { token: "function", foreground: "DCDCAA" },
    ] as any,
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
  };
}

function FileDiffHeader({
  controller,
  status,
}: {
  controller: ReturnType<typeof useFileDiffController>;
  status: string;
}) {
  return (
    <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-background-secondary">
      <FileDiffBreadcrumbs
        status={status}
        breadcrumbs={controller.breadcrumbs}
      />
      <FileDiffActions
        lineCount={controller.lineCount}
        copied={controller.copied}
        onCopyPath={controller.handleCopyPath}
      />
    </div>
  );
}

function FileDiffBreadcrumbs({
  status,
  breadcrumbs,
}: {
  status: string;
  breadcrumbs: string[];
}) {
  return (
    <div className="flex items-center gap-2 flex-1 min-w-0">
      <span className="text-[10px] font-semibold text-foreground-secondary flex-shrink-0">
        {status}
      </span>
      <div className="flex-shrink-0">
        <div className="w-4 h-4 bg-background-tertiary rounded text-xs flex items-center justify-center text-foreground-secondary">
          📄
        </div>
      </div>
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
  );
}

function FileDiffActions({
  lineCount,
  copied,
  onCopyPath,
}: {
  lineCount: number;
  copied: boolean;
  onCopyPath: () => void;
}) {
  return (
    <div className="flex items-center gap-2 flex-shrink-0">
      {lineCount > 0 && (
        <span className="text-[10px] text-foreground-secondary flex items-center gap-1">
          <FileText className="w-3 h-3" />
          {lineCount} lines
        </span>
      )}
      <button
        onClick={onCopyPath}
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
  );
}
