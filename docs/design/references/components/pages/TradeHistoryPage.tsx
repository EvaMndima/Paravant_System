
import React, { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  History, Calendar, Filter, Search, ChevronDown, ChevronUp,
  ArrowRight, TrendingUp, TrendingDown, Bot, Zap,
  CheckCircle2, XCircle, Clock, AlertTriangle, Activity, Download
} from 'lucide-react';

import { PageHeader } from '../layout/PageHeader';
import { GlassCard } from '../ui/GlassCard';
import { MetricCard } from '../ui/MetricCard';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { SearchInput } from '../ui/SearchInput';
import { Dropdown } from '../ui/Dropdown';
import { AreaChart } from '../dashboard/charts/AreaChart';
import { LoadingState } from '../ui/LoadingState';
import { EmptyState } from '../ui/EmptyState';
import { ErrorBoundary } from '../ui/ErrorBoundary';
import { ExportModal, ExportConfig } from '../dashboard/ExportModal';
import { cn, formatCurrency, formatNumber, formatPercent } from '../../lib/utils';
import { staggerContainer, fadeInUp, smoothSpring } from '../../lib/animations';
import { useToast } from '../../contexts/ToastContext';

// --- Types ---

export type TradeDirection = 'Long' | 'Short';
export type TradeOutcome = 'Profit' | 'Loss' | 'Breakeven' | 'Open';
export type AgentName = 'Alpha Seeker' | 'Momentum Prime' | 'Macro Sentinel' | 'Arb Hunter';

export interface TradeRecord {
  id: string;
  symbol: string;
  direction: TradeDirection;
  entryPrice: number;
  exitPrice: number | null;
  quantity: number;
  pnl: number;
  pnlPercent: number;
  duration: string;
  timestamp: Date;
  outcome: TradeOutcome;
  
  // AI Reasoning
  agent: AgentName;
  strategy: string;
  reasoning: string;
  confidence: number; // 0-100
  signals: string[];
  
  // Exit Details
  exitReason?: string;
  status: 'Closed' | 'Open';
}

// --- Mock Data Generation ---

const generateTrades = (count: number): TradeRecord[] => {
  const trades: TradeRecord[] = [];
  const agents: AgentName[] = ['Alpha Seeker', 'Momentum Prime', 'Macro Sentinel', 'Arb Hunter'];
  const strategies = ['Mean Reversion', 'Breakout', 'Trend Following', 'Statistical Arbitrage', 'Macro Discretionary'];
  const symbols = ['NVDA', 'BTC', 'ETH', 'TSLA', 'AAPL', 'MSFT', 'AMD', 'COIN', 'MSTR'];
  
  const now = new Date();

  for (let i = 0; i < count; i++) {
    const date = new Date(now.getTime() - Math.random() * 1000 * 60 * 60 * 24 * 30); // Last 30 days
    const agent = agents[Math.floor(Math.random() * agents.length)];
    const symbol = symbols[Math.floor(Math.random() * symbols.length)];
    const direction = Math.random() > 0.5 ? 'Long' : 'Short';
    
    // Outcome Logic (60% win rate)
    const isWin = Math.random() > 0.4;
    const entryPrice = 100 + Math.random() * 1000;
    const volatility = 0.05; // 5% move
    const move = entryPrice * volatility * (Math.random() * 1.5);
    
    let exitPrice = null;
    let pnl = 0;
    let pnlPercent = 0;
    let outcome: TradeOutcome = 'Open';
    const status = Math.random() > 0.85 ? 'Open' : 'Closed';

    if (status === 'Closed') {
        const change = isWin ? move : -move * 0.5; // Wins bigger than losses
        exitPrice = direction === 'Long' ? entryPrice + change : entryPrice - change;
        pnlPercent = (change / entryPrice) * 100;
        pnl = pnlPercent * 1000; // Mock position size multiplier
        outcome = pnl > 0 ? 'Profit' : pnl < 0 ? 'Loss' : 'Breakeven';
    } else {
        // Open trade PnL (Unrealized)
        const currentPrice = direction === 'Long' ? entryPrice + (move * (Math.random() - 0.5)) : entryPrice - (move * (Math.random() - 0.5));
        pnlPercent = ((currentPrice - entryPrice) / entryPrice) * 100 * (direction === 'Short' ? -1 : 1);
        pnl = pnlPercent * 1000;
    }

    // Reasoning Generation
    const reasonTemplates = [
        `RSI oversold at 28 with bullish divergence on the 4H chart.`,
        `Volume spike of 250% detected alongside breakout of key resistance level.`,
        `Macro sentiment shift following CPI data print. Sector rotation inflow detected.`,
        `Statistical mean reversion triggered after 3-standard deviation move.`,
        `Cross-exchange arbitrage opportunity detected with 0.8% spread.`,
        `MACD crossover confirmed momentum shift while holding above 50 SMA.`
    ];
    
    const signalsList = [
        ['RSI Oversold', 'Bullish Div', 'Volume Spike'],
        ['Breakout', 'High Volume', 'Trend Align'],
        ['Macro Catalyst', 'Sector Flow', 'Sentiment'],
        ['Mean Reversion', 'Bollinger Band', 'Extremes'],
        ['Arb Gap', 'Low Latency', 'Spread'],
    ];

    const exitReasons = [
        'Take Profit Hit', 'Stop Loss Triggered', 'Signal Reversal', 'Time Limit Reached', 'Risk Parameter Breach'
    ];

    trades.push({
        id: `TRD-${Math.random().toString(36).substr(2, 6).toUpperCase()}`,
        symbol,
        direction,
        entryPrice,
        exitPrice,
        quantity: Math.floor(Math.random() * 100) + 10,
        pnl,
        pnlPercent,
        duration: `${Math.floor(Math.random() * 8) + 1}h ${Math.floor(Math.random() * 59)}m`,
        timestamp: date,
        outcome: status === 'Open' ? 'Open' : outcome,
        status,
        agent,
        strategy: strategies[Math.floor(Math.random() * strategies.length)],
        reasoning: reasonTemplates[Math.floor(Math.random() * reasonTemplates.length)] + ` Confidence score derived from historical win rate in this volatility regime.`,
        confidence: Math.floor(Math.random() * 30) + 65, // 65-95%
        signals: signalsList[Math.floor(Math.random() * signalsList.length)],
        exitReason: status === 'Closed' ? exitReasons[Math.floor(Math.random() * exitReasons.length)] : undefined
    });
  }

  return trades.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
};

const mockTrades = generateTrades(40);

// --- Sub-Components ---

const TradeCard = ({ trade }: { trade: TradeRecord }) => {
  const [expanded, setExpanded] = useState(false);
  
  const isProfit = trade.pnl >= 0;
  const isClosed = trade.status === 'Closed';

  // Mock Mini Chart for Detail
  const chartData = useMemo(() => {
     return Array.from({ length: 20 }).map((_, i) => ({
         date: i.toString(),
         value: trade.entryPrice * (1 + (Math.random() - 0.5) * 0.05)
     }));
  }, [trade]);

  return (
    <motion.div layout className="relative">
      <GlassCard 
        variant="subtle" 
        padding="none" 
        className={cn(
            "overflow-hidden transition-all duration-300 border-l-4",
            isProfit ? "border-l-gain" : "border-l-loss"
        )}
      >
        <div 
            onClick={() => setExpanded(!expanded)}
            className="grid grid-cols-1 lg:grid-cols-12 gap-6 p-5 cursor-pointer hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors"
        >
            {/* LEFT: Trade Facts */}
            <div className="lg:col-span-3 flex flex-col justify-between gap-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="font-display font-bold text-lg text-obsidian-400 dark:text-paper-100">{trade.symbol}</span>
                        <Badge 
                            variant={trade.direction === 'Long' ? 'success' : 'danger'} 
                            size="sm"
                            className="h-5 px-1.5 text-[10px] uppercase"
                        >
                            {trade.direction}
                        </Badge>
                    </div>
                    <span className="text-xs font-mono text-obsidian-400/50 dark:text-paper-100/50">
                        {trade.timestamp.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </span>
                </div>

                <div className="space-y-1">
                    <div className="flex items-center gap-2 text-sm font-mono">
                        <span className="opacity-60">Entry:</span>
                        <span>{formatCurrency(trade.entryPrice)}</span>
                    </div>
                    {isClosed && trade.exitPrice && (
                        <div className="flex items-center gap-2 text-sm font-mono">
                            <span className="opacity-60">Exit:</span>
                            <div className="flex items-center gap-1">
                                <ArrowRight className="w-3 h-3 opacity-50" />
                                <span>{formatCurrency(trade.exitPrice)}</span>
                            </div>
                        </div>
                    )}
                </div>

                <div className="flex items-center gap-2 mt-1">
                    <span className={cn(
                        "text-lg font-mono font-bold",
                        isProfit ? "text-gain" : "text-loss"
                    )}>
                        {isProfit ? '+' : ''}{formatCurrency(trade.pnl)}
                    </span>
                    <Badge variant={isProfit ? 'success' : 'danger'} size="sm" className="h-5 px-1.5">
                        {isProfit ? '+' : ''}{trade.pnlPercent.toFixed(2)}%
                    </Badge>
                </div>
            </div>

            {/* CENTER: AI Reasoning */}
            <div className="lg:col-span-6 relative flex flex-col gap-3 pl-0 lg:pl-6 border-l-0 lg:border-l border-deep-teal-800/5 dark:border-white/5">
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 px-2 py-1 rounded-lg bg-deep-teal-800/5 dark:bg-white/5 border border-deep-teal-800/10 dark:border-white/10">
                        <Bot className="w-3.5 h-3.5 text-deep-teal-800 dark:text-turquoise-mist" />
                        <span className="text-xs font-medium text-deep-teal-800 dark:text-turquoise-mist">{trade.agent}</span>
                    </div>
                    <Badge variant="outline" size="sm" className="text-[10px] opacity-70">
                        {trade.strategy}
                    </Badge>
                    <div className="flex items-center gap-1 text-[10px] font-mono text-obsidian-400/50 dark:text-paper-100/50 ml-auto">
                        <Zap className="w-3 h-3 text-warning" fill="currentColor" />
                        Conf: {trade.confidence}%
                    </div>
                </div>

                <p className="text-sm text-obsidian-400/80 dark:text-paper-100/80 leading-relaxed font-sans">
                    {trade.reasoning}
                </p>

                <div className="flex flex-wrap gap-2 mt-auto">
                    {trade.signals.map(sig => (
                        <span key={sig} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-deep-teal-800/5 dark:bg-white/5 text-obsidian-400/60 dark:text-paper-100/60 border border-deep-teal-800/10 dark:border-white/10">
                            {sig}
                        </span>
                    ))}
                </div>
            </div>

            {/* RIGHT: Outcome */}
            <div className="lg:col-span-3 flex flex-col items-start lg:items-end justify-between pl-0 lg:pl-6 border-l-0 lg:border-l border-deep-teal-800/5 dark:border-white/5">
                <Badge variant={trade.status === 'Open' ? 'info' : 'neutral'} dot pulsing={trade.status === 'Open'}>
                    {trade.status}
                </Badge>

                {isClosed && (
                    <div className="flex flex-col items-start lg:items-end gap-1 mt-4 lg:mt-0">
                        <span className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
                            Exit Reason
                        </span>
                        <div className="flex items-center gap-1.5 text-sm font-medium text-obsidian-400 dark:text-paper-100">
                            {trade.exitReason?.includes('Profit') ? <CheckCircle2 className="w-4 h-4 text-gain" /> : 
                             trade.exitReason?.includes('Stop') ? <XCircle className="w-4 h-4 text-loss" /> :
                             <Clock className="w-4 h-4 text-warning" />}
                            {trade.exitReason}
                        </div>
                        <span className="text-[10px] text-obsidian-400/40 dark:text-paper-100/40 mt-1">
                            Held for {trade.duration}
                        </span>
                    </div>
                )}

                <div className="mt-auto pt-4 lg:pt-0 w-full flex justify-between lg:justify-end items-center">
                    <span className="text-xs text-turquoise-mist group-hover:underline lg:hidden">
                        {expanded ? "Hide Details" : "View Details"}
                    </span>
                    {expanded ? <ChevronUp className="w-4 h-4 opacity-50" /> : <ChevronDown className="w-4 h-4 opacity-50" />}
                </div>
            </div>
        </div>

        {/* EXPANDED DETAILS */}
        <AnimatePresence>
            {expanded && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={smoothSpring}
                    className="border-t border-deep-teal-800/5 dark:border-white/5 bg-deep-teal-800/[0.02] dark:bg-white/[0.02]"
                >
                    <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                        {/* Mini Chart Area */}
                        <div className="h-40 bg-white/50 dark:bg-black/20 rounded-xl border border-deep-teal-800/5 dark:border-white/5 p-2 relative">
                            <div className="absolute top-2 left-2 text-[10px] font-mono opacity-50">Price Action at Entry</div>
                            <AreaChart data={chartData} height={140} showGrid={false} />
                        </div>

                        {/* Text Details */}
                        <div className="space-y-4">
                            <div>
                                <h4 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/60 dark:text-paper-100/60 mb-2">Technical Context</h4>
                                <p className="text-sm text-obsidian-400/80 dark:text-paper-100/80">
                                    {trade.symbol} was trading 2.3 standard deviations below VWAP. Institutional order flow detected on bid side. {trade.agent} determined probability of mean reversion > 75%.
                                </p>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <h4 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/60 dark:text-paper-100/60 mb-1">Risk / Reward</h4>
                                    <span className="text-sm font-mono font-medium">1 : 3.2</span>
                                </div>
                                <div>
                                    <h4 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/60 dark:text-paper-100/60 mb-1">Volatility (ATR)</h4>
                                    <span className="text-sm font-mono font-medium">Low (1.2%)</span>
                                </div>
                            </div>
                            <div className="pt-2">
                                <Button size="sm" variant="secondary" className="h-8 text-xs">View Agent Log</Button>
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
      </GlassCard>
    </motion.div>
  );
};

// --- Main Page Component ---

export const TradeHistoryPage = () => {
  const { toast } = useToast();
  const [searchTerm, setSearchTerm] = useState('');
  const [filterAgent, setFilterAgent] = useState('All Agents');
  const [filterOutcome, setFilterOutcome] = useState('All Outcomes');
  const [isLoading, setIsLoading] = useState(true);
  const [isExportOpen, setIsExportOpen] = useState(false);

  // Simulate Fetch
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 800);
    return () => clearTimeout(timer);
  }, []);

  // Filtering
  const filteredTrades = useMemo(() => {
    return mockTrades.filter(trade => {
        const matchesSearch = trade.symbol.toLowerCase().includes(searchTerm.toLowerCase()) || 
                              trade.id.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesAgent = filterAgent === 'All Agents' || trade.agent === filterAgent;
        const matchesOutcome = filterOutcome === 'All Outcomes' || 
                               (filterOutcome === 'Profitable' && trade.pnl > 0) ||
                               (filterOutcome === 'Loss' && trade.pnl < 0);
        return matchesSearch && matchesAgent && matchesOutcome;
    });
  }, [searchTerm, filterAgent, filterOutcome]);

  // Statistics
  const stats = useMemo(() => {
    const closedTrades = filteredTrades.filter(t => t.status === 'Closed');
    const wins = closedTrades.filter(t => t.pnl > 0);
    const losses = closedTrades.filter(t => t.pnl < 0);
    
    const winRate = closedTrades.length > 0 ? (wins.length / closedTrades.length) * 100 : 0;
    const totalPnL = closedTrades.reduce((acc, t) => acc + t.pnl, 0);
    const avgPnL = closedTrades.length > 0 ? totalPnL / closedTrades.length : 0;
    
    // Find best trade
    const bestTrade = closedTrades.length > 0 
      ? closedTrades.reduce((prev, current) => (prev.pnl > current.pnl) ? prev : current)
      : null;

    return {
        total: filteredTrades.length,
        winRate,
        avgPnL,
        bestTradePnL: bestTrade?.pnl ?? 0,
        bestTradeSym: bestTrade?.symbol ?? '-'
    };
  }, [filteredTrades]);

  const handleExport = (config: ExportConfig) => {
    toast({
      title: 'Export Started',
      description: `Generating ${config.format.toUpperCase()} report from ${config.startDate} to ${config.endDate}...`,
      type: 'info'
    });
  };

  if (isLoading) {
    return <LoadingState variant="page" message="Loading Trade History..." />;
  }

  return (
    <ErrorBoundary>
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="space-y-8 pt-2 pb-10"
      >
        {/* 1. Header */}
        <PageHeader
          title="Trade History"
          description="Complete log of all automated trades with AI reasoning and execution context."
          actions={
            <div className="flex gap-3 w-full md:w-auto">
               <div className="w-full md:w-64">
                  <SearchInput 
                      placeholder="Search symbol..." 
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                  />
               </div>
               <Button variant="secondary" onClick={() => setIsExportOpen(true)} leftIcon={<Download className="w-4 h-4" />}>
                  Export
               </Button>
            </div>
          }
        />

        {/* 2. Filters Row */}
        <motion.div variants={fadeInUp} className="flex flex-wrap gap-3 pb-2">
           <Dropdown 
              trigger={<Button variant="ghost" size="sm" className="bg-paper-100 dark:bg-white/5 border border-deep-teal-800/10 dark:border-white/10" rightIcon={<ChevronDown className="w-3 h-3" />}>Date: This Month</Button>}
              items={[{ label: 'Today' }, { label: 'This Week' }, { label: 'This Month' }, { label: 'Last 3 Months' }]}
           />
           <Dropdown 
              trigger={<Button variant="ghost" size="sm" className="bg-paper-100 dark:bg-white/5 border border-deep-teal-800/10 dark:border-white/10" rightIcon={<ChevronDown className="w-3 h-3" />}>Agent: {filterAgent}</Button>}
              items={[
                  { label: 'All Agents', onClick: () => setFilterAgent('All Agents') },
                  { type: 'divider' },
                  { label: 'Alpha Seeker', onClick: () => setFilterAgent('Alpha Seeker') },
                  { label: 'Momentum Prime', onClick: () => setFilterAgent('Momentum Prime') },
                  { label: 'Macro Sentinel', onClick: () => setFilterAgent('Macro Sentinel') }
              ]}
           />
           <Dropdown 
              trigger={<Button variant="ghost" size="sm" className="bg-paper-100 dark:bg-white/5 border border-deep-teal-800/10 dark:border-white/10" rightIcon={<ChevronDown className="w-3 h-3" />}>Outcome: {filterOutcome}</Button>}
              items={[
                  { label: 'All Outcomes', onClick: () => setFilterOutcome('All Outcomes') },
                  { type: 'divider' },
                  { label: 'Profitable', onClick: () => setFilterOutcome('Profitable') },
                  { label: 'Loss', onClick: () => setFilterOutcome('Loss') }
              ]}
           />
        </motion.div>

        {/* 3. Summary Stats */}
        <motion.div variants={fadeInUp} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
           <MetricCard 
              title="Total Trades" 
              value={stats.total} 
              format="raw" 
              icon={History}
              variant="subtle"
              className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent"
           />
           <MetricCard 
              title="Win Rate" 
              value={stats.winRate} 
              suffix="%" 
              change={2.5}
              changeLabel="vs last month"
              icon={Activity}
              variant="subtle"
              className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent"
           />
           <MetricCard 
              title="Avg P&L" 
              value={stats.avgPnL} 
              prefix={stats.avgPnL >= 0 ? "+$" : "-$"} 
              icon={TrendingUp}
              variant="subtle"
              className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent"
           />
           <MetricCard 
              title="Best Trade" 
              value={stats.bestTradePnL} 
              prefix="+$"
              changeLabel={stats.bestTradeSym} 
              icon={AlertTriangle} // Using alert icon for standout event
              variant="subtle"
              className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent"
           />
        </motion.div>

        {/* 4. Trade List */}
        <div className="space-y-4">
           {filteredTrades.map((trade, i) => (
              <motion.div key={trade.id} variants={fadeInUp}>
                 <TradeCard trade={trade} />
              </motion.div>
           ))}
           {filteredTrades.length === 0 && (
              <EmptyState 
                title="No trades found"
                description="Try adjusting your filters or search terms."
                variant="search"
                action={
                  <Button variant="secondary" onClick={() => { setSearchTerm(''); setFilterAgent('All Agents'); setFilterOutcome('All Outcomes'); }}>
                    Reset Filters
                  </Button>
                }
              />
           )}
        </div>

        <ExportModal 
          isOpen={isExportOpen} 
          onClose={() => setIsExportOpen(false)} 
          onExport={handleExport}
          title="Export Trade History"
        />

      </motion.div>
    </ErrorBoundary>
  );
};
