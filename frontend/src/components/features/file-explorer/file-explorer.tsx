import React, { useState, useEffect, useCallback } from "react";
import {
  Folder,
  FolderOpen,
  File,
  MoreHorizontal,
  Trash2,
  Edit3,
  Download,
  Eye,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  Search,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "#/components/ui/button";
import { Input } from "#/components/ui/input";
import { Badge } from "#/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "#/components/ui/dropdown-menu";
import { cn } from "#/utils/utils";
import Forge from "#/api/forge";
import { FileIcon } from "#/components/ui/file-icon";
import { logger } from "#/utils/logger";

export interface FileNode {
  name: string;
  path: string;
  type: "file" | "folder";
  size?: number;
  modified?: string;
  status?: "new" | "modified" | "deleted" | "unchanged";
  children?: FileNode[];
  isExpanded?: boolean;
}

interface FileExplorerProps {
  conversationId: string;
  onFileSelect?: (filePath: string) => void;
  onFileOpen?: (filePath: string) => void;
  onFileDelete?: (filePath: string) => void;
  // onFileRename is reserved for future use
  // eslint-disable-next-line react/no-unused-prop-types
  onFileRename?: (oldPath: string, newPath: string) => void;
  className?: string;
  showActions?: boolean;
  showStatus?: boolean;
  showSearch?: boolean;
}

// Removed custom getFileIcon - now using FileIcon component from ui/file-icon.tsx

// Helper functions
const getStatusColor = (status?: string) => {
  switch (status) {
    case "new":
      return "bg-[var(--text-success)]/10 text-[var(--text-success)] border-[var(--text-success)]/30";
    case "modified":
      return "bg-[var(--border-accent)]/10 text-[var(--border-accent)] border-[var(--border-accent)]/30";
    case "deleted":
      return "bg-[var(--text-danger)]/10 text-[var(--text-danger)] border-[var(--text-danger)]/30";
    default:
      return "bg-[var(--text-tertiary)]/10 text-[var(--text-tertiary)] border-[var(--text-tertiary)]/30";
  }
};

const buildFileTree = (files: string[]): FileNode[] => {
  const tree: FileNode[] = [];
  const nodeMap = new Map<string, FileNode>();

  // Sort files to ensure consistent ordering
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
          node.isExpanded = false;
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

function filterNodeBySearch(
  node: FileNode,
  searchTerm: string,
): FileNode | null {
  const matchesSearch = node.name
    .toLowerCase()
    .includes(searchTerm.toLowerCase());

  if (node.type === "file") {
    return matchesSearch ? node : null;
  }

  const filteredChildren =
    node.children
      ?.map((child) => filterNodeBySearch(child, searchTerm))
      .filter((child): child is FileNode => child !== null) ?? [];

  if (matchesSearch || filteredChildren.length > 0) {
    return {
      ...node,
      children: filteredChildren,
      isExpanded: true,
    };
  }

  return null;
}

// Leaf components
function NodeIndicator({
  node,
  isExpanded,
}: {
  node: FileNode;
  isExpanded: boolean;
}) {
  if (node.type !== "folder") {
    return <div className="w-4 h-4" />;
  }

  return (
    <div className="w-4 h-4 flex items-center justify-center">
      {isExpanded ? (
        <ChevronDown className="w-3 h-3 text-[var(--text-tertiary)]" />
      ) : (
        <ChevronRight className="w-3 h-3 text-[var(--text-tertiary)]" />
      )}
    </div>
  );
}

function NodeIcon({
  node,
  isExpanded,
}: {
  node: FileNode;
  isExpanded: boolean;
}) {
  if (node.type === "folder") {
    return (
      <div className="flex-shrink-0">
        {isExpanded ? (
          <FolderOpen className="w-4 h-4 text-[var(--text-success)]" />
        ) : (
          <Folder className="w-4 h-4 text-[var(--text-success)]" />
        )}
      </div>
    );
  }

  return (
    <div className="flex-shrink-0">
      <FileIcon
        filename={node.name}
        size={16}
        className="transition-transform duration-200 group-hover:scale-110"
      />
    </div>
  );
}

function NodeLabel({
  node,
  isSelected,
}: {
  node: FileNode;
  isSelected: boolean;
}) {
  return (
    <span
      className={cn(
        "flex-1 truncate",
        isSelected
          ? "text-[var(--text-primary)] font-medium"
          : "text-[var(--text-primary)]",
      )}
    >
      {node.name}
    </span>
  );
}

function NodeStatusBadge({
  node,
  showStatus,
}: {
  node: FileNode;
  showStatus: boolean;
}) {
  if (!showStatus || !node.status || node.status === "unchanged") {
    return null;
  }

  let label = "?";
  if (node.status === "new") {
    label = "N";
  } else if (node.status === "modified") {
    label = "M";
  } else if (node.status === "deleted") {
    label = "D";
  }

  return (
    <Badge
      variant="outline"
      className={cn("text-xs px-1.5 py-0.5", getStatusColor(node.status))}
    >
      {label}
    </Badge>
  );
}

function NodeActions({
  node,
  showActions,
  onAction,
}: {
  node: FileNode;
  showActions: boolean;
  onAction: (
    action: "open" | "rename" | "delete" | "download",
    path: string,
  ) => void;
}) {
  const { t } = useTranslation();

  if (!showActions) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="opacity-0 group-hover:opacity-100 h-6 w-6 p-0 transition-opacity"
          onClick={(event) => event.stopPropagation()}
        >
          <MoreHorizontal className="w-3 h-3" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => onAction("open", node.path)}>
          <Eye className="w-4 h-4 mr-2" />
          {t("fileExplorer.open", "Open")}
        </DropdownMenuItem>
        {node.type === "file" && (
          <>
            <DropdownMenuItem onClick={() => onAction("download", node.path)}>
              <Download className="w-4 h-4 mr-2" />
              {t("fileExplorer.download", "Download")}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onAction("rename", node.path)}>
              <Edit3 className="w-4 h-4 mr-2" />
              {t("fileExplorer.rename", "Rename")}
            </DropdownMenuItem>
          </>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => onAction("delete", node.path)}
          className="text-red-500"
        >
          <Trash2 className="w-4 h-4 mr-2" />
          {t("fileExplorer.delete", "Delete")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Component that uses leaf components
function renderFileNode({
  node,
  depth,
  expandedFolders,
  selectedFile,
  toggleFolder,
  onSelect,
  showStatus,
  showActions,
  handleFileAction,
  renderChild,
}: {
  node: FileNode;
  depth: number;
  expandedFolders: Set<string>;
  selectedFile: string | null;
  toggleFolder: (path: string) => void;
  onSelect: (path: string) => void;
  showStatus: boolean;
  showActions: boolean;
  handleFileAction: (
    action: "open" | "rename" | "delete" | "download",
    path: string,
  ) => void;
  renderChild: (node: FileNode, depth: number) => React.ReactNode;
}) {
  const isExpanded = expandedFolders.has(node.path);
  const isSelected = selectedFile === node.path;

  return (
    <div key={node.path}>
      <div
        className={cn(
          "flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer group transition-all duration-150",
          "hover:bg-[var(--bg-tertiary)]",
          isSelected &&
            "bg-[var(--bg-elevated)] border-l-2 border-[var(--border-accent)]",
          "text-sm",
        )}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
        onClick={() => {
          if (node.type === "folder") {
            toggleFolder(node.path);
          } else {
            onSelect(node.path);
          }
        }}
      >
        <NodeIndicator node={node} isExpanded={isExpanded} />
        <NodeIcon node={node} isExpanded={isExpanded} />
        <NodeLabel node={node} isSelected={isSelected} />
        <NodeStatusBadge node={node} showStatus={showStatus} />
        <NodeActions
          node={node}
          showActions={showActions}
          onAction={handleFileAction}
        />
      </div>

      {node.type === "folder" && isExpanded && node.children && (
        <div>{node.children.map((child) => renderChild(child, depth + 1))}</div>
      )}
    </div>
  );
}

// Main component
export function FileExplorer({
  conversationId,
  onFileSelect,
  onFileOpen,
  onFileDelete,
  className,
  showActions = true,
  showStatus = true,
  showSearch = true,
}: FileExplorerProps) {
  const { t } = useTranslation();
  const [files, setFiles] = useState<string[]>([]);
  const [fileTree, setFileTree] = useState<FileNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(
    new Set(),
  );
  const [isClient, setIsClient] = useState(false);

  // Prevent hydration issues
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Load files from API
  const loadFiles = useCallback(async () => {
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
    } catch (error) {
      logger.error("Failed to load files:", error);
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  // Load files on mount and when conversation changes
  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  // Toggle folder expansion
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

  // Handle file selection
  const handleFileSelect = (filePath: string) => {
    setSelectedFile(filePath);
    onFileSelect?.(filePath);
  };

  // Handle file actions
  const handleFileAction = (action: string, filePath: string) => {
    switch (action) {
      case "open":
        onFileOpen?.(filePath);
        break;
      case "delete":
        onFileDelete?.(filePath);
        break;
      case "rename":
        // TODO: Implement rename functionality
        break;
      case "download":
        // TODO: Implement download functionality
        break;
      default:
        // Unknown action, do nothing
        break;
    }
  };

  // Filter files based on search term
  const filteredTree = React.useMemo(() => {
    if (!searchTerm) return fileTree;

    return fileTree
      .map((node) => filterNodeBySearch(node, searchTerm))
      .filter((node): node is FileNode => node !== null);
  }, [fileTree, searchTerm]);

  // Render file/folder node
  const renderNode = React.useCallback(
    (node: FileNode, depth = 0): React.JSX.Element | null =>
      renderFileNode({
        node,
        depth,
        expandedFolders,
        selectedFile,
        toggleFolder,
        onSelect: handleFileSelect,
        showStatus,
        showActions,
        handleFileAction,
        renderChild: (child, childDepth): React.JSX.Element | null =>
          renderNode(child, childDepth),
      }),
    [
      expandedFolders,
      selectedFile,
      toggleFolder,
      handleFileSelect,
      showStatus,
      showActions,
      handleFileAction,
    ],
  );

  // Don't render on server side to prevent hydration issues
  if (!isClient) {
    return (
      <div
        className={cn(
          "flex flex-col h-full bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl overflow-hidden",
          className,
        )}
      >
        <div
          className="flex items-center justify-center h-32"
          data-testid="file-explorer-loading"
        >
          <div className="text-[var(--text-tertiary)] italic">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col h-full bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-xl overflow-hidden shadow-sm",
        className,
      )}
    >
      {/* Header - Modern Slate themed */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-[var(--border-primary)] bg-[var(--bg-secondary)]">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            {t("fileExplorer.files", "Files")}
          </h3>
          <Badge
            variant="secondary"
            className="text-[10px] bg-[var(--border-accent)]/10 text-[var(--text-accent)] border-[var(--border-accent)]/20 px-1.5 h-4"
          >
            {files.length}
          </Badge>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={loadFiles}
            disabled={loading}
            className="h-7 w-7 p-0 hover:bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
          >
            <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} />
          </Button>
        </div>
      </div>

      {/* Search - Modern Slate themed */}
      {showSearch && (
        <div className="px-3 py-2 border-b border-[var(--border-primary)] bg-[var(--bg-primary)]">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-tertiary)]" />
            <Input
              placeholder="Search files..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 h-8 text-xs bg-[var(--bg-input)] border-[var(--border-primary)] text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:border-[var(--border-accent)] focus:ring-1 focus:ring-[var(--border-accent)]/20 rounded-lg"
            />
          </div>
        </div>
      )}

      {/* File Tree */}
      <div className="flex-1 overflow-y-auto p-2">
        {loading && (
          <div
            className="flex items-center justify-center h-32"
            data-testid="file-explorer-loading"
          >
            <RefreshCw className="w-5 h-5 animate-spin text-[var(--text-tertiary)]" />
          </div>
        )}
        {!loading && filteredTree.length === 0 && (
          <div className="flex flex-col items-center justify-center h-32 text-[var(--text-tertiary)]">
            <File className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">
              {t("fileExplorer.noFilesFound", "No files found")}
            </p>
            {searchTerm && (
              <p className="text-xs mt-1">
                {t(
                  "fileExplorer.tryAdjustingSearch",
                  "Try adjusting your search",
                )}
              </p>
            )}
          </div>
        )}
        {!loading && filteredTree.length > 0 && (
          <div className="space-y-1">
            {filteredTree.map((node) => renderNode(node))}
          </div>
        )}
      </div>
    </div>
  );
}
