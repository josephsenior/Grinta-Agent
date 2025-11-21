import React from "react";

export function SkeletonLoader() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header skeleton */}
      <header className="border-b border-border-primary p-4 safe-area-top">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="skeleton-avatar" />
            <div className="skeleton-text w-32 h-6" />
          </div>
          <div className="flex items-center space-x-2">
            <div className="skeleton w-6 h-6" />
            <div className="skeleton-avatar" />
          </div>
        </div>
      </header>

      {/* Main content skeleton */}
      <main className="p-6">
        <div className="max-w-4xl mx-auto">
          {/* Hero section skeleton */}
          <div className="text-center mb-12">
            <div className="skeleton-avatar w-16 h-16 mx-auto mb-4" />
            <div className="skeleton-text w-64 h-8 mx-auto mb-4" />
            <div className="skeleton-text w-96 h-6 mx-auto mb-6" />
            <div className="skeleton-button w-40 h-10 mx-auto" />
          </div>

          {/* Content grid skeleton - Enhanced with stagger */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="border border-border-primary/50 rounded-xl p-6 bg-background-elevated/30 backdrop-blur-md scroll-reveal"
                style={{ animationDelay: `${(i - 1) * 50}ms` }}
              >
                <div className="skeleton w-8 h-8 mb-4" />
                <div className="skeleton-text w-3/4 h-6 mb-2" />
                <div className="skeleton-text w-full h-4 mb-2" />
                <div className="skeleton-text w-2/3 h-4" />
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

export default SkeletonLoader;
