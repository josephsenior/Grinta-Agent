import React, { useState, useRef, useEffect } from "react";
import { logger } from "#/utils/logger";

interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
  placeholder?: string;
  fallback?: string;
  width?: number;
  height?: number;
  quality?: number;
  priority?: boolean;
  onLoad?: () => void;
  onError?: () => void;
}

// Helper function to optimize image sources
function optimizeImageSrc(
  src: string,
  width?: number,
  height?: number,
  quality?: number,
): string {
  // If it's already a data URL or external service, return as is
  if (src.startsWith("data:") || src.startsWith("http")) {
    return src;
  }

  // For local images, you could add optimization logic here
  // For example, using a service like Cloudinary, ImageKit, or Next.js Image Optimization
  let optimizedSrc = src;

  // Example: Add query parameters for optimization
  const params = new URLSearchParams();
  if (width) params.set("w", width.toString());
  if (height) params.set("h", height.toString());
  if (quality) params.set("q", quality.toString());
  params.set("f", "auto"); // Auto format
  params.set("c", "limit"); // Limit dimensions

  if (params.toString()) {
    optimizedSrc += `?${params.toString()}`;
  }

  return optimizedSrc;
}

export function LazyImage(props: Readonly<LazyImageProps>) {
  const {
    src,
    alt,
    className = "",
    placeholder = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5YTNhZiIgdGV4dC1hbmNob3I9Im1pZGRzZSIgZHk9Ii4zZW0iPkxvYWRpbmcuLi48L3RleHQ+PC9zdmc+",
    fallback = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5YTNhZiIgdGV4dC1hbmNob3I9Im1pZGRzZSIgZHk9Ii4zZW0iPkVycm9yPC90ZXh0Pjwvc3ZnPg==",
    width,
    height,
    quality = 80,
    priority = false,
    onLoad,
    onError,
  } = props;
  const [imageSrc, setImageSrc] = useState(placeholder);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(priority);
  const [hasError, setHasError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  // Intersection Observer for lazy loading
  useEffect(() => {
    if (priority) {
      return undefined;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      {
        threshold: 0.1,
        rootMargin: "50px",
      },
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => {
      observer.disconnect();
    };
  }, [priority]);

  // Load image when in view
  useEffect(() => {
    if (!isInView || hasError) return;

    const img = new Image();

    img.onload = () => {
      setImageSrc(src);
      setIsLoaded(true);
      onLoad?.();
    };

    img.onerror = () => {
      setImageSrc(fallback);
      setHasError(true);
      onError?.();
    };

    // Add quality parameter if it's a supported image service
    const optimizedSrc = optimizeImageSrc(src, width, height, quality);
    img.src = optimizedSrc;
  }, [
    isInView,
    src,
    width,
    height,
    quality,
    fallback,
    onLoad,
    onError,
    hasError,
  ]);

  return (
    <img
      ref={imgRef}
      src={imageSrc}
      alt={alt}
      className={`transition-opacity duration-300 ${
        isLoaded ? "opacity-100" : "opacity-70"
      } ${className}`}
      width={width}
      height={height}
      loading={priority ? "eager" : "lazy"}
      decoding="async"
    />
  );
}

// (optimizeImageSrc is hoisted above)

// Hook for preloading images
export const useImagePreload = (srcs: string[]) => {
  const [loadedImages, setLoadedImages] = useState<Set<string>>(new Set());
  const [loadingImages, setLoadingImages] = useState<Set<string>>(new Set());

  // Hoisted helper to create a preload Promise for a src
  function preloadSingleImage(src: string): Promise<string> {
    return new Promise<string>((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(src);
      img.onerror = () => reject(new Error(`Failed to load image: ${src}`));
      img.src = src;
    });
  }

  // named handler to process success
  function handlePreloadSuccess(s: string) {
    setLoadedImages((prev) => new Set(prev).add(s));
    setLoadingImages((prev) => {
      const newSet = new Set(prev);
      newSet.delete(s);
      return newSet;
    });
  }

  // named handler to process failure
  function handlePreloadFailure(src: string) {
    setLoadingImages((prev) => {
      const newSet = new Set(prev);
      newSet.delete(src);
      return newSet;
    });
  }

  useEffect(() => {
    const preloadImages = async () => {
      const promises: Promise<string>[] = [];

      for (const src of srcs) {
        const already = loadedImages.has(src) || loadingImages.has(src);
        if (already) {
          // skip
        } else {
          setLoadingImages((prev) => new Set(prev).add(src));

          const p = preloadSingleImage(src)
            .then((s) => {
              handlePreloadSuccess(s);
              return s;
            })
            .catch(() => {
              handlePreloadFailure(src);
              throw new Error(`Failed to load image: ${src}`);
            });

          promises.push(p);
        }
      }

      try {
        await Promise.allSettled(promises);
      } catch (error) {
        if (process.env.NODE_ENV === "development") {
          logger.warn("Some images failed to preload:", error);
        }
      }
    };

    preloadImages();
  }, [srcs, loadedImages, loadingImages]);

  return {
    loadedImages,
    loadingImages,
    isLoaded: (src: string) => loadedImages.has(src),
    isLoading: (src: string) => loadingImages.has(src),
  };
};

export default LazyImage;
