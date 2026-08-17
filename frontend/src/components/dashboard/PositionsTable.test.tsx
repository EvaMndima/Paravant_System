/**
 * Tests for PositionsTable.
 *
 * The behaviour worth defending is not that it renders a table -- it is the
 * three states around the table. Loading must not show stale rows, an empty
 * result must say so rather than showing nothing, and a loss must be visually
 * distinguishable from a gain. The P&L sign handling is the one a reviewer
 * would catch on a demo and the one that matters to an operator.
 *
 * It also pins the mock-data fallback, which is a real footgun rather than a
 * feature -- see the test that documents it.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { Position } from './PositionsTable';
import { PositionsTable } from './PositionsTable';

function position(overrides: Partial<Position> = {}): Position {
  return {
    id: 'p1',
    symbol: 'BTCUSDT',
    name: 'Bitcoin',
    quantity: 0.5,
    avgPrice: 50_000,
    currentPrice: 52_000,
    pl: 1_000,
    plPercent: 4,
    weight: 25,
    ...overrides,
  };
}

describe('PositionsTable', () => {
  describe('rendering supplied data', () => {
    it('renders a row per supplied position', () => {
      render(
        <PositionsTable
          data={[
            position({ id: 'a', symbol: 'BTCUSDT' }),
            position({ id: 'b', symbol: 'ETHUSDT', name: 'Ethereum' }),
          ]}
        />,
      );

      expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
      expect(screen.getByText('ETHUSDT')).toBeInTheDocument();
    });

    it('formats the mark price as currency', () => {
      render(<PositionsTable data={[position({ currentPrice: 52_000 })]} />);

      expect(screen.getByText('$52,000.00')).toBeInTheDocument();
    });

    it('honours the limit prop', () => {
      render(
        <PositionsTable
          limit={1}
          data={[
            position({ id: 'a', symbol: 'BTCUSDT' }),
            position({ id: 'b', symbol: 'ETHUSDT' }),
          ]}
        />,
      );

      expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
      expect(screen.queryByText('ETHUSDT')).not.toBeInTheDocument();
    });

    it('renders a custom title', () => {
      render(<PositionsTable data={[position()]} title="Open Positions" />);

      expect(screen.getByText('Open Positions')).toBeInTheDocument();
    });
  });

  describe('profit and loss presentation', () => {
    it('prefixes a gain with + and marks it as a gain', () => {
      render(<PositionsTable data={[position({ pl: 1_000 })]} />);

      const cell = screen.getByText('+$1,000.00');
      expect(cell).toHaveClass('text-gain');
    });

    it('marks a loss without adding a + and uses the loss colour', () => {
      // A loss rendered in the gain colour, or with a + prefix, misreports the
      // account to the operator.
      render(<PositionsTable data={[position({ pl: -2_500 })]} />);

      const cell = screen.getByText('-$2,500.00');
      expect(cell).toHaveClass('text-loss');
      expect(cell.textContent).not.toContain('+');
    });

    it('treats exactly zero as a gain, not a loss', () => {
      // Boundary: `>= 0` is the implementation's rule. Pinned so a future
      // change to `> 0` is a visible decision rather than an accident.
      render(<PositionsTable data={[position({ pl: 0 })]} />);

      expect(screen.getByText('+$0.00')).toHaveClass('text-gain');
    });

    it('renders the percentage as an absolute value with a direction icon', () => {
      // The sign is carried by the icon, so the number itself is unsigned.
      render(<PositionsTable data={[position({ plPercent: -28.41 })]} />);

      expect(screen.getByText('28.41%')).toBeInTheDocument();
    });
  });

  describe('empty and loading states', () => {
    it('shows the empty state for an explicitly empty result', () => {
      render(<PositionsTable data={[]} />);

      expect(screen.getByText('No positions found')).toBeInTheDocument();
    });

    it('does not render position rows while loading', () => {
      // Showing the previous result during a refresh is how an operator ends
      // up acting on a stale number.
      render(<PositionsTable data={[position({ symbol: 'BTCUSDT' })]} isLoading />);

      expect(screen.queryByText('BTCUSDT')).not.toBeInTheDocument();
    });
  });

  describe('interaction', () => {
    it('passes the clicked position to onPositionClick', async () => {
      const onPositionClick = vi.fn();
      const row = position({ id: 'clicked', symbol: 'BTCUSDT' });
      render(<PositionsTable data={[row]} onPositionClick={onPositionClick} />);

      await userEvent.click(screen.getByText('BTCUSDT'));

      expect(onPositionClick).toHaveBeenCalledTimes(1);
      expect(onPositionClick.mock.calls[0][0]).toMatchObject({ id: 'clicked' });
    });

    it('does not throw when clicked without a handler', async () => {
      render(<PositionsTable data={[position({ symbol: 'BTCUSDT' })]} />);

      await userEvent.click(screen.getByText('BTCUSDT'));

      expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    });
  });

  describe('absent data', () => {
    it('shows the empty state when data is omitted entirely', () => {
      // Regression guard for a removed footgun. This component used to fall
      // back to six hardcoded equity positions (NVDA, MSFT, TSLA...) when
      // `data` was undefined -- in a crypto-only system. A fetch that returned
      // undefined would have presented fabricated holdings as real, with
      // plausible P&L. Omitting data must now be indistinguishable from having
      // none.
      render(<PositionsTable />);

      expect(screen.getByText('No positions found')).toBeInTheDocument();
    });

    it('renders no equity symbols anywhere, with or without data', () => {
      // The mock list is gone rather than merely unreachable. If it is ever
      // reintroduced, this fails.
      const { container } = render(<PositionsTable />);

      for (const symbol of ['NVDA', 'MSFT', 'TSLA', 'AAPL', 'GOOGL']) {
        expect(container.textContent).not.toContain(symbol);
      }
    });

    it('treats an omitted data prop the same as an empty array', () => {
      const omitted = render(<PositionsTable />);
      const omittedText = omitted.container.textContent;
      omitted.unmount();

      const empty = render(<PositionsTable data={[]} />);

      expect(empty.container.textContent).toBe(omittedText);
    });
  });
});
