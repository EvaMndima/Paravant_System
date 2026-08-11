import { useState } from 'react';
import { motion } from 'framer-motion';
import { Download } from 'lucide-react';
import { useDashboard } from '@/contexts/DashboardContext';
import { GlassCard, Badge, Button, MetricCard } from '@/components/ui';
import { SVGAreaChart, DonutChart } from '@/components/charts';
import { PositionsTable } from '@/components/dashboard';
import type { AreaChartData } from '@/components/charts/AreaChart';
import type { Position } from '@/components/dashboard/PositionsTable';
import { staggerContainer, fadeInUp } from '@/lib/animations';

// ── Static data ───────────────────────────────────────────────────────────────

type TimeRange = '1M' | '3M' | '6M' | 'YTD' | '1Y' | 'ALL';

const POSITIONS: Position[] = [
  { id: '1', symbol: 'BTC',  name: 'Bitcoin',   quantity: 0.42,  avgPrice: 59200, currentPrice: 62840, pl: 1528.80,  plPercent: 6.15,   weight: 38.2, assetType: 'Crypto' },
  { id: '2', symbol: 'ETH',  name: 'Ethereum',  quantity: 2.80,  avgPrice: 3240,  currentPrice: 3185,  pl: -154.00,  plPercent: -1.70,  weight: 24.6, assetType: 'Crypto' },
  { id: '3', symbol: 'SOL',  name: 'Solana',    quantity: 18,    avgPrice: 142,   currentPrice: 148,   pl: 108.00,   plPercent: 4.23,   weight: 12.1, assetType: 'Crypto' },
  { id: '4', symbol: 'BNB',  name: 'BNB',       quantity: 3.50,  avgPrice: 570,   currentPrice: 584,   pl: 49.00,    plPercent: 2.46,   weight: 11.8, assetType: 'Crypto' },
  { id: '5', symbol: 'AVAX', name: 'Avalanche', quantity: 24,    avgPrice: 41.5,  currentPrice: 38.2,  pl: -79.20,   plPercent: -7.95,  weight: 5.3,  assetType: 'Crypto' },
  { id: '6', symbol: 'XRP',  name: 'XRP',       quantity: 580,   avgPrice: 0.51,  currentPrice: 0.524, pl: 8.12,     plPercent: 2.74,   weight: 3.1,  assetType: 'Crypto' },
  { id: '7', symbol: 'DOGE', name: 'Dogecoin',  quantity: 2400,  avgPrice: 0.17,  currentPrice: 0.162, pl: -19.20,   plPercent: -4.71,  weight: 2.0,  assetType: 'Crypto' },
];

const USDT_BALANCE  = 5820.40;
const totalValue    = POSITIONS.reduce((s, p) => s + p.quantity * p.currentPrice, 0);
const totalPnl      = POSITIONS.reduce((s, p) => s + p.pl, 0);
const portfolioValue = totalValue + USDT_BALANCE;

const ALLOCATION_DATA = [
  { name: 'BTC',  value: 38.2, color: '#f7931a' },
  { name: 'ETH',  value: 24.6, color: '#627eea' },
  { name: 'SOL',  value: 12.1, color: '#9945ff' },
  { name: 'BNB',  value: 11.8, color: '#f3ba2f' },
  { name: 'AVAX', value: 5.3,  color: '#e84142' },
  { name: 'XRP',  value: 3.1,  color: '#00aae4' },
  { name: 'DOGE', value: 2.0,  color: '#c2a633' },
  { name: 'USDT', value: 2.9,  color: '#26a17b' },
];

// Equity curves keyed by time range
const buildCurve = (days: number, start: number): AreaChartData[] =>
  Array.from({ length: days }, (_, i) => ({
    date: new Date(Date.now() - (days - 1 - i) * 86400000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    value: start + Math.round((Math.sin(i * 0.25) * 600) + (i * 80) + (Math.random() * 300)),
  }));

const CURVES: Record<TimeRange, AreaChartData[]> = {
  '1M':  buildCurve(30,  95000),
  '3M':  buildCurve(90,  82000),
  '6M':  buildCurve(180, 75000),
  'YTD': buildCurve(120, 80000),
  '1Y':  buildCurve(365, 68000),
  'ALL': buildCurve(500, 60000),
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function PortfolioPage() {
  const { openPositionDrawer, openExportModal } = useDashboard();
  const [timeRange, setTimeRange] = useState<TimeRange>('1M');

  const curve = CURVES[timeRange];
  const curveStart = curve[0]?.value ?? 0;
  const curveEnd   = curve[curve.length - 1]?.value ?? 0;
  const curveGain  = curveEnd - curveStart;

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="space-y-4"
    >
      {/* Header */}
      <motion.div variants={fadeInUp} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-paper-100">Portfolio</h1>
          <p className="text-sm text-paper-400 mt-1">Crypto holdings, equity curve, and allocation</p>
        </div>
        <Button variant="ghost" size="sm" onClick={openExportModal}>
          <Download className="w-4 h-4 mr-1" /> Export
        </Button>
      </motion.div>

      {/* KPI Row */}
      <motion.div variants={fadeInUp} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Portfolio Value"
          value={portfolioValue}
          format="currency"
          prefix="$"
        />
        <MetricCard
          title="Unrealized P&L"
          value={totalPnl}
          format="currency"
          prefix="$"
          change={totalPnl}
        />
        <MetricCard
          title="Open Positions"
          value={POSITIONS.length}
          format="number"
        />
        <MetricCard
          title="USDT Available"
          value={USDT_BALANCE}
          format="currency"
          prefix="$"
        />
      </motion.div>

      {/* Chart + Allocation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Equity Curve */}
        <motion.div variants={fadeInUp} className="lg:col-span-2">
          <GlassCard>
            <div className="flex items-center justify-between mb-2">
              <div>
                <h2 className="text-sm font-medium text-paper-200">Portfolio Equity</h2>
                <div className={`text-xs mt-0.5 ${curveGain >= 0 ? 'text-gain' : 'text-loss'}`}>
                  {curveGain >= 0 ? '+' : ''}${curveGain.toLocaleString()} over period
                </div>
              </div>
              <div className="flex gap-1">
                {(['1M', '3M', '6M', 'YTD', '1Y', 'ALL'] as TimeRange[]).map(r => (
                  <button
                    key={r}
                    onClick={() => setTimeRange(r)}
                    className={`px-2 py-1 text-xs rounded transition-colors ${
                      timeRange === r
                        ? 'bg-turquoise/10 text-turquoise font-medium'
                        : 'text-paper-400 hover:text-paper-200'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
            <SVGAreaChart data={curve} height={180} showGrid />
          </GlassCard>
        </motion.div>

        {/* Allocation Donut */}
        <motion.div variants={fadeInUp}>
          <GlassCard className="h-full">
            <h2 className="text-sm font-medium text-paper-200 mb-3">Asset Allocation</h2>
            <DonutChart
              data={ALLOCATION_DATA}
              height={200}
              showLegend
              centerContent={
                <div className="text-center">
                  <div className="text-base font-semibold text-paper-100">
                    ${Math.round(portfolioValue / 1000)}K
                  </div>
                  <div className="text-xs text-paper-400">total</div>
                </div>
              }
            />
          </GlassCard>
        </motion.div>
      </div>

      {/* Holdings Table */}
      <motion.div variants={fadeInUp}>
        <GlassCard>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-paper-200">Holdings</h2>
            <Badge variant="neutral" size="sm">{POSITIONS.length} positions</Badge>
          </div>
          <PositionsTable
            data={POSITIONS}
            onPositionClick={(p) => {
              openPositionDrawer({
                id: p.id,
                symbol: p.symbol,
                name: p.name,
                sector: 'Crypto',
                assetType: 'Crypto',
                quantity: p.quantity,
                avgCost: p.avgPrice,
                price: p.currentPrice,
                value: p.quantity * p.currentPrice,
                pnl: p.pl,
                pnlPercent: p.plPercent,
                weight: p.weight,
              });
            }}
          />
          {/* USDT cash row */}
          <div className="mt-2 pt-2 border-t border-obsidian-200 flex items-center justify-between text-sm">
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-full bg-[#26a17b]/20 flex items-center justify-center">
                <span className="text-xs font-bold text-[#26a17b]">U</span>
              </div>
              <div>
                <div className="text-paper-200 font-medium">USDT</div>
                <div className="text-xs text-paper-400">Tether USD &mdash; Cash</div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-paper-200 font-medium">${USDT_BALANCE.toLocaleString()}</div>
              <div className="text-xs text-paper-400">2.9% of portfolio</div>
            </div>
          </div>
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
