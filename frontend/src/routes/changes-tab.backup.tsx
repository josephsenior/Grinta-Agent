import { useTranslation } from "react-i18next";
import React from "react";
import { Files, Search, RefreshCw, Zap, Folder, Eye, Download, Copy, Filter } from "lucide-react";
import { FileDiffViewer } from "#/components/features/diff-viewer/file-diff-viewer";
import { StreamingFileViewer } from "#/components/features/diff-viewer/streaming-file-viewer";
import FileTree, {
  type GitChange,
} from "#/components/features/diff-viewer/file-tree";
import type { GitChangeStatus } from "#/api/open-hands.types";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";
import { useGetGitChanges } from "#/hooks/query/use-get-git-changes";
import {
  useStreamingChunks,
  useLatestStreamingContent,
} from "#/hooks/use-ws-events";
import { I18nKey } from "#/i18n/declaration";
import { useRuntimeIsReady } from "#/hooks/use-runtime-is-ready";
import { useConversationId } from "#/hooks/use-conversation-id";
import OpenHands from "#/api/open-hands";
import { LazyMonaco } from "#/components/shared/lazy-monaco";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";
import toast from "#/utils/toast";
// Protips removed: RandomTip intentionally omitted to prevent protips from appearing

// Error message patterns
const GIT_REPO_ERROR_PATTERN = /not a git repository/i;

function StatusMessage({ children }: React.PropsWithChildren) {
  return (
    <div className="w-full h-full flex flex-col items-center text-center justify-center text-2xl text-foreground-secondary">
      {children}
    </div>
  );
}

// File tree building utilities
interface FileNode {
  name: string;
  path: string;
  type: "file" | "folder";
  children?: FileNode[];
  status?: "new" | "modified" | "deleted" | "unchanged";
}

const buildFileTree = (files: string[]): FileNode[] => {
  const tree: FileNode[] = [];
  const nodeMap = new Map<string, FileNode>();
  
  const sortedFiles = [...files].sort();
  
  for (const filePath of sortedFiles) {
    const parts = filePath.split('/').filter(Boolean);
    let currentPath = '';
    
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const parentPath = currentPath;
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      
      if (!nodeMap.has(currentPath)) {
        const isLast = i === parts.length - 1;
        const node: FileNode = {
          name: part,
          path: currentPath,
          type: isLast ? 'file' : 'folder',
          status: 'unchanged'
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

// Get file icon based on extension
const getFileIcon = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase();
  return ext ? `📄` : '📄'; // Simple emoji icons for now
};

function GitChanges() {
  const { t } = useTranslation();
  const { conversationId } = useConversationId();
  const {
    data: gitChanges,
    isSuccess,
    error,
    isLoading: loadingGitChanges,
  } = useGetGitChanges();

  // Streaming content integration
  const streamingChunks = useStreamingChunks();
  const latestStreamingContent = useLatestStreamingContent();
  const isStreaming =
    streamingChunks.length > 0 &&
    streamingChunks[streamingChunks.length - 1]?.args.is_final === false;

  // Runtime state - must be declared before useEffect that uses it
  const runtimeIsActive = useRuntimeIsReady();

  // File management state
  const [viewMode, setViewMode] = React.useState<"changes" | "all">("changes");
  const [allFiles, setAllFiles] = React.useState<string[]>([]);
  const [fileTree, setFileTree] = React.useState<FileNode[]>([]);
  const [loadingAllFiles, setLoadingAllFiles] = React.useState(false);
  const [expandedFolders, setExpandedFolders] = React.useState<Set<string>>(new Set());
  const [selectedFileContent, setSelectedFileContent] = React.useState<string>("");
  const [loadingFileContent, setLoadingFileContent] = React.useState(false);

  // Debug: Log rendering and runtime state
  React.useEffect(() => {
    console.log("Editor tab rendering:", { 
      isSuccess, 
      gitChangesCount: gitChanges?.length,
      loadingGitChanges,
      error: error?.message,
      runtimeIsActive 
    });
  }, [isSuccess, gitChanges, loadingGitChanges, error, runtimeIsActive]);

  const [statusMessage, setStatusMessage] = React.useState<string[] | null>(
    null,
  );

  const isNotGitRepoError =
    error && GIT_REPO_ERROR_PATTERN.test(retrieveAxiosErrorMessage(error));

  React.useEffect(() => {
    if (!runtimeIsActive) {
      setStatusMessage([I18nKey.DIFF_VIEWER$WAITING_FOR_RUNTIME]);
    } else if (loadingGitChanges) {
      setStatusMessage([I18nKey.DIFF_VIEWER$LOADING]);
    } else if (error) {
      const errorMessage = retrieveAxiosErrorMessage(error);
      // Handle 404 errors gracefully (runtime starting or no git repo)
      if (errorMessage.includes('404') || errorMessage.includes('Not Found')) {
        setStatusMessage([I18nKey.DIFF_VIEWER$WAITING_FOR_RUNTIME]);
      } else if (GIT_REPO_ERROR_PATTERN.test(errorMessage)) {
        setStatusMessage([
          I18nKey.DIFF_VIEWER$NOT_A_GIT_REPO,
          I18nKey.DIFF_VIEWER$ASK_OH,
        ]);
      } else {
        setStatusMessage([errorMessage]);
      }
    } else {
      setStatusMessage(null);
    }
  }, [
    runtimeIsActive,
    isNotGitRepoError,
    loadingGitChanges,
    error,
    setStatusMessage,
  ]);

  const [selected, setSelected] = React.useState<{
    path: string;
    status?: string;
  } | null>(null);

  // Streaming mode state
  const [showStreamingMode, setShowStreamingMode] = React.useState(false);

  React.useEffect(() => {
    // auto-select first file when list updates
    if (isSuccess && gitChanges && gitChanges.length && !selected) {
      setSelected({ path: gitChanges[0].path, status: gitChanges[0].status });
    }
  }, [isSuccess, gitChanges]);

  const [searchQuery, setSearchQuery] = React.useState("");
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const fileListRef = React.useRef<HTMLDivElement>(null);

  // Load all files when switching to "all" mode
  const loadAllFiles = React.useCallback(async () => {
    if (!conversationId) return;
    
    setLoadingAllFiles(true);
    try {
      const response = await OpenHands.getFiles(conversationId);
      setAllFiles(response);
      setFileTree(buildFileTree(response));
    } catch (err) {
      console.error('Failed to load all files:', err);
      toast.error('load-files-error', 'Failed to load workspace files');
    } finally {
      setLoadingAllFiles(false);
    }
  }, [conversationId]);

  // Load all files when view mode changes to "all"
  React.useEffect(() => {
    if (viewMode === "all" && allFiles.length === 0) {
      loadAllFiles();
    }
  }, [viewMode, allFiles.length, loadAllFiles]);

  // Load file content for "all files" mode
  const loadFileContent = React.useCallback(async (filePath: string) => {
    if (!conversationId) return;
    
    setLoadingFileContent(true);
    try {
      const response = await OpenHands.getFile(conversationId, filePath);
      setSelectedFileContent(response || "");
    } catch (err) {
      console.error('Failed to load file content:', err);
      toast.error('load-content-error', 'Failed to load file content');
      setSelectedFileContent("");
    } finally {
      setLoadingFileContent(false);
    }
  }, [conversationId]);

  // Toggle folder expansion
  const toggleFolder = (folderPath: string) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(folderPath)) {
        newSet.delete(folderPath);
      } else {
        newSet.add(folderPath);
      }
      return newSet;
    });
  };

  // Handle file copy
  const handleCopyFile = async () => {
    if (!selectedFileContent) return;
    try {
      await navigator.clipboard.writeText(selectedFileContent);
      toast.success('copy-success', 'File content copied to clipboard');
    } catch (err) {
      console.error('Failed to copy:', err);
      toast.error('copy-error', 'Failed to copy to clipboard');
    }
  };

  // Handle file download
  const handleDownloadFile = () => {
    if (!selectedFileContent || !selected) return;
    
    const blob = new Blob([selectedFileContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = selected.path.split('/').pop() || 'file';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('download-success', `Downloaded ${selected.path}`);
  };

  const filteredChanges = React.useMemo(() => {
    if (!searchQuery || !gitChanges) return gitChanges;
    return gitChanges.filter((change) =>
      change.path.toLowerCase().includes(searchQuery.toLowerCase()),
    );
  }, [gitChanges, searchQuery]);

  // Render file tree node for "all files" mode
  const renderFileNode = (node: FileNode, depth: number): React.ReactNode => {
    const isExpanded = expandedFolders.has(node.path);
    const isSelected = selected?.path === node.path;
    
    return (
      <div key={node.path}>
        <button
          type="button"
          className={cn(
            "flex items-center gap-2 w-full px-2 py-1.5 rounded text-xs transition-all duration-150",
            "hover:bg-black",
            isSelected && "bg-brand-500/10 border-l-2 border-brand-500"
          )}
          style={{ paddingLeft: `${8 + depth * 12}px` }}
          onClick={() => {
            if (node.type === 'folder') {
              toggleFolder(node.path);
            } else {
              setSelected({ path: node.path, status: node.status });
              loadFileContent(node.path);
            }
          }}
        >
          <span className="flex-shrink-0 text-sm">
            {node.type === 'folder' ? (isExpanded ? '📂' : '📁') : getFileIcon(node.name)}
          </span>
          <span className={cn(
            "flex-1 truncate text-left",
            isSelected ? "text-brand-500 font-medium" : "text-foreground-secondary"
          )}>
            {node.name}
          </span>
        </button>
        
        {node.type === 'folder' && isExpanded && node.children && (
          <div>
            {node.children.map(child => renderFileNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1000);
  };

  // Keyboard navigation
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!filteredChanges || filteredChanges.length === 0) return;

      const currentIndex = filteredChanges.findIndex(
        (change) => change.path === selected?.path,
      );

      if (e.key === "ArrowDown") {
        e.preventDefault();
        const nextIndex = Math.min(
          currentIndex + 1,
          filteredChanges.length - 1,
        );
        setSelected({
          path: filteredChanges[nextIndex].path,
          status: filteredChanges[nextIndex].status,
        });
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        const prevIndex = Math.max(currentIndex - 1, 0);
        setSelected({
          path: filteredChanges[prevIndex].path,
          status: filteredChanges[prevIndex].status,
        });
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [filteredChanges, selected]);

  return (
    <main className="h-full overflow-hidden flex flex-col bg-black">
      {!isSuccess || !gitChanges.length ? (
        <div className="relative flex h-full w-full items-center justify-center">
          <div className="flex flex-col items-center justify-center gap-4 text-center px-6">
            {statusMessage && (
              <StatusMessage>
                {statusMessage.map((msg) => (
                  <span
                    key={msg}
                    className="text-foreground-secondary text-base"
                  >
                    {t(msg)}
                  </span>
                ))}
              </StatusMessage>
            )}
          </div>
        </div>
      ) : (
        <>
          {/* Bolt-Style Header */}
          <div className="flex-none border-b border-violet-500/20 bg-black backdrop-blur-sm">
            <div className="flex items-center justify-between px-4 py-2.5">
              <div className="flex items-center gap-2.5">
                {viewMode === "changes" ? (
                  <Files className="w-4 h-4 text-brand-500" />
                ) : (
                  <Folder className="w-4 h-4 text-brand-500" />
                )}
                <h2 className="text-xs font-medium text-foreground">
                  {viewMode === "changes" 
                    ? t("WORKSPACE$CHANGES_TAB_LABEL", { defaultValue: "Changes" })
                    : "All Files"
                  }
                </h2>
                <span className="px-1.5 py-0.5 text-[10px] font-medium bg-black text-foreground rounded">
                  {viewMode === "changes" 
                    ? (filteredChanges?.length || 0)
                    : (allFiles.length || 0)
                  }
                </span>
                {searchQuery && viewMode === "changes" && (
                  <span className="text-[10px] text-foreground-secondary">
                    (filtered from {gitChanges?.length || 0})
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                {/* View Mode Toggle */}
                <div className="flex items-center border border-violet-500/20 rounded-md p-0.5 mr-1">
                  <button
                    type="button"
                    onClick={() => setViewMode("changes")}
                    className={cn(
                      "px-2 py-1 text-[10px] font-medium rounded transition-all duration-150",
                      viewMode === "changes"
                        ? "bg-brand-500 text-white"
                        : "text-foreground-secondary hover:text-foreground hover:bg-black"
                    )}
                    title="Show only changed files"
                  >
                    <Files className="w-3 h-3 inline mr-1" />
                    Changes
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode("all")}
                    className={cn(
                      "px-2 py-1 text-[10px] font-medium rounded transition-all duration-150",
                      viewMode === "all"
                        ? "bg-brand-500 text-white"
                        : "text-foreground-secondary hover:text-foreground hover:bg-black"
                    )}
                    title="Show all workspace files"
                  >
                    <Folder className="w-3 h-3 inline mr-1" />
                    All Files
                  </button>
                </div>
                <div className="flex items-center gap-1">
                {/* Streaming Toggle */}
                {isStreaming && (
                  <button
                    type="button"
                    onClick={() => setShowStreamingMode(!showStreamingMode)}
                    className={`p-1 rounded transition-all duration-150 ${
                      showStreamingMode
                        ? "text-brand-500 bg-brand-500/10"
                        : "text-foreground-secondary hover:text-brand-500 hover:bg-black"
                    }`}
                    aria-label="Toggle streaming mode"
                    title={
                      showStreamingMode
                        ? "Show git changes"
                        : "Show streaming content"
                    }
                  >
                    <Zap
                      className={`w-3.5 h-3.5 ${isStreaming ? "animate-pulse" : ""}`}
                    />
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleRefresh}
                  className="p-1 rounded text-foreground-secondary hover:text-brand-500 hover:bg-black transition-all duration-150"
                  aria-label="Refresh"
                  title="Refresh changes"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`}
                  />
                </button>
              </div>
              </div>
            </div>

            {/* Search Bar */}
            <div className="px-4 pb-2.5">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-foreground-secondary" />
                <input
                  type="text"
                  placeholder="Search files..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-black border border-violet-500/20 rounded text-foreground placeholder:text-foreground-secondary/50 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition-all duration-150"
                />
              </div>
            </div>
          </div>

          {/* Main Content Area */}
          <div className="flex-1 flex gap-0 min-h-0 overflow-hidden">
            {/* Bolt-Style Sidebar */}
            <aside
              ref={fileListRef}
              className="w-80 max-w-[40%] min-w-[280px] border-r border-violet-500/20 bg-transparent overflow-hidden flex flex-col"
            >
              {viewMode === "changes" ? (
                <>
                  {filteredChanges && filteredChanges.length > 0 && (
                    <div className="px-3 py-2 border-b border-violet-500/20 bg-black">
                      <div className="text-[10px] text-foreground-secondary">
                        Use ↑↓ to navigate
                      </div>
                    </div>
                  )}
                  <div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
                    <div className="p-1.5">
                      <FileTree
                        changes={(filteredChanges || []) as GitChange[]}
                        selected={selected?.path ?? null}
                        onSelect={(path, status) => setSelected({ path, status })}
                        className="bolt-file-tree"
                      />
                    </div>
                  </div>
                </>
              ) : (
                <>
                  {/* All Files Mode */}
                  <div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
                    {loadingAllFiles ? (
                      <div className="flex items-center justify-center h-32">
                        <RefreshCw className="w-5 h-5 animate-spin text-text-secondary" />
                      </div>
                    ) : fileTree.length === 0 ? (
                      <div className="flex flex-col items-center justify-center h-32 text-text-secondary p-4">
                        <Folder className="w-8 h-8 mb-2 opacity-50" />
                        <p className="text-xs text-center">No files found</p>
                      </div>
                    ) : (
                      <div className="p-1.5">
                        {fileTree.map(node => renderFileNode(node, 0))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </aside>

            {/* File Viewer */}
            <section className="flex-1 overflow-hidden bg-black flex flex-col">
              {(() => {
                // Streaming mode - show streaming content
                if (showStreamingMode && isStreaming) {
                  return (
                    <StreamingFileViewer
                      path="streaming-content.md"
                      content={latestStreamingContent}
                      isStreaming={isStreaming}
                    />
                  );
                }
                
                // All Files mode - show full file content
                if (viewMode === "all" && selected) {
                  const fileName = selected.path.split('/').pop() || selected.path;
                  const language = selected.path.split('.').pop()?.toLowerCase() || 'plaintext';
                  
                  return (
                    <div className="flex flex-col h-full">
                      {/* File viewer header */}
                      <div className="flex items-center justify-between px-4 py-2 border-b border-violet-500/20 bg-black">
                        <div className="flex items-center gap-2">
                          <Eye className="w-3.5 h-3.5 text-brand-500" />
                          <span className="text-xs font-medium text-foreground">{fileName}</span>
                          <Badge variant="outline" className="text-[10px]">{language}</Badge>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleCopyFile}
                            className="h-6 px-2 text-[10px]"
                          >
                            <Copy className="w-3 h-3 mr-1" />
                            Copy
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleDownloadFile}
                            className="h-6 px-2 text-[10px]"
                          >
                            <Download className="w-3 h-3 mr-1" />
                            Download
                          </Button>
                        </div>
                      </div>
                      
                      {/* File content */}
                      <div className="flex-1 overflow-hidden">
                        {loadingFileContent ? (
                          <div className="flex items-center justify-center h-full">
                            <RefreshCw className="w-5 h-5 animate-spin text-text-secondary" />
                          </div>
                        ) : (
                          <LazyMonaco
                            value={selectedFileContent}
                            onChange={() => {}}
                            language={language}
                            height="100%"
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
                          />
                        )}
                      </div>
                    </div>
                  );
                }
                
                // Git diff mode - show selected file
                if (viewMode === "changes" && selected) {
                  return (
                    <FileDiffViewer
                      path={selected.path}
                      type={(selected.status as GitChangeStatus) ?? "M"}
                    />
                  );
                }
                
                // Empty state
                return (
                  <div className="h-full w-full flex flex-col items-center justify-center text-foreground-secondary">
                    {viewMode === "all" ? (
                      <>
                        <Folder className="w-12 h-12 mb-4 opacity-50" />
                        <p className="text-sm">Select a file to view its content</p>
                      </>
                    ) : (
                      <>
                        <Files className="w-12 h-12 mb-4 opacity-50" />
                        <p className="text-sm">
                          {showStreamingMode && isStreaming
                            ? "Streaming content will appear here..."
                            : t(I18nKey.DIFF_VIEWER$NO_CHANGES, {
                                defaultValue: "Select a file to view changes",
                              })}
                        </p>
                      </>
                    )}
                  </div>
                );
              })()}
            </section>
          </div>
        </>
      )}
    </main>
  );
}

export default GitChanges;
