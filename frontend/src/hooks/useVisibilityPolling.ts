import { useEffect, useState } from 'react';

/**
 * Hook that returns a polling interval only when the page is visible
 * Returns false when page is hidden to stop polling (saves API requests)
 *
 * @param intervalMs - Polling interval in milliseconds when visible
 * @returns interval (ms) when visible, false when hidden
 */
export function useVisibilityPolling(intervalMs: number): number | false {
  const [isVisible, setIsVisible] = useState(!document.hidden);

  useEffect(() => {
    const handler = () => setIsVisible(!document.hidden);
    document.addEventListener('visibilitychange', handler);
    return () => document.removeEventListener('visibilitychange', handler);
  }, []);

  return isVisible ? intervalMs : false;
}
