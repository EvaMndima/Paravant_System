/**
 * Where a chart's data came from.
 *
 * Twelve files in this dashboard call `Math.random()`. Seven of them are
 * components that fabricate profit and loss, equity curves, drawdown series and
 * win/loss outcomes, because the pages were ported from a visual prototype and
 * six of them are still not wired to the API. That is defensible while it is
 * visible and indefensible the moment it is not: a plausible equity curve with
 * no label is a claim about a real account.
 *
 * The contract here is deliberately **fail-closed**. A chart renders without a
 * banner only when it is told, explicitly, that its data is `'live'`. Synthetic
 * data is labelled. *Untagged* data is also labelled, and that is the point --
 * the eighth component, written six months from now by someone who has not read
 * this file, gets the banner by default rather than by remembering.
 *
 * The alternative -- tag the synthetic paths and treat everything else as real
 * -- is the same shape as a per-route authentication dependency, and fails the
 * same way: protection depends on every future author remembering, and nothing
 * breaks when they forget. `src/api/auth.py` rejects that reasoning for the API
 * for exactly this reason. It is rejected here for the same one.
 *
 * @see SyntheticDataBadge for the banner itself
 * @see provenance.test.tsx for the test that enumerates chart components
 */

/** Data fetched from the PARAVANT API. Renders clean. */
export const LIVE = 'live' as const;

/** Data fabricated in the browser for layout purposes. Always labelled. */
export const SYNTHETIC = 'synthetic' as const;

export type Provenance = typeof LIVE | typeof SYNTHETIC;

/**
 * Props every component that renders financial values should accept.
 *
 * Optional on purpose. Making it required would be caught by `tsc` and would
 * therefore be satisfied by whatever value made the error go away, which is not
 * the same as being considered. Leaving it optional and defaulting to "not
 * live" means the omission is visible in the rendered output instead.
 */
export interface ProvenanceProps {
  /**
   * Where `data` came from. Omit it and the component treats the data as
   * unverified and shows the banner.
   */
  dataProvenance?: Provenance;
}

/**
 * Whether a banner must be shown.
 *
 * True for `'synthetic'` and true for `undefined`. False only for an explicit
 * `'live'`.
 *
 * @param provenance - The declared provenance, if any.
 * @returns True when the rendered values are not known to be real.
 */
export function requiresSyntheticLabel(provenance?: Provenance): boolean {
  return provenance !== LIVE;
}

/**
 * Resolve the provenance of a component that may fall back to generated data.
 *
 * A component given no `data` generates its own, which is synthetic regardless
 * of what the caller declared. A caller cannot mark a generated series `'live'`
 * by passing `dataProvenance="live"` and omitting `data`, which is the mistake
 * this is here to make impossible.
 *
 * @param provenance - Provenance declared by the caller.
 * @param data - The data the caller supplied, if any.
 * @returns The provenance that actually applies to what will be rendered.
 */
export function resolveProvenance<T>(
  provenance: Provenance | undefined,
  data: T | undefined,
): Provenance {
  if (data === undefined) return SYNTHETIC;
  return provenance === LIVE ? LIVE : SYNTHETIC;
}
