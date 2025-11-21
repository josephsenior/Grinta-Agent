import { useState, useCallback, useRef, useEffect } from "react";

interface UseLoadingStateOptions {
  initialLoading?: boolean;
  delay?: number; // Delay before showing loading state (in ms)
  minDuration?: number; // Minimum duration to show loading state (in ms)
}

interface UseLoadingStateReturn {
  isLoading: boolean;
  setLoading: (loading: boolean) => void;
  withLoading: <T>(asyncFn: () => Promise<T>) => Promise<T>;
  withLoadingSync: <T>(syncFn: () => T) => T;
}

export function useLoadingState(
  options: UseLoadingStateOptions = {},
): UseLoadingStateReturn {
  const { initialLoading = false, delay = 0, minDuration = 0 } = options;

  const [isLoading, setIsLoading] = useState(initialLoading);
  const [isDelayed, setIsDelayed] = useState(false);
  const delayTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const minDurationTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number | null>(null);

  const setLoading = useCallback(
    (loading: boolean) => {
      if (loading) {
        startTimeRef.current = Date.now();

        if (delay > 0) {
          // Clear any existing delay timeout
          if (delayTimeoutRef.current) {
            clearTimeout(delayTimeoutRef.current);
          }

          // Set delayed loading state
          delayTimeoutRef.current = setTimeout(() => {
            setIsDelayed(true);
          }, delay);
        } else {
          setIsDelayed(true);
        }
      } else {
        // Clear delay timeout if it exists
        if (delayTimeoutRef.current) {
          clearTimeout(delayTimeoutRef.current);
          delayTimeoutRef.current = null;
        }

        if (minDuration > 0 && startTimeRef.current) {
          const elapsed = Date.now() - startTimeRef.current;
          const remaining = minDuration - elapsed;

          if (remaining > 0) {
            // Wait for minimum duration before hiding loading state
            minDurationTimeoutRef.current = setTimeout(() => {
              setIsLoading(false);
              setIsDelayed(false);
              startTimeRef.current = null;
            }, remaining);
          } else {
            setIsLoading(false);
            setIsDelayed(false);
            startTimeRef.current = null;
          }
        } else {
          setIsLoading(false);
          setIsDelayed(false);
          startTimeRef.current = null;
        }
      }
    },
    [delay, minDuration],
  );

  // Update isLoading based on isDelayed
  useEffect(() => {
    setIsLoading(isDelayed);
  }, [isDelayed]);

  // Cleanup timeouts on unmount
  useEffect(
    () => () => {
      if (delayTimeoutRef.current) {
        clearTimeout(delayTimeoutRef.current);
      }
      if (minDurationTimeoutRef.current) {
        clearTimeout(minDurationTimeoutRef.current);
      }
    },
    [],
  );

  const withLoading = useCallback(
    async <T>(asyncFn: () => Promise<T>): Promise<T> => {
      setLoading(true);
      try {
        const result = await asyncFn();
        return result;
      } finally {
        setLoading(false);
      }
    },
    [setLoading],
  );

  const withLoadingSync = useCallback(
    <T>(syncFn: () => T): T => {
      setLoading(true);
      try {
        const result = syncFn();
        return result;
      } finally {
        setLoading(false);
      }
    },
    [setLoading],
  );

  return {
    isLoading,
    setLoading,
    withLoading,
    withLoadingSync,
  };
}

// Hook for managing multiple loading states
export function useMultipleLoadingStates(keys: string[]) {
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>(
    keys.reduce((acc, key) => ({ ...acc, [key]: false }), {}),
  );

  const setLoading = useCallback((key: string, loading: boolean) => {
    setLoadingStates((prev) => ({
      ...prev,
      [key]: loading,
    }));
  }, []);

  const withLoading = useCallback(
    async <T>(key: string, asyncFn: () => Promise<T>): Promise<T> => {
      setLoading(key, true);
      try {
        const result = await asyncFn();
        return result;
      } finally {
        setLoading(key, false);
      }
    },
    [setLoading],
  );

  const isLoading = (key: string) => loadingStates[key] || false;
  const isAnyLoading = Object.values(loadingStates).some(Boolean);
  const isAllLoading = Object.values(loadingStates).every(Boolean);

  return {
    loadingStates,
    setLoading,
    withLoading,
    isLoading,
    isAnyLoading,
    isAllLoading,
  };
}

// Hook for managing async operations with error handling
export function useAsyncOperation<T = any>() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [data, setData] = useState<T | null>(null);

  const execute = useCallback(async (asyncFn: () => Promise<T>) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await asyncFn();
      setData(result);
      return result;
    } catch (err) {
      const caughtError = err instanceof Error ? err : new Error(String(err));
      setError(caughtError);
      throw caughtError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setIsLoading(false);
    setError(null);
    setData(null);
  }, []);

  return {
    isLoading,
    error,
    data,
    execute,
    reset,
  };
}
