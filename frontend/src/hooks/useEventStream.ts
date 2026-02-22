import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface EventStreamStatus {
  connected: boolean;
  reconnectAttempt: number;
}

/**
 * SSE (Server-Sent Events) hook for real-time updates
 * Handles automatic reconnection with exponential backoff
 * Updates react-query cache automatically on events
 */
export function useEventStream() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<EventStreamStatus>({
    connected: false,
    reconnectAttempt: 0,
  });

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let reconnectAttempt = 0;
    const maxReconnectDelay = 30000; // 30 seconds max

    const connect = () => {
      eventSource = new EventSource('/api/v1/events/stream');

      eventSource.onopen = () => {
        setStatus({ connected: true, reconnectAttempt: 0 });
        reconnectAttempt = 0;
      };

      eventSource.onerror = () => {
        eventSource?.close();
        setStatus({ connected: false, reconnectAttempt });

        // Exponential backoff: 1s → 2s → 4s → 8s → 16s → max 30s
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempt), maxReconnectDelay);
        reconnectAttempt++;

        setTimeout(connect, delay);
      };

      // ========== Event Handlers ==========

      // Kill switch changed (Tier 1 - Critical)
      eventSource.addEventListener('kill_switch_changed', (e) => {
        const data = JSON.parse(e.data);
        queryClient.setQueryData(['risk', 'kill-switch'], data.data);
      });

      // System status changed (Tier 1)
      eventSource.addEventListener('system_status_changed', (e) => {
        const data = JSON.parse(e.data);
        queryClient.setQueryData(['system', 'status'], data.data);
      });

      // Position updated (Tier 1)
      eventSource.addEventListener('position_updated', (e) => {
        JSON.parse(e.data);
        // Invalidate both dashboard positions and full position list
        queryClient.invalidateQueries({ queryKey: ['dashboard', 'positions'] });
        queryClient.invalidateQueries({ queryKey: ['positions'] });
      });

      // Alert created (Tier 1)
      eventSource.addEventListener('alert_created', (e) => {
        JSON.parse(e.data);
        queryClient.invalidateQueries({ queryKey: ['dashboard', 'alerts'] });
      });

      // Risk status changed (Tier 1)
      eventSource.addEventListener('risk_status_changed', (e) => {
        const data = JSON.parse(e.data);
        queryClient.setQueryData(['risk', 'status'], data.data);
      });

      // Regime changed (Tier 1 - triggers dashboard refresh)
      eventSource.addEventListener('regime_changed', (e) => {
        const data = JSON.parse(e.data);
        queryClient.setQueryData(['system', 'regime'], data.data);
        // Invalidate dashboard since regime affects strategy behavior
        queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] });
      });
    };

    connect();

    return () => {
      eventSource?.close();
    };
  }, [queryClient]);

  return status;
}
