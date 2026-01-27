import React from "react";
import { useTranslation } from "react-i18next";
import { Upload, X, FileText, Image as ImageIcon } from "lucide-react";
import { ChatInput } from "./chat-input";
import { cn } from "#/utils/utils";
import { ImageCarousel } from "../images/image-carousel";
import { UploadImageInput } from "../images/upload-image-input";
import { FileList } from "../files/file-list";
import { FilePreviewModal } from "../files/file-preview-modal";
import { isFileImage } from "#/utils/is-file-image";
import { validateFiles } from "#/utils/file-validation";
import { Card, CardContent } from "#/components/ui/card";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";
import {
  displaySuccessToast,
  displayErrorToast,
} from "#/utils/custom-toast-handlers";
import { useAutonomyMode } from "#/hooks/use-autonomy-mode";

interface InteractiveChatBoxProps {
  isDisabled?: boolean;
  mode?: "stop" | "submit";
  onSubmit: (message: string, images: File[], files: File[]) => void;
  onStop: () => void;
  value?: string;
  onChange?: (message: string) => void;
  placeholder?: string;
  onFocus?: () => void;
  onBlur?: () => void;
  // Quick edit last message (↑ key)
  onEditLastMessage?: () => string | null;
}

export function InteractiveChatBox({
  isDisabled,
  mode = "submit",
  onSubmit,
  onStop,
  value,
  onChange,
  placeholder,
  onFocus,
  onBlur,
  onEditLastMessage,
}: InteractiveChatBoxProps) {
  const { t } = useTranslation();
  // useAutonomyMode is called but values not currently used
  useAutonomyMode();
  type ImageEntry = { file: File; previewUrl: string };
  const [images, setImages] = React.useState<ImageEntry[]>([]);
  const [files, setFiles] = React.useState<File[]>([]);
  const [showFileUpload, setShowFileUpload] = React.useState(false);
  const [pendingFiles, setPendingFiles] = React.useState<File[]>([]);
  const [showFilePreview, setShowFilePreview] = React.useState(false);
  const [isDraggingOverContainer, setIsDraggingOverContainer] =
    React.useState(false); // For drag-drop overlay
  const hiddenFileInputRef = React.useRef<HTMLInputElement | null>(null);

  const revokePreviewUrl = (entry: ImageEntry) => {
    try {
      URL.revokeObjectURL(entry.previewUrl);
    } catch (error) {
      // ignore revoke errors
    }
  };

  const imageEntriesRef = React.useRef<ImageEntry[]>(images);

  React.useEffect(() => {
    imageEntriesRef.current = images;
  }, [images]);

  React.useEffect(
    () => () => {
      imageEntriesRef.current.forEach(revokePreviewUrl);
    },
    [],
  );

  const clearImages = React.useCallback(() => {
    setImages((prev) => {
      prev.forEach(revokePreviewUrl);
      return [];
    });
  }, []);

  const handleUpload = (selectedFiles: File[]) => {
    // Validate files before adding them
    const validation = validateFiles(selectedFiles, [
      ...images.map((entry) => entry.file),
      ...files,
    ]);

    if (!validation.isValid) {
      displayErrorToast(`Error: ${validation.errorMessage}`);
      return; // Don't add any files if validation fails
    }

    // Show preview modal
    setPendingFiles(selectedFiles);
    setShowFilePreview(true);
  };

  const handleConfirmUpload = (confirmedFiles: File[]) => {
    // Filter valid files by type
    const validFiles = confirmedFiles.filter((f) => !isFileImage(f));
    const validImages = confirmedFiles.filter((f) => isFileImage(f));

    setFiles((prevFiles) => [...prevFiles, ...validFiles]);
    setImages((prevImages) => [
      ...prevImages,
      ...validImages.map((file) => ({
        file,
        previewUrl: URL.createObjectURL(file),
      })),
    ]);
    setShowFilePreview(false);
    setPendingFiles([]);
    setShowFileUpload(false);
    displaySuccessToast(t("Files uploaded successfully"));
  };

  const handleCancelUpload = () => {
    setShowFilePreview(false);
    setPendingFiles([]);
  };

  const removeElementByIndex = (array: Array<File>, index: number) => {
    const newArray = [...array];
    newArray.splice(index, 1);
    return newArray;
  };

  const handleRemoveFile = (index: number) => {
    setFiles(removeElementByIndex(files, index));
  };
  const handleRemoveImage = (index: number) => {
    setImages((prevImages) => {
      if (index < 0 || index >= prevImages.length) {
        return prevImages;
      }
      const updated = [...prevImages];
      const [removed] = updated.splice(index, 1);
      if (removed) {
        revokePreviewUrl(removed);
      }
      return updated;
    });
  };

  const handleSubmit = (message: string) => {
    onSubmit(
      message,
      images.map((entry) => entry.file),
      files,
    );
    setFiles([]);
    clearImages();
    if (message) {
      onChange?.("");
    }
  };

  const hasFiles = images.length > 0 || files.length > 0;

  // Container-level drag-and-drop handlers (bolt.diy style)
  const handleContainerDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (event.dataTransfer.types.includes("Files")) {
      setIsDraggingOverContainer(true);
    }
  };

  const handleContainerDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    // Only hide overlay if leaving the container (not child elements)
    if (event.currentTarget === event.target) {
      setIsDraggingOverContainer(false);
    }
  };

  const handleContainerDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDraggingOverContainer(false);

    if (event.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(event.dataTransfer.files);
      handleUpload(droppedFiles);
    }
  };

  const handleHiddenInputChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    if (event.target.files) {
      const selectedFiles = Array.from(event.target.files);
      handleUpload(selectedFiles);
      // Allow selecting the same file repeatedly by resetting the value
      if (hiddenFileInputRef.current) {
        hiddenFileInputRef.current.value = "";
      }
    }
  };

  const handleUploadButtonClick = () => {
    if (!showFileUpload) {
      hiddenFileInputRef.current?.click();
    }
    setShowFileUpload((prev) => !prev);
  };

  return (
    <div
      data-testid="interactive-chat-box"
      className="flex flex-col gap-2 relative"
      onDragOver={handleContainerDragOver}
      onDragLeave={handleContainerDragLeave}
      onDrop={handleContainerDrop}
    >
      <input
        ref={hiddenFileInputRef}
        data-testid="upload-image-input"
        type="file"
        multiple
        className="hidden"
        onChange={handleHiddenInputChange}
      />
      {/* Drag-and-drop overlay (bolt.diy style) */}
      {isDraggingOverContainer && (
        <div className="absolute inset-0 z-50 bg-[#007acc]/10 border-2 border-dashed border-[#007acc] rounded flex items-center justify-center animate-fade-in">
          <div className="text-center space-y-2">
            <Upload className="h-12 w-12 text-[#007acc] mx-auto animate-bounce" />
            <p className="text-lg font-semibold text-[#cccccc]">
              {t("chat.dropFilesHere", "Drop files here")}
            </p>
            <p className="text-sm text-[#858585]">
              {t(
                "chat.releaseToUpload",
                "Release to upload images and documents",
              )}
            </p>
          </div>
        </div>
      )}

      {/* File Upload Area - Collapsible */}
      {showFileUpload && (
        <Card className="animate-slide-down bg-[var(--bg-input)] border border-[var(--border-primary)]">
          <CardContent className="p-3 sm:p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-text-primary">
                {t("chat.uploadFiles", "Upload Files")}
              </h3>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setShowFileUpload(false)}
                className="h-6 w-6 text-text-secondary hover:text-text-primary"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex-1">
                <UploadImageInput
                  onUpload={handleUpload}
                  inputTestId="upload-image-input-visible"
                />
              </div>

              <div className="flex items-center gap-2 text-xs text-text-foreground-secondary">
                <ImageIcon className="h-3 w-3" />
                <span>{t("chat.images", "Images")}</span>
                <FileText className="h-3 w-3 ml-2" />
                <span>{t("chat.documents", "Documents")}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Image Preview - Mobile Optimized */}
      {images.length > 0 && (
        <Card className="animate-slide-up bg-black border border-violet-500/20 shadow-lg shadow-violet-500/10">
          <CardContent className="p-2 sm:p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <ImageIcon className="h-3 w-3 text-text-secondary" />
                <Badge variant="outline" className="text-xs">
                  {t("Images ({{count}})", { count: images.length })}
                </Badge>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={clearImages}
                className="h-6 w-6 text-text-secondary hover:text-text-primary"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
            <ImageCarousel
              size="small"
              images={images.map((entry) => entry.previewUrl)}
              onRemove={handleRemoveImage}
            />
          </CardContent>
        </Card>
      )}

      {/* File List - Mobile Optimized */}
      {files.length > 0 && (
        <Card className="animate-slide-up bg-black border border-violet-500/20 shadow-lg shadow-violet-500/10">
          <CardContent className="p-2 sm:p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <FileText className="h-3 w-3 text-text-secondary" />
                <Badge variant="outline" className="text-xs">
                  {t("Files ({{count}})", { count: files.length })}
                </Badge>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setFiles([])}
                className="h-6 w-6 text-text-secondary hover:text-text-primary"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
            <FileList
              files={files.map((f) => f.name)}
              onRemove={handleRemoveFile}
            />
          </CardContent>
        </Card>
      )}

      {/* Enhanced Input Container - Auth Form Style */}
      <div className="group relative rounded-lg border border-[var(--border-primary)] bg-[var(--bg-input)] transition-all duration-200 focus-within:border-[var(--border-accent)] focus-within:ring-2 focus-within:ring-[rgba(139,92,246,0.2)]">
        <div className="flex items-end gap-2 p-2">
          {/* Upload Button - Inside Input */}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={handleUploadButtonClick}
            className={cn(
              "flex-shrink-0 h-8 w-8 rounded transition-all duration-200",
              "text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]",
              hasFiles && "text-[#8b5cf6] bg-[var(--bg-tertiary)]",
            )}
            title={hasFiles ? "Manage Files" : "Add Files"}
          >
            <Upload className="h-4 w-4" />
            {hasFiles && (
              <Badge
                variant="outline"
                className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed] text-white border-none"
              >
                {images.length + files.length}
              </Badge>
            )}
          </Button>

          {/* Enhanced Chat Input - Auth Form Style */}
          <div className="flex-1 min-w-0 flex items-end gap-2">
            <ChatInput
              disabled={isDisabled}
              button={mode}
              onChange={onChange}
              maxRows={4}
              onSubmit={handleSubmit}
              onStop={onStop}
              value={value}
              onFilesPaste={handleUpload}
              placeholder={placeholder}
              onEditLastMessage={onEditLastMessage}
              onFocus={onFocus}
              onBlur={onBlur}
              className="flex-1 min-w-0 text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] font-normal leading-relaxed text-sm bg-transparent border-0 shadow-none focus:ring-0 focus:border-0 resize-none"
              buttonClassName="flex-shrink-0"
            />
          </div>
        </div>
      </div>

      {/* File Preview Modal */}
      <FilePreviewModal
        files={pendingFiles}
        isOpen={showFilePreview}
        onConfirm={handleConfirmUpload}
        onCancel={handleCancelUpload}
      />
    </div>
  );
}
