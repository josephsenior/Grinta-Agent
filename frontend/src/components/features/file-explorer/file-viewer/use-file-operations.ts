import { useCallback, useState } from "react";
import { logger } from "#/utils/logger";

export function useFileOperations(
  content: string,
  filePath: string | null,
  onFileEdit?: (filePath: string, content: string) => void,
) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      logger.error("Failed to copy:", error);
    }
  }, [content]);

  const handleDownload = useCallback(() => {
    if (!content || !filePath) return;

    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filePath.split("/").pop() || "file";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [content, filePath]);

  const handleSave = useCallback(
    (
      editContent: string,
      setContent: (content: string) => void,
      setEditing: (editing: boolean) => void,
    ) => {
      if (onFileEdit && filePath) {
        onFileEdit(filePath, editContent);
        setContent(editContent);
        setEditing(false);
      }
    },
    [onFileEdit, filePath],
  );

  return {
    copied,
    handleCopy,
    handleDownload,
    handleSave,
  };
}
