import React, { useState, useCallback } from "react";
import { PanelLeft } from "lucide-react";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";
import { logger } from "#/utils/logger";
import { useFileHistory } from "./file-management-panel/use-file-history";
import { useViewState } from "./file-management-panel/use-view-state";
import { ViewHeader } from "./file-management-panel/view-header";
import { ViewContent } from "./file-management-panel/view-content";
import { RecentFiles } from "./file-management-panel/recent-files";

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
  const [isClient, setIsClient] = useState(false);
  const { viewedFiles, addToHistory } = useFileHistory();
  const {
    view,
    setView,
    selectedFile,
    handleFileSelect,
    handleFileOpen,
    handleCloseViewer,
  } = useViewState(defaultView);

  React.useEffect(() => {
    setIsClient(true);
  }, []);

  const onFileSelect = useCallback(
    (filePath: string) => {
      handleFileSelect(filePath, addToHistory);
    },
    [handleFileSelect, addToHistory],
  );

  const onFileOpen = useCallback(
    (filePath: string) => {
      handleFileOpen(filePath, addToHistory);
    },
    [handleFileOpen, addToHistory],
  );

  const handleFileDelete = useCallback((filePath: string) => {
    logger.debug("Delete file:", filePath);
  }, []);

  const handleFileRename = useCallback((oldPath: string, newPath: string) => {
    logger.debug("Rename file:", oldPath, "to", newPath);
  }, []);

  const handleFileEdit = useCallback((filePath: string, content: string) => {
    logger.debug("Edit file:", filePath, "content length:", content.length);
  }, []);

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
      <ViewHeader
        view={view}
        onViewChange={setView}
        onClose={onToggle}
        viewedFilesCount={viewedFiles.length}
        hasSelectedFile={!!selectedFile}
      />

      <div className="flex-1 flex overflow-hidden">
        <ViewContent
          view={view}
          conversationId={conversationId}
          selectedFile={selectedFile}
          onFileSelect={onFileSelect}
          onFileOpen={onFileOpen}
          onFileDelete={handleFileDelete}
          onFileRename={handleFileRename}
          onFileEdit={handleFileEdit}
          onCloseViewer={handleCloseViewer}
        />
      </div>

      <RecentFiles
        viewedFiles={viewedFiles}
        selectedFile={selectedFile}
        onFileSelect={onFileSelect}
      />
    </div>
  );
}
