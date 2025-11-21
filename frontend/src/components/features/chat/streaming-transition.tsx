import React from "react";
import { cn } from "#/utils/utils";

interface StreamingTransitionProps {
  children: React.ReactNode;
  isVisible: boolean;
  delay?: number;
  duration?: number;
  className?: string;
}

interface StreamingFadeInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  direction?: "up" | "down" | "left" | "right";
  className?: string;
}

export function StreamingFadeIn({
  children,
  delay = 0,
  duration = 500,
  direction = "up",
  className,
}: StreamingFadeInProps) {
  const [isVisible, setIsVisible] = React.useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, delay);
    return () => clearTimeout(timer);
  }, [delay]);

  const directionClasses = {
    up: "translate-y-4",
    down: "-translate-y-4",
    left: "translate-x-4",
    right: "-translate-x-4",
  };

  return (
    <div
      className={cn(
        "transition-all ease-out",
        isVisible
          ? "opacity-100 translate-y-0 translate-x-0"
          : `opacity-0 ${directionClasses[direction]}`,
        className,
      )}
      style={{
        transitionDuration: `${duration}ms`,
        transitionDelay: `${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

export function StreamingTransition({
  children,
  isVisible,
  delay = 0,
  duration = 300,
  className,
}: StreamingTransitionProps) {
  const [shouldRender, setShouldRender] = React.useState(isVisible);
  const [isAnimating, setIsAnimating] = React.useState(false);

  React.useEffect(() => {
    if (isVisible) {
      setShouldRender(true);
      const timer = setTimeout(() => {
        setIsAnimating(true);
      }, delay);
      return () => clearTimeout(timer);
    }
    setIsAnimating(false);
    const timer = setTimeout(() => {
      setShouldRender(false);
    }, duration);
    return () => clearTimeout(timer);
  }, [isVisible, delay, duration]);

  if (!shouldRender) return null;

  return (
    <div
      className={cn(
        "transition-all ease-in-out",
        isAnimating
          ? "opacity-100 scale-100 translate-y-0"
          : "opacity-0 scale-95 translate-y-2",
        className,
      )}
      style={{
        transitionDuration: `${duration}ms`,
        transitionDelay: isVisible ? `${delay}ms` : "0ms",
      }}
    >
      {children}
    </div>
  );
}

interface StreamingSlideInProps {
  children: React.ReactNode;
  isVisible: boolean;
  direction?: "left" | "right" | "up" | "down";
  duration?: number;
  className?: string;
}

export function StreamingSlideIn({
  children,
  isVisible,
  direction = "left",
  duration = 400,
  className,
}: StreamingSlideInProps) {
  const directionClasses = {
    left: isVisible ? "translate-x-0" : "-translate-x-full",
    right: isVisible ? "translate-x-0" : "translate-x-full",
    up: isVisible ? "translate-y-0" : "-translate-y-full",
    down: isVisible ? "translate-y-0" : "translate-y-full",
  };

  return (
    <div
      className={cn(
        "transition-transform ease-out",
        directionClasses[direction],
        className,
      )}
      style={{
        transitionDuration: `${duration}ms`,
      }}
    >
      {children}
    </div>
  );
}

interface StreamingStaggerProps {
  children: React.ReactNode[];
  delay?: number;
  staggerDelay?: number;
  className?: string;
}

export function StreamingStagger({
  children,
  delay = 0,
  staggerDelay = 100,
  className,
}: StreamingStaggerProps) {
  return (
    <div className={cn("space-y-2", className)}>
      {children.map((child, index) => (
        <StreamingFadeIn
          key={index}
          delay={delay + index * staggerDelay}
          duration={300}
        >
          {child}
        </StreamingFadeIn>
      ))}
    </div>
  );
}

interface StreamingTypewriterProps {
  text: string;
  speed?: number;
  delay?: number;
  onComplete?: () => void;
  className?: string;
}

export function StreamingTypewriter({
  text,
  speed = 50,
  delay = 0,
  onComplete,
  className,
}: StreamingTypewriterProps) {
  const [displayedText, setDisplayedText] = React.useState("");
  const [currentIndex, setCurrentIndex] = React.useState(0);

  React.useEffect(() => {
    if (currentIndex >= text.length) {
      onComplete?.();
      return undefined;
    }

    const timer = setTimeout(() => {
      setDisplayedText((prev) => prev + text[currentIndex]);
      setCurrentIndex((prev) => prev + 1);
    }, speed);

    return () => {
      clearTimeout(timer);
    };
  }, [currentIndex, text, speed, onComplete]);

  React.useEffect(() => {
    const startTimer = setTimeout(() => {
      setCurrentIndex(0);
      setDisplayedText("");
    }, delay);

    return () => clearTimeout(startTimer);
  }, [delay]);

  return (
    <span className={cn("font-mono", className)}>
      {displayedText}
      <span className="animate-pulse">|</span>
    </span>
  );
}

interface StreamingProgressProps {
  progress: number;
  label?: string;
  showPercentage?: boolean;
  color?: "primary" | "success" | "warning" | "error";
  className?: string;
}

export function StreamingProgress({
  progress,
  label,
  showPercentage = true,
  color = "primary",
  className,
}: StreamingProgressProps) {
  const colorClasses = {
    primary: "bg-gradient-to-r from-primary-500 to-primary-600",
    success: "bg-gradient-to-r from-green-500 to-green-600",
    warning: "bg-gradient-to-r from-yellow-500 to-yellow-600",
    error: "bg-gradient-to-r from-red-500 to-red-600",
  };

  return (
    <div className={cn("w-full", className)}>
      {label && (
        <div className="flex justify-between text-sm mb-2">
          <span className="text-foreground-secondary">{label}</span>
          {showPercentage && (
            <span className="text-foreground-secondary">
              {Math.round(progress)}%
            </span>
          )}
        </div>
      )}
      <div className="w-full bg-background-tertiary/70/50 rounded-full h-2 overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500 ease-out",
            colorClasses[color],
          )}
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
    </div>
  );
}
