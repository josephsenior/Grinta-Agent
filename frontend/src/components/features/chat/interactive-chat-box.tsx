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
import { AutonomyModeSelector } from "../controls/autonomy-mode-selector";
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
  // Optional MetaSOP toggle support
  sopEnabled?: boolean;
  onToggleSop?: (enabled: boolean) => void;
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
  sopEnabled,
  onToggleSop,
  onEditLastMessage,
}: InteractiveChatBoxProps) {
  const { t } = useTranslation();
  const { currentMode, handleModeChange } = useAutonomyMode();
  const [images, setImages] = React.useState<File[]>([]);
  const [files, setFiles] = React.useState<File[]>([]);
  const [showFileUpload, setShowFileUpload] = React.useState(false);
  const [pendingFiles, setPendingFiles] = React.useState<File[]>([]);
  const [showFilePreview, setShowFilePreview] = React.useState(false);
  const [isDraggingOverContainer, setIsDraggingOverContainer] = React.useState(false); // For drag-drop overlay
  const hiddenFileInputRef = React.useRef<HTMLInputElement | null>(null);

  // Helper to safely extract HTTP status from various error shapes.
  const extractResponseStatus = (err: unknown): number | undefined => {
    if (!err || typeof err !== "object") {
      return undefined;
    }

    const errObj = err as Record<string, unknown>;
    const resp = errObj.response;
    if (!resp || typeof resp !== "object") {
      return undefined;
    }

    const st = (resp as Record<string, unknown>).status;
    return typeof st === "number" ? st : undefined;
  };

  const handleUpload = (selectedFiles: File[]) => {
    // Validate files before adding them
    const validation = validateFiles(selectedFiles, [...images, ...files]);

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
    setImages((prevImages) => [...prevImages, ...validImages]);
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
    setImages(removeElementByIndex(images, index));
  };

  const handleSubmit = (message: string) => {
    onSubmit(message, images, files);
    setFiles([]);
    setImages([]);
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

  const handleHiddenInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const selectedFiles = Array.from(event.target.files);
      handleUpload(selectedFiles);
      // Allow selecting the same file repeatedly by resetting the value
      event.target.value = "";
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
        <div className="absolute inset-0 z-50 bg-violet-500/10 backdrop-blur-sm border-2 border-dashed border-violet-500 rounded-xl flex items-center justify-center animate-fade-in">
          <div className="text-center space-y-2">
            <Upload className="h-12 w-12 text-violet-500 mx-auto animate-bounce" />
            <p className="text-lg font-semibold text-text-primary">
              Drop files here
            </p>
            <p className="text-sm text-text-secondary">
              Release to upload images and documents
            </p>
          </div>
        </div>
      )}
      
      {/* File Upload Area - Collapsible */}
      {showFileUpload && (
        <Card className="animate-slide-down bg-black border border-violet-500/20 shadow-lg shadow-violet-500/10">
          <CardContent className="p-3 sm:p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-text-primary">
                Upload Files
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
                <span>Images</span>
                <FileText className="h-3 w-3 ml-2" />
                <span>Documents</span>
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
                onClick={() => setImages([])}
                className="h-6 w-6 text-text-secondary hover:text-text-primary"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
            <ImageCarousel
              size="small"
              images={images.map((image) => URL.createObjectURL(image))}
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

      {/* Enhanced Input Container - Mobile Optimized */}
      <Card className="group bg-black border-0 shadow-lg shadow-violet-500/10 transition-all duration-300 [&]:focus-visible:outline-none [&]:focus-within:outline-none [&_*]:focus-visible:outline-none">
        <CardContent
          className={cn("flex items-end gap-2 sm:gap-3 p-0")}
        >
          {/* Upload Button - Inside Input */}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={handleUploadButtonClick}
            className={cn(
              "flex-shrink-0 h-10 w-10 rounded-full transition-all duration-200",
              "text-violet-400 hover:text-violet-300 hover:bg-violet-500/10",
              hasFiles && "text-violet-500 bg-violet-500/10"
            )}
            title={hasFiles ? "Manage Files" : "Add Files"}
          >
            <Upload className="h-4 w-4" />
            {hasFiles && (
              <Badge 
                variant="outline" 
                className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs bg-violet-500 text-white border-none"
              >
                {images.length + files.length}
              </Badge>
            )}
          </Button>

          {/* Enhanced Chat Input - Mobile Optimized */}
          <div className="flex-1 min-w-0">
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
              className="py-1.5 sm:py-2 px-2 sm:px-3 text-foreground placeholder:text-foreground-secondary/50 font-medium leading-relaxed text-sm sm:text-base min-h-[40px] sm:min-h-[44px]"
              buttonClassName="py-1.5 sm:py-2 transition-all duration-200 hover:scale-105 min-h-[40px] sm:min-h-[44px]"
            />
          </div>
        </CardContent>
      </Card>

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
