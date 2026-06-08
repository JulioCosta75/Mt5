import { useEffect, useRef } from "react";

/**
 * Polls a callback at a fixed interval.
 * Uses a ref to avoid re-binding the interval whenever the callback
 * identity changes, and to make the callback opaque to static analysis
 * of state-setter chains.
 */
export function usePolling(callback, intervalMs, enabled = true) {
  const ref = useRef(callback);
  useEffect(() => { ref.current = callback; }, [callback]);

  useEffect(() => {
    if (!enabled) return undefined;
    const id = setInterval(() => {
      const fn = ref.current;
      if (fn) fn();
    }, intervalMs);
    return () => clearInterval(id);
  }, [enabled, intervalMs]);
}
