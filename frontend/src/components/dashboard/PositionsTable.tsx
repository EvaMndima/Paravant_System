import React from 'react';
import type { Column } from '@/components/ui/DataTable';
import { DataTable } from '@/components/ui/DataTable';
import { GlassCard } from '@/components/ui/GlassCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { cn, formatCurrency, formatNumber } from '@/lib/utils';
import { ArrowUpRight, ArrowDownRight, Minus, PieChart } from 'lucide-react';

// --- Types ---

export interface Position {
  id: string;
  symbol: string;
  name: string;
  quantity: number;
  avgPrice: number;
  currentPrice: number;
  pl: number;
  plPercent: number;
  weight: number;
  sector?: string;
  assetType?: 'Stock' | 'ETF' | 'Option' | 'Cash' | 'Crypto';
}

// --- Mock Data (used when no data prop is supplied) ---

const mockPositions: Position[] = [
  { id: '1', symbol: 'NVDA', name: 'NVIDIA Corp.', quantity: 450, avgPrice: 420.50, currentPrice: 890.25, pl: 211387.50, plPercent: 111.71, weight: 24.5, sector: 'Technology', assetType: 'Stock' },
  { id: '2', symbol: 'MSFT', name: 'Microsoft Corp.', quantity: 1200, avgPrice: 310.00, currentPrice: 425.10, pl: 138120.00, plPercent: 37.13, weight: 18.2, sector: 'Technology', assetType: 'Stock' },
  { id: '3', symbol: 'BTC', name: 'Bitcoin', quantity: 8.5, avgPrice: 42000.00, currentPrice: 67500.00, pl: 216750.00, plPercent: 60.71, weight: 15.8, sector: 'Crypto', assetType: 'Crypto' },
  { id: '4', symbol: 'TSLA', name: 'Tesla Inc.', quantity: 800, avgPrice: 245.00, currentPrice: 175.40, pl: -55680.00, plPercent: -28.41, weight: 8.5, sector: 'Consumer Cyclical', assetType: 'Stock' },
  { id: '5', symbol: 'AAPL', name: 'Apple Inc.', quantity: 1500, avgPrice: 155.00, currentPrice: 172.50, pl: 26250.00, plPercent: 11.29, weight: 12.1, sector: 'Technology', assetType: 'Stock' },
  { id: '6', symbol: 'GOOGL', name: 'Alphabet Inc.', quantity: 600, avgPrice: 135.00, currentPrice: 142.00, pl: 4200.00, plPercent: 5.19, weight: 5.4, sector: 'Technology', assetType: 'Stock' },
];

// --- Component ---

interface PositionsTableProps {
  data?: Position[];
  isLoading?: boolean;
  limit?: number;
  className?: string;
  onPositionClick?: (position: Position) => void;
  title?: string;
  compact?: boolean;
}

export const PositionsTable: React.FC<PositionsTableProps> = ({
  data,
  isLoading = false,
  limit,
  className,
  onPositionClick,
  title = 'Top Holdings',
  compact = false,
}) => {
  const displayData = data
    ? (limit ? data.slice(0, limit) : data)
    : (limit ? mockPositions.slice(0, limit) : mockPositions);

  const columns: Column<Position>[] = [
    {
      key: 'symbol',
      header: 'Instrument',
      sortable: true,
      render: (_, row) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-deep-teal-800/5 dark:bg-white/5 border border-deep-teal-800/10 dark:border-white/10 flex items-center justify-center text-[10px] font-bold text-deep-teal-800 dark:text-turquoise-mist shrink-0">
            {row.symbol[0]}
          </div>
          <div className="min-w-0">
            <div className="font-bold font-sans text-obsidian-400 dark:text-paper-100 truncate">{row.symbol}</div>
            <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-sans truncate max-w-[100px]">{row.name}</div>
          </div>
        </div>
      ),
    },
    {
      key: 'quantity',
      header: 'Qty',
      align: 'right',
      sortable: true,
      className: compact ? 'hidden lg:table-cell' : 'hidden md:table-cell',
      render: (val) => <span className="font-mono text-obsidian-400/80 dark:text-paper-100/80">{formatNumber(val as number)}</span>,
    },
    {
      key: 'avgPrice',
      header: 'Avg Price',
      align: 'right',
      sortable: true,
      className: 'hidden lg:table-cell',
      render: (val) => <span className="font-mono text-obsidian-400/60 dark:text-paper-100/60">{formatCurrency(val as number)}</span>,
    },
    {
      key: 'currentPrice',
      header: 'Mark',
      align: 'right',
      sortable: true,
      render: (val) => <span className="font-mono font-medium">{formatCurrency(val as number)}</span>,
    },
    {
      key: 'pl',
      header: 'P&L ($)',
      align: 'right',
      sortable: true,
      render: (val) => (
        <span className={cn(
          'font-mono font-medium',
          (val as number) >= 0 ? 'text-gain' : 'text-loss'
        )}>
          {(val as number) >= 0 ? '+' : ''}{formatCurrency(val as number)}
        </span>
      ),
    },
    {
      key: 'plPercent',
      header: 'P&L (%)',
      align: 'right',
      sortable: true,
      className: 'hidden sm:table-cell',
      render: (val) => {
        const v = val as number;
        const isPositive = v >= 0;
        const Icon = v === 0 ? Minus : (isPositive ? ArrowUpRight : ArrowDownRight);
        return (
          <div className={cn(
            'flex items-center justify-end gap-1 font-mono',
            isPositive ? 'text-gain' : 'text-loss'
          )}>
            <Icon className="w-3 h-3" strokeWidth={2} />
            <span>{Math.abs(v).toFixed(2)}%</span>
          </div>
        );
      },
    },
    {
      key: 'weight',
      header: 'Weight',
      align: 'right',
      sortable: true,
      className: 'hidden xl:table-cell',
      render: (val) => (
        <div className="flex items-center justify-end gap-2">
          <span className="font-mono text-xs text-obsidian-400/70 dark:text-paper-100/70">{(val as number).toFixed(1)}%</span>
          <div className="w-16 h-1.5 bg-obsidian-400/5 dark:bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-deep-teal-600 dark:bg-turquoise-mist rounded-full opacity-80"
              style={{ width: `${Math.min(val as number, 100)}%` }}
            />
          </div>
        </div>
      ),
    },
  ];

  if (isLoading) {
    return (
      <GlassCard className={cn('p-0 overflow-hidden flex flex-col', className)}>
        <div className="px-6 py-4 border-b border-deep-teal-800/10 dark:border-white/5">
          <Skeleton variant="text" className="w-1/3 h-6" />
        </div>
        <div className="p-4 space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex justify-between items-center">
              <div className="flex items-center gap-3 w-1/3">
                <Skeleton variant="circle" className="w-8 h-8" />
                <div className="space-y-1 flex-1">
                  <Skeleton variant="text" className="w-1/2 h-4" />
                  <Skeleton variant="text" className="w-3/4 h-3" />
                </div>
              </div>
              <Skeleton variant="text" className="w-20 h-4" />
              <Skeleton variant="text" className="w-20 h-4" />
            </div>
          ))}
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard className={cn('p-0 overflow-hidden flex flex-col', className)}>
      <div className="px-6 py-4 border-b border-deep-teal-800/10 dark:border-white/5 flex items-center justify-between shrink-0">
        <h3 className="font-display text-lg font-medium text-obsidian-400 dark:text-paper-100">{title}</h3>
        <button className="text-xs font-mono uppercase tracking-widest text-turquoise-mist hover:text-turquoise-bright transition-colors">
          View All
        </button>
      </div>
      <div className="flex-1 overflow-auto">
        {displayData.length === 0 ? (
          <EmptyState
            title="No positions found"
            description="Your portfolio is currently all cash."
            variant="default"
            icon={PieChart}
          />
        ) : (
          <DataTable
            columns={columns as unknown as import('@/components/ui/DataTable').Column<Record<string, unknown>>[]}
            data={displayData as unknown as Record<string, unknown>[]}
            isLoading={isLoading}
            onRowClick={onPositionClick as unknown as ((row: Record<string, unknown>) => void) | undefined}
          />
        )}
      </div>
    </GlassCard>
  );
};
