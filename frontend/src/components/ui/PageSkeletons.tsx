/**
 * PageSkeletons.tsx — Page-specific skeleton layouts that match the exact
 * structure of each page, preventing layout shift (CLS < 0.1).
 *
 * Usage: Show during initial data load (isLoading) only.
 * Do NOT show during background refetches — previous data should stay visible.
 */

import { Skeleton } from './Skeleton';

// ---- Shared building blocks ----

const MetricCardSkeleton = () => (
  <Skeleton className="h-32 rounded-2xl" />
);

const TableSkeleton = ({ rows = 5 }: { rows?: number }) => (
  <div className="space-y-2">
    <Skeleton className="h-10 rounded-xl" />
    {Array.from({ length: rows }).map((_, i) => (
      <Skeleton key={i} className="h-14 rounded-xl" />
    ))}
  </div>
);

// ---- Page Skeletons ----

export const CockpitSkeleton = () => (
  <div className="space-y-6 pb-12">
    {/* Title */}
    <Skeleton className="h-10 w-56 rounded-xl" />
    {/* 6 metric cards */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: 6 }).map((_, i) => <MetricCardSkeleton key={i} />)}
    </div>
    {/* Risk + Regime */}
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Skeleton className="h-48 rounded-2xl" />
      <Skeleton className="h-48 rounded-2xl" />
    </div>
    {/* Positions table */}
    <Skeleton className="h-64 rounded-2xl" />
    {/* Strategies + Alerts */}
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Skeleton className="h-64 rounded-2xl" />
      <Skeleton className="h-64 rounded-2xl" />
    </div>
  </div>
);

export const PortfolioSkeleton = () => (
  <div className="space-y-6 pb-12">
    <Skeleton className="h-10 w-48 rounded-xl" />
    {/* Equity curve */}
    <Skeleton className="h-80 rounded-2xl" />
    {/* 4 metric cards */}
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)}
    </div>
    {/* Trade table */}
    <Skeleton className="h-64 rounded-2xl" />
  </div>
);

export const StrategiesSkeleton = () => (
  <div className="space-y-6 pb-12">
    <Skeleton className="h-10 w-40 rounded-xl" />
    {/* Filter bar */}
    <Skeleton className="h-12 rounded-2xl" />
    {/* Strategy cards grid */}
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-56 rounded-2xl" />
      ))}
    </div>
  </div>
);

export const RiskSkeleton = () => (
  <div className="space-y-6 pb-12">
    <Skeleton className="h-10 w-36 rounded-xl" />
    {/* Kill switch + 3 gauges */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)}
    </div>
    {/* Risk limits table */}
    <Skeleton className="h-64 rounded-2xl" />
  </div>
);

export const OrdersSkeleton = () => (
  <div className="space-y-6 pb-12">
    <Skeleton className="h-10 w-32 rounded-xl" />
    <TableSkeleton rows={8} />
  </div>
);

export const AlertsSkeleton = () => (
  <div className="space-y-6 pb-12">
    <Skeleton className="h-10 w-32 rounded-xl" />
    {/* Filter row */}
    <Skeleton className="h-10 rounded-xl" />
    {Array.from({ length: 6 }).map((_, i) => (
      <Skeleton key={i} className="h-20 rounded-2xl" />
    ))}
  </div>
);

export const AccountsSkeleton = () => (
  <div className="space-y-6 pb-12">
    <Skeleton className="h-10 w-36 rounded-xl" />
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {Array.from({ length: 2 }).map((_, i) => (
        <Skeleton key={i} className="h-48 rounded-2xl" />
      ))}
    </div>
  </div>
);

export const BacktestSkeleton = () => (
  <div className="space-y-6 pb-12">
    <Skeleton className="h-10 w-40 rounded-xl" />
    {/* Config panel */}
    <Skeleton className="h-48 rounded-2xl" />
    {/* Results */}
    <Skeleton className="h-64 rounded-2xl" />
  </div>
);

// Generic fallback — used by Suspense in App.tsx
export const PageSkeleton = () => (
  <div className="p-8 space-y-4">
    <Skeleton className="h-10 w-48 rounded-xl" />
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-28 rounded-2xl" />
      ))}
    </div>
    <Skeleton className="h-64 rounded-2xl" />
  </div>
);
