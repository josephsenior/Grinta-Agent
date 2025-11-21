import { useState, useCallback } from "react";

export type ViewMode = "split" | "explorer" | "viewer";

export function useViewState(defaultView: ViewMode = "split") {
  const [view, setView] = useState<ViewMode>(defaultView);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const handleFileSelect = useCallback(
    (filePath: string, addToHistory: (path: string) => void) => {
      setSelectedFile(filePath);
      setView("split");
      addToHistory(filePath);
    },
    [],
  );

  const handleFileOpen = useCallback(
    (filePath: string, addToHistory: (path: string) => void) => {
      setSelectedFile(filePath);
      setView("viewer");
      addToHistory(filePath);
    },
    [],
  );

  const handleCloseViewer = useCallback(() => {
    setSelectedFile(null);
    setView("explorer");
  }, []);

  return {
    view,
    setView,
    selectedFile,
    handleFileSelect,
    handleFileOpen,
    handleCloseViewer,
  };
}
