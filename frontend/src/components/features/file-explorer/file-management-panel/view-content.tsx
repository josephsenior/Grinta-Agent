import React from "react";
import { FileText } from "lucide-react";
import { FileExplorer } from "../file-explorer";
import { FileViewer } from "../file-viewer";
import type { ViewMode } from "./use-view-state";

interface ViewContentProps {
  view: ViewMode;
  conversationId: string;
  selectedFile: string | null;
  onFileSelect: (filePath: string) => void;
  onFileOpen: (filePath: string) => void;
  onFileDelete: (filePath: string) => void;
  onFileRename: (oldPath: string, newPath: string) => void;
  onFileEdit: (filePath: string, content: string) => void;
  onCloseViewer: () => void;
}

function EmptyState({
  message,
  subMessage,
}: {
  message: string;
  subMessage: string;
}) {
  return (
    <div className="flex items-center justify-center h-full p-8">
      <div className="text-center text-[var(--text-tertiary)] min-w-[320px] max-w-2xl px-4">
        <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p
          className="text-sm"
          style={{ wordBreak: "normal", whiteSpace: "normal" }}
        >
          {message}
        </p>
        <p
          className="text-xs mt-1"
          style={{ wordBreak: "normal", whiteSpace: "normal" }}
        >
          {subMessage}
        </p>
      </div>
    </div>
  );
}

export function ViewContent({
  view,
  conversationId,
  selectedFile,
  onFileSelect,
  onFileOpen,
  onFileDelete,
  onFileRename,
  onFileEdit,
  onCloseViewer,
}: ViewContentProps) {
  const explorerProps = {
    conversationId,
    onFileSelect,
    onFileOpen,
    onFileDelete,
    onFileRename,
    showActions: true,
    showStatus: true,
    showSearch: true,
  };

  if (view === "explorer") {
    return (
      <div className="flex-1">
        <FileExplorer
          conversationId={explorerProps.conversationId}
          onFileSelect={explorerProps.onFileSelect}
          onFileOpen={explorerProps.onFileOpen}
          onFileDelete={explorerProps.onFileDelete}
          onFileRename={explorerProps.onFileRename}
          showActions={explorerProps.showActions}
          showStatus={explorerProps.showStatus}
          showSearch={explorerProps.showSearch}
        />
      </div>
    );
  }

  if (view === "split") {
    return (
      <>
        <div className="w-1/2 border-r border-border">
          <FileExplorer
            conversationId={explorerProps.conversationId}
            onFileSelect={explorerProps.onFileSelect}
            onFileOpen={explorerProps.onFileOpen}
            onFileDelete={explorerProps.onFileDelete}
            onFileRename={explorerProps.onFileRename}
            showActions={explorerProps.showActions}
            showStatus={explorerProps.showStatus}
            showSearch={explorerProps.showSearch}
          />
        </div>
        <div className="w-1/2">
          {selectedFile ? (
            <FileViewer
              filePath={selectedFile}
              conversationId={conversationId}
              onClose={onCloseViewer}
              onFileEdit={onFileEdit}
              editable
            />
          ) : (
            <EmptyState
              message="Select a file to view"
              subMessage="Choose a file from the explorer"
            />
          )}
        </div>
      </>
    );
  }

  // viewer mode
  return (
    <div className="flex-1">
      {selectedFile ? (
        <FileViewer
          filePath={selectedFile}
          conversationId={conversationId}
          onClose={onCloseViewer}
          onFileEdit={onFileEdit}
          editable
        />
      ) : (
        <EmptyState
          message="No file selected"
          subMessage="Open a file to view its content"
        />
      )}
    </div>
  );
}
