import React, { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";

interface PerformanceOptimizedImageProps {
  src: string;
  alt: string;
  className?: string;
  width?: number;
  height?: number;
  priority?: boolean;
}

export function PerformanceOptimizedImage({
  src,
  alt,
  className = "",
  width,
  height,
  priority = false,
}: PerformanceOptimizedImageProps) {
  const { t } = useTranslation();
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);

  const handleLoad = useCallback(() => {
    setIsLoaded(true);
  }, []);

  const handleError = useCallback(() => {
    setHasError(true);
  }, []);

  if (hasError) {
    return (
      <div
        className={`bg-background-tertiary flex items-center justify-center ${className}`}
        style={{ width, height }}
      >
        <span className="text-foreground-secondary text-sm">
          {t("common.imageLoadError", "Image failed to load")}
        </span>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`} style={{ width, height }}>
      {!isLoaded && (
        <div
          className="absolute inset-0 bg-background-tertiary animate-pulse flex items-center justify-center"
          style={{ width, height }}
        >
          <div className="w-8 h-8 border-2 border-border border-t-blue-500 rounded-full animate-spin" />
        </div>
      )}
      <img
        src={src}
        alt={alt}
        onLoad={handleLoad}
        onError={handleError}
        loading={priority ? "eager" : "lazy"}
        decoding="async"
        className={`transition-opacity duration-300 ${isLoaded ? "opacity-100" : "opacity-0"}`}
        style={{ width, height }}
      />
    </div>
  );
}
