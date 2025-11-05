import React, { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { 
  Folder, 
  FolderOpen, 
  File,
  MoreHorizontal,
  Plus,
  Trash2,
  Edit3,
  Download,
  Eye,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  Search,
  Filter
} from "lucide-react";
import { Button } from "#/components/ui/button";
import { Input } from "#/components/ui/input";
import { Badge } from "#/components/ui/badge";
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from "#/components/ui/dropdown-menu";
import { cn } from "#/utils/utils";
import OpenHands from "#/api/open-hands";
import { FileIcon } from "#/components/ui/file-icon";

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
  onFileRename?: (oldPath: string, newPath: string) => void;
  className?: string;
  showActions?: boolean;
  showStatus?: boolean;
  showSearch?: boolean;
}

// Removed custom getFileIcon - now using FileIcon component from ui/file-icon.tsx

// Status color mapping
const getStatusColor = (status?: string) => {
  switch (status) {
    case 'new':
      return 'bg-green-500/10 text-green-500 border-green-500/30';
    case 'modified':
      return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/30';
    case 'deleted':
      return 'bg-red-500/10 text-red-500 border-red-500/30';
    default:
      return 'bg-gray-500/10 text-gray-500 border-gray-500/30';
  }
};

// Build tree structure from flat file list
const buildFileTree = (files: string[]): FileNode[] => {
  const tree: FileNode[] = [];
  const nodeMap = new Map<string, FileNode>();
  
  // Sort files to ensure consistent ordering
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

export function FileExplorer({
  conversationId,
  onFileSelect,
  onFileOpen,
  onFileDelete,
  onFileRename,
  className,
  showActions = true,
  showStatus = true,
  showSearch = true
}: FileExplorerProps) {
  const { t } = useTranslation();
  const [files, setFiles] = useState<string[]>([]);
  const [fileTree, setFileTree] = useState<FileNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
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
      const response = await OpenHands.getFiles(conversationId);
      setFiles(response);
      setFileTree(buildFileTree(response));
    } catch (error) {
      console.error('Failed to load files:', error);
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

  // Handle file selection
  const handleFileSelect = (filePath: string) => {
    setSelectedFile(filePath);
    onFileSelect?.(filePath);
  };

  // Handle file actions
  const handleFileAction = (action: string, filePath: string) => {
    switch (action) {
      case 'open':
        onFileOpen?.(filePath);
        break;
      case 'delete':
        onFileDelete?.(filePath);
        break;
      case 'rename':
        // TODO: Implement rename functionality
        break;
      case 'download':
        // TODO: Implement download functionality
        break;
    }
  };

  // Filter files based on search term
  const filteredTree = React.useMemo(() => {
    if (!searchTerm) return fileTree;
    
    const filterNode = (node: FileNode): FileNode | null => {
      const matchesSearch = node.name.toLowerCase().includes(searchTerm.toLowerCase());
      
      if (node.type === 'file') {
        return matchesSearch ? node : null;
      }
      
      // For folders, include if folder name matches or any child matches
      const filteredChildren = node.children
        ?.map(filterNode)
        .filter((child): child is FileNode => child !== null) || [];
      
      if (matchesSearch || filteredChildren.length > 0) {
        return {
          ...node,
          children: filteredChildren,
          isExpanded: true // Auto-expand filtered folders
        };
      }
      
      return null;
    };
    
    return fileTree.map(filterNode).filter((node): node is FileNode => node !== null);
  }, [fileTree, searchTerm]);

  // Render file/folder node
  const renderNode = (node: FileNode, depth = 0) => {
    const isExpanded = expandedFolders.has(node.path);
    const isSelected = selectedFile === node.path;
    
    return (
      <div key={node.path}>
        <div
          className={cn(
            "flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer group transition-all duration-200",
            "hover:bg-brand-500/5 hover:border-l-2 hover:border-brand-500/30",
            isSelected && "bg-brand-500/10 border-l-2 border-brand-500 shadow-sm shadow-brand-500/10",
            "text-sm"
          )}
          style={{ paddingLeft: `${8 + depth * 16}px` }}
          onClick={() => {
            if (node.type === 'folder') {
              toggleFolder(node.path);
            } else {
              handleFileSelect(node.path);
            }
          }}
        >
          {/* Expand/Collapse Icon */}
          {node.type === 'folder' && (
            <div className="w-4 h-4 flex items-center justify-center">
              {isExpanded ? (
                <ChevronDown className="w-3 h-3 text-text-secondary" />
              ) : (
                <ChevronRight className="w-3 h-3 text-text-secondary" />
              )}
            </div>
          )}
          
          {/* File/Folder Icon - Using FileIcon component for proper file-icons-js rendering */}
          <div className="flex-shrink-0">
            {node.type === 'folder' ? (
              isExpanded ? (
                <FolderOpen className="w-4 h-4 text-violet-500" />
              ) : (
                <Folder className="w-4 h-4 text-brand-400" />
              )
            ) : (
              <FileIcon 
                filename={node.name} 
                size={16}
                className="transition-transform duration-200 group-hover:scale-110"
              />
            )}
          </div>
          
          {/* File/Folder Name */}
          <span className={cn(
            "flex-1 truncate",
            isSelected ? "text-violet-500 font-medium" : "text-text-primary"
          )}>
            {node.name}
          </span>
          
          {/* Status Badge */}
          {showStatus && node.status && node.status !== 'unchanged' && (
            <Badge 
              variant="outline" 
              className={cn("text-xs px-1.5 py-0.5", getStatusColor(node.status))}
            >
              {node.status === 'new' ? 'N' : node.status === 'modified' ? 'M' : 'D'}
            </Badge>
          )}
          
          {/* Actions Menu */}
          {showActions && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="opacity-0 group-hover:opacity-100 h-6 w-6 p-0 transition-opacity"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreHorizontal className="w-3 h-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => handleFileAction('open', node.path)}>
                  <Eye className="w-4 h-4 mr-2" />
                  Open
                </DropdownMenuItem>
                {node.type === 'file' && (
                  <>
                    <DropdownMenuItem onClick={() => handleFileAction('download', node.path)}>
                      <Download className="w-4 h-4 mr-2" />
                      Download
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleFileAction('rename', node.path)}>
                      <Edit3 className="w-4 h-4 mr-2" />
                      Rename
                    </DropdownMenuItem>
                  </>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem 
                  onClick={() => handleFileAction('delete', node.path)}
                  className="text-red-500"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
        
        {/* Render Children */}
        {node.type === 'folder' && isExpanded && node.children && (
          <div>
            {node.children.map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  // Don't render on server side to prevent hydration issues
  if (!isClient) {
    return (
      <div className={cn("flex flex-col h-full bg-background-primary border border-border rounded-lg", className)}>
        <div className="flex items-center justify-center h-32">
          <div className="text-text-secondary">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full bg-black/95 backdrop-blur-xl border border-brand-500/10 rounded-lg shadow-lg", className)}>
      {/* Header - Violet themed */}
      <div className="flex items-center justify-between p-3 border-b border-brand-500/10 bg-brand-500/5">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-foreground">Files</h3>
          <Badge variant="secondary" className="text-xs bg-brand-500/20 text-brand-400 border-brand-500/30">
            {files.length} {files.length === 1 ? 'file' : 'files'}
          </Badge>
        </div>
        
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={loadFiles}
            disabled={loading}
            className="h-7 w-7 p-0"
          >
            <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} />
          </Button>
        </div>
      </div>
      
      {/* Search - Violet themed */}
      {showSearch && (
        <div className="p-3 border-b border-brand-500/10">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-violet-500/60" />
            <Input
              placeholder="Search files..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 h-8 text-sm bg-brand-500/5 border-brand-500/20 focus:border-brand-500/40 focus:ring-brand-500/20"
            />
          </div>
        </div>
      )}
      
      {/* File Tree */}
      <div className="flex-1 overflow-y-auto p-2">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <RefreshCw className="w-5 h-5 animate-spin text-text-secondary" />
          </div>
        ) : filteredTree.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-text-secondary">
            <File className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">No files found</p>
            {searchTerm && (
              <p className="text-xs mt-1">Try adjusting your search</p>
            )}
          </div>
        ) : (
          <div className="space-y-1">
            {filteredTree.map(node => renderNode(node))}
          </div>
        )}
      </div>
    </div>
  );
}
