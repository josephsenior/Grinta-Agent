import { useState, useEffect, useRef, useCallback } from "react";

interface UseStreamingOptions {
  speed?: number; // Characters per interval
  interval?: number; // Milliseconds between updates
  delay?: number; // Initial delay before starting
  onComplete?: () => void;
  autoStart?: boolean;
}

interface UseStreamingReturn {
  displayedText: string;
  isStreaming: boolean;
  isComplete: boolean;
  startStreaming: () => void;
  stopStreaming: () => void;
  resetStreaming: () => void;
  progress: number; // 0-100
}

export function useStreaming(
  text: string,
  options: UseStreamingOptions = {},
): UseStreamingReturn {
  const {
    speed = 2,
    interval = 30,
    delay = 0,
    onComplete,
    autoStart = true,
  } = options;

  const [displayedText, setDisplayedText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const delayTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const startStreaming = useCallback(() => {
    if (isStreaming || isComplete) return;

    setIsStreaming(true);
    setIsComplete(false);

    // Clear any existing intervals/timeouts
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (delayTimeoutRef.current) clearTimeout(delayTimeoutRef.current);

    // Start streaming after delay
    delayTimeoutRef.current = setTimeout(() => {
      intervalRef.current = setInterval(() => {
        setDisplayedText((prev) => {
          const nextLength = Math.min(prev.length + speed, text.length);
          const nextText = text.slice(0, nextLength);

          if (nextLength >= text.length) {
            setIsComplete(true);
            setIsStreaming(false);
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
            }
            onComplete?.();
          }

          return nextText;
        });
      }, interval);
    }, delay);
  }, [text, speed, interval, delay, onComplete, isStreaming, isComplete]);

  const stopStreaming = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (delayTimeoutRef.current) {
      clearTimeout(delayTimeoutRef.current);
      delayTimeoutRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const resetStreaming = useCallback(() => {
    stopStreaming();
    setDisplayedText("");
    setIsComplete(false);
    setIsStreaming(false);
  }, [stopStreaming]);

  // Auto-start streaming when text changes
  useEffect(() => {
    if (autoStart && text && !isStreaming && !isComplete) {
      startStreaming();
    }
  }, [text, autoStart, isStreaming, isComplete, startStreaming]);

  // Cleanup on unmount
  useEffect(
    () => () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (delayTimeoutRef.current) clearTimeout(delayTimeoutRef.current);
    },
    [],
  );

  // Calculate progress percentage
  const progress =
    text.length > 0 ? (displayedText.length / text.length) * 100 : 0;

  return {
    displayedText,
    isStreaming,
    isComplete,
    startStreaming,
    stopStreaming,
    resetStreaming,
    progress,
  };
}

// Hook for streaming multiple items sequentially
interface UseSequentialStreamingOptions extends UseStreamingOptions {
  items: string[];
  itemDelay?: number; // Delay between items
}

export function useSequentialStreaming(options: UseSequentialStreamingOptions) {
  const { items, itemDelay = 500, ...streamingOptions } = options;
  const [currentIndex, setCurrentIndex] = useState(0);
  const [allStreamedItems, setAllStreamedItems] = useState<string[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const itemTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const currentItem = items[currentIndex] || "";
  const currentStreaming = useStreaming(currentItem, {
    ...streamingOptions,
    autoStart: false,
    onComplete: () => {
      // Move to next item after a delay
      if (currentIndex < items.length - 1) {
        itemTimeoutRef.current = setTimeout(() => {
          setAllStreamedItems((prev) => [...prev, currentItem]);
          setCurrentIndex((prev) => prev + 1);
        }, itemDelay);
      } else {
        // All items complete
        setAllStreamedItems((prev) => [...prev, currentItem]);
        setIsComplete(true);
      }
    },
  });

  // Start streaming the first item
  useEffect(() => {
    if (items.length > 0 && currentIndex === 0) {
      currentStreaming.startStreaming();
    }
  }, [items.length, currentIndex, currentStreaming]);

  // Start streaming new items
  useEffect(() => {
    if (currentIndex > 0 && currentIndex < items.length) {
      currentStreaming.resetStreaming();
      currentStreaming.startStreaming();
    }
  }, [currentIndex, currentStreaming]);

  // Cleanup
  useEffect(
    () => () => {
      if (itemTimeoutRef.current) clearTimeout(itemTimeoutRef.current);
    },
    [],
  );

  const reset = () => {
    setCurrentIndex(0);
    setAllStreamedItems([]);
    setIsComplete(false);
    currentStreaming.resetStreaming();
  };

  return {
    currentItem: currentStreaming.displayedText,
    allStreamedItems,
    currentIndex,
    isComplete,
    progress:
      ((currentIndex + currentStreaming.progress / 100) / items.length) * 100,
    reset,
  };
}

// Hook for streaming with typing simulation
interface UseTypingStreamingOptions extends UseStreamingOptions {
  realisticTyping?: boolean; // Vary speed like human typing
  pauseOnPunctuation?: boolean;
  punctuationDelay?: number;
}

export function useTypingStreaming(
  text: string,
  options: UseTypingStreamingOptions = {},
): UseStreamingReturn {
  const {
    realisticTyping = false,
    pauseOnPunctuation = true,
    punctuationDelay = 200,
    speed = 1,
    interval = 50,
    ...restOptions
  } = options;

  const getTypingSpeed = useCallback(
    (char: string, index: number, totalLength: number) => {
      if (!realisticTyping) return speed;

      // Simulate human typing patterns
      const baseSpeed = speed;
      let variation = 1;

      // Position-based variation: slower at start (warming up), faster in middle, slower at end (tiring)
      const positionRatio = index / Math.max(1, totalLength);
      if (positionRatio < 0.1) {
        // First 10% - warming up, slightly slower
        variation *= 1.2;
      } else if (positionRatio > 0.9) {
        // Last 10% - tiring, slightly slower
        variation *= 1.15;
      } else {
        // Middle 80% - peak performance, slightly faster
        variation *= 0.95;
      }

      // Slower on punctuation
      if (pauseOnPunctuation && /[.!?;:,]/.test(char)) {
        variation *= 2;
      }

      // Faster on spaces
      if (char === " ") {
        variation *= 0.7;
      }

      // Random variation for natural feel
      variation *= 0.5 + Math.random() * 1;

      return Math.max(1, Math.round(baseSpeed * variation));
    },
    [realisticTyping, pauseOnPunctuation, speed],
  );

  const [displayedText, setDisplayedText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const delayTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const currentIndexRef = useRef(0);

  const startStreaming = useCallback(() => {
    if (isStreaming || isComplete) return;

    setIsStreaming(true);
    setIsComplete(false);
    currentIndexRef.current = 0;

    // Clear any existing intervals/timeouts
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (delayTimeoutRef.current) clearTimeout(delayTimeoutRef.current);

    const streamNext = () => {
      if (currentIndexRef.current >= text.length) {
        setIsComplete(true);
        setIsStreaming(false);
        restOptions.onComplete?.();
        return;
      }

      const char = text[currentIndexRef.current];

      setDisplayedText((prev) => prev + char);
      currentIndexRef.current += 1;

      // Calculate delay based on character type
      let nextDelay = interval;

      if (char === " ") {
        // Faster on spaces
        nextDelay = interval;
      } else if (pauseOnPunctuation && /[.!?;:,]/.test(char)) {
        // Use punctuationDelay for punctuation marks
        nextDelay = punctuationDelay + Math.random() * 50;
      } else if (realisticTyping) {
        // Apply realistic typing variation with position awareness
        const speedVariation = getTypingSpeed(
          char,
          currentIndexRef.current,
          text.length,
        );
        nextDelay = interval * speedVariation + Math.random() * 20;
      } else {
        // Default variation
        nextDelay = interval + Math.random() * 20;
      }

      intervalRef.current = setTimeout(streamNext, nextDelay);
    };

    // Start streaming after delay
    delayTimeoutRef.current = setTimeout(streamNext, restOptions.delay || 0);
  }, [
    text,
    getTypingSpeed,
    interval,
    isStreaming,
    isComplete,
    pauseOnPunctuation,
    punctuationDelay,
    realisticTyping,
    restOptions,
  ]);

  const stopStreaming = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (delayTimeoutRef.current) {
      clearTimeout(delayTimeoutRef.current);
      delayTimeoutRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const resetStreaming = useCallback(() => {
    stopStreaming();
    setDisplayedText("");
    setIsComplete(false);
    setIsStreaming(false);
    currentIndexRef.current = 0;
  }, [stopStreaming]);

  // Cleanup on unmount
  useEffect(
    () => () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (delayTimeoutRef.current) clearTimeout(delayTimeoutRef.current);
    },
    [],
  );

  // Calculate progress percentage
  const progress =
    text.length > 0 ? (displayedText.length / text.length) * 100 : 0;

  return {
    displayedText,
    isStreaming,
    isComplete,
    startStreaming,
    stopStreaming,
    resetStreaming,
    progress,
  };
}
