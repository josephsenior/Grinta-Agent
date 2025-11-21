import React from "react";
import { cn } from "#/utils/utils";

interface SkeletonLoaderProps {
  variant?: "text" | "circular" | "rectangular" | "message" | "card";
  width?: string | number;
  height?: string | number;
  count?: number;
  className?: string;
  animated?: boolean;
}

/**
 * Enhanced Skeleton Loader with multiple variants
 * Provides better loading states than simple spinners
 */
function Skeleton({
  baseClasses,
  variantClasses,
  variant,
  width,
  height,
  className,
}: {
  baseClasses: string;
  variantClasses: Record<string, string>;
  variant: SkeletonLoaderProps["variant"];
  width?: string | number;
  height?: string | number;
  className?: string;
}) {
  return (
    <div
      className={cn(baseClasses, variantClasses[variant || "text"], className)}
      style={{
        width: width || (variant === "circular" ? height : "100%"),
        height: height || undefined,
      }}
    />
  );
}

export function EnhancedSkeletonLoader({
  variant = "text",
  width,
  height,
  count = 1,
  className,
  animated = true,
}: SkeletonLoaderProps) {
  const baseClasses = cn(
    "bg-gradient-to-r from-background-tertiary via-background-elevated to-background-tertiary",
    "bg-[length:200%_100%]",
    animated && "animate-shimmer",
  );

  const variantClasses = {
    text: "h-4 rounded",
    circular: "rounded-full",
    rectangular: "rounded-lg",
    message: "h-20 rounded-xl",
    card: "h-48 rounded-2xl",
  };

  if (count === 1) {
    return (
      <Skeleton
        baseClasses={baseClasses}
        variantClasses={variantClasses}
        variant={variant}
        width={width}
        height={height}
        className={className}
      />
    );
  }

  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, index) => (
        <Skeleton
          key={index}
          baseClasses={baseClasses}
          variantClasses={variantClasses}
          variant={variant}
          width={width}
          height={height}
          className={className}
        />
      ))}
    </div>
  );
}

/**
 * Chat Message Skeleton - Mimics actual chat message layout
 */
export function ChatMessageSkeleton({ isUser = false }: { isUser?: boolean }) {
  return (
    <div
      className={cn(
        "w-full flex items-start gap-3",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      {/* Avatar */}
      {!isUser && (
        <EnhancedSkeletonLoader variant="circular" width={32} height={32} />
      )}

      {/* Message Content */}
      <div
        className={cn(
          "flex flex-col gap-2",
          isUser ? "items-end" : "items-start",
          "max-w-[85%]",
        )}
      >
        <EnhancedSkeletonLoader width={isUser ? 200 : 250} height={16} />
        <EnhancedSkeletonLoader width={isUser ? 150 : 300} height={16} />
        <EnhancedSkeletonLoader width={isUser ? 180 : 200} height={16} />
      </div>

      {/* Avatar */}
      {isUser && (
        <EnhancedSkeletonLoader variant="circular" width={32} height={32} />
      )}
    </div>
  );
}

/**
 * Card Skeleton - For dashboard cards, knowledge base cards, etc.
 */
export function CardSkeleton() {
  return (
    <div className="p-6 border border-border rounded-xl bg-background-tertiary/50">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <EnhancedSkeletonLoader width={120} height={24} />
          <EnhancedSkeletonLoader variant="circular" width={24} height={24} />
        </div>

        {/* Content */}
        <div className="space-y-2">
          <EnhancedSkeletonLoader height={16} />
          <EnhancedSkeletonLoader width="80%" height={16} />
        </div>

        {/* Footer */}
        <div className="flex items-center gap-2 pt-2">
          <EnhancedSkeletonLoader width={80} height={32} />
          <EnhancedSkeletonLoader width={80} height={32} />
        </div>
      </div>
    </div>
  );
}

/**
 * List Skeleton - For file lists, conversation lists, etc.
 */
export function ListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="flex items-center gap-3 p-3 rounded-lg bg-background-tertiary/30"
        >
          <EnhancedSkeletonLoader variant="circular" width={40} height={40} />
          <div className="flex-1 space-y-2">
            <EnhancedSkeletonLoader width="60%" height={16} />
            <EnhancedSkeletonLoader width="40%" height={12} />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Terminal Skeleton - For terminal output loading
 */
export function TerminalSkeleton() {
  return (
    <div className="p-4 rounded-lg border border-border bg-background-tertiary/50 font-mono">
      <div className="space-y-1.5">
        <EnhancedSkeletonLoader width="30%" height={12} />
        <EnhancedSkeletonLoader width="80%" height={12} />
        <EnhancedSkeletonLoader width="60%" height={12} />
        <EnhancedSkeletonLoader width="90%" height={12} />
        <EnhancedSkeletonLoader width="40%" height={12} />
      </div>
    </div>
  );
}

// Add shimmer animation to Tailwind
// This should be added to tailwind.config.js:
/*
animation: {
  shimmer: "shimmer 2s linear infinite",
},
keyframes: {
  shimmer: {
    "0%": { backgroundPosition: "-200% 0" },
    "100%": { backgroundPosition: "200% 0" },
  },
},
*/
