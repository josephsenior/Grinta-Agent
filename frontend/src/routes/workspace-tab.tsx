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
  FolderPlus
} from "lucide-react";
import { useConversationId } from "#/hooks/use-conversation-id";
import Forge from "#/api/forge";
import { LazyMonaco } from "#/components/shared/lazy-monaco";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";
import { cn } from "#/utils/utils";
import toast from "#/utils/toast";

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
  const ext = filename.split('.').pop()?.toLowerCase();
  
  // Code files
  if (['js', 'jsx', 'ts', 'tsx', 'py', 'java', 'cpp', 'c', 'go', 'rs', 'php', 'rb'].includes(ext || '')) {
    return <FileCode className="w-4 h-4 text-violet-400" />;
  }
  
  // Images
  if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'ico'].includes(ext || '')) {
    return <FileImage className="w-4 h-4 text-green-400" />;
  }
  
  // Documents
  if (['md', 'txt', 'pdf', 'doc', 'docx'].includes(ext || '')) {
    return <FileText className="w-4 h-4 text-blue-400" />;
  }
  
  return <File className="w-4 h-4 text-gray-400" />;
};

// Get language from file extension
const getLanguageFromPath = (path: string): string => {
  const ext = path.split('.').pop()?.toLowerCase();
  const langMap: Record<string, string> = {
    ts: 'typescript', tsx: 'typescript',
    js: 'javascript', jsx: 'javascript',
    py: 'python', java: 'java', cpp: 'cpp', c: 'c',
    go: 'go', rs: 'rust', php: 'php', rb: 'ruby',
    html: 'html', css: 'css', scss: 'scss',
    json: 'json', yaml: 'yaml', yml: 'yaml',
    md: 'markdown', txt: 'plaintext',
    sh: 'shell', bash: 'shell'
  };
  return langMap[ext || ''] || 'plaintext';
};

function WorkspaceFilesTab() {
  const { t } = useTranslation();
  const { conversationId } = useConversationId();
  
  // State
  const [files, setFiles] = React.useState<string[]>([]);
  const [fileTree, setFileTree] = React.useState<FileNode[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedFile, setSelectedFile] = React.useState<string | null>(null);
  const [fileContent, setFileContent] = React.useState<string>('');
  const [loadingContent, setLoadingContent] = React.useState(false);
  const [expandedFolders, setExpandedFolders] = React.useState<Set<string>>(new Set());
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  
  // Load workspace files
  const loadFiles = React.useCallback(async () => {
    if (!conversationId) return;
    
    setLoading(true);
    try {
      const response = await Forge.getFiles(conversationId);
      const normalized: string[] = (response || []).map((entry: any) =>
        typeof entry === 'string' ? entry : entry?.path ?? '',
      );
      setFiles(normalized);
      setFileTree(buildFileTree(normalized));

      // Auto-select first actual file (not a directory)
      if (normalized.length > 0 && !selectedFile) {
        const firstFile = normalized.find((path: string) => !path.endsWith('/') && path.includes('.'));
        if (firstFile) {
          setSelectedFile(firstFile);
          loadFileContent(firstFile);
        }
      }
    } catch (err) {
      console.error('Failed to load workspace files:', err);
      toast.error('load-files-error', 'Failed to load workspace files');
    } finally {
      setLoading(false);
    }
  }, [conversationId, selectedFile]);
  
  // Load file content
  const loadFileContent = React.useCallback(async (filePath: string) => {
    if (!conversationId) return;
    
    // Safety check: Don't try to load directories
    if (filePath.endsWith('/')) {
      console.warn('Attempted to load directory as file:', filePath);
      toast.error('not-a-file', 'Cannot view directory contents');
      return;
    }
    
    setLoadingContent(true);
    try {
      const content = await Forge.getFile(conversationId, filePath);
      setFileContent(content || '');
    } catch (err: any) {
      console.error('Failed to load file:', err);
      
      // Check if it's a "is a directory" error
      if (err?.message?.includes('Is a directory') || err?.response?.data?.includes('Is a directory')) {
        toast.error('is-directory', 'This is a folder, not a file');
      } else {
        toast.error('load-file-error', 'Failed to load file content');
      }
      
      setFileContent('');
    } finally {
      setLoadingContent(false);
    }
  }, [conversationId]);
  
  // Initial load
  React.useEffect(() => {
    loadFiles();
  }, [loadFiles]);
  
  // Toggle folder
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
  
  // Handle file select
  const handleFileSelect = (filePath: string, nodeType?: 'file' | 'folder') => {
    // Safety check: Don't try to load folders as files
    if (nodeType === 'folder') {
      console.warn('Attempted to select a folder as a file:', filePath);
      return;
    }
    
    // Also check if path ends with '/' which typically indicates a directory
    if (filePath.endsWith('/')) {
      console.warn('File path ends with /, skipping:', filePath);
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
      toast.success('copy-success', 'Copied to clipboard');
    } catch (err) {
      toast.error('copy-error', 'Failed to copy');
    }
  };
  
  const handleDownload = () => {
    if (!fileContent || !selectedFile) return;
    const blob = new Blob([fileContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedFile.split('/').pop() || 'file';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('download-success', `Downloaded ${selectedFile}`);
  };
  
  // Handle import workspace (file upload)
  const handleImportWorkspace = () => {
    fileInputRef.current?.click();
  };
  
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFiles = event.target.files;
    if (!uploadedFiles || uploadedFiles.length === 0 || !conversationId) return;
    
    try {
      const filesArray = Array.from(uploadedFiles);
      await Forge.uploadFiles(conversationId, filesArray);
      toast.success('upload-success', `Uploaded ${filesArray.length} file(s)`);
      
      // Reload files to show the uploaded ones
      await loadFiles();
    } catch (err) {
      console.error('Failed to upload files:', err);
      toast.error('upload-error', 'Failed to upload files');
    }
    
    // Reset the input so the same file can be uploaded again if needed
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  // Filter tree
  const filteredTree = React.useMemo(() => {
    if (!searchQuery) return fileTree;
    
    const filterNode = (node: FileNode): FileNode | null => {
      const matches = node.name.toLowerCase().includes(searchQuery.toLowerCase());
      
      if (node.type === 'file') {
        return matches ? node : null;
      }
      
      const filteredChildren = node.children
        ?.map(filterNode)
        .filter((child): child is FileNode => child !== null) || [];
      
      if (matches || filteredChildren.length > 0) {
        return {
          ...node,
          children: filteredChildren
        };
      }
      
      return null;
    };
    
    return fileTree.map(filterNode).filter((node): node is FileNode => node !== null);
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
            "hover:bg-white/5",
            isSelected && "bg-violet-500/10 border-l-2 border-violet-500"
          )}
          style={{ paddingLeft: `${8 + depth * 12}px` }}
          onClick={() => {
            if (node.type === 'folder') {
              toggleFolder(node.path);
            } else {
              handleFileSelect(node.path, node.type);
            }
          }}
        >
          {/* Folder chevron */}
          {node.type === 'folder' && (
            <div className="w-4 h-4 flex items-center justify-center">
              {isExpanded ? (
                <ChevronDown className="w-3 h-3 text-gray-400" />
              ) : (
                <ChevronRight className="w-3 h-3 text-gray-400" />
              )}
            </div>
          )}
          
          {/* Icon */}
          <div className="flex-shrink-0">
            {node.type === 'folder' ? (
              isExpanded ? (
                <FolderOpen className="w-4 h-4 text-violet-400" />
              ) : (
                <Folder className="w-4 h-4 text-violet-500" />
              )
            ) : (
              getFileIcon(node.name)
            )}
          </div>
          
          {/* Name */}
          <span className={cn(
            "flex-1 truncate text-left text-sm",
            isSelected ? "text-violet-400 font-medium" : "text-gray-300"
          )}>
            {node.name}
          </span>
        </button>
        
        {/* Children */}
        {node.type === 'folder' && isExpanded && node.children && (
          <div>
            {node.children.map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };
  
  // Get filename and language
  const fileName = selectedFile?.split('/').pop() || '';
  const language = selectedFile ? getLanguageFromPath(selectedFile) : 'plaintext';
  
  return (
    <main className="h-full overflow-hidden flex flex-col bg-black">
      {/* Header - bolt.new style */}
      <div className="flex-none border-b border-violet-500/20 bg-black">
            <div className="flex items-center justify-between px-4 py-2.5">
              <div className="flex items-center gap-2.5">
                <Folder className="w-4 h-4 text-violet-500" />
                <h2 className="text-xs font-semibold text-white">Workspace</h2>
                <Badge variant="secondary" className="text-[10px] bg-violet-500/20 text-violet-400 border-violet-500/30">
                  {files.length} files
                </Badge>
              </div>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={loadFiles}
                disabled={loading}
                className="h-7 px-2"
              >
                <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
              </Button>
            </div>
            
            {/* Search */}
            <div className="px-4 pb-2.5">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search files..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-white/5 border border-violet-500/20 rounded text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-violet-500 focus:border-violet-500"
                />
              </div>
            </div>
          </div>
          
          {/* Main Content */}
          <div className="flex-1 flex gap-0 min-h-0 overflow-hidden">
        {/* File Tree Sidebar */}
        <aside className="w-80 max-w-[40%] min-w-[280px] border-r border-violet-500/20 bg-black overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto overflow-x-hidden p-2 custom-scrollbar">
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <RefreshCw className="w-5 h-5 animate-spin text-gray-400" />
              </div>
            ) : filteredTree.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                <Folder className="w-8 h-8 mb-2 opacity-50" />
                <p className="text-xs">
                  {searchQuery ? 'No files match your search' : 'No files in workspace'}
                </p>
              </div>
            ) : (
              <div className="space-y-0.5">
                {filteredTree.map(node => renderNode(node, 0))}
              </div>
            )}
          </div>
        </aside>
        
        {/* File Viewer */}
        <section className="flex-1 overflow-hidden bg-black flex flex-col">
          {selectedFile ? (
            <>
              {/* File Header */}
              <div className="flex items-center justify-between px-4 py-2 border-b border-violet-500/20 bg-black">
                <div className="flex items-center gap-2">
                  <Eye className="w-3.5 h-3.5 text-violet-500" />
                  <span className="text-xs font-medium text-white">{fileName}</span>
                  <Badge variant="outline" className="text-[10px] border-violet-500/30">{language}</Badge>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopy}
                    className="h-7 px-2"
                  >
                    <Copy className="w-3 h-3 mr-1" />
                    <span className="text-[10px]">Copy</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleDownload}
                    className="h-7 px-2"
                  >
                    <Download className="w-3 h-3 mr-1" />
                    <span className="text-[10px]">Download</span>
                  </Button>
                </div>
              </div>
              
              {/* File Content */}
              <div className="flex-1 overflow-hidden">
                {loadingContent ? (
                  <div className="flex items-center justify-center h-full">
                    <RefreshCw className="w-5 h-5 animate-spin text-gray-400" />
                  </div>
                ) : (
                  <LazyMonaco
                    value={fileContent}
                    onChange={() => {}}
                    language={language}
                    height="100%"
                    theme="vs-dark"
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
                    beforeMount={(monaco: any) => {
                      monaco.editor.defineTheme('pure-black', {
                        base: 'vs-dark',
                        inherit: true,
                        rules: [],
                        colors: {
                          'editor.background': '#000000',
                          'editor.lineHighlightBackground': '#000000',
                          'editorGutter.background': '#000000',
                          'editorWidget.background': '#000000',
                          'editorGroupHeader.tabsBackground': '#000000',
                          'editorLineNumber.foreground': '#666666',
                          'editorLineNumber.activeForeground': '#999999',
                        }
                      });
                      monaco.editor.setTheme('pure-black');
                    }}
                  />
                )}
              </div>
            </>
          ) : (
            <div className="h-full w-full flex flex-col items-center justify-center text-gray-500 gap-4">
              <Folder className="w-12 h-12 opacity-50" />
              <p className="text-sm">Select a file to view its content</p>
              
              {/* Violet button */}
              <Button
                onClick={handleImportWorkspace}
                className={cn(
                  "px-6 py-2.5 h-auto",
                  "bg-gradient-to-r from-violet-600 to-purple-600",
                  "hover:from-violet-500 hover:to-purple-500",
                  "text-white font-medium text-sm",
                  "rounded-lg shadow-lg shadow-violet-500/20",
                  "transition-all duration-200",
                  "hover:shadow-xl hover:shadow-violet-500/30",
                  "hover:scale-105"
                )}
              >
                <FolderPlus className="w-4 h-4 mr-2" />
                Import Workspace
              </Button>
              
              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileUpload}
                className="hidden"
                aria-label="Upload files"
              />
              
              <p className="text-xs text-gray-600">Synced with VSCode workspace</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

export default WorkspaceFilesTab;

