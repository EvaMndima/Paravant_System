/**
 * ConnectionBanner — Fixed top banner showing SSE/REST connection status.
 * Self-contained: uses internal hooks (useEventStream, useHealthCheck).
 *
 * Two states:
 * - SSE disconnected/connecting: amber "Live connection lost. Reconnecting..."
 * - SSE + REST health failed: red "Connection lost. Data may be stale."
 *
 * Auto-hides when SSE reconnects. Placed in MainLayout as <ConnectionBanner />.
 */
import React, { useState } from 'react';
import { Wifi, WifiOff, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useEventStream, useHealthCheck } from '@/hooks';
import { cn } from '@/lib/utils';

export const ConnectionBanner: React.FC = () => {
  const [dismissed, setDismissed] = useState(false);

  // useEventStream returns { connected: boolean, reconnectAttempt: number }
  const { connected: sseConnected, reconnectAttempt } = useEventStream();
  // useHealthCheck polls /health endpoint
  const healthQuery = useHealthCheck();

  const healthOk = healthQuery.data?.status === 'ok';

  // Reset dismiss when connection is lost again
  // (so the banner re-appears if connection drops after being dismissed)
  React.useEffect(() => {
    if (!sseConnected) setDismissed(false);
  }, [sseConnected]);

  // Determine visibility and severity
  const visible = !sseConnected && !dismissed;
  const isFullyDown = !sseConnected && !healthOk;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: -60, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -60, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className={cn(
            'fixed top-0 left-0 right-0 z-[200] flex items-center justify-center gap-3',
            'px-4 py-2.5 text-sm font-medium',
            isFullyDown
              ? 'bg-loss/90 text-white'
              : 'bg-warning/20 text-warning border-b border-warning/30',
          )}
          role="alert"
          aria-live="polite"
        >
          {isFullyDown ? (
            <WifiOff className="w-4 h-4 flex-shrink-0" />
          ) : (
            <Wifi className="w-4 h-4 flex-shrink-0 animate-pulse" />
          )}
          <span>
            {isFullyDown
              ? '❌ Connection lost. Data may be stale.'
              : `⚠️ Live connection lost. Reconnecting${reconnectAttempt > 0 ? ` (attempt ${reconnectAttempt})` : ''}...`}
          </span>
          {/* Allow dismissing non-critical banners */}
          {!isFullyDown && (
            <button
              onClick={() => setDismissed(true)}
              className="ml-auto p-0.5 rounded hover:bg-warning/20 transition-colors"
              aria-label="Dismiss banner"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
};
