import React, { useState, useEffect } from "react";
import { cn } from "#/utils/utils";
import { useFileOperations } from "#/hooks/use-file-operations";
import { logger } from "#/utils/logger";
import {
  getLanguageFromPath,
  isBinaryFile,
  getViewerState,
} from "./file-viewer/file-utils";
import { useFileOperations as useViewerFileOperations } from "./file-viewer/use-file-operations";
import { ViewerHeader } from "./file-viewer/viewer-header";
import { ViewerContent } from "./file-viewer/viewer-content";

interface FileViewerProps {
  filePath: string | null;
  conversationId: string;
  onClose?: () => void;
  onFileEdit?: (filePath: string, content: string) => void;
  className?: string;
  editable?: boolean;
  maxHeight?: string;
}

const renderSkeletonContainer = (className?: string) => (
  <div
    className={cn(
      "flex flex-col h-full bg-background-primary border border-border rounded-lg overflow-hidden",
      className,
    )}
  >
    <div className="flex items-center justify-center h-32">
      <div className="text-text-secondary">Loading...</div>
    </div>
  </div>
);

export function FileViewer({
  filePath,
  conversationId,
  onClose,
  onFileEdit,
  className,
  editable = false,
  maxHeight = "400px",
}: FileViewerProps) {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  const { getFileContent } = useFileOperations({ conversationId });
  const { copied, handleCopy, handleDownload, handleSave } =
    useViewerFileOperations(content, filePath, onFileEdit);

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
        logger.error("Failed to load file:", error);
        setContent("");
      } finally {
        setLoading(false);
      }
    };

    loadContent();
  }, [filePath, getFileContent]);

  const handleSaveClick = () => {
    handleSave(editContent, setContent, setEditing);
  };

  const handleCancel = () => {
    setEditContent(content);
    setEditing(false);
  };

  const toggleFullscreen = () => setIsFullscreen((prev) => !prev);

  if (!filePath) {
    return null;
  }

  if (!isClient) {
    return renderSkeletonContainer(className);
  }

  const language = getLanguageFromPath(filePath);
  const isBinary = isBinaryFile(filePath);
  const fileName = filePath.split("/").pop() || filePath;
  const viewerState = getViewerState({ isLoading: loading, isBinary, editing });

  return (
    <div
      className={cn(
        "flex flex-col bg-background-primary border border-border rounded-lg overflow-hidden",
        isFullscreen ? "fixed inset-4 z-50" : "",
        className,
      )}
      style={isFullscreen ? undefined : { maxHeight }}
    >
      <ViewerHeader
        fileName={fileName}
        language={language}
        contentLength={content.length}
        editable={editable}
        editing={editing}
        copied={copied}
        isFullscreen={isFullscreen}
        onCopy={handleCopy}
        onDownload={handleDownload}
        onEdit={() => setEditing(true)}
        onSave={handleSaveClick}
        onCancel={handleCancel}
        onToggleFullscreen={toggleFullscreen}
        onClose={onClose}
      />

      <div className="flex-1 overflow-hidden">
        <ViewerContent
          state={viewerState}
          content={content}
          editContent={editContent}
          language={language}
          onEditContentChange={setEditContent}
        />
      </div>
    </div>
  );
}
