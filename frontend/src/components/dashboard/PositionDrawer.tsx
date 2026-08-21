import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Bell, TrendingUp, TrendingDown, Star,
  MoreHorizontal, DollarSign, ArrowRightLeft,
  FileText, ExternalLink, Activity,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Dropdown } from '@/components/ui/Dropdown';
import { AreaChart } from '@/components/charts/AreaChart';
import { cn, formatCurrency, formatNumber, formatPercent } from '@/lib/utils';
import { SyntheticDataBadge } from '@/components/ui/SyntheticDataBadge';
import { requiresSyntheticLabel, resolveProvenance } from '@/lib/provenance';
import type { ProvenanceProps } from '@/lib/provenance';

// --- Types ---

export interface DrawerPosition {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  assetType: 'Stock' | 'ETF' | 'Option' | 'Cash' | 'Crypto';
  quantity: number;
  avgCost: number;
  price: number;
  value: number;
  pnl: number;
  pnlPercent: number;
  weight: number;
}

interface PositionDrawerProps extends ProvenanceProps {
  isOpen: boolean;
  onClose: () => void;
  position: DrawerPosition | null;
  onAlert?: (symbol: string) => void;
}

// --- Mock Data Generators ---

interface ChartPoint {
  date: string;
  value: number;
}

const generateChartData = (currentPrice: number): ChartPoint[] => {
  const data: ChartPoint[] = [];
  let price = currentPrice * 0.9;
  for (let i = 0; i < 30; i++) {
    const date = new Date();
    date.setDate(date.getDate() - (29 - i));
    price = price * (1 + (Math.random() - 0.45) * 0.03);
    data.push({
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: price,
    });
  }
  data[data.length - 1].value = currentPrice;
  return data;
};

const mockTransactions = [
  { id: 1, date: 'Oct 24, 2024', type: 'Buy', qty: 50, price: 840.20, total: 42010.00 },
  { id: 2, date: 'Sep 12, 2024', type: 'Buy', qty: 120, price: 780.50, total: 93660.00 },
  { id: 3, date: 'Aug 05, 2024', type: 'Sell', qty: 25, price: 810.00, total: 20250.00 },
];

// --- Sub-components ---

const DetailRow = ({
  label,
  value,
  subValue,
  highlight = false,
}: {
  label: string;
  value: string;
  subValue?: string;
  highlight?: boolean;
}) => (
  <div className="flex flex-col">
    <span className="text-[10px] uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 font-mono mb-1">
      {label}
    </span>
    <span className={cn(
      'text-base font-medium font-mono',
      highlight ? 'text-deep-teal-800 dark:text-turquoise-mist' : 'text-obsidian-400 dark:text-paper-100'
    )}>
      {value}
    </span>
    {subValue && (
      <span className="text-xs text-obsidian-400/60 dark:text-paper-100/60">{subValue}</span>
    )}
  </div>
);

// --- Main Component ---


export const PositionDrawer: React.FC<PositionDrawerProps> = ({
  isOpen,
  onClose,
  position,
  onAlert,
  dataProvenance,
}) => {
  // The price series in this drawer is generated regardless of whether
  // `position` is real, so the view always contains fabricated values.
  const provenance = resolveProvenance(dataProvenance, undefined);
  const [mounted, setMounted] = useState(false);
  const [note, setNote] = useState('');
  const [isWatchlisted, setIsWatchlisted] = useState(false);

  // Memoize chart data so it only recalculates when position changes
  const chartData = useMemo(() => {
    return position ? generateChartData(position.price) : [];
  }, [position]);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  // Lock scroll when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => { document.body.style.overflow = 'unset'; };
  }, [isOpen]);

  if (!mounted) return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && position && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 z-[100] bg-obsidian-400/40 backdrop-blur-sm"
          />

          {/* Drawer Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className={cn(
              'fixed inset-y-0 right-0 z-[110] w-full md:w-[480px] shadow-2xl flex flex-col',
              'bg-paper-100/95 dark:bg-obsidian-300/95 backdrop-blur-xl border-l border-deep-teal-800/10 dark:border-white/10'
            )}
          >
            {/* Header */}
            <div className="flex-shrink-0 px-6 py-5 border-b border-deep-teal-800/5 dark:border-white/5 flex items-start justify-between bg-white/50 dark:bg-black/10">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <h2 className="text-2xl font-display font-bold text-obsidian-400 dark:text-paper-100 tracking-tight">
                    {position.symbol}
                  </h2>
                  <Badge variant="neutral" size="sm" className="font-normal opacity-80">
                    {position.assetType}
                  </Badge>
                  {requiresSyntheticLabel(provenance) && <SyntheticDataBadge compact />}
                </div>
                <div className="text-sm text-obsidian-400/60 dark:text-paper-100/60 font-sans">
                  {position.name}
                </div>
              </div>

              <div className="flex flex-col items-end">
                <div className="text-xl font-mono font-medium text-obsidian-400 dark:text-paper-100">
                  {formatCurrency(position.price)}
                </div>
                <div className={cn(
                  'flex items-center gap-1 text-xs font-bold font-mono',
                  position.pnlPercent >= 0 ? 'text-gain' : 'text-loss'
                )}>
                  {position.pnlPercent >= 0
                    ? <TrendingUp className="w-3 h-3" />
                    : <TrendingDown className="w-3 h-3" />
                  }
                  {Math.abs(position.pnlPercent / 10).toFixed(2)}% (Day)
                </div>
              </div>

              <button
                onClick={onClose}
                className="absolute top-5 right-5 p-2 rounded-full hover:bg-deep-teal-800/5 dark:hover:bg-white/10 transition-colors md:static md:ml-4 md:p-1.5 md:-mt-1"
              >
                <X className="w-5 h-5 text-obsidian-400/50 dark:text-paper-100/50" />
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">

              {/* Quick Actions */}
              <div className="px-6 py-4 flex items-center gap-2 border-b border-deep-teal-800/5 dark:border-white/5">
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => onAlert?.(position.symbol)}
                  leftIcon={<Bell className="w-4 h-4" />}
                >
                  Set Alert
                </Button>

                <button
                  onClick={() => setIsWatchlisted(!isWatchlisted)}
                  className={cn(
                    'w-10 h-10 flex items-center justify-center rounded-xl border transition-all',
                    isWatchlisted
                      ? 'bg-warning/10 border-warning text-warning'
                      : 'bg-transparent border-deep-teal-800/10 dark:border-white/10 text-obsidian-400/40 dark:text-paper-100/40 hover:bg-deep-teal-800/5 dark:hover:bg-white/5'
                  )}
                >
                  <Star className={cn('w-5 h-5', isWatchlisted && 'fill-current')} />
                </button>

                <Dropdown
                  align="end"
                  trigger={
                    <button className="w-10 h-10 flex items-center justify-center rounded-xl border border-deep-teal-800/10 dark:border-white/10 text-obsidian-400/40 dark:text-paper-100/40 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-all">
                      <MoreHorizontal className="w-5 h-5" />
                    </button>
                  }
                  items={[
                    { label: 'View Chart', icon: Activity },
                    { label: 'Company Profile', icon: FileText },
                    { label: 'Option Chain', icon: ExternalLink },
                  ]}
                />
              </div>

              {/* Summary Grid */}
              <div className="p-6 grid grid-cols-2 gap-y-6 gap-x-4">
                <DetailRow label="Total Quantity" value={formatNumber(position.quantity)} />
                <DetailRow label="Market Value" value={formatCurrency(position.value)} highlight />
                <DetailRow label="Avg Cost" value={formatCurrency(position.avgCost)} />
                <DetailRow
                  label="Unrealized P&L"
                  value={formatCurrency(position.pnl)}
                  subValue={formatPercent(position.pnlPercent)}
                  highlight={position.pnl >= 0}
                />
                <DetailRow label="Portfolio Weight" value={`${position.weight.toFixed(2)}%`} />
                <DetailRow
                  label="Day P&L"
                  value={formatCurrency(position.value * 0.012)}
                  subValue="+1.20%"
                />
              </div>

              {/* 30-Day Chart */}
              <div className="px-6 py-2">
                <div className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-3">
                  Performance (30D)
                </div>
                <div className="h-48 w-full bg-deep-teal-800/5 dark:bg-white/5 rounded-xl border border-deep-teal-800/5 dark:border-white/5 overflow-hidden p-2">
                  <AreaChart
                    data={chartData}
                    height={180}
                    showGrid={false}
                    showTooltip={true}
                    curveType="monotone"
                  />
                </div>
              </div>

              {/* Recent Transactions */}
              <div className="px-6 py-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
                    Recent History
                  </div>
                  <button className="text-xs text-turquoise-mist hover:underline">View All</button>
                </div>
                <div className="space-y-1">
                  {mockTransactions.map((tx) => (
                    <div key={tx.id} className="flex items-center justify-between p-3 rounded-lg hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          'w-8 h-8 rounded-full flex items-center justify-center border',
                          tx.type === 'Buy'
                            ? 'bg-gain/10 border-gain/20 text-gain'
                            : 'bg-loss/10 border-loss/20 text-loss'
                        )}>
                          {tx.type === 'Buy'
                            ? <DollarSign className="w-4 h-4" />
                            : <ArrowRightLeft className="w-4 h-4" />
                          }
                        </div>
                        <div>
                          <div className="text-sm font-medium font-sans">{tx.type} {tx.qty} Shares</div>
                          <div className="text-[10px] text-obsidian-400/50 dark:text-paper-100/50 font-mono">{tx.date}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-mono font-medium">{formatCurrency(tx.price)}</div>
                        <div className="text-[10px] text-obsidian-400/50 dark:text-paper-100/50 font-mono">
                          Total: {formatCurrency(tx.total)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Fundamentals */}
              <div className="px-6 pb-6">
                <div className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-3">
                  Fundamentals
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { label: 'Market Cap', value: '2.24T' },
                    { label: 'P/E Ratio', value: '74.2' },
                    { label: 'Div Yield', value: '0.02%' },
                    { label: '52W Range', value: '400 - 950' },
                  ].map(({ label, value }) => (
                    <div key={label} className="p-3 bg-deep-teal-800/5 dark:bg-white/5 rounded-lg border border-deep-teal-800/5 dark:border-white/5">
                      <div className="text-[10px] opacity-60 mb-1">{label}</div>
                      <div className="font-mono text-sm font-medium">{value}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Personal Notes */}
              <div className="px-6 pb-8">
                <div className="flex items-center gap-2 mb-3">
                  <FileText className="w-3 h-3 text-obsidian-400/50 dark:text-paper-100/50" />
                  <div className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
                    Personal Notes
                  </div>
                </div>
                <div className="relative">
                  <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Add research notes, price targets, or thesis..."
                    className="w-full h-24 bg-deep-teal-800/5 dark:bg-white/5 rounded-xl border border-deep-teal-800/10 dark:border-white/10 p-3 text-sm font-sans focus:outline-none focus:ring-2 focus:ring-turquoise-mist/20 resize-none placeholder:text-obsidian-400/30"
                  />
                  <div className="absolute bottom-3 right-3">
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={!note}
                      className="h-7 text-xs bg-white/50 dark:bg-black/20 hover:bg-white dark:hover:bg-black/40"
                    >
                      Save
                    </Button>
                  </div>
                </div>
              </div>

            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>,
    document.body
  );
};
