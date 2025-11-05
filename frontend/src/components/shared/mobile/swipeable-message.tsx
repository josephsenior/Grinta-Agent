import React, { useState, useRef, useEffect } from "react";
import { Trash2, Copy, Reply } from "lucide-react";
import { cn } from "#/utils/utils";
import { triggerHaptic } from "#/utils/haptic-feedback";

interface SwipeableMessageProps {
  children: React.ReactNode;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onDelete?: () => void;
  onCopy?: () => void;
  onReply?: () => void;
  threshold?: number; // Distance in pixels to trigger action
  className?: string;
}

export function SwipeableMessage({
  children,
  onSwipeLeft,
  onSwipeRight,
  onDelete,
  onCopy,
  onReply,
  threshold = 80,
  className,
}: SwipeableMessageProps) {
  const [swipeDistance, setSwipeDistance] = useState(0);
  const [isSwiping, setIsSwiping] = useState(false);
  const startX = useRef(0);
  const startY = useRef(0);
  const elementRef = useRef<HTMLDivElement>(null);

  const handleTouchStart = (e: React.TouchEvent) => {
    startX.current = e.touches[0].clientX;
    startY.current = e.touches[0].clientY;
    setIsSwiping(false);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    const currentX = e.touches[0].clientX;
    const currentY = e.touches[0].clientY;
    const deltaX = currentX - startX.current;
    const deltaY = currentY - startY.current;

    // Determine if horizontal swipe (not vertical scroll)
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
      setIsSwiping(true);
      setSwipeDistance(deltaX);

      // Haptic feedback at threshold
      if (Math.abs(deltaX) >= threshold && Math.abs(swipeDistance) < threshold) {
        triggerHaptic("selection");
      }

      // Prevent vertical scrolling during horizontal swipe
      e.preventDefault();
    }
  };

  const handleTouchEnd = () => {
    if (!isSwiping) {
      setSwipeDistance(0);
      return;
    }

    const absDistance = Math.abs(swipeDistance);

    if (absDistance >= threshold) {
      // Trigger action based on swipe direction
      if (swipeDistance > 0) {
        // Swipe right
        triggerHaptic("success");
        onSwipeRight?.();
        onReply?.(); // Default action for right swipe
      } else {
        // Swipe left
        triggerHaptic("warning");
        onSwipeLeft?.();
        onDelete?.(); // Default action for left swipe
      }
    }

    // Snap back
    setSwipeDistance(0);
    setIsSwiping(false);
  };

  const progress = Math.min((Math.abs(swipeDistance) / threshold) * 100, 100);
  const isTriggered = Math.abs(swipeDistance) >= threshold;

  return (
    <div className={cn("relative overflow-hidden", className)}>
      {/* Left Action Indicator (Swipe Right) */}
      <div
        className={cn(
          "absolute left-0 top-0 bottom-0 z-0",
          "flex items-center justify-start pl-4",
          "bg-brand-500/20 transition-all duration-200",
        )}
        style={{
          width: `${Math.max(0, swipeDistance)}px`,
          opacity: swipeDistance > 0 ? progress / 100 : 0,
        }}
      >
        <Reply
          className={cn(
            "w-5 h-5 transition-all duration-200",
            isTriggered ? "text-violet-500 scale-110" : "text-violet-500/70",
          )}
        />
      </div>

      {/* Right Action Indicator (Swipe Left) */}
      <div
        className={cn(
          "absolute right-0 top-0 bottom-0 z-0",
          "flex items-center justify-end pr-4",
          "bg-red-500/20 transition-all duration-200",
        )}
        style={{
          width: `${Math.max(0, -swipeDistance)}px`,
          opacity: swipeDistance < 0 ? progress / 100 : 0,
        }}
      >
        <Trash2
          className={cn(
            "w-5 h-5 transition-all duration-200",
            isTriggered ? "text-red-500 scale-110" : "text-red-500/70",
          )}
        />
      </div>

      {/* Swipeable Content */}
      <div
        ref={elementRef}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        className="relative z-10 touch-pan-y"
        style={{
          transform: `translateX(${swipeDistance}px)`,
          transition: isSwiping ? "none" : "transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      >
        {children}
      </div>
    </div>
  );
}

