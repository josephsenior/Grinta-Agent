import React from "react";
import { cn } from "#/utils/utils";

interface MessageSkeletonProps {
  count?: number;
  className?: string;
}

export function MessageSkeleton({
  count = 3,
  className,
}: MessageSkeletonProps) {
  return (
    <div className={cn("space-y-4 sm:space-y-6", className)}>
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="flex gap-3 sm:gap-4"
          style={{
            animationDelay: `${index * 100}ms`,
          }}
        >
          {/* Avatar skeleton - with violet glow */}
          <div className="shrink-0">
            <div className="w-10 h-10 rounded-full skeleton bg-linear-to-br from-brand-500/20 to-brand-600/10 border border-brand-500/20" />
          </div>

          {/* Message skeleton */}
          <div className="flex-1 space-y-3 py-1">
            {/* Header line - with shimmer */}
            <div className="skeleton h-4 rounded-lg w-24 bg-linear-to-r from-background-surface/50 via-brand-500/10 to-background-surface/50" />

            {/* Content lines - staggered shimmer */}
            <div className="space-y-2">
              <div
                className="skeleton h-3 rounded-lg w-full bg-linear-to-r from-background-surface/50 via-brand-500/10 to-background-surface/50 [animation-delay:100ms]"
              />
              <div
                className="skeleton h-3 rounded-lg w-5/6 bg-linear-to-r from-background-surface/50 via-brand-500/10 to-background-surface/50 [animation-delay:200ms]"
              />
              {index % 2 === 0 && (
                <>
                  <div
                    className="skeleton h-3 rounded-lg w-4/6 bg-linear-to-r from-background-surface/50 via-brand-500/10 to-background-surface/50 [animation-delay:300ms]"
                  />
                  <div
                    className="skeleton h-3 rounded-lg w-3/4 bg-linear-to-r from-background-surface/50 via-brand-500/10 to-background-surface/50 [animation-delay:400ms]"
                  />
                </>
              )}
            </div>

            {/* Code block skeleton (alternate) - with shimmer */}
            {index % 3 === 0 && (
              <div className="mt-3 space-y-2 p-3 rounded-lg border border-brand-500/15 bg-linear-to-br from-background-surface/30 to-brand-500/5">
                <div className="skeleton h-2 rounded w-2/3 bg-linear-to-r from-background-surface/50 via-brand-500/10 to-background-surface/50" />
                <div
                  className="skeleton h-2 rounded w-3/4 bg-linear-to-r from-background-surface/50 via-brand-500/10 to-background-surface/50 [animation-delay:150ms]"
                />
                <div
                  className="skeleton h-2 rounded w-1/2 bg-linear-to-r from-background-surface/50 via-brand-500/10 to-background-surface/50 [animation-delay:300ms]"
                />
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

interface TypingSkeletonProps {
  className?: string;
}

export function TypingSkeleton({ className }: TypingSkeletonProps) {
  return (
    <div className={cn("flex gap-3 sm:gap-4 animate-fade-in", className)}>
      {/* Avatar - Violet themed with pulse */}
      <div className="shrink-0">
        <div className="w-10 h-10 rounded-full bg-linear-to-br from-brand-500/20 to-brand-600/10 border border-brand-500/30 flex items-center justify-center shadow-lg shadow-brand-500/10">
          <div className="w-6 h-6 bg-brand-500/40 rounded-full animate-pulse" />
        </div>
      </div>

      {/* Typing dots - Violet themed with smooth bounce */}
      <div className="flex-1 py-1">
        <div className="flex items-center gap-1.5 px-4 py-3 bg-linear-to-br from-background-surface/60 to-brand-500/5 rounded-lg border border-brand-500/20 shadow-md shadow-brand-500/5">
          <div
            className="w-2 h-2 rounded-full bg-brand-500 animate-bounce shadow-sm shadow-brand-500/50 [animation-delay:0ms]"
          />
          <div
            className="w-2 h-2 rounded-full bg-brand-500 animate-bounce shadow-sm shadow-brand-500/50 [animation-delay:150ms]"
          />
          <div
            className="w-2 h-2 rounded-full bg-brand-500 animate-bounce shadow-sm shadow-brand-500/50 [animation-delay:300ms]"
          />
        </div>
      </div>
    </div>
  );
}
