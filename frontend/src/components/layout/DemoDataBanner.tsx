import React from 'react';

/**
 * Persistent notice that most of this dashboard renders demonstration data.
 *
 * The frontend makes three real network calls in total -- regime state, paper
 * sessions, and backtest results. Every other view renders static seed arrays
 * driven by `useRealtimeSimulation`, which fabricates price and P&L ticks on
 * timers.
 *
 * That is honest in the source, but it was not visible on screen, and a
 * screenshot of a trading dashboard is read as live state by default. This
 * banner makes the distinction impossible to miss without requiring anyone to
 * open a file.
 *
 * It is deliberately not dismissible. A notice you can close is a notice that
 * is absent from the screenshot someone actually takes.
 */
export const DemoDataBanner: React.FC = () => (
  <div
    role="note"
    aria-label="Demonstration data notice"
    className="
      w-full border-b
      border-amber-400/40 dark:border-amber-300/25
      bg-amber-50 dark:bg-amber-500/10
      px-4 py-2
      text-center text-xs sm:text-sm
      text-amber-900 dark:text-amber-200
    "
  >
    <span className="font-semibold">Demonstration data.</span>{' '}
    Most views render static seed values, not live trading state. No strategy in
    this system has passed its validation gates, and live trading is disabled.
    See <code className="font-mono">docs/RESEARCH_FINDINGS.md</code>.
  </div>
);
