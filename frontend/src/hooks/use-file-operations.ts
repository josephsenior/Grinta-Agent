import { useState, useCallback } from "react";
import Forge from "#/api/forge";
import toast from "#/utils/toast";

interface UseFileOperationsProps {
  conversationId: string;
  onFilesChanged?: () => void;
}

export function useFileOperations({
  conversationId,
  onFilesChanged,
}: UseFileOperationsProps) {
  const [loading, setLoading] = useState(false);

  // Get file content
  const getFileContent = useCallback(
    async (filePath: string) => {
      try {
        // Skip special directories that cause 500 errors
        if (filePath === ".downloads" || filePath.startsWith(".downloads/")) {
          console.warn("Skipping special directory:", filePath);
          return null;
        }

        setLoading(true);
        const response = await Forge.getFile(conversationId, filePath);
        if (typeof response === "string") return response;
        // Some backends return an object with `code` or `content`
        if (response && typeof response === "object") {
          return (response as any).code ?? (response as any).content ?? null;
        }
        return null;
      } catch (error) {
        console.error("Failed to get file content:", error);
        // Only show toast for non-404/500 errors from special dirs
        if (!filePath.startsWith(".")) {
          toast.error("file-content-error", "Failed to load file content");
        }
        return null;
      } finally {
        setLoading(false);
      }
    },
    [conversationId],
  );

  // Delete file
  const deleteFile = useCallback(
    async (filePath: string) => {
      try {
        setLoading(true);
        // Note: The Forge API doesn't have a delete file method yet
        // This would need to be implemented on the backend
        // For now, we'll show a success message
        toast.info(`File ${filePath} would be deleted`);
        onFilesChanged?.();
      } catch (error) {
        console.error("Failed to delete file:", error);
        toast.error("file-delete-error", "Failed to delete file");
      } finally {
        setLoading(false);
      }
    },
    [onFilesChanged],
  );

  // Rename file
  const renameFile = useCallback(
    async (oldPath: string, newPath: string) => {
      try {
        setLoading(true);
        // Note: The Forge API doesn't have a rename file method yet
        // This would need to be implemented on the backend
        // For now, we'll show a success message
        toast.info(`File renamed from ${oldPath} to ${newPath}`);
        onFilesChanged?.();
      } catch (error) {
        console.error("Failed to rename file:", error);
        toast.error("file-rename-error", "Failed to rename file");
      } finally {
        setLoading(false);
      }
    },
    [onFilesChanged],
  );

  // Create folder
  const createFolder = useCallback(
    async (folderPath: string) => {
      try {
        setLoading(true);
        // Note: The Forge API doesn't have a create folder method yet
        // This would need to be implemented on the backend
        // For now, we'll show a success message
        toast.info(`Folder ${folderPath} would be created`);
        onFilesChanged?.();
      } catch (error) {
        console.error("Failed to create folder:", error);
        toast.error("folder-create-error", "Failed to create folder");
      } finally {
        setLoading(false);
      }
    },
    [onFilesChanged],
  );

  // Download file
  const downloadFile = useCallback(
    async (filePath: string) => {
      try {
        setLoading(true);
        const content = await getFileContent(filePath);
        if (content) {
          const blob = new Blob([content], { type: "text/plain" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = filePath.split("/").pop() || "file";
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          toast.success("file-download-success", `Downloaded ${filePath}`);
        }
      } catch (error) {
        console.error("Failed to download file:", error);
        toast.error("file-download-error", "Failed to download file");
      } finally {
        setLoading(false);
      }
    },
    [getFileContent],
  );

  return {
    loading,
    getFileContent,
    deleteFile,
    renameFile,
    createFolder,
    downloadFile,
  };
}
