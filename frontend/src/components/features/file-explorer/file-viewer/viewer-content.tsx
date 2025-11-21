import React from "react";
import { useTranslation } from "react-i18next";
import { EyeOff, RefreshCw } from "lucide-react";
import { Textarea } from "#/components/ui/textarea";
import { LazyMonaco } from "#/components/shared/lazy-monaco";

type ViewerState = "loading" | "binary" | "editing" | "preview";

interface ViewerContentProps {
  state: ViewerState;
  content: string;
  editContent: string;
  language: string;
  onEditContentChange: (value: string) => void;
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-full">
      <RefreshCw className="w-5 h-5 animate-spin text-text-secondary" />
    </div>
  );
}

function BinaryPlaceholder() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-center h-full p-8">
      <div className="text-center">
        <EyeOff className="w-12 h-12 text-text-secondary mx-auto mb-3 opacity-50" />
        <p className="text-text-secondary">
          {t(
            "viewerContent.binaryFile",
            "Binary file - cannot display content",
          )}
        </p>
        <p className="text-xs text-text-tertiary mt-1">
          {t("viewerContent.useDownload", "Use download to access this file")}
        </p>
      </div>
    </div>
  );
}

function EditingView({
  editContent,
  onEditContentChange,
}: {
  editContent: string;
  onEditContentChange: (value: string) => void;
}) {
  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 p-4">
        <Textarea
          value={editContent}
          onChange={(event) => onEditContentChange(event.target.value)}
          className="h-full resize-none font-mono text-sm"
          placeholder="Edit file content..."
        />
      </div>
    </div>
  );
}

function PreviewView({
  content,
  language,
}: {
  content: string;
  language: string;
}) {
  return (
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
  );
}

export function ViewerContent({
  state,
  content,
  editContent,
  language,
  onEditContentChange,
}: ViewerContentProps) {
  switch (state) {
    case "loading":
      return <LoadingSpinner />;
    case "binary":
      return <BinaryPlaceholder />;
    case "editing":
      return (
        <EditingView
          editContent={editContent}
          onEditContentChange={onEditContentChange}
        />
      );
    case "preview":
      return <PreviewView content={content} language={language} />;
    default:
      return null;
  }
}
