import React from "react";
import { cn } from "#/utils/utils";

interface StreamingTypingIndicatorProps {
  isVisible?: boolean;
  message?: string;
  variant?: "dots" | "text" | "pulse";
  className?: string;
}

export function StreamingTypingIndicator({
  isVisible = true,
  message = "Thinking...",
  variant = "dots",
  className,
}: StreamingTypingIndicatorProps) {
  if (!isVisible) return null;

  const renderDots = () => (
    <div className="flex items-center gap-1">
      <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
      <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse delay-100" />
      <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse delay-200" />
    </div>
  );

  const renderText = () => (
    <div className="flex items-center gap-2">
      <span className="text-sm text-foreground-secondary">{message}</span>
      <div className="flex items-center gap-1">
        <div className="w-1 h-1 bg-foreground-secondary rounded-full animate-pulse" />
        <div className="w-1 h-1 bg-foreground-secondary rounded-full animate-pulse delay-100" />
        <div className="w-1 h-1 bg-foreground-secondary rounded-full animate-pulse delay-200" />
      </div>
    </div>
  );

  const renderPulse = () => (
    <div className="flex items-center gap-2">
      <div className="w-3 h-3 bg-brand-500 rounded-full animate-ping" />
      <span className="text-sm text-foreground-secondary">{message}</span>
    </div>
  );

  return (
    <div
      className={cn(
        "flex items-center justify-center p-4 rounded-xl bg-background-secondary border border-border",
        className,
      )}
    >
      {variant === "dots" && renderDots()}
      {variant === "text" && renderText()}
      {variant === "pulse" && renderPulse()}
    </div>
  );
}

interface StreamingProgressBarProps {
  progress: number; // 0-100
  label?: string;
  className?: string;
}

export function StreamingProgressBar({
  progress,
  label = "Processing...",
  className,
}: StreamingProgressBarProps) {
  return (
    <div
      className={cn(
        "w-full p-4 rounded-xl bg-background-secondary border border-border",
        className,
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-foreground">{label}</span>
        <span className="text-sm text-foreground-secondary">
          {Math.round(progress)}%
        </span>
      </div>
      <div className="w-full bg-background-tertiary rounded-full h-2 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-brand-500 to-accent-500 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
    </div>
  );
}

interface StreamingFileGenerationProps {
  fileName: string;
  progress: number;
  isComplete: boolean;
  className?: string;
}

export function StreamingFileGeneration({
  fileName,
  progress,
  isComplete,
  className,
}: StreamingFileGenerationProps) {
  return (
    <div
      className={cn(
        "w-full p-4 rounded-xl bg-background-secondary border border-border",
        className,
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-brand-500 rounded flex items-center justify-center">
            <span className="text-xs text-white">📄</span>
          </div>
          <span className="text-sm font-medium text-foreground">
            {fileName}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-foreground-secondary">
            {Math.round(progress)}%
          </span>
          {isComplete && (
            <div className="w-4 h-4 bg-success-500 rounded-full flex items-center justify-center">
              <span className="text-xs text-white">✓</span>
            </div>
          )}
        </div>
      </div>
      <div className="w-full bg-background-tertiary rounded-full h-2 overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-300 ease-out",
            isComplete
              ? "bg-gradient-to-r from-success-500 to-success-500/80"
              : "bg-gradient-to-r from-brand-500 to-accent-500",
          )}
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
    </div>
  );
}
