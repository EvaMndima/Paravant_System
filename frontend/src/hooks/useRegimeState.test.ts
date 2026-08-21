/**
 * Tests for useRegimeState.
 *
 * This hook is one of only three places the frontend actually talks to the
 * backend, so it is the highest-value thing in the UI to pin down. What is
 * being defended is the failure behaviour: the hook must degrade to a stated
 * "unknown" regime rather than throwing or hanging, because the regime badge
 * is what an operator reads to decide whether the router is even active.
 */
import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useRegimeState } from './useRegimeState';

const POLL_INTERVAL_MS = 30_000;

/**
 * Advance fake timers and let React commit the resulting state.
 *
 * `advanceTimersByTimeAsync` alone is not enough. The hook's load path awaits
 * twice (fetch, then res.json()) before calling setState, and React 19 will
 * not flush a state update queued outside `act`. Without this wrapper the
 * assertions run against the render before the fetch resolved.
 */
async function advance(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => body,
  } as Response;
}

describe('useRegimeState', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('starts in a loading state with no regime', () => {
    vi.mocked(fetch).mockReturnValue(new Promise(() => {})); // never settles

    const { result } = renderHook(() => useRegimeState());

    expect(result.current.isLoading).toBe(true);
    expect(result.current.regime).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('maps the API snake_case payload onto camelCase fields', async () => {
    // The backend returns updated_at; the UI reads updatedAt. This mapping is
    // the kind of thing that breaks silently on an API rename.
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({
        state: 'trending_bull',
        updated_at: '2026-08-15T10:00:00Z',
        source: 'sub_regime_detector',
      }),
    );

    const { result } = renderHook(() => useRegimeState());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.regime).toEqual({
      state: 'trending_bull',
      updatedAt: '2026-08-15T10:00:00Z',
      source: 'sub_regime_detector',
    });
    expect(result.current.error).toBeNull();
  });

  it('substitutes "unknown" for missing fields rather than rendering undefined', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}));

    const { result } = renderHook(() => useRegimeState());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.regime).toEqual({
      state: 'unknown',
      updatedAt: null,
      source: 'unknown',
    });
  });

  it('surfaces a non-2xx response as an error and falls back to unknown', async () => {
    // Fail-visible, not fail-silent: an operator must be able to tell the
    // difference between "regime is genuinely unknown" and "we could not ask".
    vi.mocked(fetch).mockResolvedValue(jsonResponse(null, false, 503));

    const { result } = renderHook(() => useRegimeState());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe('HTTP 503');
    expect(result.current.regime?.state).toBe('unknown');
  });

  it('surfaces a network rejection as an error', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('Failed to fetch'));

    const { result } = renderHook(() => useRegimeState());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe('Failed to fetch');
    expect(result.current.regime?.state).toBe('unknown');
  });

  it('calls the regime endpoint', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ state: 'ranging' }));

    renderHook(() => useRegimeState());

    await waitFor(() => expect(fetch).toHaveBeenCalled());
    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toContain('/api/v1/regime/current');
  });

  it('polls on an interval', async () => {
    vi.useFakeTimers();
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ state: 'ranging' }));

    renderHook(() => useRegimeState());
    await advance(0);
    expect(fetch).toHaveBeenCalledTimes(1);

    await advance(POLL_INTERVAL_MS);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('stops polling after unmount', async () => {
    // A leaked interval keeps hitting the API for the life of the tab and
    // logs a React warning on every tick.
    vi.useFakeTimers();
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ state: 'ranging' }));

    const { unmount } = renderHook(() => useRegimeState());
    await advance(0);
    const callsBeforeUnmount = vi.mocked(fetch).mock.calls.length;

    unmount();
    await advance(POLL_INTERVAL_MS * 3);

    expect(vi.mocked(fetch).mock.calls.length).toBe(callsBeforeUnmount);
  });

  it('clears a previous error once a poll succeeds again', async () => {
    vi.useFakeTimers();
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(null, false, 503))
      .mockResolvedValue(jsonResponse({ state: 'trending_bull' }));

    const { result } = renderHook(() => useRegimeState());
    await advance(0);
    expect(result.current.error).toBe('HTTP 503');

    await advance(POLL_INTERVAL_MS);
    expect(result.current.error).toBeNull();
    expect(result.current.regime?.state).toBe('trending_bull');
  });

  it('keeps the last good regime when a later poll fails', async () => {
    // Regression guard for a fixed defect. The catch block used to read
    // `regime` from the first render's closure (the effect has an empty
    // dependency array), so it was always null and the "fall back to unknown"
    // branch always fired. One transient network blip discarded a valid regime
    // and replaced it with "unknown" -- and the router reads regime state to
    // decide whether strategies activate. Better a stale reading, clearly
    // flagged as errored, than a wrong one.
    vi.useFakeTimers();
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ state: 'trending_bull' }))
      .mockRejectedValue(new Error('network blip'));

    const { result } = renderHook(() => useRegimeState());
    await advance(0);
    expect(result.current.regime?.state).toBe('trending_bull');

    await advance(POLL_INTERVAL_MS);

    // Regime preserved, and the failure is still surfaced rather than hidden.
    expect(result.current.regime?.state).toBe('trending_bull');
    expect(result.current.error).toBe('network blip');
  });

  it('still falls back to unknown when the very first poll fails', async () => {
    // The fallback must survive for the case it was written for: no reading
    // has ever succeeded, so there is nothing to preserve.
    vi.useFakeTimers();
    vi.mocked(fetch).mockRejectedValue(new Error('down from the start'));

    const { result } = renderHook(() => useRegimeState());
    await advance(0);

    expect(result.current.regime?.state).toBe('unknown');
    expect(result.current.error).toBe('down from the start');
  });
});
