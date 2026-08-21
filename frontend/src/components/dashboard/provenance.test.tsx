/**
 * Fabricated financial values must be visibly labelled, and must stay labelled.
 *
 * Two kinds of test, because they fail differently.
 *
 * `TestTheMechanismWorks` renders charts and asserts the banner appears for
 * synthetic and untagged data and does not appear for live data. It proves the
 * contract does what it says.
 *
 * `TestNoComponentCanOptOut` reads the source of every dashboard component,
 * finds the ones that call `Math.random()`, and asserts each is
 * provenance-aware. That is the one that matters. A rendering test can only
 * cover components someone remembered to add to it; this one covers a component
 * written six months from now by someone who has not read any of this.
 *
 * @see ../../lib/provenance
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ThemeProvider } from '@/contexts/ThemeContext';

import { DrawdownChart } from './DrawdownChart';
import { EquityChart } from './EquityChart';
import { TradeHistoryTable } from './TradeHistoryTable';

const BADGE = 'synthetic-data-badge';

/**
 * Render inside the providers a chart needs.
 *
 * `AreaChart` calls `useTheme`, which throws outside a `ThemeProvider`. Wrapping
 * here rather than mocking the context keeps these tests exercising the real
 * component tree -- the badge is rendered by the component under test, not by a
 * stand-in.
 */
function renderChart(ui: React.ReactElement) {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
}

describe('the mechanism works', () => {
  describe('EquityChart', () => {
    it('labels generated data', () => {
      renderChart(<EquityChart />);
      expect(screen.getByTestId(BADGE)).toBeInTheDocument();
    });

    it('labels supplied data that is not declared live', () => {
      renderChart(<EquityChart data={[{ date: 'Jan 1', value: 100 }]} />);
      expect(screen.getByTestId(BADGE)).toBeInTheDocument();
    });

    it('does not label data declared live', () => {
      renderChart(
        <EquityChart data={[{ date: 'Jan 1', value: 100 }]} dataProvenance="live" />,
      );
      expect(screen.queryByTestId(BADGE)).not.toBeInTheDocument();
    });

    it('labels generated data even when the caller claims it is live', () => {
      // The mistake this is here to make impossible: declaring `live` while
      // passing no data, so the component generates a series and the caller's
      // claim launders it.
      renderChart(<EquityChart dataProvenance="live" />);
      expect(screen.getByTestId(BADGE)).toBeInTheDocument();
    });
  });

  describe('DrawdownChart', () => {
    it('labels generated data', () => {
      renderChart(<DrawdownChart />);
      expect(screen.getByTestId(BADGE)).toBeInTheDocument();
    });

    it('does not label data declared live', () => {
      renderChart(
        <DrawdownChart
          data={[{ date: 'Jan 1', drawdown: -1 }]}
          dataProvenance="live"
        />,
      );
      expect(screen.queryByTestId(BADGE)).not.toBeInTheDocument();
    });
  });

  describe('TradeHistoryTable', () => {
    it('labels its built-in mock trades', () => {
      renderChart(<TradeHistoryTable />);
      expect(screen.getByTestId(BADGE)).toBeInTheDocument();
    });

    it('does not label supplied trades declared live', () => {
      renderChart(<TradeHistoryTable trades={[]} dataProvenance="live" />);
      expect(screen.queryByTestId(BADGE)).not.toBeInTheDocument();
    });
  });

  it('the badge says what it is, in text a reader will see', () => {
    renderChart(<EquityChart />);
    expect(screen.getByTestId(BADGE)).toHaveTextContent(/sample/i);
  });
});

/**
 * The structural guard.
 *
 * Enumerating the filesystem rather than a hardcoded list is the whole point.
 * A list has to be updated by the person adding the eighth component, which is
 * the same person who forgot the banner.
 */
describe('no component can opt out', () => {
  // Vite's glob rather than node:fs. This project's tsconfig has no node types
  // -- it is a browser bundle -- and reading through the bundler means the test
  // sees exactly the module set the build sees.
  const sources = import.meta.glob('./*.tsx', {
    query: '?raw',
    import: 'default',
    eager: true,
  }) as Record<string, string>;

  /** Components that fabricate values in the browser. */
  const fabricating = Object.entries(sources)
    .filter(([file]) => !file.includes('.test.'))
    .filter(([, source]) => source.includes('Math.random'))
    .map(([file, source]) => ({ name: file.replace('./', ''), source }));

  it('finds the components known to fabricate data', () => {
    // Guards the guard. If a refactor moves these elsewhere the filter silently
    // matches nothing and every assertion below passes vacuously -- the same
    // trap `test_claim_is_actually_stated_somewhere` covers on the Python side.
    expect(fabricating.length).toBeGreaterThanOrEqual(7);
  });

  // A plain loop rather than `it.each`: vitest's each-typing rejects a bare
  // string[] under this project's tsconfig, and a loop reads more clearly here
  // anyway -- each file gets its own named test, which is what makes a failure
  // point at the offending component.
  for (const { name, source } of fabricating) {
    describe(name, () => {
      it('renders the synthetic-data badge', () => {
        expect(source).toContain('SyntheticDataBadge');
      });

      it('decides whether to show it via requiresSyntheticLabel', () => {
        // Asserting the helper rather than any conditional: a component that
        // hand-rolls `provenance === 'synthetic'` gets the fail-open default
        // wrong for untagged data, which is the case this exists to catch.
        expect(source).toContain('requiresSyntheticLabel');
      });

      it('resolves provenance rather than trusting the caller', () => {
        expect(source).toContain('resolveProvenance');
      });
    });
  }
});
