import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const POLL_INTERVAL_MS = 30_000;

export interface RegimeStateData {
  state: string;
  updatedAt: string | null;
  source: string;
}

export interface UseRegimeStateResult {
  regime: RegimeStateData | null;
  isLoading: boolean;
  error: string | null;
}

const REGIME_DEFAULTS: RegimeStateData = {
  state: 'unknown',
  updatedAt: null,
  source: 'unknown',
};

async function fetchRegime(signal: AbortSignal): Promise<RegimeStateData> {
  const res = await fetch(`${API_BASE}/api/v1/regime/current`, { signal });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  return {
    state: json.state ?? 'unknown',
    updatedAt: json.updated_at ?? null,
    source: json.source ?? 'unknown',
  };
}

export function useRegimeState(): UseRegimeStateResult {
  const [regime, setRegime] = useState<RegimeStateData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const controller = new AbortController();
      try {
        const data = await fetchRegime(controller.signal);
        if (!cancelled) {
          setRegime(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled && (err as Error).name !== 'AbortError') {
          setError((err as Error).message);
          if (regime === null) setRegime(REGIME_DEFAULTS);
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
    // regime intentionally excluded — we don't want to restart the interval when it updates
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { regime, isLoading, error };
}
