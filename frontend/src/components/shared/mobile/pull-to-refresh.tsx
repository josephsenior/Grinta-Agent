import React, { useState, useRef, useEffect } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { cn } from "#/utils/utils";
import { triggerHaptic } from "#/utils/haptic-feedback";

interface PullToRefreshProps {
  onRefresh: () => Promise<void>;
  children: React.ReactNode;
  threshold?: number; // Distance in pixels to trigger refresh
  disabled?: boolean;
}

export function PullToRefresh({
  onRefresh,
  children,
  threshold = 80,
  disabled = false,
}: PullToRefreshProps) {
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [canPull, setCanPull] = useState(false);
  const startY = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleTouchStart = (e: TouchEvent) => {
    if (disabled || isRefreshing) return;

    // Only allow pull-to-refresh when scrolled to top
    const scrollTop = containerRef.current?.scrollTop || 0;
    if (scrollTop === 0) {
      setCanPull(true);
      startY.current = e.touches[0].clientY;
    }
  };

  const handleTouchMove = (e: TouchEvent) => {
    if (!canPull || disabled || isRefreshing) return;

    const currentY = e.touches[0].clientY;
    const distance = Math.max(0, currentY - startY.current);

    // Add resistance as user pulls further
    const resistance = 0.5;
    const adjustedDistance = Math.min(distance * resistance, threshold * 1.5);

    setPullDistance(adjustedDistance);

    // Haptic feedback when threshold reached
    if (adjustedDistance >= threshold && pullDistance < threshold) {
      triggerHaptic("medium");
    }

    // Prevent default scrolling when pulling
    if (distance > 10) {
      e.preventDefault();
    }
  };

  const handleTouchEnd = async () => {
    if (!canPull || disabled || isRefreshing) {
      setPullDistance(0);
      setCanPull(false);
      return;
    }

    if (pullDistance >= threshold) {
      // Trigger refresh
      setIsRefreshing(true);
      triggerHaptic("success");

      try {
        await onRefresh();
      } catch (error) {
        console.error("Refresh failed:", error);
        triggerHaptic("error");
      } finally {
        setIsRefreshing(false);
        setPullDistance(0);
        setCanPull(false);
      }
    } else {
      // Snap back without refreshing
      setPullDistance(0);
      setCanPull(false);
    }
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener("touchstart", handleTouchStart, {
      passive: true,
    });
    container.addEventListener("touchmove", handleTouchMove, {
      passive: false,
    });
    container.addEventListener("touchend", handleTouchEnd);

    return () => {
      container.removeEventListener("touchstart", handleTouchStart);
      container.removeEventListener("touchmove", handleTouchMove);
      container.removeEventListener("touchend", handleTouchEnd);
    };
  }, [canPull, pullDistance, isRefreshing, disabled]);

  const progress = Math.min((pullDistance / threshold) * 100, 100);
  const isTriggered = pullDistance >= threshold;

  return (
    <div ref={containerRef} className="relative h-full overflow-y-auto">
      {/* Pull Indicator */}
      <div
        className={cn(
          "absolute top-0 left-0 right-0 z-50",
          "flex items-center justify-center",
          "transition-all duration-200 ease-out",
        )}
        style={{
          height: `${pullDistance}px`,
          opacity: pullDistance > 0 ? 1 : 0,
        }}
      >
        <div
          className={cn(
            "flex flex-col items-center gap-2",
            "transition-all duration-200",
          )}
        >
          {/* Refresh Icon */}
          <div
            className={cn(
              "w-8 h-8 rounded-full",
              "flex items-center justify-center",
              "bg-brand-500/20 border border-brand-500/40",
              "transition-all duration-200",
              isTriggered && "bg-brand-500 border-brand-500",
            )}
            style={{
              transform: `rotate(${progress * 3.6}deg)`,
            }}
          >
            {isRefreshing ? (
              <Loader2 className="w-4 h-4 text-white animate-spin" />
            ) : (
              <RefreshCw
                className={cn(
                  "w-4 h-4",
                  isTriggered ? "text-white" : "text-violet-500",
                )}
              />
            )}
          </div>

          {/* Progress Text */}
          <div className="text-xs text-foreground-secondary font-medium">
            {isRefreshing
              ? "Refreshing..."
              : isTriggered
                ? "Release to refresh"
                : "Pull to refresh"}
          </div>
        </div>
      </div>

      {/* Content */}
      <div
        style={{
          transform: `translateY(${pullDistance}px)`,
          transition: canPull ? "none" : "transform 0.2s ease-out",
        }}
      >
        {children}
      </div>
    </div>
  );
}
