import React from "react";
import TextareaAutosize from "react-textarea-autosize";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { cn } from "#/utils/utils";
import { SubmitButton } from "#/components/shared/buttons/submit-button";
import { StopButton } from "#/components/shared/buttons/stop-button";

interface ChatInputProps {
  name?: string;
  button?: "submit" | "stop";
  disabled?: boolean;
  showButton?: boolean;
  value?: string;
  maxRows?: number;
  placeholder?: string;
  onSubmit: (message: string) => void;
  onStop?: () => void;
  onChange?: (message: string) => void;
  onFocus?: () => void;
  onBlur?: () => void;
  onFilesPaste?: (files: File[]) => void;
  onEditLastMessage?: () => string | null; // Returns last user message for editing
  className?: React.HTMLAttributes<HTMLDivElement>["className"];
  buttonClassName?: React.HTMLAttributes<HTMLButtonElement>["className"];
}

export function ChatInput({
  name,
  button = "submit",
  disabled,
  showButton = true,
  value,
  maxRows = 10, // Increased from 8 to 10 for bolt.diy comfort
  onSubmit,
  onStop,
  onChange,
  onFocus,
  onBlur,
  onFilesPaste,
  placeholder,
  onEditLastMessage,
  className,
  buttonClassName,
}: ChatInputProps) {
  const { t } = useTranslation();
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);
  const [isDraggingOver, setIsDraggingOver] = React.useState(false);

  const handlePaste = (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
    // Only handle paste if we have an image paste handler and there are files
    if (onFilesPaste && event.clipboardData.files.length > 0) {
      const files = Array.from(event.clipboardData.files);
      // Only prevent default if we found image files to handle
      event.preventDefault();
      onFilesPaste(files);
    }
    // For text paste, let the default behavior handle it
  };

  const handleDragOver = (event: React.DragEvent<HTMLTextAreaElement>) => {
    event.preventDefault();
    if (event.dataTransfer.types.includes("Files")) {
      setIsDraggingOver(true);
    }
  };

  const handleDragLeave = (event: React.DragEvent<HTMLTextAreaElement>) => {
    event.preventDefault();
    setIsDraggingOver(false);
  };

  const handleDrop = (event: React.DragEvent<HTMLTextAreaElement>) => {
    event.preventDefault();
    setIsDraggingOver(false);
    if (onFilesPaste && event.dataTransfer.files.length > 0) {
      const files = Array.from(event.dataTransfer.files);
      if (files.length > 0) {
        onFilesPaste(files);
      }
    }
  };

  const handleSubmitMessage = () => {
    const message = value || textareaRef.current?.value || "";
    if (message.trim()) {
      onSubmit(message);
      onChange?.("");
      if (textareaRef.current) {
        textareaRef.current.value = "";
      }
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Quick edit last message with ↑ key (Slack/Discord/Telegram UX pattern)
    if (
      event.key === "ArrowUp" &&
      !event.shiftKey &&
      !value &&
      onEditLastMessage
    ) {
      event.preventDefault();
      const lastMessage = onEditLastMessage();
      if (lastMessage) {
        onChange?.(lastMessage);
        // Focus at end of text
        setTimeout(() => {
          if (textareaRef.current) {
            const { length } = lastMessage;
            textareaRef.current.setSelectionRange(length, length);
          }
        }, 0);
      }
      return;
    }

    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !disabled &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      handleSubmitMessage();
    }
  };

  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange?.(event.target.value);
  };

  const handleFocus = () => {
    onFocus?.();
  };

  const handleBlur = () => {
    onBlur?.();
  };

  return (
    <div data-testid="chat-input" className="flex items-end gap-2 w-full">
      <TextareaAutosize
        ref={textareaRef}
        name={name}
        placeholder={placeholder ?? t(I18nKey.SUGGESTIONS$WHAT_TO_BUILD)}
        onKeyDown={handleKeyPress}
        onChange={handleChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onPaste={handlePaste}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        value={value}
        minRows={1}
        maxRows={maxRows}
        data-dragging-over={isDraggingOver}
        className={cn(
          "flex-1 min-w-0 text-sm resize-none outline-none ring-0",
          "px-2 py-2",
          "bg-transparent",
          "text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]",
          "transition-all duration-200",
          "focus:outline-none",
          isDraggingOver && [
            "bg-gradient-to-br from-primary-500/20 to-primary-600/10",
          ],
          className,
        )}
      />
      {showButton && (
        <div className={buttonClassName}>
          {button === "submit" && (
            <SubmitButton isDisabled={disabled} onClick={handleSubmitMessage} />
          )}
          {button === "stop" && (
            <StopButton isDisabled={disabled} onClick={onStop} />
          )}
        </div>
      )}
    </div>
  );
}
