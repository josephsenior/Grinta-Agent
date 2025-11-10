import React, { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  PanelLeft,
  PanelLeftClose,
  FileText,
  Grid3X3,
  List,
} from "lucide-react";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";
import { cn } from "#/utils/utils";
import { FileExplorer } from "./file-explorer";
import { FileViewer } from "./file-viewer";

interface FileManagementPanelProps {
  conversationId: string;
  isOpen: boolean;
  onToggle: () => void;
  className?: string;
  defaultView?: "split" | "explorer" | "viewer";
}

export function FileManagementPanel({
  conversationId,
  isOpen,
  onToggle,
  className,
  defaultView = "split",
}: FileManagementPanelProps) {
  const { t } = useTranslation();
  const [view, setView] = useState<"split" | "explorer" | "viewer">(
    defaultView,
  );
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [viewedFiles, setViewedFiles] = useState<string[]>([]);
  const [isClient, setIsClient] = useState(false);

  // Prevent hydration issues
  React.useEffect(() => {
    setIsClient(true);
  }, []);

  // Handle file selection
  const handleFileSelect = useCallback((filePath: string) => {
    setSelectedFile(filePath);
    setView("split");

    // Add to viewed files history
    setViewedFiles((prev) => {
      const filtered = prev.filter((f) => f !== filePath);
      return [filePath, ...filtered].slice(0, 10); // Keep last 10 files
    });
  }, []);

  // Handle file open (opens in viewer)
  const handleFileOpen = useCallback((filePath: string) => {
    setSelectedFile(filePath);
    setView("viewer");

    // Add to viewed files history
    setViewedFiles((prev) => {
      const filtered = prev.filter((f) => f !== filePath);
      return [filePath, ...filtered].slice(0, 10);
    });
  }, []);

  // Handle file operations
  const handleFileDelete = useCallback((filePath: string) => {
    // TODO: Implement file deletion
    console.log("Delete file:", filePath);
  }, []);

  const handleFileRename = useCallback((oldPath: string, newPath: string) => {
    // TODO: Implement file renaming
    console.log("Rename file:", oldPath, "to", newPath);
  }, []);

  const handleFileEdit = useCallback((filePath: string, content: string) => {
    // TODO: Implement file editing
    console.log("Edit file:", filePath, "content length:", content.length);
  }, []);

  // Close viewer
  const handleCloseViewer = useCallback(() => {
    setSelectedFile(null);
    setView("explorer");
  }, []);

  // Don't render on server side to prevent hydration issues
  if (!isClient) {
    return null;
  }

  if (!isOpen) {
    return (
      <Button
        variant="ghost"
        size="sm"
        onClick={onToggle}
        className={cn(
          "fixed left-4 top-20 z-40 h-8 w-8 p-0",
          "bg-background-primary/80 backdrop-blur-sm border border-border",
          "hover:bg-background-secondary/80 transition-all duration-200",
        )}
      >
        <PanelLeft className="w-4 h-4" />
      </Button>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col h-full bg-background-primary border-r border-border",
        "transition-all duration-300 ease-in-out",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-border bg-background-secondary">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-violet-500" />
          <h2 className="text-sm font-semibold text-text-primary">
            File Manager
          </h2>
          <Badge variant="secondary" className="text-xs">
            {viewedFiles.length} recent
          </Badge>
        </div>

        <div className="flex items-center gap-1">
          {/* View Toggle */}
          <div className="flex items-center border border-border rounded-md p-0.5">
            <Button
              variant={view === "explorer" ? "default" : "ghost"}
              size="sm"
              onClick={() => setView("explorer")}
              className="h-6 w-6 p-0"
            >
              <List className="w-3 h-3" />
            </Button>
            <Button
              variant={view === "split" ? "default" : "ghost"}
              size="sm"
              onClick={() => setView("split")}
              className="h-6 w-6 p-0"
            >
              <Grid3X3 className="w-3 h-3" />
            </Button>
            <Button
              variant={view === "viewer" ? "default" : "ghost"}
              size="sm"
              onClick={() => setView("viewer")}
              className="h-6 w-6 p-0"
              disabled={!selectedFile}
            >
              <FileText className="w-3 h-3" />
            </Button>
          </div>

          {/* Close Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggle}
            className="h-6 w-6 p-0"
          >
            <PanelLeftClose className="w-3 h-3" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Explorer Only View */}
        {view === "explorer" && (
          <div className="flex-1">
            <FileExplorer
              conversationId={conversationId}
              onFileSelect={handleFileSelect}
              onFileOpen={handleFileOpen}
              onFileDelete={handleFileDelete}
              onFileRename={handleFileRename}
              showActions
              showStatus
              showSearch
            />
          </div>
        )}

        {/* Split View */}
        {view === "split" && (
          <>
            <div className="w-1/2 border-r border-border">
              <FileExplorer
                conversationId={conversationId}
                onFileSelect={handleFileSelect}
                onFileOpen={handleFileOpen}
                onFileDelete={handleFileDelete}
                onFileRename={handleFileRename}
                showActions
                showStatus
                showSearch
              />
            </div>
            <div className="w-1/2">
              {selectedFile ? (
                <FileViewer
                  filePath={selectedFile}
                  conversationId={conversationId}
                  onClose={handleCloseViewer}
                  onFileEdit={handleFileEdit}
                  editable
                />
              ) : (
                <div className="flex items-center justify-center h-full p-8">
                  <div className="text-center text-text-secondary">
                    <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">Select a file to view</p>
                    <p className="text-xs mt-1">
                      Choose a file from the explorer
                    </p>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {/* Viewer Only View */}
        {view === "viewer" && (
          <div className="flex-1">
            {selectedFile ? (
              <FileViewer
                filePath={selectedFile}
                conversationId={conversationId}
                onClose={handleCloseViewer}
                onFileEdit={handleFileEdit}
                editable
              />
            ) : (
              <div className="flex items-center justify-center h-full p-8">
                <div className="text-center text-text-secondary">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p className="text-sm">No file selected</p>
                  <p className="text-xs mt-1">
                    Open a file to view its content
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Recent Files Footer */}
      {viewedFiles.length > 0 && (
        <div className="border-t border-border p-2 bg-background-secondary">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-text-secondary">
              Recent Files
            </span>
          </div>
          <div className="flex flex-wrap gap-1">
            {viewedFiles.slice(0, 5).map((filePath) => {
              const fileName = filePath.split("/").pop() || filePath;
              const isSelected = selectedFile === filePath;

              return (
                <Button
                  key={filePath}
                  variant="ghost"
                  size="sm"
                  onClick={() => handleFileSelect(filePath)}
                  className={cn(
                    "h-6 px-2 text-xs",
                    isSelected && "bg-brand-500/10 text-violet-500",
                  )}
                >
                  <span className="truncate max-w-20" title={fileName}>
                    {fileName}
                  </span>
                </Button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
