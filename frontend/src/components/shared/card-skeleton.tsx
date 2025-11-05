/**
 * Loading skeleton for card-based layouts
 */

export function CardSkeleton() {
  return (
    <div className="bg-background-secondary border border-border rounded-lg p-4 animate-pulse">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3 flex-1">
          <div className="w-10 h-10 bg-background rounded-md" />
          <div className="flex-1">
            <div className="h-5 bg-background rounded w-3/4 mb-2" />
            <div className="h-3 bg-background rounded w-1/2" />
          </div>
        </div>
        <div className="w-5 h-5 bg-background rounded" />
      </div>

      {/* Description */}
      <div className="mb-3">
        <div className="h-3 bg-background rounded w-full mb-2" />
        <div className="h-3 bg-background rounded w-5/6" />
      </div>

      {/* Content */}
      <div className="mb-3 p-3 bg-background rounded">
        <div className="h-3 bg-background-secondary rounded w-full mb-1" />
        <div className="h-3 bg-background-secondary rounded w-4/5 mb-1" />
        <div className="h-3 bg-background-secondary rounded w-3/4" />
      </div>

      {/* Tags */}
      <div className="flex gap-2 mb-3">
        <div className="h-6 w-16 bg-background rounded" />
        <div className="h-6 w-20 bg-background rounded" />
        <div className="h-6 w-14 bg-background rounded" />
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-border">
        <div className="h-3 w-20 bg-background rounded" />
        <div className="h-8 w-24 bg-background rounded" />
      </div>
    </div>
  );
}

export function CardSkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

