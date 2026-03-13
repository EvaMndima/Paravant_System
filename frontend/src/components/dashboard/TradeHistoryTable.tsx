import React, { useState, useMemo } from 'react';
import { ArrowUpRight, ArrowDownLeft, Filter } from 'lucide-react';
import { DataTable } from '@/components/ui/DataTable';
import type { Column } from '@/components/ui/DataTable';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { DateRangePicker } from '@/components/ui/DateRangePicker';
import type { DateRange } from '@/components/ui/DateRangePicker';
import { Pagination } from '@/components/ui/Pagination';
import { GlassCard } from '@/components/ui/GlassCard';
import { cn } from '@/lib/utils';
import type { TradeDetail } from './TradeDetailModal';

export interface TradeHistoryTableProps {
  trades?: TradeDetail[];
  onRowClick?: (trade: TradeDetail) => void;
  className?: string;
}

// Generate mock trade data
function generateMockTrades(count: number): TradeDetail[] {
  const symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];
  const strategies = ['Simple_MA', 'Scalper_RSI', 'Momentum_MACD', 'Donchian_BB', 'BreakoutRetest'];
  const sides: ('long' | 'short')[] = ['long', 'short'];
  const statuses: ('closed' | 'open' | 'cancelled')[] = ['closed', 'closed', 'closed', 'open', 'closed'];

  return Array.from({ length: count }, (_, i) => {
    const side = sides[i % 2];
    const symbol = symbols[i % 3];
    const entry = symbol === 'BTCUSDT' ? 42_000 + (Math.random() - 0.5) * 4_000
      : symbol === 'ETHUSDT' ? 2_400 + (Math.random() - 0.5) * 400
      : 320 + (Math.random() - 0.5) * 40;
    const pnlPct = (Math.random() - 0.42) * 6;
    const qty = symbol === 'BTCUSDT' ? 0.05 + Math.random() * 0.1
      : symbol === 'ETHUSDT' ? 0.5 + Math.random() * 1.5
      : 2 + Math.random() * 5;
    const exitPrice = entry * (1 + (side === 'long' ? 1 : -1) * pnlPct / 100);
    const pnl = (exitPrice - entry) * qty * (side === 'long' ? 1 : -1);
    const d = new Date();
    d.setDate(d.getDate() - i);

    return {
      id: `TRD-${String(count - i).padStart(4, '0')}`,
      symbol,
      side,
      status: statuses[i % 5],
      entryPrice: entry,
      exitPrice: statuses[i % 5] === 'open' ? undefined : exitPrice,
      quantity: qty,
      pnl: statuses[i % 5] === 'open' ? undefined : pnl,
      pnlPercent: statuses[i % 5] === 'open' ? undefined : pnlPct,
      entryTime: new Date(d.setHours(9, Math.floor(Math.random() * 60))).toISOString(),
      exitTime: statuses[i % 5] === 'open' ? undefined : new Date(d.setHours(14, Math.floor(Math.random() * 60))).toISOString(),
      strategy: strategies[i % 5],
      fees: entry * qty * 0.001,
      slippage: entry * qty * 0.0002,
    } as TradeDetail;
  });
}

const MOCK_TRADES = generateMockTrades(120);

const SYMBOL_OPTIONS = [
  { value: 'all', label: 'All Symbols' },
  { value: 'BTCUSDT', label: 'BTCUSDT' },
  { value: 'ETHUSDT', label: 'ETHUSDT' },
  { value: 'BNBUSDT', label: 'BNBUSDT' },
];

const SIDE_OPTIONS = [
  { value: 'all', label: 'Both Sides' },
  { value: 'long', label: 'Long' },
  { value: 'short', label: 'Short' },
];

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Status' },
  { value: 'closed', label: 'Closed' },
  { value: 'open', label: 'Open' },
];

export const TradeHistoryTable: React.FC<TradeHistoryTableProps> = ({
  trades = MOCK_TRADES,
  onRowClick,
  className,
}) => {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [symbolFilter, setSymbolFilter] = useState('all');
  const [sideFilter, setSideFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dateRange, setDateRange] = useState<DateRange | undefined>();

  const filtered = useMemo(() => {
    return trades.filter(t => {
      if (symbolFilter !== 'all' && t.symbol !== symbolFilter) return false;
      if (sideFilter !== 'all' && t.side !== sideFilter) return false;
      if (statusFilter !== 'all' && t.status !== statusFilter) return false;
      if (dateRange) {
        const entryDate = t.entryTime.split('T')[0];
        if (entryDate < dateRange.from || entryDate > dateRange.to) return false;
      }
      return true;
    });
  }, [trades, symbolFilter, sideFilter, statusFilter, dateRange]);

  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: 'id',
      header: 'Trade ID',
      render: (v) => (
        <span className="font-mono text-xs text-obsidian-400/60 dark:text-paper-100/60">{String(v)}</span>
      ),
    },
    {
      key: 'symbol',
      header: 'Symbol',
      sortable: true,
      render: (v, row) => (
        <div className="flex items-center gap-2">
          <div className={cn(
            'p-1 rounded-lg',
            row.side === 'long' ? 'bg-gain/10 text-gain' : 'bg-loss/10 text-loss'
          )}>
            {row.side === 'long'
              ? <ArrowUpRight className="w-3 h-3" />
              : <ArrowDownLeft className="w-3 h-3" />}
          </div>
          <span className="font-mono text-sm font-medium">{String(v)}</span>
        </div>
      ),
    },
    {
      key: 'entryPrice',
      header: 'Entry',
      align: 'right',
      sortable: true,
      render: (v) => (
        <span className="font-mono text-sm">${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
      ),
    },
    {
      key: 'exitPrice',
      header: 'Exit',
      align: 'right',
      render: (v) => v
        ? <span className="font-mono text-sm">${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        : <span className="font-mono text-xs text-obsidian-400/30 dark:text-paper-100/30">—</span>,
    },
    {
      key: 'pnl',
      header: 'P&L',
      align: 'right',
      sortable: true,
      render: (v, row) => {
        if (v === undefined || v === null) return <span className="font-mono text-xs text-obsidian-400/30 dark:text-paper-100/30">Open</span>;
        const pnl = Number(v);
        return (
          <div className="text-right">
            <span className={cn('font-mono text-sm font-medium', pnl >= 0 ? 'text-gain' : 'text-loss')}>
              {pnl >= 0 ? '+' : ''}${Math.abs(pnl).toFixed(2)}
            </span>
            <div className={cn('text-[10px] font-mono', pnl >= 0 ? 'text-gain/60' : 'text-loss/60')}>
              {Number(row.pnlPercent) >= 0 ? '+' : ''}{Number(row.pnlPercent).toFixed(2)}%
            </div>
          </div>
        );
      },
    },
    {
      key: 'strategy',
      header: 'Strategy',
      render: (v) => (
        <span className="text-xs font-mono text-obsidian-400/60 dark:text-paper-100/60">{String(v)}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      align: 'center',
      render: (v) => (
        <Badge
          variant={v === 'closed' ? 'default' : v === 'open' ? 'success' : 'warning'}
          size="sm"
          dot={v === 'open'}
        >
          {String(v)}
        </Badge>
      ),
    },
    {
      key: 'entryTime',
      header: 'Date',
      sortable: true,
      render: (v) => {
        const d = new Date(String(v));
        return (
          <span className="text-xs font-mono text-obsidian-400/60 dark:text-paper-100/60">
            {d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          </span>
        );
      },
    },
  ];

  return (
    <GlassCard variant="default" padding="md" className={cn('space-y-4', className)}>
      {/* Header + filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 mr-auto">
          <Filter className="w-4 h-4 text-obsidian-400/40 dark:text-paper-100/40" />
          <span className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
            Trade History
          </span>
          <span className="text-xs font-mono text-obsidian-400/30 dark:text-paper-100/30">
            ({filtered.length} trades)
          </span>
        </div>

        <DateRangePicker
          value={dateRange}
          onChange={(range) => { setDateRange(range); setPage(1); }}
        />
        <Select
          options={SYMBOL_OPTIONS}
          value={symbolFilter}
          onChange={v => { setSymbolFilter(v); setPage(1); }}
          size="sm"
          className="w-36"
        />
        <Select
          options={SIDE_OPTIONS}
          value={sideFilter}
          onChange={v => { setSideFilter(v); setPage(1); }}
          size="sm"
          className="w-32"
        />
        <Select
          options={STATUS_OPTIONS}
          value={statusFilter}
          onChange={v => { setStatusFilter(v); setPage(1); }}
          size="sm"
          className="w-32"
        />
      </div>

      {/* Table */}
      <DataTable
        columns={columns}
        data={paginated as Record<string, unknown>[]}
        onRowClick={(row) => onRowClick?.(row as unknown as TradeDetail)}
        emptyMessage="No trades match current filters"
        stickyHeader
      />

      {/* Pagination */}
      <div className="pt-2 border-t border-deep-teal-800/5 dark:border-white/5">
        <Pagination
          page={page}
          pageSize={pageSize}
          total={filtered.length}
          onPageChange={setPage}
          onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
        />
      </div>
    </GlassCard>
  );
};
