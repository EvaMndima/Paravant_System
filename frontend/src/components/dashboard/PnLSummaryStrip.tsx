import React from 'react';
import { TrendingUp, TrendingDown, DollarSign, BarChart2, Target, Activity } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { cn } from '@/lib/utils';

export interface PnLSummaryData {
  todayPnl: number;
  totalReturn: number;        // percent
  unrealizedPnl: number;
  realizedPnl: number;
  winRate: number;            // percent 0-100
  totalTrades: number;
  openPositions: number;
}

export interface PnLSummaryStripProps {
  data?: Partial<PnLSummaryData>;
  className?: string;
}

const MOCK: PnLSummaryData = {
  todayPnl: 1_243.50,
  totalReturn: 24.35,
  unrealizedPnl: 3_120.00,
  realizedPnl: 18_750.00,
  winRate: 67.4,
  totalTrades: 248,
  openPositions: 3,
};

interface TileProps {
  label: string;
  value: string;
  sub?: string;
  icon: React.ElementType;
  positive?: boolean | null; // null = neutral
}

const Tile: React.FC<TileProps> = ({ label, value, sub, icon: Icon, positive }) => {
  const valueColor =
    positive === true
      ? 'text-gain'
      : positive === false
      ? 'text-loss'
      : 'text-obsidian-400 dark:text-paper-100';

  return (
    <div className="flex items-start gap-3 p-4">
      <div className={cn(
        'p-2 rounded-xl shrink-0',
        positive === true ? 'bg-gain/10 text-gain'
          : positive === false ? 'bg-loss/10 text-loss'
          : 'bg-deep-teal-800/5 dark:bg-white/5 text-obsidian-400/50 dark:text-paper-100/50'
      )}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
          {label}
        </p>
        <p className={cn('text-base font-mono font-bold leading-tight', valueColor)}>
          {value}
        </p>
        {sub && (
          <p className="text-[10px] font-sans text-obsidian-400/40 dark:text-paper-100/40 mt-0.5">{sub}</p>
        )}
      </div>
    </div>
  );
};

function fmt(n: number, prefix = '$') {
  const abs = Math.abs(n);
  const str = abs >= 1_000 ? `${prefix}${(abs / 1_000).toFixed(1)}k` : `${prefix}${abs.toFixed(0)}`;
  return n < 0 ? `-${str}` : `+${str}`;
}

export const PnLSummaryStrip: React.FC<PnLSummaryStripProps> = ({ data, className }) => {
  const d: PnLSummaryData = { ...MOCK, ...data };

  const tiles: TileProps[] = [
    {
      label: "Today's P&L",
      value: fmt(d.todayPnl),
      sub: 'Since market open',
      icon: d.todayPnl >= 0 ? TrendingUp : TrendingDown,
      positive: d.todayPnl >= 0,
    },
    {
      label: 'Total Return',
      value: `${d.totalReturn >= 0 ? '+' : ''}${d.totalReturn.toFixed(2)}%`,
      sub: `Realized: ${fmt(d.realizedPnl)}`,
      icon: BarChart2,
      positive: d.totalReturn >= 0,
    },
    {
      label: 'Unrealized P&L',
      value: fmt(d.unrealizedPnl),
      sub: `${d.openPositions} open position${d.openPositions !== 1 ? 's' : ''}`,
      icon: DollarSign,
      positive: d.unrealizedPnl >= 0,
    },
    {
      label: 'Win Rate',
      value: `${d.winRate.toFixed(1)}%`,
      sub: `${d.totalTrades} total trades`,
      icon: Target,
      positive: null,
    },
    {
      label: 'Total Trades',
      value: d.totalTrades.toString(),
      sub: `${d.openPositions} currently open`,
      icon: Activity,
      positive: null,
    },
  ];

  return (
    <GlassCard variant="default" padding="none" className={cn('overflow-hidden', className)}>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 divide-x divide-deep-teal-800/5 dark:divide-white/5">
        {tiles.map((tile, idx) => (
          <div
            key={tile.label}
            className={cn(
              idx > 0 && 'border-t border-deep-teal-800/5 dark:border-white/5 sm:border-t-0',
              idx > 2 && 'hidden lg:block',
              idx === 2 && 'hidden sm:block lg:block'
            )}
          >
            <Tile {...tile} />
          </div>
        ))}
      </div>
    </GlassCard>
  );
};
