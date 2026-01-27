import React from "react";
import { useTranslation } from "react-i18next";
import { cn } from "#/utils/utils";
import { LoadingSpinner } from "../loading-spinner";
import { SkeletonLoader } from "./skeleton-loader";

interface LoadingStateProps {
  isLoading: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  skeleton?: boolean;
  skeletonVariant?: "text" | "rectangular" | "circular" | "rounded";
  skeletonLines?: number;
  className?: string;
  spinnerSize?: "xs" | "small" | "medium" | "large" | "xl";
  spinnerVariant?: "default" | "dots" | "pulse" | "bars";
  loadingText?: string;
  overlay?: boolean;
}

export function LoadingState({
  isLoading,
  children,
  fallback,
  skeleton = false,
  skeletonVariant = "rectangular",
  skeletonLines = 3,
  className,
  spinnerSize = "medium",
  spinnerVariant = "default",
  loadingText,
  overlay = false,
}: LoadingStateProps) {
  if (!isLoading) {
    return children;
  }

  if (fallback) {
    return fallback;
  }

  if (skeleton) {
    return (
      <div className={cn("space-y-2", className)}>
        <SkeletonLoader
          variant={skeletonVariant}
          lines={skeletonLines}
          className="w-full"
        />
      </div>
    );
  }

  const loadingContent = (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 p-8",
        className,
      )}
    >
      <LoadingSpinner size={spinnerSize} variant={spinnerVariant} />
      {loadingText && (
        <p
          className="text-sm text-[var(--text-tertiary)] animate-pulse"
          style={{ wordBreak: "normal", whiteSpace: "normal" }}
        >
          {loadingText}
        </p>
      )}
    </div>
  );

  if (overlay) {
    return (
      <div className="relative">
        {children}
        <div className="absolute inset-0 bg-[var(--bg-primary)]/90 flex items-center justify-center z-10">
          {loadingContent}
        </div>
      </div>
    );
  }

  return loadingContent;
}

// Specialized loading components for common use cases
export function LoadingButton({
  isLoading,
  children,
  loadingText,
  disabled,
  className,
  type = "button",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  isLoading: boolean;
  loadingText?: string;
}) {
  const { t } = useTranslation();
  const defaultLoadingText = loadingText || t("common.loading", "Loading...");
  let buttonType: "button" | "submit" | "reset" = "button";
  if (type === "submit") {
    buttonType = "submit";
  } else if (type === "reset") {
    buttonType = "reset";
  }
  return (
    <button
      // eslint-disable-next-line react/button-has-type
      type={buttonType}
      // eslint-disable-next-line react/jsx-props-no-spreading
      {...props}
      disabled={disabled || isLoading}
      className={cn(
        "relative flex items-center justify-center gap-2",
        "px-4 py-2 rounded-xl font-medium transition-all duration-200",
        "bg-primary-500 hover:bg-primary-600 text-white",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        className,
      )}
    >
      {isLoading && <LoadingSpinner size="small" variant="default" />}
      <span className={cn(isLoading && "opacity-0")}>
        {isLoading ? defaultLoadingText : children}
      </span>
    </button>
  );
}

export function LoadingCard({
  isLoading,
  children,
  className,
  skeletonLines = 4,
}: {
  isLoading: boolean;
  children: React.ReactNode;
  className?: string;
  skeletonLines?: number;
}) {
  return (
    <LoadingState
      isLoading={isLoading}
      skeleton
      skeletonVariant="rectangular"
      skeletonLines={skeletonLines}
      className={cn(
        "p-4 bg-[var(--bg-elevated)] rounded border border-[var(--border-primary)]",
        className,
      )}
    >
      {children}
    </LoadingState>
  );
}

export function LoadingTable({
  isLoading,
  children,
  rows = 5,
  className,
}: {
  isLoading: boolean;
  children: React.ReactNode;
  rows?: number;
  className?: string;
}) {
  return (
    <LoadingState
      isLoading={isLoading}
      skeleton
      skeletonVariant="text"
      skeletonLines={rows + 1} // +1 for header
      className={className}
    >
      {children}
    </LoadingState>
  );
}

export function LoadingOverlay({
  isLoading,
  children,
  loadingText,
  className,
}: {
  isLoading: boolean;
  children: React.ReactNode;
  loadingText?: string;
  className?: string;
}) {
  return (
    <LoadingState
      isLoading={isLoading}
      overlay
      loadingText={loadingText}
      className={className}
    >
      {children}
    </LoadingState>
  );
}
