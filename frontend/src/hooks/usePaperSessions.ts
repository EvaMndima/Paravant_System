import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const POLL_INTERVAL_MS = 60_000;

export interface PaperSessionSummary {
  sessionId: string;
  templateId: string;
  symbol: string;
  initialCapital: number;
  currentEquity: number;
  pnlUsdt: number;
  pnlPct: number;
  pnlDayUsdt: number;
  totalTrades: number;
  isActive: boolean;
  startedAt: string;
  lastUpdated: string;
  sparkline: number[];
}

export interface UsePaperSessionsResult {
  sessions: PaperSessionSummary[];
  isLoading: boolean;
  error: string | null;
}

function mapSession(raw: Record<string, unknown>): PaperSessionSummary {
  return {
    sessionId:      String(raw.session_id ?? ''),
    templateId:     String(raw.template_id ?? ''),
    symbol:         String(raw.symbol ?? ''),
    initialCapital: Number(raw.initial_capital ?? 0),
    currentEquity:  Number(raw.current_equity ?? 0),
    pnlUsdt:        Number(raw.pnl_usdt ?? 0),
    pnlPct:         Number(raw.pnl_pct ?? 0),
    pnlDayUsdt:     Number(raw.pnl_day_usdt ?? 0),
    totalTrades:    Number(raw.total_trades ?? 0),
    isActive:       Boolean(raw.is_active),
    startedAt:      String(raw.started_at ?? ''),
    lastUpdated:    String(raw.last_updated ?? ''),
    sparkline:      Array.isArray(raw.sparkline)
      ? (raw.sparkline as number[])
      : [],
  };
}

async function fetchSessions(signal: AbortSignal): Promise<PaperSessionSummary[]> {
  const res = await fetch(`${API_BASE}/api/v1/regime/paper-sessions`, { signal });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  const rows: Record<string, unknown>[] = Array.isArray(json.sessions) ? json.sessions : [];
  return rows.map(mapSession);
}

export function usePaperSessions(): UsePaperSessionsResult {
  const [sessions, setSessions] = useState<PaperSessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const controller = new AbortController();
      try {
        const data = await fetchSessions(controller.signal);
        if (!cancelled) {
          setSessions(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled && (err as Error).name !== 'AbortError') {
          setError((err as Error).message);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    const id = setInterval(load, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return { sessions, isLoading, error };
}
