import React from "react";
import { cn } from "#/utils/utils";

interface SkeletonLoaderProps {
  className?: string;
  variant?: "text" | "rectangular" | "circular" | "rounded";
  width?: string | number;
  height?: string | number;
  lines?: number;
  animation?: "pulse" | "wave" | "none";
}

export function SkeletonLoader({
  className,
  variant = "rectangular",
  width,
  height,
  lines = 1,
  animation = "pulse",
}: SkeletonLoaderProps) {
  const baseClasses = "bg-background-elevated animate-pulse";

  const variantClasses = {
    text: "h-4 rounded",
    rectangular: "rounded-lg",
    circular: "rounded-full",
    rounded: "rounded-xl",
  };

  const animationClasses = {
    pulse: "animate-pulse",
    wave: "animate-wave",
    none: "",
  };

  const style = {
    width: typeof width === "number" ? `${width}px` : width,
    height: typeof height === "number" ? `${height}px` : height,
  };

  if (lines > 1) {
    return (
      <div className="space-y-2">
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className={cn(
              baseClasses,
              variantClasses[variant],
              animationClasses[animation],
              className,
            )}
            style={index === lines - 1 ? { width: "75%" } : style}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={cn(
        baseClasses,
        variantClasses[variant],
        animationClasses[animation],
        className,
      )}
      style={style}
    />
  );
}

// Pre-built skeleton components for common use cases
export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn("p-4 space-y-3", className)}>
      <SkeletonLoader variant="rectangular" height={20} width="60%" />
      <SkeletonLoader variant="text" lines={3} />
      <div className="flex gap-2">
        <SkeletonLoader variant="rounded" height={32} width={80} />
        <SkeletonLoader variant="rounded" height={32} width={100} />
      </div>
    </div>
  );
}

export function SkeletonDropdown({ className }: { className?: string }) {
  return (
    <div className={cn("space-y-2", className)}>
      <SkeletonLoader variant="rounded" height={40} width="100%" />
      <div className="space-y-1">
        <SkeletonLoader variant="text" height={16} width="80%" />
        <SkeletonLoader variant="text" height={16} width="90%" />
        <SkeletonLoader variant="text" height={16} width="70%" />
      </div>
    </div>
  );
}

export function SkeletonForm({ className }: { className?: string }) {
  return (
    <div className={cn("space-y-4", className)}>
      <div className="space-y-2">
        <SkeletonLoader variant="text" height={16} width="20%" />
        <SkeletonLoader variant="rounded" height={40} width="100%" />
      </div>
      <div className="space-y-2">
        <SkeletonLoader variant="text" height={16} width="25%" />
        <SkeletonLoader variant="rounded" height={40} width="100%" />
      </div>
      <div className="flex gap-2">
        <SkeletonLoader variant="rounded" height={40} width={100} />
        <SkeletonLoader variant="rounded" height={40} width={80} />
      </div>
    </div>
  );
}

export function SkeletonTable({
  rows = 5,
  className,
}: {
  rows?: number;
  className?: string;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      {/* Header */}
      <div className="flex gap-4">
        <SkeletonLoader variant="text" height={20} width="25%" />
        <SkeletonLoader variant="text" height={20} width="30%" />
        <SkeletonLoader variant="text" height={20} width="20%" />
        <SkeletonLoader variant="text" height={20} width="25%" />
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex gap-4">
          <SkeletonLoader variant="text" height={16} width="25%" />
          <SkeletonLoader variant="text" height={16} width="30%" />
          <SkeletonLoader variant="text" height={16} width="20%" />
          <SkeletonLoader variant="text" height={16} width="25%" />
        </div>
      ))}
    </div>
  );
}
