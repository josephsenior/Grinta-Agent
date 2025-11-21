import { useState, useCallback } from "react";

const MAX_HISTORY_SIZE = 10;

export function useFileHistory() {
  const [viewedFiles, setViewedFiles] = useState<string[]>([]);

  const addToHistory = useCallback((filePath: string) => {
    setViewedFiles((prev) => {
      const filtered = prev.filter((f) => f !== filePath);
      return [filePath, ...filtered].slice(0, MAX_HISTORY_SIZE);
    });
  }, []);

  return {
    viewedFiles,
    addToHistory,
  };
}
