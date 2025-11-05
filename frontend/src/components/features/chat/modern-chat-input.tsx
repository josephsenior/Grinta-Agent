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
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const [inputValue, setInputValue] = useState(value || "");

  const { textareaRef, adjustHeight } = useAutoResizeTextarea({
    minHeight: 48,
    maxHeight: 150,
  });

  // Quick action suggestions
  const quickActions = [
    { icon: Lightbulb, label: "Generate Code", action: "generate code" },
    { icon: Rocket, label: "Launch App", action: "launch app" },
    { icon: Palette, label: "UI Components", action: "ui components" },
    { icon: BarChart3, label: "Analytics", action: "analytics" },
  ];

  const handlePaste = (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
    if (onFilesPaste && event.clipboardData.files.length > 0) {
      const files = Array.from(event.clipboardData.files);
      event.preventDefault();
      onFilesPaste(files);
    }
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
    const message = inputValue.trim();
    if (message && !disabled) {
      onSubmit(message);
      setInputValue("");
      onChange?.("");
      if (textareaRef.current) {
        textareaRef.current.value = "";
        adjustHeight(true);
      }
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
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
    const newValue = event.target.value;
    setInputValue(newValue);
    onChange?.(newValue);
    adjustHeight();
  };

  const handleFocus = () => {
    setIsFocused(true);
    onFocus?.();
  };

  const handleBlur = () => {
    setIsFocused(false);
    onBlur?.();
  };

  const handleQuickAction = (action: string) => {
    if (onQuickAction) {
      onQuickAction(action);
    } else {
      setInputValue(action);
      onChange?.(action);
    }
  };

  return (
    <div className={cn("w-full space-y-4", className)}>
      {/* Quick Actions */}
      {showQuickActions && (
        <div className="flex items-center justify-center flex-wrap gap-2">
          {quickActions.map((action, index) => {
            const IconComponent = action.icon;
            return (
              <Button
                key={index}
                variant="outline"
                size="sm"
                onClick={() => handleQuickAction(action.action)}
                className="flex items-center gap-2 rounded-full border-border-glass bg-background-glass/50 text-text-secondary hover:text-text-primary hover:bg-primary-500/10 hover:border-primary-500/40 transition-all duration-200 backdrop-blur-sm"
              >
                <IconComponent className="w-4 h-4" />
                <span className="text-xs font-medium">{action.label}</span>
              </Button>
            );
          })}
        </div>
      )}

      {/* Main Input Container */}
      <Card
        className={cn(
          "group relative overflow-hidden transition-all duration-300",
          "bg-background-glass backdrop-blur-xl border-0",
          "shadow-2xl shadow-primary-500/10",
          isFocused && "shadow-primary-500/20",
          isDraggingOver && "shadow-primary-500/30",
        )}
      >
        {/* Animated Background Gradient */}
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
          <div className="absolute inset-0 bg-gradient-to-r from-primary-500/5 via-transparent to-accent-pink/5" />
        </div>

        <CardContent className="relative p-4">
          <div className="flex items-end gap-3">
            {/* Upload Button */}
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

            {/* Textarea Container */}
            <div className="flex-1 min-w-0">
              <div className="relative">
                <textarea
                  ref={textareaRef}
                  name={name}
                  placeholder={
                    placeholder || t(I18nKey.SUGGESTIONS$WHAT_TO_BUILD)
                  }
                  value={inputValue}
                  onChange={handleChange}
                  onKeyDown={handleKeyPress}
                  onFocus={handleFocus}
                  onBlur={handleBlur}
                  onPaste={handlePaste}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
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
                    maxHeight: "150px",
                    overflow: "hidden",
                  }}
                />

                {/* Typing Indicator */}
                {isTyping && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse" />
                    <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse delay-75" />
                    <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse delay-150" />
                  </div>
                )}
              </div>
            </div>

            {/* Submit Button */}
            {showButton && (
              <div className={cn("flex-shrink-0", buttonClassName)}>
                {button === "submit" && (
                  <Button
                    type="button"
                    onClick={handleSubmitMessage}
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
                )}
                {button === "stop" && (
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
                )}
              </div>
            )}
          </div>

          {/* Drag Overlay */}
          {isDraggingOver && (
            <div className="absolute inset-0 flex items-center justify-center bg-primary-500/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-2 text-primary-500 font-medium">
                <Sparkles className="h-5 w-5" />
                <span>Drop files here</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
