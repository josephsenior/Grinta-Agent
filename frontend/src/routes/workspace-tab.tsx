import React from "react";
import { useTranslation } from "react-i18next";
import {
  Folder,
  FolderOpen,
  File,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  Search,
  Copy,
  Download,
  Eye,
  FileCode,
  FileImage,
  FileText,
  FolderPlus,
} from "lucide-react";
import { useConversationId } from "#/hooks/use-conversation-id";
import Forge from "#/api/forge";
import { LazyMonaco } from "#/components/shared/lazy-monaco";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";
import { cn } from "#/utils/utils";
import toast from "#/utils/toast";
import { logger } from "#/utils/logger";

/**
 * Simple, bolt.new-style file explorer
 * - Single section showing workspace files
 * - Synced with VSCode extension workspace
 * - Clean, minimal UI
 */

interface FileNode {
  name: string;
  path: string;
  type: "file" | "folder";
  children?: FileNode[];
}

// Build tree structure from flat file list
const buildFileTree = (files: string[]): FileNode[] => {
  const tree: FileNode[] = [];
  const nodeMap = new Map<string, FileNode>();

  const sortedFiles = [...files].sort();

  for (const filePath of sortedFiles) {
    const parts = filePath.split("/").filter(Boolean);
    let currentPath = "";

    for (let i = 0; i < parts.length; i += 1) {
      const part = parts[i];
      const parentPath = currentPath;
      currentPath = currentPath ? `${currentPath}/${part}` : part;

      if (!nodeMap.has(currentPath)) {
        const isLast = i === parts.length - 1;
        const node: FileNode = {
          name: part,
          path: currentPath,
          type: isLast ? "file" : "folder",
        };

        if (!isLast) {
          node.children = [];
        }

        nodeMap.set(currentPath, node);

        if (parentPath) {
          const parent = nodeMap.get(parentPath);
          if (parent && parent.children) {
            parent.children.push(node);
          }
        } else {
          tree.push(node);
        }
      }
    }
  }

  return tree;
};

// Get file icon based on extension (simple, clean icons)
const getFileIcon = (filename: string) => {
  const ext = filename.split(".").pop()?.toLowerCase();

  // Code files
  if (
    [
      "js",
      "jsx",
      "ts",
      "tsx",
      "py",
      "java",
      "cpp",
      "c",
      "go",
      "rs",
      "php",
      "rb",
    ].includes(ext || "")
  ) {
    return <FileCode className="w-4 h-4 text-[#4ec9b0]" />;
  }

  // Images
  if (["jpg", "jpeg", "png", "gif", "svg", "webp", "ico"].includes(ext || "")) {
    return <FileImage className="w-4 h-4 text-green-400" />;
  }

  // Documents
  if (["md", "txt", "pdf", "doc", "docx"].includes(ext || "")) {
    return <FileText className="w-4 h-4 text-blue-400" />;
  }

  return <File className="w-4 h-4 text-[#858585]" />;
};

// Get language from file extension
const getLanguageFromPath = (path: string): string => {
  const ext = path.split(".").pop()?.toLowerCase();
  const langMap: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    py: "python",
    java: "java",
    cpp: "cpp",
    c: "c",
    go: "go",
    rs: "rust",
    php: "php",
    rb: "ruby",
    html: "html",
    css: "css",
    scss: "scss",
    json: "json",
    yaml: "yaml",
    yml: "yaml",
    md: "markdown",
    txt: "plaintext",
    sh: "shell",
    bash: "shell",
  };
  return langMap[ext || ""] || "plaintext";
};

function WorkspaceFilesTab() {
  const { t } = useTranslation();
  const { conversationId } = useConversationId();

  // State
  const [files, setFiles] = React.useState<string[]>([]);
  const [fileTree, setFileTree] = React.useState<FileNode[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState("");
  const [selectedFile, setSelectedFile] = React.useState<string | null>(null);
  const [fileContent, setFileContent] = React.useState<string>("");
  const [loadingContent, setLoadingContent] = React.useState(false);
  const [expandedFolders, setExpandedFolders] = React.useState<Set<string>>(
    new Set(),
  );
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // Load file content
  const loadFileContent = React.useCallback(
    async (filePath: string) => {
      if (!conversationId) return;

      // Safety check: Don't try to load directories
      if (filePath.endsWith("/")) {
        logger.warn("Attempted to load directory as file:", filePath);
        toast.error("not-a-file", "Cannot view directory contents");
        return;
      }

      setLoadingContent(true);
      try {
        const content = await Forge.getFile(conversationId, filePath);
        setFileContent(content || "");
      } catch (err: unknown) {
        logger.error("Failed to load file:", err);

        // Check if it's a "is a directory" error
        const error = err as { message?: string; response?: { data?: string } };
        if (
          error?.message?.includes("Is a directory") ||
          error?.response?.data?.includes("Is a directory")
        ) {
          toast.error("is-directory", "This is a folder, not a file");
        } else {
          toast.error("load-file-error", "Failed to load file content");
        }

        setFileContent("");
      } finally {
        setLoadingContent(false);
      }
    },
    [conversationId],
  );

  // Load workspace files
  const loadFiles = React.useCallback(async () => {
    if (!conversationId) return;

    setLoading(true);
    try {
      const response = await Forge.getFiles(conversationId);
      const normalized: string[] = (response || []).map(
        (entry: string | { path?: string }) =>
          typeof entry === "string" ? entry : (entry?.path ?? ""),
      );
      setFiles(normalized);
      setFileTree(buildFileTree(normalized));

      // Auto-select first actual file (not a directory)
      if (normalized.length > 0 && !selectedFile) {
        const firstFile = normalized.find(
          (path: string) => !path.endsWith("/") && path.includes("."),
        );
        if (firstFile) {
          setSelectedFile(firstFile);
          loadFileContent(firstFile);
        }
      }
    } catch (err) {
      const error = err as {
        message?: string;
        response?: { data?: { error_code?: string } };
      };
      const errorCode = error?.response?.data?.error_code;

      // Don't show error toast for RUNTIME_NOT_READY - it's expected during startup
      if (errorCode !== "RUNTIME_NOT_READY") {
        logger.error("Failed to load workspace files:", err);
        toast.error("load-files-error", "Failed to load workspace files");
      } else {
        logger.debug("Runtime not ready yet, will retry automatically");
      }
    } finally {
      setLoading(false);
    }
  }, [conversationId, selectedFile, loadFileContent]);

  // Initial load
  React.useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  // Toggle folder
  const toggleFolder = (folderPath: string) => {
    setExpandedFolders((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(folderPath)) {
        newSet.delete(folderPath);
      } else {
        newSet.add(folderPath);
      }
      return newSet;
    });
  };

  // Handle file select
  const handleFileSelect = (filePath: string, nodeType?: "file" | "folder") => {
    // Safety check: Don't try to load folders as files
    if (nodeType === "folder") {
      logger.warn("Attempted to select a folder as a file:", filePath);
      return;
    }

    // Also check if path ends with '/' which typically indicates a directory
    if (filePath.endsWith("/")) {
      logger.warn("File path ends with /, skipping:", filePath);
      return;
    }

    setSelectedFile(filePath);
    loadFileContent(filePath);
  };

  // File actions
  const handleCopy = async () => {
    if (!fileContent) return;
    try {
      await navigator.clipboard.writeText(fileContent);
      toast.success("copy-success", "Copied to clipboard");
    } catch (err) {
      toast.error("copy-error", "Failed to copy");
    }
  };

  const handleDownload = () => {
    if (!fileContent || !selectedFile) return;
    const blob = new Blob([fileContent], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = selectedFile.split("/").pop() || "file";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("download-success", `Downloaded ${selectedFile}`);
  };

  // Handle import workspace (file upload)
  const handleImportWorkspace = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const uploadedFiles = event.target.files;
    if (!uploadedFiles || uploadedFiles.length === 0 || !conversationId) return;

    try {
      const filesArray = Array.from(uploadedFiles);
      await Forge.uploadFiles(conversationId, filesArray);
      toast.success("upload-success", `Uploaded ${filesArray.length} file(s)`);

      // Reload files to show the uploaded ones
      await loadFiles();
    } catch (err) {
      logger.error("Failed to upload files:", err);
      toast.error("upload-error", "Failed to upload files");
    }

    // Reset the input so the same file can be uploaded again if needed
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Filter tree
  const filteredTree = React.useMemo(() => {
    if (!searchQuery) return fileTree;

    const filterNode = (node: FileNode): FileNode | null => {
      const matches = node.name
        .toLowerCase()
        .includes(searchQuery.toLowerCase());

      if (node.type === "file") {
        return matches ? node : null;
      }

      const filteredChildren =
        node.children
          ?.map(filterNode)
          .filter((child): child is FileNode => child !== null) || [];

      if (matches || filteredChildren.length > 0) {
        return {
          ...node,
          children: filteredChildren,
        };
      }

      return null;
    };

    return fileTree
      .map(filterNode)
      .filter((node): node is FileNode => node !== null);
  }, [fileTree, searchQuery]);

  // Render file tree node
  const renderNode = (node: FileNode, depth: number): React.ReactNode => {
    const isExpanded = expandedFolders.has(node.path);
    const isSelected = selectedFile === node.path;

    return (
      <div key={node.path}>
        <button
          type="button"
          className={cn(
            "flex items-center gap-2 w-full px-2 py-1.5 rounded transition-all duration-150",
            "hover:bg-[var(--bg-tertiary)]",
            isSelected &&
              "bg-[var(--border-accent)]/20 border-l-2 border-[var(--border-accent)] shadow-sm",
          )}
          style={{ paddingLeft: `${8 + depth * 12}px` }}
          onClick={() => {
            if (node.type === "folder") {
              toggleFolder(node.path);
            } else {
              handleFileSelect(node.path, node.type);
            }
          }}
        >
          {/* Folder chevron */}
          {node.type === "folder" && (
            <div className="w-4 h-4 flex items-center justify-center">
              {isExpanded ? (
                <ChevronDown className="w-3 h-3 text-[var(--text-tertiary)]" />
              ) : (
                <ChevronRight className="w-3 h-3 text-[var(--text-tertiary)]" />
              )}
            </div>
          )}

          {/* Icon */}
          <div className="flex-shrink-0">
            {(() => {
              if (node.type === "folder") {
                return isExpanded ? (
                  <FolderOpen className="w-4 h-4 text-[var(--text-accent)]" />
                ) : (
                  <Folder className="w-4 h-4 text-[var(--text-accent)]" />
                );
              }
              return getFileIcon(node.name);
            })()}
          </div>

          {/* Name */}
          <span
            className={cn(
              "flex-1 truncate text-left text-sm",
              isSelected
                ? "text-[var(--text-primary)] font-medium"
                : "text-[var(--text-secondary)]",
            )}
          >
            {node.name}
          </span>
        </button>

        {/* Children */}
        {node.type === "folder" && isExpanded && node.children && (
          <div>
            {node.children.map((child) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  // Get filename and language
  const fileName = selectedFile?.split("/").pop() || "";
  const language = selectedFile
    ? getLanguageFromPath(selectedFile)
    : "plaintext";

  return (
    <main className="h-full overflow-hidden flex flex-col bg-transparent">
      {/* Header - Modern Slate style - more compact */}
      <div className="flex-none border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)]/40">
        <div className="flex items-center justify-between px-4 py-2">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-[var(--border-accent)]/10">
              <Folder className="w-3.5 h-3.5 text-[var(--text-accent)]" />
            </div>
            <h2 className="text-xs font-semibold text-[var(--text-primary)] uppercase tracking-tight">
              {t("workspace.title", "Workspace")}
            </h2>
            <Badge
              variant="secondary"
              className="text-[10px] bg-[var(--border-accent)]/10 text-[var(--text-accent)] border-[var(--border-accent)]/20 px-1.5 h-4"
            >
              {files.length}
            </Badge>
          </div>

          <div className="flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={loadFiles}
              disabled={loading}
              className="h-7 w-7 p-0 hover:bg-[var(--bg-tertiary)] text-[var(--text-tertiary)]"
            >
              <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} />
            </Button>
          </div>
        </div>

        {/* Search - Integrated into header area */}
        <div className="px-4 pb-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-[var(--text-tertiary)]" />
            <input
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1 text-[11px] bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:border-[var(--border-accent)] focus:ring-1 focus:ring-[var(--border-accent)]/40"
            />
          </div>
        </div>
      </div>
      {/* Main Content */}
      <div className="flex-1 flex gap-0 min-h-0 overflow-hidden">
        {/* File Tree Sidebar - Slightly transparent */}
        <aside className="w-72 max-w-[40%] min-w-[240px] border-r border-[var(--border-subtle)] bg-[var(--bg-secondary)] overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto overflow-x-hidden p-2 custom-scrollbar">
            {(() => {
              if (loading) {
                return (
                  <div className="flex items-center justify-center h-32">
                    <RefreshCw className="w-4 h-4 animate-spin text-[var(--text-tertiary)]" />
                  </div>
                );
              }
              if (filteredTree.length === 0) {
                return (
                  <div className="flex flex-col items-center justify-center h-32 text-[var(--text-tertiary)] opacity-60">
                    <Folder className="w-6 h-6 mb-2" />
                    <p className="text-[10px] uppercase tracking-widest font-semibold">
                      {searchQuery ? "No matches" : "Empty Workspace"}
                    </p>
                  </div>
                );
              }
              return (
                <div className="space-y-0.5">
                  {filteredTree.map((node) => renderNode(node, 0))}
                </div>
              );
            })()}
          </div>
        </aside>

        {/* File Viewer */}
        <section className="flex-1 overflow-hidden bg-transparent flex flex-col">
          {selectedFile ? (
            <>
              <div className="flex items-center justify-between px-4 py-1.5 border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)]/30">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="p-1 rounded bg-[var(--bg-tertiary)] flex-shrink-0">
                    <Eye className="w-3 h-3 text-[var(--text-accent)]" />
                  </div>
                  <span className="text-[11px] font-medium text-[var(--text-primary)] truncate">
                    {fileName}
                  </span>
                  <Badge
                    variant="outline"
                    className="text-[9px] px-1 h-3.5 border-[var(--border-subtle)] text-[var(--text-tertiary)] uppercase"
                  >
                    {language}
                  </Badge>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopy}
                    className="h-6 px-1.5 hover:bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
                  >
                    <Copy className="w-3 h-3 mr-1" />
                    <span className="text-[10px]">Copy</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleDownload}
                    className="h-6 px-1.5 hover:bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
                  >
                    <Download className="w-3 h-3 mr-1" />
                    <span className="text-[10px]">Download</span>
                  </Button>
                </div>
              </div>

              <div className="flex-1 overflow-hidden bg-[var(--bg-primary)]">
                {loadingContent ? (
                  <div className="flex items-center justify-center h-full">
                    <RefreshCw className="w-5 h-5 animate-spin text-[var(--text-tertiary)]" />
                  </div>
                ) : (
                  <LazyMonaco
                    value={fileContent}
                    onChange={() => {}}
                    language={language}
                    height="100%"
                    theme="modern-slate-editor"
                    options={{
                      readOnly: true,
                      minimap: { enabled: false },
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
                    beforeMount={(monaco: unknown) => {
                      const monacoEditor = monaco as {
                        editor: {
                          defineTheme: (
                            name: string,
                            theme: Record<string, unknown>,
                          ) => void;
                        };
                      };
                      monacoEditor.editor.defineTheme("modern-slate-editor", {
                        base: "vs-dark",
                        inherit: true,
                        rules: [],
                        colors: {
                          "editor.background": "#0b0d11",
                          "editor.lineHighlightBackground": "#12151a",
                          "editorGutter.background": "#0b0d11",
                          "editorWidget.background": "#1a1e24",
                          "editorGroupHeader.tabsBackground": "#12151a",
                          "editorLineNumber.foreground": "#475569",
                          "editorLineNumber.activeForeground": "#8b5cf6",
                        },
                      });
                    }}
                  />
                )}
              </div>
            </>
          ) : (
            <div className="h-full w-full flex flex-col items-center justify-center text-[var(--text-tertiary)] gap-6 p-8">
              <div className="relative">
                <div className="absolute inset-0 bg-violet-500/10 blur-2xl rounded-full" />
                <Folder className="w-16 h-16 opacity-20 relative z-10" />
              </div>
              <div className="text-center space-y-1.5">
                <p className="text-sm font-medium text-[var(--text-primary)]">
                  {t(
                    "workspace.selectFile",
                    "Select a file to view its content",
                  )}
                </p>
                <p className="text-xs text-[var(--text-tertiary)] max-w-[280px]">
                  Explore your project structure and view source code directly
                  in the workspace.
                </p>
              </div>

              <Button
                onClick={handleImportWorkspace}
                className={cn(
                  "px-8 py-2.5 h-auto",
                  "bg-gradient-to-r from-violet-600 to-purple-600",
                  "hover:from-violet-500 hover:to-purple-500",
                  "text-white font-semibold text-sm",
                  "rounded-xl shadow-lg shadow-violet-500/20",
                  "transition-all duration-300",
                  "hover:shadow-xl hover:shadow-violet-500/30",
                  "hover:scale-[1.02] active:scale-[0.98]",
                )}
              >
                <FolderPlus className="w-4 h-4 mr-2" />
                {t("workspace.importWorkspace", "Import Workspace")}
              </Button>

              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileUpload}
                className="hidden"
              />

              <div className="flex items-center gap-2 text-[10px] text-[var(--text-muted)] uppercase tracking-widest font-bold opacity-50 pt-4">
                <div className="w-8 h-[1px] bg-current" />
                {t("workspace.syncedWithVSCode", "Synced with VSCode")}
                <div className="w-8 h-[1px] bg-current" />
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

export default WorkspaceFilesTab;
