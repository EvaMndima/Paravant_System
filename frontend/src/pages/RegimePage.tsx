import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Bell, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { useDashboard } from '@/contexts/DashboardContext';
import { GlassCard, Badge, Button } from '@/components/ui';
import { SparklineChart } from '@/components/charts';
import { MarketRegimePanel } from '@/components/dashboard';
import type { MarketRegimeData } from '@/components/dashboard/MarketRegimePanel';
import { staggerContainer, fadeInUp } from '@/lib/animations';
import { useRegimeState } from '@/hooks/useRegimeState';

// ── Types ─────────────────────────────────────────────────────────────────────

type MoverTab = 'watchlist' | 'gainers' | 'losers';

interface CryptoIndex {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  sparkline: number[];
}

interface Sector {
  name: string;
  changePercent: number;
  description: string;
  color: string;
}

interface Mover {
  symbol: string;
  name: string;
  price: number;
  changePercent: number;
  volume: string;
}

// ── Static data ───────────────────────────────────────────────────────────────

const CRYPTO_INDICES: CryptoIndex[] = [
  { symbol: 'BTC',  name: 'Bitcoin',   price: 62840, change: 1420,  changePercent: 2.31,  sparkline: [58000,59200,60100,61400,60800,62100,61500,62840] },
  { symbol: 'ETH',  name: 'Ethereum',  price: 3185,  change: -42,   changePercent: -1.30, sparkline: [3350, 3290, 3310, 3270, 3240, 3200, 3220, 3185] },
  { symbol: 'BNB',  name: 'BNB',       price: 584,   change: 8.2,   changePercent: 1.42,  sparkline: [565,  570,  568,  574,  571,  578,  576,  584] },
  { symbol: 'SOL',  name: 'Solana',    price: 148,   change: 3.5,   changePercent: 2.42,  sparkline: [136,  139,  141,  140,  143,  145,  146,  148] },
  { symbol: 'AVAX', name: 'Avalanche', price: 38.2,  change: -0.8,  changePercent: -2.05, sparkline: [42,   41.5, 40.8, 40.2, 39.5, 39.1, 38.7, 38.2] },
  { symbol: 'XRP',  name: 'XRP',       price: 0.524, change: 0.012, changePercent: 2.35,  sparkline: [0.49, 0.50, 0.505, 0.51, 0.512, 0.515, 0.52, 0.524] },
];

const BTC_DOMINANCE = 52.4;
const FEAR_GREED    = 22;  // 0-100, lower = more fear

const SECTORS: Sector[] = [
  { name: 'L1 Blockchains',     changePercent: 1.84,  description: 'BTC, ETH, SOL, AVAX, BNB',  color: '#14b8a6' },
  { name: 'DeFi Protocols',     changePercent: -2.14, description: 'AAVE, UNI, CRV, COMP',       color: '#6366f1' },
  { name: 'L2 Solutions',       changePercent: -1.08, description: 'MATIC, ARB, OP, BASE',       color: '#f59e0b' },
  { name: 'Exchange Tokens',    changePercent: 1.42,  description: 'BNB, FTT, KCS, OKB',         color: '#3b82f6' },
  { name: 'Meme Coins',         changePercent: -3.21, description: 'DOGE, SHIB, PEPE, FLOKI',    color: '#ec4899' },
  { name: 'Stablecoins',        changePercent: 0.01,  description: 'USDT, USDC, DAI, FDUSD',     color: '#26a17b' },
];

const REGIME_INDICATORS: MarketRegimeData['indicators'] = {
  vix:         { value: 28.4,  label: 'Crypto Fear Index',  status: 'elevated' },
  breadth:     { value: '34%', label: 'Coins Above 20MA',   status: 'weak'     },
  trend:       { value: -3.2,  label: 'BTC 7d Change %',    status: 'bearish'  },
  correlation: { value: 0.82,  label: 'Cross-Asset Corr',   status: 'high'     },
  putCall:     { value: 22,    label: 'Fear & Greed Index', status: 'fear'     },
};

const REGIME_DISPLAY: Record<string, { type: string; commentary: string }> = {
  strong_bull:  {
    type: 'STRONG BULL',
    commentary: 'BTC above EMA50 in confirmed bull structure (EMA50 > EMA200). Bull strategies active.',
  },
  pullback_bull: {
    type: 'PULLBACK BULL',
    commentary: 'BTC in bull structure (EMA50 > EMA200) but pulling back below EMA50. Monitoring for re-entry.',
  },
  bounce_bear:  {
    type: 'BOUNCE BEAR',
    commentary: 'BTC showing a bear bounce. EMA50 < EMA200 — bear structure intact. Bear strategies active.',
  },
  strong_bear:  {
    type: 'STRONG BEAR',
    commentary: 'BTC below EMA50 in confirmed bear structure (EMA50 < EMA200). Bear strategies active.',
  },
  unknown:      {
    type: 'UNKNOWN',
    commentary: 'Regime detection in progress or insufficient data. Monitoring all-regime strategies only.',
  },
};

const MOVERS_GAINERS: Mover[] = [
  { symbol: 'BTC',  name: 'Bitcoin',   price: 62840, changePercent: 2.31,  volume: '$28.4B' },
  { symbol: 'SOL',  name: 'Solana',    price: 148,   changePercent: 2.42,  volume: '$3.1B' },
  { symbol: 'XRP',  name: 'XRP',       price: 0.524, changePercent: 2.35,  volume: '$1.8B' },
  { symbol: 'BNB',  name: 'BNB',       price: 584,   changePercent: 1.42,  volume: '$980M' },
  { symbol: 'LINK', name: 'Chainlink', price: 14.82, changePercent: 4.12,  volume: '$420M' },
];

const MOVERS_LOSERS: Mover[] = [
  { symbol: 'DOGE', name: 'Dogecoin',  price: 0.162, changePercent: -2.41, volume: '$890M' },
  { symbol: 'AVAX', name: 'Avalanche', price: 38.2,  changePercent: -2.05, volume: '$340M' },
  { symbol: 'ETH',  name: 'Ethereum',  price: 3185,  changePercent: -1.30, volume: '$12.1B' },
  { symbol: 'MATIC',name: 'Polygon',   price: 0.78,  changePercent: -3.14, volume: '$280M' },
  { symbol: 'PEPE', name: 'PEPE',      price: 0.000011, changePercent: -5.82, volume: '$190M' },
];

const WATCHLIST_MOVERS: Mover[] = [
  { symbol: 'BTC',  name: 'Bitcoin',   price: 62840, changePercent: 2.31,  volume: '$28.4B' },
  { symbol: 'ETH',  name: 'Ethereum',  price: 3185,  changePercent: -1.30, volume: '$12.1B' },
  { symbol: 'SOL',  name: 'Solana',    price: 148,   changePercent: 2.42,  volume: '$3.1B' },
  { symbol: 'BNB',  name: 'BNB',       price: 584,   changePercent: 1.42,  volume: '$980M' },
  { symbol: 'AVAX', name: 'Avalanche', price: 38.2,  changePercent: -2.05, volume: '$340M' },
  { symbol: 'XRP',  name: 'XRP',       price: 0.524, changePercent: 2.35,  volume: '$1.8B' },
  { symbol: 'DOGE', name: 'Dogecoin',  price: 0.162, changePercent: -2.41, volume: '$890M' },
];

function fearGreedLabel(score: number): { label: string; variant: 'danger' | 'warning' | 'neutral' | 'success' } {
  if (score <= 25)  return { label: 'Extreme Fear', variant: 'danger' };
  if (score <= 45)  return { label: 'Fear',         variant: 'warning' };
  if (score <= 55)  return { label: 'Neutral',      variant: 'neutral' };
  if (score <= 75)  return { label: 'Greed',        variant: 'success' };
  return { label: 'Extreme Greed', variant: 'success' };
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function RegimePage() {
  const { openAlertModal } = useDashboard();
  const [moverTab, setMoverTab] = useState<MoverTab>('watchlist');
  const { regime } = useRegimeState();

  const regimeData: MarketRegimeData = useMemo(() => {
    const display = REGIME_DISPLAY[regime?.state ?? 'unknown'] ?? REGIME_DISPLAY['unknown'];
    return {
      type: display.type,
      confidence: 78,
      duration: regime?.updatedAt
        ? new Date(regime.updatedAt).toLocaleDateString()
        : '—',
      indicators: REGIME_INDICATORS,
      commentary: display.commentary,
    };
  }, [regime]);

  const fearGreed = fearGreedLabel(FEAR_GREED);

  const moverData: Record<MoverTab, Mover[]> = {
    watchlist: WATCHLIST_MOVERS,
    gainers:   MOVERS_GAINERS,
    losers:    MOVERS_LOSERS,
  };

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
          <h1 className="text-2xl font-semibold text-paper-100">Markets</h1>
          <p className="text-sm text-paper-400 mt-1">Crypto market regime, sector performance, and movers</p>
        </div>
        <Button variant="ghost" size="sm" onClick={() => openAlertModal()}>
          <Bell className="w-4 h-4 mr-1" /> Set Alert
        </Button>
      </motion.div>

      {/* Crypto Indices Row */}
      <motion.div variants={fadeInUp} className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {CRYPTO_INDICES.map(idx => (
          <GlassCard key={idx.symbol} className="p-3 cursor-pointer hover:border-turquoise/20 transition-colors"
            onClick={() => openAlertModal(idx.symbol)}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-paper-200">{idx.symbol}</span>
              <span className={`text-xs font-medium ${idx.changePercent >= 0 ? 'text-gain' : 'text-loss'}`}>
                {idx.changePercent >= 0 ? '+' : ''}{idx.changePercent.toFixed(2)}%
              </span>
            </div>
            <div className="text-sm font-semibold text-paper-100 mb-2">
              ${idx.price >= 1 ? idx.price.toLocaleString() : idx.price.toFixed(4)}
            </div>
            <SparklineChart
              data={idx.sparkline}
              width="100%"
              height={28}
              color={idx.changePercent >= 0 ? 'gain' : 'loss'}
            />
          </GlassCard>
        ))}
      </motion.div>

      {/* Market Regime + Sentiment */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        <motion.div variants={fadeInUp} className="lg:col-span-2">
          <MarketRegimePanel data={regimeData} />
        </motion.div>

        {/* Sentiment Indicators */}
        <motion.div variants={fadeInUp}>
          <GlassCard className="h-full">
            <h2 className="text-sm font-medium text-paper-200 mb-4">Market Sentiment</h2>
            <div className="space-y-4">

              {/* BTC Dominance */}
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-paper-400">BTC Dominance</span>
                  <span className="text-paper-200 font-medium">{BTC_DOMINANCE}%</span>
                </div>
                <div className="h-2 bg-obsidian-200 rounded-full overflow-hidden">
                  <div className="h-full bg-[#f7931a] rounded-full" style={{ width: `${BTC_DOMINANCE}%` }} />
                </div>
                <div className="text-xs text-paper-500 mt-1">High dominance = risk-off, alts underperform</div>
              </div>

              {/* Fear & Greed */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs text-paper-400">Fear &amp; Greed Index</span>
                  <Badge variant={fearGreed.variant} size="sm">{fearGreed.label}</Badge>
                </div>
                <div className="relative h-8 bg-gradient-to-r from-loss via-warning to-gain rounded-full overflow-hidden">
                  <div
                    className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-paper-100 rounded-full shadow-lg border-2 border-obsidian-400"
                    style={{ left: `calc(${FEAR_GREED}% - 6px)` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-paper-500 mt-1">
                  <span>0 Extreme Fear</span>
                  <span className="font-medium text-paper-300">{FEAR_GREED}</span>
                  <span>100 Extreme Greed</span>
                </div>
              </div>

              {/* Market Regime Summary */}
              <div className="p-3 rounded-lg bg-obsidian-300/50 border border-obsidian-200">
                <div className="text-xs font-medium text-warning mb-1">Current Regime: BEAR TREND</div>
                <p className="text-xs text-paper-400">
                  BTC below 20-day MA. High dominance signals altcoin weakness.
                  BTF and trend-following strategies active.
                </p>
              </div>
            </div>
          </GlassCard>
        </motion.div>
      </div>

      {/* Sector Performance + Movers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Sector Performance */}
        <motion.div variants={fadeInUp}>
          <GlassCard>
            <h2 className="text-sm font-medium text-paper-200 mb-4">Crypto Sector Performance</h2>
            <div className="space-y-3">
              {SECTORS.map(sector => (
                <div key={sector.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: sector.color }} />
                    <div className="min-w-0">
                      <div className="text-sm text-paper-200">{sector.name}</div>
                      <div className="text-xs text-paper-500 truncate">{sector.description}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {sector.changePercent > 0.1
                      ? <TrendingUp className="w-3 h-3 text-gain" />
                      : sector.changePercent < -0.1
                      ? <TrendingDown className="w-3 h-3 text-loss" />
                      : <Minus className="w-3 h-3 text-paper-400" />}
                    <span className={`text-sm font-medium w-14 text-right ${
                      sector.changePercent > 0.1 ? 'text-gain'
                      : sector.changePercent < -0.1 ? 'text-loss'
                      : 'text-paper-400'}`}>
                      {sector.changePercent >= 0 ? '+' : ''}{sector.changePercent.toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </motion.div>

        {/* Market Movers */}
        <motion.div variants={fadeInUp}>
          <GlassCard>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-paper-200">Market Movers</h2>
              <div className="flex gap-1">
                {(['watchlist', 'gainers', 'losers'] as MoverTab[]).map(tab => (
                  <button
                    key={tab}
                    onClick={() => setMoverTab(tab)}
                    className={`px-2 py-1 text-xs rounded capitalize transition-colors ${
                      moverTab === tab
                        ? 'bg-turquoise/10 text-turquoise'
                        : 'text-paper-400 hover:text-paper-200'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-1">
              <div className="grid grid-cols-4 text-xs text-paper-500 pb-1 border-b border-obsidian-200">
                <span>Symbol</span>
                <span className="text-right">Price</span>
                <span className="text-right">Change</span>
                <span className="text-right">Volume</span>
              </div>
              {moverData[moverTab].map(m => (
                <div
                  key={m.symbol}
                  className="grid grid-cols-4 py-2 hover:bg-obsidian-300/30 rounded px-1 cursor-pointer transition-colors"
                  onClick={() => openAlertModal(m.symbol)}
                >
                  <div>
                    <div className="text-sm font-medium text-paper-100">{m.symbol}</div>
                    <div className="text-xs text-paper-500">{m.name}</div>
                  </div>
                  <div className="text-right text-sm text-paper-200 self-center">
                    ${m.price >= 1 ? m.price.toLocaleString() : m.price.toFixed(6)}
                  </div>
                  <div className={`text-right text-sm font-medium self-center ${m.changePercent >= 0 ? 'text-gain' : 'text-loss'}`}>
                    {m.changePercent >= 0 ? '+' : ''}{m.changePercent.toFixed(2)}%
                  </div>
                  <div className="text-right text-xs text-paper-400 self-center">{m.volume}</div>
                </div>
              ))}
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </motion.div>
  );
}
