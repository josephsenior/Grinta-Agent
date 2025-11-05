import clsx from "clsx";
import React, { useRef, useState } from "react";
import { NavTab } from "./nav-tab";
import { ScrollLeftButton } from "./scroll-left-button";
import { ScrollRightButton } from "./scroll-right-button";
import { useTrackElementWidth } from "#/hooks/use-track-element-width";

interface ContainerProps {
  label?: React.ReactNode;
  labels?: {
    label: string | React.ReactNode;
    to: string;
    icon?: React.ReactNode;
    isBeta?: boolean;
    isLoading?: boolean;
    rightContent?: React.ReactNode;
  }[];
  children: React.ReactNode;
  className?: React.HTMLAttributes<HTMLDivElement>["className"];
  variant?: "glass" | "plain" | "dark";
}

export function Container({
  label,
  labels,
  children,
  className,
  variant = "glass",
}: ContainerProps) {
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const [showScrollButtons, setShowScrollButtons] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Check scroll position and update button states
  const updateScrollButtons = () => {
    if (scrollContainerRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } =
        scrollContainerRef.current;
      setCanScrollLeft(scrollLeft > 0);
      setCanScrollRight(scrollLeft < scrollWidth - clientWidth);
    }
  };

  // Track container width using ResizeObserver
  useTrackElementWidth({
    elementRef: containerRef,
    callback: (width: number) => {
      // Only update scroll button visibility when crossing the threshold
      const shouldShowScrollButtons =
        width < 598 && Boolean(labels) && labels!.length > 0;
      if (shouldShowScrollButtons) {
        setShowScrollButtons(shouldShowScrollButtons);
      }
      updateScrollButtons();
    },
  });

  // Scroll functions
  const scrollLeft = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ left: -200, behavior: "smooth" });
    }
  };

  const scrollRight = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ left: 200, behavior: "smooth" });
    }
  };

  return (
    <div
      ref={containerRef}
      className={clsx(
        "rounded-2xl flex flex-col h-full w-full",
        variant === "glass" && [
          "glass border-grey-800/50 shadow-luxury backdrop-blur-xl",
          "bg-gradient-to-br from-grey-950/80 to-grey-900/60",
          "transition-all duration-300 hover:shadow-luxury-lg hover:border-grey-700/60",
        ],
        variant === "plain" && "bg-black",
        variant === "dark" && "bg-black lavender-gradient-border",
        className,
      )}
    >
      {labels && (
        <div
          className={clsx(
            "relative flex items-center h-[42px] w-full rounded-t-2xl",
            variant === "glass"
              ? "border-b border-grey-800/50 bg-gradient-to-r from-grey-900/50 to-grey-950/30"
              : "border-b border-grey-900 bg-black",
          )}
        >
          {/* Enhanced Left scroll button */}
          {showScrollButtons && (
            <div
              className={clsx(
                "absolute left-0 z-10 pl-2 pr-4",
                variant === "glass"
                  ? "bg-gradient-to-r from-grey-900 to-transparent"
                  : "bg-black",
              )}
            >
              <ScrollLeftButton
                scrollLeft={scrollLeft}
                canScrollLeft={canScrollLeft}
              />
            </div>
          )}

          {/* Enhanced Scrollable tabs container */}
          <div
            ref={scrollContainerRef}
            className={clsx(
              "flex text-sm font-medium overflow-x-auto scrollbar-hide w-full relative",
              showScrollButtons && "mx-10",
            )}
            onScroll={updateScrollButtons}
          >
            {labels.map(
              ({ label: l, to, icon, isBeta, isLoading, rightContent }) => (
                <NavTab
                  key={to}
                  to={to}
                  label={l}
                  icon={icon}
                  isBeta={isBeta}
                  isLoading={isLoading}
                  rightContent={rightContent}
                />
              ),
            )}
          </div>

          {/* Enhanced Right scroll button */}
          {showScrollButtons && (
            <div
              className={clsx(
                "absolute right-0 z-10 pr-2 pl-4",
                variant === "glass"
                  ? "bg-gradient-to-l from-grey-900 to-transparent"
                  : "bg-black",
              )}
            >
              <ScrollRightButton
                scrollRight={scrollRight}
                canScrollRight={canScrollRight}
              />
            </div>
          )}
        </div>
      )}
      {!labels && label && (
        <div
          className={clsx(
            "px-4 h-[42px] text-sm font-medium flex items-center rounded-t-2xl text-foreground-secondary",
            variant === "glass"
              ? "border-b border-grey-800/50 bg-gradient-to-r from-grey-900/50 to-grey-950/30"
              : "border-b border-grey-900 bg-black",
          )}
        >
          {label}
        </div>
      )}
      <div
        className={clsx(
          "overflow-hidden flex-grow rounded-b-2xl",
          variant === "glass"
            ? "bg-gradient-to-br from-grey-970/50 to-grey-985/80 backdrop-blur-sm"
            : "bg-black",
        )}
      >
        {children}
      </div>
    </div>
  );
}
