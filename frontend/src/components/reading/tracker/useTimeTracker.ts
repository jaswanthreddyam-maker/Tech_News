import { useEffect, useRef, useState, useCallback } from 'react';

export function useTimeTracker(isActive: boolean) {
  const [accumulatedSeconds, setAccumulatedSeconds] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isActive) {
      intervalRef.current = setInterval(() => {
        setAccumulatedSeconds(prev => prev + 1);
      }, 1000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isActive]);

  const reset = useCallback(() => setAccumulatedSeconds(0), []);

  return { accumulatedSeconds, reset };
}
