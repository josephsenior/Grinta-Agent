import React from "react";

interface UseRateProps {
  threshold: number;
}

const DEFAULT_CONFIG: UseRateProps = { threshold: 1000 };

export const useRate = (config = DEFAULT_CONFIG) => {
  // Circular buffer: only the last 2 entries are ever needed for rate calc.
  const bufferRef = React.useRef<[number | null, number | null]>([null, null]);
  const [rate, setRate] = React.useState<number | null>(null);
  const [lastUpdated, setLastUpdated] = React.useState<number | null>(null);
  const [isUnderThreshold, setIsUnderThreshold] = React.useState(true);

  /**
   * Record an entry in order to calculate the rate.
   * Internally keeps only the last 2 timestamps (constant memory).
   * @param entry Timestamp to record
   *
   * @example
   * record(Date.now());
   */
  const record = React.useCallback(
    (entry: number) => {
      const buf = bufferRef.current;
      // Shift: previous "current" becomes "previous", new entry becomes "current"
      buf[0] = buf[1];
      buf[1] = entry;
      setLastUpdated(entry);

      if (buf[0] !== null && buf[1] !== null) {
        const newRate = buf[1] - buf[0];
        setRate(newRate);
        setIsUnderThreshold(newRate <= config.threshold);
      }
    },
    [config.threshold],
  );

  React.useEffect(() => {
    // Interval to detect inactivity: if time since last update
    // exceeds threshold, mark as not under threshold.
    const intervalId = setInterval(() => {
      if (lastUpdated !== null) {
        const timeSinceLastUpdate = Date.now() - lastUpdated;
        setIsUnderThreshold(timeSinceLastUpdate <= config.threshold);
      } else {
        setIsUnderThreshold(false);
      }
    }, config.threshold);

    return () => clearInterval(intervalId);
  }, [lastUpdated, config.threshold]);

  return {
    rate,
    lastUpdated,
    isUnderThreshold,
    record,
  };
};
