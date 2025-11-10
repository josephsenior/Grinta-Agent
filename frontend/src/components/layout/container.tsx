import clsx from "clsx";
import React, { useRef, useState, useCallback } from "react";
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
  const scroll = useContainerScroll(labels);

  return (
    <div
      ref={scroll.containerRef}
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
        <ContainerTabsHeader
          labels={labels}
          variant={variant}
          scroll={scroll}
        />
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

function useContainerScroll(labels?: ContainerProps["labels"]) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const [showScrollButtons, setShowScrollButtons] = useState(false);

  const updateScrollButtons = useCallback(() => {
    const element = scrollContainerRef.current;
    if (!element) {
      return;
    }
    const { scrollLeft, scrollWidth, clientWidth } = element;
    setCanScrollLeft(scrollLeft > 0);
    setCanScrollRight(scrollLeft < scrollWidth - clientWidth);
  }, []);

  useTrackElementWidth({
    elementRef: containerRef,
    callback: (width: number) => {
      const shouldShow = Boolean(labels?.length) && width < 598;
      setShowScrollButtons(shouldShow);
      updateScrollButtons();
    },
  });

  const scrollBy = useCallback((delta: number) => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({
        left: delta,
        behavior: "smooth",
      });
    }
  }, []);

  const scrollLeft = useCallback(() => scrollBy(-200), [scrollBy]);
  const scrollRight = useCallback(() => scrollBy(200), [scrollBy]);

  return {
    containerRef,
    scrollContainerRef,
    showScrollButtons,
    canScrollLeft,
    canScrollRight,
    updateScrollButtons,
    scrollLeft,
    scrollRight,
  } as const;
}

function ContainerTabsHeader({
  labels,
  variant,
  scroll,
}: {
  labels: NonNullable<ContainerProps["labels"]>;
  variant: ContainerProps["variant"];
  scroll: ReturnType<typeof useContainerScroll>;
}) {
  const gradientClass =
    variant === "glass"
      ? "border-b border-grey-800/50 bg-gradient-to-r from-grey-900/50 to-grey-950/30"
      : "border-b border-grey-900 bg-black";

  return (
    <div
      className={clsx(
        "relative flex items-center h-[42px] w-full rounded-t-2xl",
        gradientClass,
      )}
    >
      {scroll.showScrollButtons && (
        <div
          className={clsx(
            "absolute left-0 z-10 pl-2 pr-4",
            variant === "glass"
              ? "bg-gradient-to-r from-grey-900 to-transparent"
              : "bg-black",
          )}
        >
          <ScrollLeftButton
            scrollLeft={scroll.scrollLeft}
            canScrollLeft={scroll.canScrollLeft}
          />
        </div>
      )}

      <div
        ref={scroll.scrollContainerRef}
        className={clsx(
          "flex text-sm font-medium overflow-x-auto scrollbar-hide w-full relative",
          scroll.showScrollButtons && "mx-10",
        )}
        onScroll={scroll.updateScrollButtons}
      >
        {labels.map(
          ({ label: tabLabel, to, icon, isBeta, isLoading, rightContent }) => (
            <NavTab
              key={to}
              to={to}
              label={tabLabel}
              icon={icon}
              isBeta={isBeta}
              isLoading={isLoading}
              rightContent={rightContent}
            />
          ),
        )}
      </div>

      {scroll.showScrollButtons && (
        <div
          className={clsx(
            "absolute right-0 z-10 pr-2 pl-4",
            variant === "glass"
              ? "bg-gradient-to-l from-grey-900 to-transparent"
              : "bg-black",
          )}
        >
          <ScrollRightButton
            scrollRight={scroll.scrollRight}
            canScrollRight={scroll.canScrollRight}
          />
        </div>
      )}
    </div>
  );
}
