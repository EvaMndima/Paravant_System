import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, ChevronDown, ChevronUp, TrendingUp, TrendingDown } from 'lucide-react';
import { useDashboard } from '@/contexts/DashboardContext';
import { GlassCard, Badge, Button, MetricCard } from '@/components/ui';
import { staggerContainer, fadeInUp } from '@/lib/animations';

// ── Types ─────────────────────────────────────────────────────────────────────

type OutcomeFilter = 'all' | 'win' | 'loss';

interface TradeRecord {
  id: string;
  symbol: string;
  pair: string;
  direction: 'long' | 'short';
  strategy: string;
  entryPrice: number;
  exitPrice: number;
  quantity: number;
  pnl: number;
  pnlPct: number;
  entryTime: string;
  exitTime: string;
  duration: string;
  confidence: number;
  signals: string[];
}

// ── Static data ───────────────────────────────────────────────────────────────

const STRATEGIES = ['All', 'Bear Trend Follower', 'Ichimoku Cloud VP', 'Cascading Momentum Filter', 'EMA Trend RSI', 'Donchian ATR', 'Supertrend Volume MACD'];

function generateTrades(): TradeRecord[] {
  const symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'AVAX', 'XRP', 'DOGE'];
  const pairs   = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'AVAXUSDT', 'XRPUSDT', 'DOGEUSDT'];
  const strats  = ['Bear Trend Follower', 'Ichimoku Cloud VP', 'Cascading Momentum Filter', 'EMA Trend RSI', 'Donchian ATR', 'Supertrend Volume MACD'];

  const entries = [
    [62100, 61200, 146, 578, 39.5, 0.512, 0.165],
    [3210,  3280,  152, 571, 40.1, 0.518, 0.170],
    [61800, 3150,  145, 575, 38.8, 0.510, 0.168],
    [62300, 3190,  149, 580, 39.8, 0.515, 0.164],
    [61500, 3100,  143, 568, 39.0, 0.508, 0.161],
  ];

  const exits = [
    [62840, 3185, 148, 584, 38.2, 0.524, 0.162],
    [62200, 3050, 145, 570, 37.8, 0.510, 0.155],
    [63100, 3220, 152, 590, 40.2, 0.530, 0.172],
    [61800, 3080, 144, 566, 38.0, 0.505, 0.158],
    [62500, 3160, 150, 585, 39.5, 0.520, 0.166],
  ];

  const signalSets = [
    ['EMA bearish cross', 'Volume spike', 'RSI < 40'],
    ['Ichimoku cloud breakdown', 'VP node rejection', 'Tenkan-Sen cross'],
    ['Momentum cascade confirmed', 'CMF negative', 'Price structure break'],
    ['Donchian lower channel break', 'ATR expansion', 'Bear candle close'],
    ['Supertrend flip', 'Volume > 1.5x avg', 'MACD histogram negative'],
  ];

  const dates = [
    '2026-04-30 14:32', '2026-04-30 12:18', '2026-04-30 10:05',
    '2026-04-29 18:42', '2026-04-29 15:30', '2026-04-29 13:15',
    '2026-04-29 09:48', '2026-04-28 22:10', '2026-04-28 19:35',
    '2026-04-28 14:20', '2026-04-28 11:05', '2026-04-28 08:30',
    '2026-04-27 20:15', '2026-04-27 17:40', '2026-04-27 14:00',
    '2026-04-27 10:22', '2026-04-27 07:45', '2026-04-26 21:30',
    '2026-04-26 18:50', '2026-04-26 15:10',
  ];

  return dates.map((entryTime, i) => {
    const si   = i % symbols.length;
    const stri = i % strats.length;
    const ei   = i % entries.length;
    const xi   = i % exits.length;
    const dir  = i % 3 === 0 ? 'short' : 'long';

    const entry  = entries[ei][si];
    const exit   = exits[xi][si];
    const qty    = si === 0 ? 0.05 : si === 1 ? 0.4 : si <= 3 ? 2 : si === 4 ? 10 : si === 5 ? 200 : 1000;
    const pnlRaw = dir === 'long' ? (exit - entry) * qty : (entry - exit) * qty;
    const pnlPct = dir === 'long' ? ((exit - entry) / entry) * 100 : ((entry - exit) / entry) * 100;

    const exitHours = 1 + (i % 24);
    const exitDate  = new Date(entryTime);
    exitDate.setHours(exitDate.getHours() + exitHours);

    return {
      id:         `t-${i + 1}`,
      symbol:     symbols[si],
      pair:       pairs[si],
      direction:  dir,
      strategy:   strats[stri],
      entryPrice: entry,
      exitPrice:  exit,
      quantity:   qty,
      pnl:        parseFloat(pnlRaw.toFixed(2)),
      pnlPct:     parseFloat(pnlPct.toFixed(2)),
      entryTime,
      exitTime:   exitDate.toISOString().replace('T', ' ').substring(0, 16),
      duration:   exitHours >= 24 ? `${Math.floor(exitHours / 24)}d ${exitHours % 24}h` : `${exitHours}h`,
      confidence: 60 + (i % 35),
      signals:    signalSets[i % signalSets.length],
    };
  });
}

const ALL_TRADES = generateTrades();

// ── Component ─────────────────────────────────────────────────────────────────

export default function TradeHistoryPage() {
  const { openExportModal } = useDashboard();
  const [outcomeFilter, setOutcomeFilter] = useState<OutcomeFilter>('all');
  const [strategyFilter, setStrategyFilter] = useState('All');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return ALL_TRADES.filter(t => {
      const matchesOutcome   = outcomeFilter === 'all' || (outcomeFilter === 'win' ? t.pnl > 0 : t.pnl < 0);
      const matchesStrategy  = strategyFilter === 'All' || t.strategy === strategyFilter;
      return matchesOutcome && matchesStrategy;
    });
  }, [outcomeFilter, strategyFilter]);

  const stats = useMemo(() => {
    const wins  = ALL_TRADES.filter(t => t.pnl > 0);
    const total = ALL_TRADES.reduce((s, t) => s + t.pnl, 0);
    const best  = ALL_TRADES.reduce((b, t) => t.pnl > b.pnl ? t : b, ALL_TRADES[0]);
    return {
      total:   ALL_TRADES.length,
      winRate: Math.round((wins.length / ALL_TRADES.length) * 100),
      avgPnl:  parseFloat((total / ALL_TRADES.length).toFixed(2)),
      bestPnl: parseFloat(best.pnl.toFixed(2)),
    };
  }, []);

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
          <h1 className="text-2xl font-semibold text-paper-100">Trade History</h1>
          <p className="text-sm text-paper-400 mt-1">Complete PARAVANT paper trading log</p>
        </div>
        <Button variant="ghost" size="sm" onClick={openExportModal}>
          <Download className="w-4 h-4 mr-1" /> Export
        </Button>
      </motion.div>

      {/* Stats */}
      <motion.div variants={fadeInUp} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Total Trades" value={stats.total}   format="number" />
        <MetricCard title="Win Rate"     value={stats.winRate} format="percent" suffix="%" />
        <MetricCard title="Avg P&L"      value={stats.avgPnl}  format="currency" prefix="$" change={stats.avgPnl} />
        <MetricCard title="Best Trade"   value={stats.bestPnl} format="currency" prefix="$" />
      </motion.div>

      {/* Filters */}
      <motion.div variants={fadeInUp} className="flex flex-wrap gap-3">
        <div className="flex gap-1">
          {(['all', 'win', 'loss'] as OutcomeFilter[]).map(f => (
            <button
              key={f}
              onClick={() => setOutcomeFilter(f)}
              className={`px-3 py-1.5 text-xs rounded-lg capitalize transition-colors ${
                outcomeFilter === f
                  ? 'bg-turquoise/10 text-turquoise font-medium'
                  : 'bg-obsidian-300 text-paper-400 hover:text-paper-200'
              }`}
            >
              {f === 'win' ? 'Winners' : f === 'loss' ? 'Losers' : 'All Trades'}
            </button>
          ))}
        </div>
        <select
          value={strategyFilter}
          onChange={e => setStrategyFilter(e.target.value)}
          className="bg-obsidian-300 border border-obsidian-200 text-paper-200 text-xs rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-turquoise focus:outline-none"
        >
          {STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <span className="text-xs text-paper-400 self-center">{filtered.length} trades</span>
      </motion.div>

      {/* Trade List */}
      <motion.div variants={staggerContainer} className="space-y-2">
        {filtered.map(trade => {
          const isExpanded = expandedId === trade.id;
          const isWin      = trade.pnl > 0;

          return (
            <motion.div key={trade.id} variants={fadeInUp}>
              <GlassCard className={`cursor-pointer hover:border-turquoise/20 transition-colors ${isExpanded ? 'border-turquoise/20' : ''}`}
                onClick={() => setExpandedId(isExpanded ? null : trade.id)}>

                {/* Summary Row */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${isWin ? 'bg-gain/10' : 'bg-loss/10'}`}>
                      {isWin
                        ? <TrendingUp className="w-3.5 h-3.5 text-gain" />
                        : <TrendingDown className="w-3.5 h-3.5 text-loss" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-paper-100">{trade.pair}</span>
                        <Badge variant={trade.direction === 'long' ? 'success' : 'danger'} size="sm">
                          {trade.direction.toUpperCase()}
                        </Badge>
                      </div>
                      <div className="text-xs text-paper-400">{trade.strategy} &bull; {trade.duration}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="hidden sm:block text-right">
                      <div className="text-xs text-paper-400">Entry</div>
                      <div className="text-sm text-paper-200">${trade.entryPrice.toLocaleString()}</div>
                    </div>
                    <div className="hidden sm:block text-right">
                      <div className="text-xs text-paper-400">Exit</div>
                      <div className="text-sm text-paper-200">${trade.exitPrice.toLocaleString()}</div>
                    </div>
                    <div className="text-right">
                      <div className={`text-sm font-semibold ${isWin ? 'text-gain' : 'text-loss'}`}>
                        {isWin ? '+' : ''}${trade.pnl.toFixed(2)}
                      </div>
                      <div className={`text-xs ${isWin ? 'text-gain' : 'text-loss'}`}>
                        {isWin ? '+' : ''}{trade.pnlPct.toFixed(2)}%
                      </div>
                    </div>
                    {isExpanded
                      ? <ChevronUp className="w-4 h-4 text-paper-400" />
                      : <ChevronDown className="w-4 h-4 text-paper-400" />}
                  </div>
                </div>

                {/* Expanded Detail */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-4 pt-4 border-t border-obsidian-200 grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <div>
                          <div className="text-xs text-paper-500 mb-1">Entry Time</div>
                          <div className="text-sm text-paper-200">{trade.entryTime}</div>
                        </div>
                        <div>
                          <div className="text-xs text-paper-500 mb-1">Exit Time</div>
                          <div className="text-sm text-paper-200">{trade.exitTime}</div>
                        </div>
                        <div>
                          <div className="text-xs text-paper-500 mb-1">Quantity</div>
                          <div className="text-sm text-paper-200">{trade.quantity} {trade.symbol}</div>
                        </div>
                        <div>
                          <div className="text-xs text-paper-500 mb-1">Confidence</div>
                          <div className="text-sm text-paper-200">{trade.confidence}%</div>
                        </div>
                      </div>
                      <div className="mt-3">
                        <div className="text-xs text-paper-500 mb-2">Entry Signals</div>
                        <div className="flex flex-wrap gap-2">
                          {trade.signals.map((sig, i) => (
                            <span key={i} className="text-xs px-2 py-1 rounded bg-obsidian-200 text-paper-300">{sig}</span>
                          ))}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </GlassCard>
            </motion.div>
          );
        })}
      </motion.div>
    </motion.div>
  );
}
