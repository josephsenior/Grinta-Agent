import React, { useState, useRef, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Send, Paperclip, X, Loader2, Sparkles, Lightbulb, Rocket, Palette, BarChart3 } from "lucide-react";
import { I18nKey } from "#/i18n/declaration";
import { cn } from "#/utils/utils";
import { Button } from "#/components/ui/button";
import { Card, CardContent } from "#/components/ui/card";

interface ModernChatInputProps {
  name?: string;
  button?: "submit" | "stop";
  disabled?: boolean;
  showButton?: boolean;
  value?: string;
  maxRows?: number;
  onSubmit: (message: string) => void;
  onStop?: () => void;
  onChange?: (message: string) => void;
  onFocus?: () => void;
  onBlur?: () => void;
  onFilesPaste?: (files: File[]) => void;
  className?: React.HTMLAttributes<HTMLDivElement>["className"];
  buttonClassName?: React.HTMLAttributes<HTMLButtonElement>["className"];
  // Enhanced props for modern styling
  isTyping?: boolean;
  placeholder?: string;
  showQuickActions?: boolean;
  onQuickAction?: (action: string) => void;
}

// Auto-resize textarea hook
function useAutoResizeTextarea({
  minHeight,
  maxHeight,
}: {
  minHeight: number;
  maxHeight?: number;
}) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const adjustHeight = useCallback(
    (reset?: boolean) => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      if (reset) {
        textarea.style.height = `${minHeight}px`;
        return;
      }

      textarea.style.height = `${minHeight}px`; // reset first
      const newHeight = Math.max(
        minHeight,
        Math.min(textarea.scrollHeight, maxHeight ?? Infinity),
      );
      textarea.style.height = `${newHeight}px`;
    },
    [minHeight, maxHeight],
  );

  useEffect(() => {
    if (textareaRef.current)
      textareaRef.current.style.height = `${minHeight}px`;
  }, [minHeight]);

  return { textareaRef, adjustHeight };
}

const QUICK_ACTIONS = [
  { icon: Lightbulb, label: "Generate Code", action: "generate code" },
  { icon: Rocket, label: "Launch App", action: "launch app" },
  { icon: Palette, label: "UI Components", action: "ui components" },
  { icon: BarChart3, label: "Analytics", action: "analytics" },
] as const;

const getFilesFromTransfer = (items: FileList | null) => (items ? Array.from(items) : []);

const useDragAndDrop = (
  onFilesPaste?: (files: File[]) => void,
): {
  isDraggingOver: boolean;
  handleDragOver: (event: React.DragEvent<HTMLTextAreaElement>) => void;
  handleDragLeave: (event: React.DragEvent<HTMLTextAreaElement>) => void;
  handleDrop: (event: React.DragEvent<HTMLTextAreaElement>) => void;
} => {
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  const handleDragOver = useCallback(
    (event: React.DragEvent<HTMLTextAreaElement>) => {
      event.preventDefault();
      if (event.dataTransfer.types.includes("Files")) {
        setIsDraggingOver(true);
      }
    },
    [],
  );

  const handleDragLeave = useCallback((event: React.DragEvent<HTMLTextAreaElement>) => {
    event.preventDefault();
    setIsDraggingOver(false);
  }, []);

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLTextAreaElement>) => {
      event.preventDefault();
      setIsDraggingOver(false);

      if (!onFilesPaste) {
        return;
      }

      const files = getFilesFromTransfer(event.dataTransfer.files);

      if (files.length > 0) {
        onFilesPaste(files);
      }
    },
    [onFilesPaste],
  );

  return { isDraggingOver, handleDragOver, handleDragLeave, handleDrop };
};

const useMessageHandlers = ({
  disabled,
  onSubmit,
  onChange,
  textareaRef,
  adjustHeight,
}: {
  disabled?: boolean;
  onSubmit: (message: string) => void;
  onChange?: (message: string) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  adjustHeight: (reset?: boolean) => void;
}) => {
  const submitMessage = useCallback(() => {
    const messageValue = textareaRef.current?.value ?? "";
    const message = messageValue.trim();

    if (!message || disabled) {
      return;
    }

    onSubmit(message);

    if (textareaRef.current) {
      textareaRef.current.value = "";
      adjustHeight(true);
    }

    onChange?.("");
  }, [adjustHeight, disabled, onChange, onSubmit, textareaRef]);

  return {
    submitMessage,
    handleEnterPress: useCallback(
      (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (
          event.key === "Enter" &&
          !event.shiftKey &&
          !disabled &&
          !event.nativeEvent.isComposing
        ) {
          event.preventDefault();
          submitMessage();
        }
      },
      [disabled, submitMessage],
    ),
  };
};

const useExternalValueSync = ({
  value,
  inputValue,
  setInputValue,
  textareaRef,
  adjustHeight,
}: {
  value: string | undefined;
  inputValue: string;
  setInputValue: React.Dispatch<React.SetStateAction<string>>;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  adjustHeight: (reset?: boolean) => void;
}) => {
  useEffect(() => {
    if (typeof value !== "string" || value === inputValue) {
      return;
    }

    setInputValue(value);

    if (textareaRef.current) {
      textareaRef.current.value = value;
      adjustHeight();
    }
  }, [adjustHeight, inputValue, setInputValue, textareaRef, value]);
};

const useClipboardPaste = (onFilesPaste?: (files: File[]) => void) =>
  useCallback(
    (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
      if (!onFilesPaste) {
        return;
      }

      const files = getFilesFromTransfer(event.clipboardData.files);

      if (files.length === 0) {
        return;
      }

      event.preventDefault();
      onFilesPaste(files);
    },
    [onFilesPaste],
  );

const useQuickActionHandler = ({
  onQuickAction,
  setInputValue,
  onChange,
}: {
  onQuickAction?: (action: string) => void;
  setInputValue: React.Dispatch<React.SetStateAction<string>>;
  onChange?: (message: string) => void;
}) =>
  useCallback(
    (action: string) => {
      if (onQuickAction) {
        onQuickAction(action);
        return;
      }

      setInputValue(action);
      onChange?.(action);
    },
    [onChange, onQuickAction, setInputValue],
  );

export function ModernChatInput({
  name,
  button = "submit",
  disabled,
  showButton = true,
  value,
  maxRows = 8,
  onSubmit,
  onStop,
  onChange,
  onFocus,
  onBlur,
  onFilesPaste,
  className,
  buttonClassName,
  isTyping = false,
  placeholder,
  showQuickActions = false,
  onQuickAction,
}: ModernChatInputProps) {
  const { t } = useTranslation();
  const [isFocused, setIsFocused] = useState(false);
  const [inputValue, setInputValue] = useState(value || "");

  const computedMaxHeight = Math.max(1, maxRows) * 24;

  const { textareaRef, adjustHeight } = useAutoResizeTextarea({
    minHeight: 48,
    maxHeight: computedMaxHeight,
  });

  const { isDraggingOver, handleDragOver, handleDragLeave, handleDrop } = useDragAndDrop(
    onFilesPaste,
  );
  const { submitMessage, handleEnterPress } = useMessageHandlers({
    disabled,
    onSubmit: message => {
      onSubmit(message);
      setInputValue("");
    },
    onChange,
    textareaRef,
    adjustHeight,
  });
  useExternalValueSync({ value, inputValue, setInputValue, textareaRef, adjustHeight });

  const handlePaste = useClipboardPaste(onFilesPaste);

  const handleChange = useCallback(
    (event: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = event.target.value;

      setInputValue(newValue);
      onChange?.(newValue);
      adjustHeight();
    },
    [adjustHeight, onChange],
  );

  const handleFocus = useCallback(() => {
    setIsFocused(true);
    onFocus?.();
  }, [onFocus]);

  const handleBlur = useCallback(() => {
    setIsFocused(false);
    onBlur?.();
  }, [onBlur]);

  const handleQuickAction = useQuickActionHandler({
    onQuickAction,
    setInputValue,
    onChange,
  });

  const actionButton = renderActionButton({
    showButton,
    mode: button,
    disabled,
    inputValue,
    submitMessage,
    onStop,
    buttonClassName,
    isTyping,
  });

  return (
    <div className={cn("w-full space-y-4", className)}>
      {showQuickActions && (
        <QuickActions quickActions={QUICK_ACTIONS} onAction={handleQuickAction} />
      )}

      <Card
        className={cn(
          "group relative overflow-hidden transition-all duration-300",
          "bg-background-glass backdrop-blur-xl border-0",
          "shadow-2xl shadow-primary-500/10",
          isFocused && "shadow-primary-500/20",
          isDraggingOver && "shadow-primary-500/30",
        )}
      >
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
          <div className="absolute inset-0 bg-gradient-to-r from-primary-500/5 via-transparent to-accent-pink/5" />
        </div>

        <CardContent className="relative p-4">
          <div className="flex items-end gap-3">
            <AttachmentButton />

            <div className="flex-1 min-w-0">
              <MessageTextarea
                textareaRef={textareaRef}
                name={name}
                placeholder={placeholder ?? t(I18nKey.SUGGESTIONS$WHAT_TO_BUILD)}
                value={inputValue}
                onChange={handleChange}
                onKeyDown={handleEnterPress}
                onFocus={handleFocus}
                onBlur={handleBlur}
                onPaste={handlePaste}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                disabled={disabled}
                isDraggingOver={isDraggingOver}
                maxHeight={computedMaxHeight}
                isTyping={isTyping}
              />
            </div>

            {actionButton}
          </div>

          <DragOverlay isVisible={isDraggingOver} />
        </CardContent>
      </Card>
    </div>
  );
}

type QuickAction = {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  action: string;
};

const QuickActions = ({
  quickActions,
  onAction,
}: {
  quickActions: readonly QuickAction[];
  onAction: (action: string) => void;
}) => (
  <div className="flex items-center justify-center flex-wrap gap-2">
    {quickActions.map(quickAction => {
      const IconComponent = quickAction.icon;
      return (
        <Button
          key={quickAction.action}
          variant="outline"
          size="sm"
          onClick={() => onAction(quickAction.action)}
          className="flex items-center gap-2 rounded-full border-border-glass bg-background-glass/50 text-text-secondary hover:text-text-primary hover:bg-primary-500/10 hover:border-primary-500/40 transition-all duration-200 backdrop-blur-sm"
        >
          <IconComponent className="w-4 h-4" />
          <span className="text-xs font-medium">{quickAction.label}</span>
        </Button>
      );
    })}
  </div>
);

const AttachmentButton = () => (
  <div className="flex-shrink-0">
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="h-10 w-10 rounded-full bg-background-glass/50 hover:bg-primary-500/10 text-text-foreground-secondary hover:text-primary-500 transition-all duration-200 backdrop-blur-sm"
    >
      <Paperclip className="h-4 w-4" />
    </Button>
  </div>
);

const MessageTextarea = ({
  textareaRef,
  name,
  placeholder,
  value,
  onChange,
  onKeyDown,
  onFocus,
  onBlur,
  onPaste,
  onDrop,
  onDragOver,
  onDragLeave,
  disabled,
  isDraggingOver,
  maxHeight,
  isTyping,
}: {
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  name?: string;
  placeholder: string;
  value: string;
  onChange: (event: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onKeyDown: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onFocus: () => void;
  onBlur: () => void;
  onPaste: (event: React.ClipboardEvent<HTMLTextAreaElement>) => void;
  onDrop: (event: React.DragEvent<HTMLTextAreaElement>) => void;
  onDragOver: (event: React.DragEvent<HTMLTextAreaElement>) => void;
  onDragLeave: (event: React.DragEvent<HTMLTextAreaElement>) => void;
  disabled?: boolean;
  isDraggingOver: boolean;
  maxHeight: number;
  isTyping: boolean;
}) => (
  <div className="relative">
    <textarea
      ref={textareaRef}
      name={name}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      onKeyDown={onKeyDown}
      onFocus={onFocus}
      onBlur={onBlur}
      onPaste={onPaste}
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      disabled={disabled}
      data-dragging-over={isDraggingOver}
      className={cn(
        "w-full resize-none outline-none ring-0 transition-all duration-300",
        "bg-transparent text-text-primary placeholder:text-text-foreground-secondary",
        "font-medium leading-relaxed text-sm",
        "focus:placeholder:text-text-secondary",
        isDraggingOver && [
          "bg-gradient-to-br from-primary-500/20 to-primary-600/10",
          "border border-primary-500/40 rounded-xl px-4 py-3",
          "shadow-[0_0_20px_rgba(189,147,249,0.3)]",
        ],
        "scrollbar-thin scrollbar-track-transparent scrollbar-thumb-primary-500/20",
      )}
      style={{
        minHeight: "48px",
        maxHeight: `${maxHeight}px`,
        overflow: "hidden",
      }}
    />

    {isTyping && <TypingIndicator />}
  </div>
);

const TypingIndicator = () => (
  <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
    <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse" />
    <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse delay-75" />
    <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse delay-150" />
  </div>
);

const DragOverlay = ({ isVisible }: { isVisible: boolean }) => {
  if (!isVisible) {
    return null;
  }

  return (
    <div className="absolute inset-0 flex items-center justify-center bg-primary-500/10 backdrop-blur-sm rounded-xl">
      <div className="flex items-center gap-2 text-primary-500 font-medium">
        <Sparkles className="h-5 w-5" />
        <span>Drop files here</span>
      </div>
    </div>
  );
};

const renderActionButton = ({
  showButton,
  mode,
  disabled,
  inputValue,
  submitMessage,
  onStop,
  buttonClassName,
  isTyping,
}: {
  showButton: boolean;
  mode: ModernChatInputProps["button"];
  disabled?: boolean;
  inputValue: string;
  submitMessage: () => void;
  onStop?: () => void;
  buttonClassName?: string;
  isTyping: boolean;
}) => {
  if (!showButton) {
    return null;
  }

  if (mode === "stop") {
    return (
      <div className={cn("flex-shrink-0", buttonClassName)}>
        <Button
          type="button"
          onClick={onStop}
          disabled={disabled}
          className={cn(
            "h-10 w-10 rounded-full transition-all duration-200",
            "bg-gradient-to-r from-danger-500 to-danger-600",
            "hover:from-danger-400 hover:to-danger-500",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "shadow-lg shadow-danger-500/25 hover:shadow-danger-500/40",
            "hover:scale-105 active:scale-95",
          )}
        >
          <X className="h-4 w-4 text-white" />
        </Button>
      </div>
    );
  }

  return (
    <div className={cn("flex-shrink-0", buttonClassName)}>
      <Button
        type="button"
        onClick={submitMessage}
        disabled={disabled || !inputValue.trim()}
        className={cn(
          "chat-button-primary",
          "h-10 w-10 rounded-full transition-all duration-200",
          "bg-gradient-to-r from-brand-500 to-brand-600",
          "hover:from-brand-400 hover:to-brand-500",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40",
          "hover:scale-105 active:scale-95",
        )}
      >
        {isTyping ? (
          <Loader2 className="h-4 w-4 animate-spin text-white" />
        ) : (
          <Send className="h-4 w-4 text-white" />
        )}
      </Button>
    </div>
  );
};
