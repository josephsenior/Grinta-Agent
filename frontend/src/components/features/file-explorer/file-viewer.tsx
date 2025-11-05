import React, { useState, useEffect } from "react";
import { 
  X, 
  Copy, 
  Download, 
  Edit3, 
  Save, 
  Eye,
  EyeOff,
  Maximize2,
  Minimize2,
  RefreshCw
} from "lucide-react";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";
import { Textarea } from "#/components/ui/textarea";
import { cn } from "#/utils/utils";
import { LazyMonaco } from "#/components/shared/lazy-monaco";
import { useFileOperations } from "#/hooks/use-file-operations";

interface FileViewerProps {
  filePath: string | null;
  conversationId: string;
  onClose?: () => void;
  onFileEdit?: (filePath: string, content: string) => void;
  className?: string;
  editable?: boolean;
  maxHeight?: string;
}

// Detect file language for syntax highlighting
const getLanguageFromPath = (filePath: string): string => {
  const ext = filePath.split('.').pop()?.toLowerCase();
  
  const languageMap: Record<string, string> = {
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'py': 'python',
    'java': 'java',
    'cpp': 'cpp',
    'c': 'c',
    'cs': 'csharp',
    'php': 'php',
    'rb': 'ruby',
    'go': 'go',
    'rs': 'rust',
    'swift': 'swift',
    'kt': 'kotlin',
    'scala': 'scala',
    'html': 'html',
    'css': 'css',
    'scss': 'scss',
    'sass': 'sass',
    'less': 'less',
    'json': 'json',
    'xml': 'xml',
    'yaml': 'yaml',
    'yml': 'yaml',
    'toml': 'toml',
    'ini': 'ini',
    'env': 'bash',
    'sh': 'bash',
    'bash': 'bash',
    'zsh': 'bash',
    'fish': 'bash',
    'ps1': 'powershell',
    'bat': 'batch',
    'cmd': 'batch',
    'md': 'markdown',
    'txt': 'plaintext',
    'sql': 'sql',
    'dockerfile': 'dockerfile',
    'gitignore': 'gitignore',
    'gitattributes': 'gitattributes',
  };
  
  return languageMap[ext || ''] || 'plaintext';
};

// Check if file is binary (image, video, audio, etc.)
const isBinaryFile = (filePath: string): boolean => {
  const ext = filePath.split('.').pop()?.toLowerCase();
  const binaryExtensions = [
    'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'ico', 'bmp', 'tiff',
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv', 'mpg', 'mpeg',
    'mp3', 'wav', 'flac', 'aac', 'ogg', 'wma',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'zip', 'rar', '7z', 'tar', 'gz', 'bz2',
    'exe', 'dll', 'so', 'dylib', 'bin'
  ];
  return binaryExtensions.includes(ext || '');
};

export function FileViewer({
  filePath,
  conversationId,
  onClose,
  onFileEdit,
  className,
  editable = false,
  maxHeight = "400px"
}: FileViewerProps) {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isClient, setIsClient] = useState(false);

  // Prevent hydration issues
  useEffect(() => {
    setIsClient(true);
  }, []);
  
  const { getFileContent } = useFileOperations({ conversationId });

  // Load file content when filePath changes
  useEffect(() => {
    if (!filePath) {
      setContent("");
      return;
    }

    const loadContent = async () => {
      setLoading(true);
      try {
        const fileContent = await getFileContent(filePath);
        if (fileContent !== null) {
          setContent(fileContent);
          setEditContent(fileContent);
        }
      } catch (error) {
        console.error('Failed to load file:', error);
        setContent("");
      } finally {
        setLoading(false);
      }
    };

    loadContent();
  }, [filePath, getFileContent]);

  // Handle copy to clipboard
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  // Handle save
  const handleSave = () => {
    if (onFileEdit && filePath) {
      onFileEdit(filePath, editContent);
      setContent(editContent);
      setEditing(false);
    }
  };

  // Handle cancel edit
  const handleCancel = () => {
    setEditContent(content);
    setEditing(false);
  };

  // Handle download
  const handleDownload = () => {
    if (!content) return;
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filePath?.split('/').pop() || 'file';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!filePath) {
    return null;
  }

  // Don't render on server side to prevent hydration issues
  if (!isClient) {
    return (
      <div className={cn(
        "flex flex-col h-full bg-background-primary border border-border rounded-lg overflow-hidden",
        className
      )}>
        <div className="flex items-center justify-center h-32">
          <div className="text-text-secondary">Loading...</div>
        </div>
      </div>
    );
  }

  const language = getLanguageFromPath(filePath);
  const isBinary = isBinaryFile(filePath);
  const fileName = filePath.split('/').pop() || filePath;

  return (
    <div className={cn(
      "flex flex-col bg-background-primary border border-border rounded-lg overflow-hidden",
      isFullscreen ? "fixed inset-4 z-50" : "",
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-border bg-background-secondary">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Eye className="w-4 h-4 text-violet-500" />
            <span className="text-sm font-medium text-text-primary truncate">
              {fileName}
            </span>
          </div>
          
          <Badge variant="outline" className="text-xs">
            {language}
          </Badge>
          
          <span className="text-xs text-text-secondary">
            {content.length.toLocaleString()} chars
          </span>
        </div>
        
        <div className="flex items-center gap-1">
          {/* Copy Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-7 px-2 text-xs"
          >
            {copied ? (
              <>
                <span className="text-success-500">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3 mr-1" />
                Copy
              </>
            )}
          </Button>
          
          {/* Download Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDownload}
            className="h-7 px-2 text-xs"
          >
            <Download className="w-3 h-3 mr-1" />
            Download
          </Button>
          
          {/* Edit Button */}
          {editable && !editing && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setEditing(true)}
              className="h-7 px-2 text-xs"
            >
              <Edit3 className="w-3 h-3 mr-1" />
              Edit
            </Button>
          )}
          
          {/* Save/Cancel Buttons */}
          {editing && (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSave}
                className="h-7 px-2 text-xs text-success-500"
              >
                <Save className="w-3 h-3 mr-1" />
                Save
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCancel}
                className="h-7 px-2 text-xs text-text-secondary"
              >
                Cancel
              </Button>
            </>
          )}
          
          {/* Fullscreen Toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="h-7 w-7 p-0"
          >
            {isFullscreen ? (
              <Minimize2 className="w-3 h-3" />
            ) : (
              <Maximize2 className="w-3 h-3" />
            )}
          </Button>
          
          {/* Close Button */}
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-7 w-7 p-0"
            >
              <X className="w-3 h-3" />
            </Button>
          )}
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <RefreshCw className="w-5 h-5 animate-spin text-text-secondary" />
          </div>
        ) : isBinary ? (
          <div className="flex items-center justify-center h-full p-8">
            <div className="text-center">
              <EyeOff className="w-12 h-12 text-text-secondary mx-auto mb-3 opacity-50" />
              <p className="text-text-secondary">Binary file - cannot display content</p>
              <p className="text-xs text-text-tertiary mt-1">Use download to access this file</p>
            </div>
          </div>
        ) : editing ? (
          <div className="h-full flex flex-col">
            <div className="flex-1 p-4">
              <Textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="h-full resize-none font-mono text-sm"
                placeholder="Edit file content..."
              />
            </div>
          </div>
        ) : (
          <div className="h-full">
            <LazyMonaco
              value={content}
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
          </div>
        )}
      </div>
    </div>
  );
}
