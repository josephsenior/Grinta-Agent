import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { Files, Search, RefreshCw, Zap, Folder, Eye, Download, Copy } from "lucide-react";
import { FileDiffViewer } from "#/components/features/diff-viewer/file-diff-viewer";
import { StreamingFileViewer } from "#/components/features/diff-viewer/streaming-file-viewer";
import FileTree, {
  type GitChange,
} from "#/components/features/diff-viewer/file-tree";
import type { GitChangeStatus } from "#/api/forge.types";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";
import { useGetGitChanges } from "#/hooks/query/use-get-git-changes";
import {
  useStreamingChunks,
  useLatestStreamingContent,
} from "#/hooks/use-ws-events";
import { I18nKey } from "#/i18n/declaration";
import { useRuntimeIsReady } from "#/hooks/use-runtime-is-ready";
import { useConversationId } from "#/hooks/use-conversation-id";
import Forge from "#/api/forge";
import { LazyMonaco } from "#/components/shared/lazy-monaco";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";
import toast from "#/utils/toast";

const GIT_REPO_ERROR_PATTERN = /not a git repository/i;

type ViewMode = "changes" | "all";

interface FileNode {
  name: string;
  path: string;
  type: "file" | "folder";
  children?: FileNode[];
  status?: "new" | "modified" | "deleted" | "unchanged";
}

interface FileSelection {
  path: string;
  status?: string;
}

interface GitChangesHeaderProps {
  viewMode: ViewMode;
  onChangeViewMode: (mode: ViewMode) => void;
  filteredChangesCount: number;
  totalChangesCount: number;
  allFilesCount: number;
  searchQuery: string;
  onSearchChange: (value: string) => void;
  isStreaming: boolean;
  showStreamingMode: boolean;
  onToggleStreamingMode: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

interface ChangesSidebarProps {
  viewMode: ViewMode;
  filteredChanges: GitChange[];
  selected: FileSelection | null;
  onSelectChange: (path: string, status?: string) => void;
  fileTree: FileNode[];
  loadingAllFiles: boolean;
  expandedFolders: Set<string>;
  onToggleFolder: (folderPath: string) => void;
  onAllFileSelect: (path: string, status?: string) => void;
  fileListRef: React.RefObject<HTMLDivElement>;
}

interface GitChangesViewerProps {
  viewMode: ViewMode;
  selected: FileSelection | null;
  showStreamingMode: boolean;
  isStreaming: boolean;
  latestStreamingContent: string;
  loadingFileContent: boolean;
  selectedFileContent: string;
  onCopyFile: () => void;
  onDownloadFile: () => void;
}

interface GitChangesController {
  showEmptyState: boolean;
  statusMessage: string[] | null;
  headerProps: GitChangesHeaderProps;
  sidebarProps: ChangesSidebarProps;
  viewerProps: GitChangesViewerProps;
}

export default function GitChanges() {
  const { t } = useTranslation();
  const controller = useGitChangesController();

  if (controller.showEmptyState) {
    return (
      <StatusSection messages={controller.statusMessage} t={t} />
    );
  }

  return (
    <main className="h-full overflow-hidden flex flex-col bg-black">
      <GitChangesHeader t={t} {...controller.headerProps} />
      <div className="flex-1 flex gap-0 min-h-0 overflow-hidden">
        <ChangesSidebar t={t} {...controller.sidebarProps} />
        <GitChangesViewer t={t} {...controller.viewerProps} />
      </div>
    </main>
  );
}

function useGitChangesController(): GitChangesController {
  const { conversationId } = useConversationId();
  const runtimeIsActive = useRuntimeIsReady();
  const {
    data: gitChanges = [],
    isSuccess,
    isLoading: loadingGitChanges,
    error,
  } = useGetGitChanges();

  const streamingChunks = useStreamingChunks();
  const latestStreamingContent = useLatestStreamingContent();
  const isStreaming = streamingChunks.length > 0 &&
    streamingChunks[streamingChunks.length - 1]?.args.is_final === false;

  const [viewMode, setViewMode] = useState<ViewMode>("changes");
  const [allFiles, setAllFiles] = useState<string[]>([]);
  const [fileTree, setFileTree] = useState<FileNode[]>([]);
  const [loadingAllFiles, setLoadingAllFiles] = useState(false);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [selectedFileContent, setSelectedFileContent] = useState("");
  const [loadingFileContent, setLoadingFileContent] = useState(false);
  const [selected, setSelected] = useState<FileSelection | null>(null);
  const [showStreamingMode, setShowStreamingMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string[] | null>(null);

  const fileListRef = useRef<HTMLDivElement>(null);

  const filteredChanges = useMemo(() => {
    if (!searchQuery) {
      return gitChanges as GitChange[];
    }
    const lower = searchQuery.toLowerCase();
    return (gitChanges || []).filter((change) =>
      (change.path ?? "").toLowerCase().includes(lower),
    ) as GitChange[];
  }, [gitChanges, searchQuery]);

  useEffect(() => {
    setStatusMessage(
      determineStatusMessage({ runtimeIsActive, loadingGitChanges, error }),
    );
  }, [runtimeIsActive, loadingGitChanges, error]);

  useEffect(() => {
    if (isSuccess && gitChanges.length > 0 && !selected) {
      const first = gitChanges[0];
      setSelected({ path: first.path ?? "", status: first.status });
    }
  }, [gitChanges, isSuccess, selected]);

  const loadAllFiles = useCallback(async () => {
    if (!conversationId) return;
    setLoadingAllFiles(true);
    try {
      const response = await Forge.getFiles(conversationId);
      const normalized: string[] = (response || []).map((entry: any) =>
        typeof entry === "string" ? entry : entry?.path ?? "",
      );
      setAllFiles(normalized);
      setFileTree(buildFileTree(normalized));
    } catch (err) {
      console.error("Failed to load all files:", err);
      toast.error("load-files-error", "Failed to load workspace files");
    } finally {
      setLoadingAllFiles(false);
    }
  }, [conversationId]);

  useEffect(() => {
    if (viewMode === "all" && allFiles.length === 0) {
      loadAllFiles();
    }
  }, [viewMode, allFiles.length, loadAllFiles]);

  const loadFileContent = useCallback(
    async (filePath: string) => {
      if (!conversationId) return;
      setLoadingFileContent(true);
      try {
        const response = await Forge.getFile(conversationId, filePath);
        setSelectedFileContent(response || "");
      } catch (err) {
        console.error("Failed to load file content:", err);
        toast.error("load-content-error", "Failed to load file content");
        setSelectedFileContent("");
      } finally {
        setLoadingFileContent(false);
      }
    },
    [conversationId],
  );

  const toggleFolder = useCallback((folderPath: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderPath)) {
        next.delete(folderPath);
      } else {
        next.add(folderPath);
      }
      return next;
    });
  }, []);

  const handleAllFileSelect = useCallback(
    (path: string, status?: string) => {
      setSelected({ path, status });
      loadFileContent(path);
    },
    [loadFileContent],
  );

  const handleCopyFile = useCallback(() => {
    if (!selectedFileContent) return;
    navigator.clipboard
      .writeText(selectedFileContent)
      .then(() => {
        toast.success("copy-success", "File content copied to clipboard");
      })
      .catch((err) => {
        console.error("Failed to copy:", err);
        toast.error("copy-error", "Failed to copy to clipboard");
      });
  }, [selectedFileContent]);

  const handleDownloadFile = useCallback(() => {
    if (!selectedFileContent || !selected) return;
    const blob = new Blob([selectedFileContent], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = selected.path.split("/").pop() || "file";
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
    toast.success("download-success", `Downloaded ${selected.path}`);
  }, [selected, selectedFileContent]);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1000);
  }, []);

  useEffect(() => {
    if (viewMode !== "changes") {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (!filteredChanges || filteredChanges.length === 0) return;

      const currentIndex = filteredChanges.findIndex(
        (change) => change.path === selected?.path,
      );

      if (event.key === "ArrowDown") {
        event.preventDefault();
        const nextIndex = Math.min(currentIndex + 1, filteredChanges.length - 1);
        const next = filteredChanges[nextIndex];
        setSelected({ path: next.path ?? "", status: next.status });
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        const prevIndex = Math.max(currentIndex - 1, 0);
        const prev = filteredChanges[prevIndex];
        setSelected({ path: prev.path ?? "", status: prev.status });
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [filteredChanges, selected, viewMode]);

  const headerProps: GitChangesHeaderProps = {
    viewMode,
    onChangeViewMode: setViewMode,
    filteredChangesCount: filteredChanges.length,
    totalChangesCount: gitChanges.length,
    allFilesCount: allFiles.length,
    searchQuery,
    onSearchChange: setSearchQuery,
    isStreaming,
    showStreamingMode,
    onToggleStreamingMode: () => setShowStreamingMode((prev) => !prev),
    onRefresh: handleRefresh,
    isRefreshing,
  };

  const sidebarProps: ChangesSidebarProps = {
    viewMode,
    filteredChanges,
    selected,
    onSelectChange: (path, status) => setSelected({ path, status }),
    fileTree,
    loadingAllFiles,
    expandedFolders,
    onToggleFolder: toggleFolder,
    onAllFileSelect: handleAllFileSelect,
    fileListRef,
  };

  const viewerProps: GitChangesViewerProps = {
    viewMode,
    selected,
    showStreamingMode,
    isStreaming,
    latestStreamingContent,
    loadingFileContent,
    selectedFileContent,
    onCopyFile: handleCopyFile,
    onDownloadFile: handleDownloadFile,
  };

  const showEmptyState = !isSuccess || gitChanges.length === 0;

  return {
    showEmptyState,
    statusMessage,
    headerProps,
    sidebarProps,
    viewerProps,
  };
}

const HeaderTitleSection = ({
  viewMode,
  changesLabel,
  allFilesLabel,
  filteredChangesCount,
  allFilesCount,
  searchQuery,
  totalChangesCount,
  t,
}: {
  viewMode: ViewMode;
  changesLabel: string;
  allFilesLabel: string;
  filteredChangesCount: number;
  allFilesCount: number;
  searchQuery: string;
  totalChangesCount: number;
  t: TFunction;
}) => {
  const isChangesView = viewMode === "changes";
  const TitleIcon = isChangesView ? Files : Folder;
  const title = isChangesView ? changesLabel : allFilesLabel;
  const count = isChangesView ? filteredChangesCount : allFilesCount;

  return (
    <div className="flex items-center gap-2.5">
      <TitleIcon className="w-4 h-4 text-brand-500" />
      <h2 className="text-xs font-medium text-foreground">{title}</h2>
      <span className="px-1.5 py-0.5 text-[10px] font-medium bg-black text-foreground rounded">
        {count}
      </span>
      {isChangesView && searchQuery && (
        <span className="text-[10px] text-foreground-secondary">
          ({t("WORKSPACE$FILTERED_FROM", { defaultValue: "filtered from" })} {totalChangesCount})
        </span>
      )}
    </div>
  );
};

const GitChangesViewModeToggle = ({
  viewMode,
  onChangeViewMode,
  changesLabel,
  allFilesLabel,
  t,
}: {
  viewMode: ViewMode;
  onChangeViewMode: (mode: ViewMode) => void;
  changesLabel: string;
  allFilesLabel: string;
  t: TFunction;
}) => (
  <div className="flex items-center border border-violet-500/20 rounded-md p-0.5 mr-1">
    <button
      type="button"
      onClick={() => onChangeViewMode("changes")}
      className={cn(
        "px-2 py-1 text-[10px] font-medium rounded transition-all duration-150",
        viewMode === "changes"
          ? "bg-brand-500 text-white"
          : "text-foreground-secondary hover:text-foreground hover:bg-black",
      )}
      title={t("WORKSPACE$SHOW_CHANGED_FILES", { defaultValue: "Show only changed files" })}
    >
      <Files className="w-3 h-3 inline mr-1" />
      {changesLabel}
    </button>
    <button
      type="button"
      onClick={() => onChangeViewMode("all")}
      className={cn(
        "px-2 py-1 text-[10px] font-medium rounded transition-all duration-150",
        viewMode === "all"
          ? "bg-brand-500 text-white"
          : "text-foreground-secondary hover:text-foreground hover:bg-black",
      )}
      title={t("WORKSPACE$SHOW_ALL_FILES", { defaultValue: "Show all workspace files" })}
    >
      <Folder className="w-3 h-3 inline mr-1" />
      {allFilesLabel}
    </button>
  </div>
);

const StreamingModeToggle = ({
  isStreaming,
  showStreamingMode,
  onToggleStreamingMode,
  t,
}: {
  isStreaming: boolean;
  showStreamingMode: boolean;
  onToggleStreamingMode: () => void;
  t: TFunction;
}) => {
  if (!isStreaming) {
    return null;
  }

  return (
    <button
      type="button"
      onClick={onToggleStreamingMode}
      className={cn(
        "p-1 rounded transition-all duration-150",
        showStreamingMode
          ? "text-brand-500 bg-brand-500/10"
          : "text-foreground-secondary hover:text-brand-500 hover:bg-black",
      )}
      aria-label={t("WORKSPACE$TOGGLE_STREAMING", { defaultValue: "Toggle streaming mode" })}
      title={
        showStreamingMode
          ? t("WORKSPACE$SHOW_GIT_CHANGES", { defaultValue: "Show git changes" })
          : t("WORKSPACE$SHOW_STREAMING_CONTENT", { defaultValue: "Show streaming content" })
      }
    >
      <Zap className={cn("w-3.5 h-3.5", isStreaming && "animate-pulse")} />
    </button>
  );
};

const RefreshButton = ({
  onRefresh,
  isRefreshing,
  t,
}: {
  onRefresh: () => void;
  isRefreshing: boolean;
  t: TFunction;
}) => (
  <button
    type="button"
    onClick={onRefresh}
    className="p-1 rounded text-foreground-secondary hover:text-brand-500 hover:bg-black transition-all duration-150"
    aria-label={t("WORKSPACE$REFRESH_CHANGES", { defaultValue: "Refresh changes" })}
  >
    <RefreshCw className={cn("w-3.5 h-3.5", isRefreshing && "animate-spin")} />
  </button>
);

const HeaderSearchInput = ({
  searchQuery,
  onSearchChange,
  t,
}: {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  t: TFunction;
}) => (
  <div className="px-4 pb-2.5">
    <div className="relative">
      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-foreground-secondary" />
      <input
        type="text"
        placeholder={t("WORKSPACE$SEARCH_FILES", { defaultValue: "Search files..." })}
        value={searchQuery}
        onChange={event => onSearchChange(event.target.value)}
        className="w-full pl-8 pr-3 py-1.5 text-xs bg-black border border-violet-500/20 rounded text-foreground placeholder:text-foreground-secondary/50 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition-all duration-150"
      />
    </div>
  </div>
);

function GitChangesHeader({
  t,
  viewMode,
  onChangeViewMode,
  filteredChangesCount,
  totalChangesCount,
  allFilesCount,
  searchQuery,
  onSearchChange,
  isStreaming,
  showStreamingMode,
  onToggleStreamingMode,
  onRefresh,
  isRefreshing,
}: GitChangesHeaderProps & { t: TFunction }) {
  const changesLabel = t("WORKSPACE$CHANGES_TAB_LABEL", { defaultValue: "Changes" });
  const allFilesLabel = t("WORKSPACE$ALL_FILES_LABEL", { defaultValue: "All Files" });

  return (
    <div className="flex-none border-b border-violet-500/20 bg-black backdrop-blur-sm">
      <div className="flex items-center justify-between px-4 py-2.5">
        <HeaderTitleSection
          viewMode={viewMode}
          changesLabel={changesLabel}
          allFilesLabel={allFilesLabel}
          filteredChangesCount={filteredChangesCount}
          allFilesCount={allFilesCount}
          searchQuery={searchQuery}
          totalChangesCount={totalChangesCount}
          t={t}
        />
        <div className="flex items-center gap-1">
          <GitChangesViewModeToggle
            viewMode={viewMode}
            onChangeViewMode={onChangeViewMode}
            changesLabel={changesLabel}
            allFilesLabel={allFilesLabel}
            t={t}
          />
          <StreamingModeToggle
            isStreaming={isStreaming}
            showStreamingMode={showStreamingMode}
            onToggleStreamingMode={onToggleStreamingMode}
            t={t}
          />
          <RefreshButton onRefresh={onRefresh} isRefreshing={isRefreshing} t={t} />
        </div>
      </div>
      <HeaderSearchInput searchQuery={searchQuery} onSearchChange={onSearchChange} t={t} />
    </div>
  );
}

function ChangesSidebar({
  t,
  viewMode,
  filteredChanges,
  selected,
  onSelectChange,
  fileTree,
  loadingAllFiles,
  expandedFolders,
  onToggleFolder,
  onAllFileSelect,
  fileListRef,
}: ChangesSidebarProps & { t: TFunction }) {
  return (
    <aside
      ref={fileListRef}
      className="w-80 max-w-[40%] min-w-[280px] border-r border-violet-500/20 bg-transparent overflow-hidden flex flex-col"
    >
      {viewMode === "changes" ? (
        <ChangesList
          t={t}
          filteredChanges={filteredChanges}
          selected={selected}
          onSelectChange={onSelectChange}
        />
      ) : (
        <AllFilesList
          fileTree={fileTree}
          loadingAllFiles={loadingAllFiles}
          selectedPath={selected?.path ?? null}
          expandedFolders={expandedFolders}
          onToggleFolder={onToggleFolder}
          onSelectFile={onAllFileSelect}
        />
      )}
    </aside>
  );
}

function ChangesList({
  t,
  filteredChanges,
  selected,
  onSelectChange,
}: {
  t: TFunction;
  filteredChanges: GitChange[];
  selected: FileSelection | null;
  onSelectChange: (path: string, status?: string) => void;
}) {
  return (
    <>
      {filteredChanges.length > 0 && (
        <div className="px-3 py-2 border-b border-violet-500/20 bg-black">
          <div className="text-[10px] text-foreground-secondary">
            {t("WORKSPACE$USE_ARROWS_HINT", { defaultValue: "Use ↑↓ to navigate" })}
          </div>
        </div>
      )}
      <div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
        <div className="p-1.5">
          <FileTree
            changes={(filteredChanges || []) as GitChange[]}
            selected={selected?.path ?? null}
            onSelect={(path, status) => onSelectChange(path, status)}
            className="bolt-file-tree"
          />
        </div>
      </div>
    </>
  );
}

function AllFilesList({
  fileTree,
  loadingAllFiles,
  selectedPath,
  expandedFolders,
  onToggleFolder,
  onSelectFile,
}: {
  fileTree: FileNode[];
  loadingAllFiles: boolean;
  selectedPath: string | null;
  expandedFolders: Set<string>;
  onToggleFolder: (folderPath: string) => void;
  onSelectFile: (path: string, status?: string) => void;
}) {
  if (loadingAllFiles) {
    return (
      <div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
        <div className="flex items-center justify-center h-32">
          <RefreshCw className="w-5 h-5 animate-spin text-text-secondary" />
        </div>
      </div>
    );
  }

  if (fileTree.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
        <div className="flex flex-col items-center justify-center h-32 text-text-secondary p-4">
          <Folder className="w-8 h-8 mb-2 opacity-50" />
          <p className="text-xs text-center">No файles found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
      <div className="p-1.5">
        <AllFilesTree
          nodes={fileTree}
          depth={0}
          expandedFolders={expandedFolders}
          onToggleFolder={onToggleFolder}
          onSelectFile={onSelectFile}
          selectedPath={selectedPath}
        />
      </div>
    </div>
  );
}

function AllFilesTree({
  nodes,
  depth,
  expandedFolders,
  onToggleFolder,
  onSelectFile,
  selectedPath,
}: {
  nodes: FileNode[];
  depth: number;
  expandedFolders: Set<string>;
  onToggleFolder: (folderPath: string) => void;
  onSelectFile: (path: string, status?: string) => void;
  selectedPath: string | null;
}) {
  return (
    <>
      {nodes.map((node) => (
        <AllFilesTreeNode
          key={node.path}
          node={node}
          depth={depth}
          expandedFolders={expandedFolders}
          onToggleFolder={onToggleFolder}
          onSelectFile={onSelectFile}
          selectedPath={selectedPath}
        />
      ))}
    </>
  );
}

function AllFilesTreeNode({
  node,
  depth,
  expandedFolders,
  onToggleFolder,
  onSelectFile,
  selectedPath,
}: {
  node: FileNode;
  depth: number;
  expandedFolders: Set<string>;
  onToggleFolder: (folderPath: string) => void;
  onSelectFile: (path: string, status?: string) => void;
  selectedPath: string | null;
}) {
  const isExpanded = expandedFolders.has(node.path);
  const isSelected = selectedPath === node.path;
  const paddingLeft = 8 + depth * 12;

  return (
    <div key={node.path}>
      <button
        type="button"
        className={cn(
          "flex items-center gap-2 w-full px-2 py-1.5 rounded text-xs transition-all duration-150",
          "hover:bg-black",
          isSelected && "bg-brand-500/10 border-l-2 border-brand-500",
        )}
        style={{ paddingLeft: `${paddingLeft}px` }}
        onClick={() => {
          if (node.type === "folder") {
            onToggleFolder(node.path);
          } else {
            onSelectFile(node.path, node.status);
          }
        }}
      >
        <span className="flex-shrink-0 text-sm">
          {node.type === "folder"
            ? isExpanded
              ? "📂"
              : "📁"
            : getFileIcon(node.name)}
        </span>
        <span
          className={cn(
            "flex-1 truncate text-left",
            isSelected ? "text-brand-500 font-medium" : "text-foreground-secondary",
          )}
        >
          {node.name}
        </span>
      </button>
      {node.type === "folder" && isExpanded && node.children && (
        <AllFilesTree
          nodes={node.children}
          depth={depth + 1}
          expandedFolders={expandedFolders}
          onToggleFolder={onToggleFolder}
          onSelectFile={onSelectFile}
          selectedPath={selectedPath}
        />
      )}
    </div>
  );
}

type GitChangesViewerState = "streaming" | "allSelected" | "changesSelected" | "empty";

const getGitChangesViewerState = ({
  showStreamingMode,
  isStreaming,
  viewMode,
  selected,
}: {
  showStreamingMode: boolean;
  isStreaming: boolean;
  viewMode: ViewMode;
  selected: FileSelection | null;
}): GitChangesViewerState => {
  if (showStreamingMode && isStreaming) {
    return "streaming";
  }

  if (viewMode === "all" && selected) {
    return "allSelected";
  }

  if (viewMode === "changes" && selected) {
    return "changesSelected";
  }

  return "empty";
};

const renderStreamingViewer = ({
  latestStreamingContent,
  isStreaming,
}: {
  latestStreamingContent: string;
  isStreaming: boolean;
}) => (
  <section className="flex-1 overflow-hidden bg-black flex flex-col">
    <StreamingFileViewer
      path="streaming-content.md"
      content={latestStreamingContent}
      isStreaming={isStreaming}
    />
  </section>
);

const getFileName = (path: string) => path.split("/").pop() || path;
const getLanguageFromPath = (path: string) => path.split(".").pop()?.toLowerCase() || "plaintext";

const renderAllFilesViewer = ({
  selected,
  loadingFileContent,
  selectedFileContent,
  onCopyFile,
  onDownloadFile,
  t,
}: {
  selected: FileSelection;
  loadingFileContent: boolean;
  selectedFileContent: string;
  onCopyFile: () => void;
  onDownloadFile: () => void;
  t: TFunction;
}) => {
  const fileName = getFileName(selected.path);
  const language = getLanguageFromPath(selected.path);

  return (
    <section className="flex-1 overflow-hidden bg-black flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-violet-500/20 bg-black">
        <div className="flex items-center gap-2">
          <Eye className="w-3.5 h-3.5 text-brand-500" />
          <span className="text-xs font-medium text-foreground">{fileName}</span>
          <Badge variant="outline" className="text-[10px]">
            {language}
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={onCopyFile} className="h-6 px-2 text-[10px]">
            <Copy className="w-3 h-3 mr-1" />
            {t("WORKSPACE$COPY", { defaultValue: "Copy" })}
          </Button>
          <Button variant="ghost" size="sm" onClick={onDownloadFile} className="h-6 px-2 text-[10px]">
            <Download className="w-3 h-3 mr-1" />
            {t("WORKSPACE$DOWNLOAD", { defaultValue: "Download" })}
          </Button>
        </div>
      </div>
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
    </section>
  );
};

const renderChangesViewer = (selected: FileSelection) => (
  <section className="flex-1 overflow-hidden bg-black flex flex-col">
    <FileDiffViewer path={selected.path} type={(selected.status as GitChangeStatus) ?? "M"} />
  </section>
);

const renderEmptyViewer = ({
  viewMode,
  showStreamingMode,
  isStreaming,
  t,
}: {
  viewMode: ViewMode;
  showStreamingMode: boolean;
  isStreaming: boolean;
  t: TFunction;
}) => (
  <section className="flex-1 overflow-hidden bg-black flex flex-col">
    <div className="h-full w-full flex flex-col items-center justify-center text-foreground-secondary">
      {viewMode === "all" ? (
        <>
          <Folder className="w-12 h-12 mb-4 opacity-50" />
          <p className="text-sm">
            {t("WORKSPACE$SELECT_FILE_TO_VIEW", { defaultValue: "Select a file to view its content" })}
          </p>
        </>
      ) : (
        <>
          <Files className="w-12 h-12 mb-4 opacity-50" />
          <p className="text-sm">
            {showStreamingMode && isStreaming
              ? t("WORKSPACE$STREAMING_CONTENT_WAIT", {
                  defaultValue: "Streaming content will appear here...",
                })
              : t(I18nKey.DIFF_VIEWER$NO_CHANGES, {
                  defaultValue: "Select a file to view changes",
                })}
          </p>
        </>
      )}
    </div>
  </section>
);

function GitChangesViewer({
  t,
  viewMode,
  selected,
  showStreamingMode,
  isStreaming,
  latestStreamingContent,
  loadingFileContent,
  selectedFileContent,
  onCopyFile,
  onDownloadFile,
}: GitChangesViewerProps & { t: TFunction }) {
  const viewerState = getGitChangesViewerState({ showStreamingMode, isStreaming, viewMode, selected });

  switch (viewerState) {
    case "streaming":
      return renderStreamingViewer({ latestStreamingContent, isStreaming });
    case "allSelected":
      return renderAllFilesViewer({
        selected: selected as FileSelection,
        loadingFileContent,
        selectedFileContent,
        onCopyFile,
        onDownloadFile,
        t,
      });
    case "changesSelected":
      return renderChangesViewer(selected as FileSelection);
    case "empty":
    default:
      return renderEmptyViewer({ viewMode, showStreamingMode, isStreaming, t });
  }
}

function StatusSection({
  messages,
  t,
}: {
  messages: string[] | null;
  t: TFunction;
}) {
  return (
    <main className="h-full overflow-hidden flex flex-col bg-black">
      <div className="relative flex h-full w-full items-center justify-center">
        <div className="flex flex-col items-center justify-center gap-4 text-center px-6">
          {messages && (
            <div className="w-full h-full flex flex-col items-center text-center justify-center text-2xl text-foreground-secondary">
              {messages.map((msg) => (
                <span key={msg} className="text-foreground-secondary text-base">
                  {t(msg, { defaultValue: msg })}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

function buildFileTree(files: string[]): FileNode[] {
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
          status: "unchanged",
        };

        if (!isLast) {
          node.children = [];
        }

        nodeMap.set(currentPath, node);

        if (parentPath) {
          const parent = nodeMap.get(parentPath);
          if (parent?.children) {
            parent.children.push(node);
          }
        } else {
          tree.push(node);
        }
      }
    }
  }

  return tree;
}

function getFileIcon(filename: string) {
  const ext = filename.split(".").pop()?.toLowerCase();
  return ext ? "📄" : "📄";
}

function determineStatusMessage({
  runtimeIsActive,
  loadingGitChanges,
  error,
}: {
  runtimeIsActive: boolean;
  loadingGitChanges: boolean;
  error: unknown;
}): string[] | null {
  if (!runtimeIsActive) {
    return [I18nKey.DIFF_VIEWER$WAITING_FOR_RUNTIME];
  }

  if (loadingGitChanges) {
    return [I18nKey.DIFF_VIEWER$LOADING];
  }

  if (!error) {
    return null;
  }

  const errorMessage = retrieveAxiosErrorMessage(error);

  if (errorMessage.includes("404") || errorMessage.includes("Not Found")) {
    return [I18nKey.DIFF_VIEWER$WAITING_FOR_RUNTIME];
  }

  if (GIT_REPO_ERROR_PATTERN.test(errorMessage)) {
    return [I18nKey.DIFF_VIEWER$NOT_A_GIT_REPO, I18nKey.DIFF_VIEWER$ASK_OH];
  }

  return [errorMessage];
}
