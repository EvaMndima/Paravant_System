import React from 'react';
import {
  ArrowRight, TrendingUp, TrendingDown, Clock, DollarSign,
  Zap, BarChart2, Hash, Layers,
} from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Badge } from '@/components/ui/Badge';
import { GlassCard } from '@/components/ui/GlassCard';
import { AreaChart } from '@/components/charts/AreaChart';
import { cn, formatCurrency, formatNumber } from '@/lib/utils';
import type { AreaChartData } from '@/components/charts/AreaChart';

export interface TradeDetail {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  status: 'open' | 'closed' | 'cancelled';
  strategyName: string;
  // Execution
  entryTime: string;
  exitTime?: string;
  duration?: string;
  entryPrice: number;
  exitPrice?: number;
  quantity: number;
  // P&L
  pnl?: number;
  pnlPct?: number;
  fees: number;
  slippage: number;
  netPnl?: number;
  // Context
  regime: string;
  signalStrength: number; // 0-100
  priceAtSignal: number;
  priceChart: AreaChartData[];
}

export interface TradeDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  trade?: TradeDetail;
}

// Generate a price chart for the trade window
function generateTradeChart(entry: number, exit: number, points = 30): AreaChartData[] {
  const data: AreaChartData[] = [];
  let price = entry;
  for (let i = 0; i <= points; i++) {
    const progress = i / points;
    const target = entry + (exit - entry) * progress;
    const noise = (Math.random() - 0.48) * entry * 0.008;
    price = price * 0.7 + target * 0.3 + noise;
    data.push({
      date: `${i}h`,
      value: Math.round(price * 100) / 100,
    });
  }
  return data;
}

const mockTrade: TradeDetail = {
  id: 'TRD-20241203-0042',
  symbol: 'BTCUSDT',
  side: 'long',
  status: 'closed',
  strategyName: 'Momentum_MACD',
  entryTime: 'Dec 3, 2024 09:14:22 UTC',
  exitTime: 'Dec 7, 2024 16:30:05 UTC',
  duration: '4d 7h 16m',
  entryPrice: 94250,
  exitPrice: 98420,
  quantity: 0.0532,
  pnl: 221.84,
  pnlPct: 4.42,
  fees: 18.62,
  slippage: 2.14,
  netPnl: 201.08,
  regime: 'trending_up',
  signalStrength: 78,
  priceAtSignal: 94180,
  priceChart: generateTradeChart(94250, 98420),
};

interface FieldRowProps {
  label: string;
  value: React.ReactNode;
  icon?: React.ElementType;
  accent?: 'gain' | 'loss' | 'neutral';
}

const FieldRow: React.FC<FieldRowProps> = ({ label, value, icon: Icon, accent }) => (
  <div className="flex items-center justify-between py-2.5 border-b border-deep-teal-800/5 dark:border-white/5 last:border-0">
    <div className="flex items-center gap-2 text-xs font-sans text-obsidian-400/60 dark:text-paper-100/60">
      {Icon && <Icon className="w-3.5 h-3.5 opacity-60" />}
      {label}
    </div>
    <span className={cn(
      'text-sm font-mono font-medium',
      accent === 'gain' ? 'text-gain' : accent === 'loss' ? 'text-loss' : 'text-obsidian-400 dark:text-paper-100'
    )}>
      {value}
    </span>
  </div>
);

export const TradeDetailModal: React.FC<TradeDetailModalProps> = ({
  isOpen,
  onClose,
  trade,
}) => {
  const t = trade ?? mockTrade;
  const isProfit = (t.netPnl ?? t.pnl ?? 0) >= 0;

  const statusVariant: Record<string, 'success' | 'info' | 'neutral'> = {
    closed: 'neutral',
    open: 'success',
    cancelled: 'neutral',
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Trade: ${t.symbol.replace('USDT', '/USDT')}`}
      description={`${t.strategyName} — ${t.id}`}
      size="md"
    >
      <div className="space-y-5">
        {/* Status badges */}
        <div className="flex flex-wrap gap-2">
          <Badge variant={statusVariant[t.status] ?? 'neutral'} size="sm" dot={t.status === 'open'} pulsing={t.status === 'open'}>
            {t.status}
          </Badge>
          <Badge variant={t.side === 'long' ? 'success' : 'danger'} size="sm">
            {t.side === 'long' ? 'LONG' : 'SHORT'}
          </Badge>
          <Badge variant="outline" size="sm">{t.regime.replace('_', ' ')}</Badge>
        </div>

        {/* P&L Hero */}
        <GlassCard
          variant={isProfit ? 'default' : 'default'}
          padding="md"
          className={cn(
            'text-center border',
            isProfit
              ? 'border-gain/20 bg-gain/5'
              : 'border-loss/20 bg-loss/5'
          )}
        >
          <div className="flex items-center justify-center gap-2 mb-1">
            {isProfit
              ? <TrendingUp className="w-5 h-5 text-gain" />
              : <TrendingDown className="w-5 h-5 text-loss" />
            }
            <span className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
              Net P&L
            </span>
          </div>
          <div className={cn('text-3xl font-mono font-bold leading-none', isProfit ? 'text-gain' : 'text-loss')}>
            {isProfit ? '+' : ''}{formatCurrency(t.netPnl ?? t.pnl ?? 0)}
          </div>
          <div className={cn('text-sm font-mono mt-1 opacity-80', isProfit ? 'text-gain' : 'text-loss')}>
            {isProfit ? '+' : ''}{formatNumber(t.pnlPct ?? 0)}%
          </div>
          <div className="text-[10px] font-sans text-obsidian-400/40 dark:text-paper-100/40 mt-1">
            After {formatCurrency(t.fees)} fees + {formatCurrency(t.slippage)} slippage
          </div>
        </GlassCard>

        {/* Price chart */}
        <div>
          <h4 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-2">
            Price During Trade
          </h4>
          <AreaChart
            data={t.priceChart}
            height={140}
            showGrid={false}
            gradientId="trade-detail-chart"
            showTooltip={true}
            animate={false}
          />
          {/* Entry / Exit markers */}
          <div className="flex items-center justify-between mt-2 px-1">
            <div className="text-center">
              <div className="text-[10px] font-mono uppercase tracking-widest text-gain/60 mb-0.5">Entry</div>
              <div className="text-xs font-mono font-bold text-gain">{formatCurrency(t.entryPrice)}</div>
            </div>
            <ArrowRight className="w-4 h-4 text-obsidian-400/30 dark:text-paper-100/30" />
            {t.exitPrice !== undefined ? (
              <div className="text-center">
                <div className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 mb-0.5">Exit</div>
                <div className={cn('text-xs font-mono font-bold', isProfit ? 'text-gain' : 'text-loss')}>
                  {formatCurrency(t.exitPrice)}
                </div>
              </div>
            ) : (
              <Badge variant="success" size="sm" dot pulsing>Live</Badge>
            )}
          </div>
        </div>

        {/* Execution details */}
        <div>
          <h4 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-2">
            Execution
          </h4>
          <GlassCard variant="subtle" padding="sm">
            <FieldRow label="Trade ID" value={t.id} icon={Hash} />
            <FieldRow label="Entry Time" value={t.entryTime} icon={Clock} />
            {t.exitTime && <FieldRow label="Exit Time" value={t.exitTime} icon={Clock} />}
            {t.duration && <FieldRow label="Duration" value={t.duration} icon={Clock} />}
            <FieldRow label="Quantity" value={`${t.quantity} ${t.symbol.replace('USDT', '')}`} icon={Layers} />
            <FieldRow label="Notional Value" value={formatCurrency(t.entryPrice * t.quantity)} icon={DollarSign} />
          </GlassCard>
        </div>

        {/* Cost breakdown */}
        <div>
          <h4 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-2">
            Cost Breakdown
          </h4>
          <GlassCard variant="subtle" padding="sm">
            {t.pnl !== undefined && (
              <FieldRow label="Gross P&L" value={`${isProfit ? '+' : ''}${formatCurrency(t.pnl)}`} icon={TrendingUp} accent={isProfit ? 'gain' : 'loss'} />
            )}
            <FieldRow label="Trading Fees" value={`-${formatCurrency(t.fees)}`} icon={DollarSign} accent="loss" />
            <FieldRow label="Slippage" value={`-${formatCurrency(t.slippage)}`} icon={Zap} accent="loss" />
            {t.netPnl !== undefined && (
              <FieldRow label="Net P&L" value={`${isProfit ? '+' : ''}${formatCurrency(t.netPnl)}`} icon={BarChart2} accent={isProfit ? 'gain' : 'loss'} />
            )}
          </GlassCard>
        </div>

        {/* Signal context */}
        <div>
          <h4 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-2">
            Signal Context
          </h4>
          <GlassCard variant="subtle" padding="sm">
            <FieldRow label="Signal Strength" value={
              <div className="flex items-center gap-2">
                <div className="w-20 h-1.5 rounded-full bg-deep-teal-800/10 dark:bg-white/10 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-turquoise-mist"
                    style={{ width: `${t.signalStrength}%` }}
                  />
                </div>
                <span>{t.signalStrength}%</span>
              </div>
            } icon={Zap} />
            <FieldRow label="Price at Signal" value={formatCurrency(t.priceAtSignal)} icon={BarChart2} />
            <FieldRow label="Market Regime" value={t.regime.replace(/_/g, ' ')} icon={TrendingUp} />
          </GlassCard>
        </div>
      </div>
    </Modal>
  );
};
