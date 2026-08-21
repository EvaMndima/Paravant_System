/**
 * Tests for the shared formatters.
 *
 * These are the lowest-level functions in the UI and the most widely used --
 * every currency figure on every page passes through `formatCurrency`. A
 * regression here is silent: the number still renders, it is just wrong.
 *
 * The negative-number and percent-scaling cases matter most. A P&L display
 * that loses a minus sign, or a percentage that renders 5% as 500%, is the
 * kind of defect a reviewer clicking through a demo would spot immediately.
 */
import { describe, expect, it } from 'vitest';

import { cn, formatCurrency, formatNumber, formatPercent, getStaggerDelay } from './utils';

describe('formatCurrency', () => {
  it('formats a positive value as USD with two decimals', () => {
    expect(formatCurrency(1234.5)).toBe('$1,234.50');
  });

  it('keeps the sign on a negative value', () => {
    // A P&L cell that drops this reads as a gain.
    expect(formatCurrency(-1234.5)).toBe('-$1,234.50');
  });

  it('formats zero without a sign', () => {
    expect(formatCurrency(0)).toBe('$0.00');
  });

  it('always shows exactly two decimals', () => {
    expect(formatCurrency(1000)).toBe('$1,000.00');
    expect(formatCurrency(0.5)).toBe('$0.50');
  });

  it('rounds rather than truncates at the third decimal', () => {
    expect(formatCurrency(1.005)).toBe('$1.01');
    expect(formatCurrency(1.004)).toBe('$1.00');
  });

  it('groups thousands', () => {
    expect(formatCurrency(1_234_567.89)).toBe('$1,234,567.89');
  });
});

describe('formatPercent', () => {
  it('treats the input as a percentage, not a fraction', () => {
    // The function divides by 100 internally. Passing 0.05 expecting "5%" is
    // the obvious misuse, and this pins which convention callers must follow.
    expect(formatPercent(5)).toBe('5.00%');
    expect(formatPercent(0.05)).toBe('0.05%');
  });

  it('keeps the sign on a negative percentage', () => {
    expect(formatPercent(-12.34)).toBe('-12.34%');
  });

  it('formats zero', () => {
    expect(formatPercent(0)).toBe('0.00%');
  });

  it('handles values above 100', () => {
    expect(formatPercent(111.71)).toBe('111.71%');
  });
});

describe('formatNumber', () => {
  it('groups thousands', () => {
    expect(formatNumber(1_234_567)).toBe('1,234,567');
  });

  it('caps at two decimals but does not pad to two', () => {
    // Differs from formatCurrency deliberately: quantities like 8.5 BTC should
    // not render as "8.50".
    expect(formatNumber(8.5)).toBe('8.5');
    expect(formatNumber(1.239)).toBe('1.24');
  });

  it('keeps the sign on a negative value', () => {
    expect(formatNumber(-450)).toBe('-450');
  });
});

describe('cn', () => {
  it('joins class names', () => {
    expect(cn('a', 'b')).toBe('a b');
  });

  it('drops falsy values', () => {
    expect(cn('a', false, undefined, null, 'b')).toBe('a b');
  });

  it('lets a later Tailwind class win over an earlier conflicting one', () => {
    // This is the whole reason twMerge is here rather than plain clsx: without
    // it, `cn('p-2', 'p-4')` emits both and the winner depends on stylesheet
    // order rather than call order.
    expect(cn('p-2', 'p-4')).toBe('p-4');
    expect(cn('text-gain', 'text-loss')).toBe('text-loss');
  });

  it('keeps non-conflicting classes', () => {
    expect(cn('p-2', 'text-gain')).toBe('p-2 text-gain');
  });
});

describe('getStaggerDelay', () => {
  it('scales linearly with index', () => {
    expect(getStaggerDelay(0)).toBe(0);
    expect(getStaggerDelay(3)).toBeCloseTo(0.3);
  });

  it('honours a custom base delay', () => {
    expect(getStaggerDelay(2, 0.5)).toBeCloseTo(1.0);
  });
});
