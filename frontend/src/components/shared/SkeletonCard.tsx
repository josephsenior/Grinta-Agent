import React from "react";

/**
 * Skeleton loading screens for better UX
 */

export function SkeletonCard() {
  return (
    <div className="glass-modern rounded-xl p-6 animate-pulse">
      <div className="flex items-start gap-4 mb-4">
        <div className="w-12 h-12 bg-brand-500/20 rounded-xl" />
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-brand-500/10 rounded w-3/4" />
          <div className="h-3 bg-brand-500/5 rounded w-1/2" />
        </div>
      </div>
      <div className="space-y-2">
        <div className="h-3 bg-brand-500/5 rounded" />
        <div className="h-3 bg-brand-500/5 rounded w-5/6" />
        <div className="h-3 bg-brand-500/5 rounded w-4/6" />
      </div>
    </div>
  );
}

export function SkeletonHero() {
  return (
    <div className="max-w-6xl mx-auto w-full animate-pulse">
      <div className="flex flex-col gap-12 items-center w-full text-center">
        {/* Badge skeleton */}
        <div className="flex gap-4 mb-8">
          <div className="h-10 w-32 bg-brand-500/20 rounded-full" />
          <div className="h-10 w-24 bg-success-500/20 rounded-full" />
        </div>

        {/* Logo skeleton */}
        <div className="w-20 h-20 bg-brand-500/20 rounded-full mb-8" />

        {/* Title skeleton */}
        <div className="space-y-4 w-full">
          <div className="h-12 bg-brand-500/10 rounded w-3/4 mx-auto" />
          <div className="h-16 bg-brand-500/20 rounded w-2/3 mx-auto" />
        </div>

        {/* Description skeleton */}
        <div className="h-6 bg-brand-500/5 rounded w-1/2 mx-auto mb-8" />

        {/* Buttons skeleton */}
        <div className="flex gap-4 justify-center">
          <div className="h-14 w-48 bg-brand-500/30 rounded-xl" />
          <div className="h-14 w-40 bg-brand-500/10 rounded-xl" />
        </div>

        {/* Social proof skeleton */}
        <div className="flex gap-4 mt-8">
          <div className="h-12 w-32 bg-brand-500/10 rounded-full" />
          <div className="h-12 w-36 bg-success-500/10 rounded-full" />
          <div className="h-12 w-32 bg-accent-500/10 rounded-full" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonFeatureGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-12 gap-6 animate-pulse">
      {[
        "md:col-span-8",
        "md:col-span-6",
        "md:col-span-6",
        "md:col-span-6",
        "md:col-span-6",
        "md:col-span-8",
      ].map((colSpan, i) => (
        <div key={i} className={`${colSpan} glass-modern rounded-xl p-6`}>
          <div className="flex items-start gap-4 mb-4">
            <div className="w-14 h-14 bg-brand-500/20 rounded-xl" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-brand-500/10 rounded w-2/3" />
              <div className="h-3 bg-brand-500/5 rounded w-1/3" />
            </div>
          </div>
          <div className="space-y-2">
            <div className="h-3 bg-brand-500/5 rounded" />
            <div className="h-3 bg-brand-500/5 rounded w-5/6" />
            <div className="h-3 bg-brand-500/5 rounded w-4/6" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2 animate-pulse">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-4 bg-brand-500/10 rounded"
          style={{ width: `${100 - i * 10}%` }}
        />
      ))}
    </div>
  );
}


