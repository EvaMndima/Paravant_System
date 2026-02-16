import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { 
  ArrowLeft, Play, Pause, Settings, Activity, AlertTriangle, 
  Cpu, TrendingUp, TrendingDown, Clock, Database, Terminal,
  RefreshCw, CheckCircle2, XCircle, Search, Power, ChevronRight
} from 'lucide-react';

import { PageHeader } from '../layout/PageHeader';
import { GlassCard } from '../ui/GlassCard';
import { MetricCard } from '../ui/MetricCard';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Section } from '../layout/Section';
import { DataTable, Column } from '../dashboard/DataTable';
import { AreaChart } from '../dashboard/charts/AreaChart';
import { PositionsTable, Position } from '../dashboard/PositionsTable';
import { cn, formatCurrency, formatNumber } from '../../lib/utils';
import { staggerContainer, fadeInUp } from '../../lib/animations';
import { useDashboard } from '../../contexts/DashboardContext';
import { StrategyType, StrategyStatus } from '../dashboard/StrategyCard';

// --- Mock Data ---

interface StrategyDetail {
  id: string;
  name: string;
  type: StrategyType;
  status: StrategyStatus;
  description: string;
  equity: number;
  config: {
    riskPerTrade: number;
    maxPositions: number;
    stopLoss: number;
    takeProfit: number;
    tradingHours: string;
    universe: string[];
  };
  metrics: {
    totalPnL: number;
    winRate: number;
    sharpe: number;
    maxDrawdown: number;
    totalTrades: number;
    avgHoldTime: string;
  };
}

const mockStrategies: Record<string, StrategyDetail> = {
  '1': {
    id: '1',
    name: 'Alpha Seeker V4',
    type: 'arbitrage',
    status: 'active',
    description: 'High-frequency statistical arbitrage strategy targeting inefficiencies across major crypto-equity pairs.',
    equity: 145230,
    config: {
      riskPerTrade: 1.5,
      maxPositions: 8,
      stopLoss: -2.5,
      takeProfit: 4.0,
      tradingHours: '24/7',
      universe: ['BTC', 'ETH', 'COIN', 'MSTR', 'NVDA']
    },
    metrics: {
      totalPnL: 45230,
      winRate: 78.5,
      sharpe: 2.4,
      maxDrawdown: -4.2,
      totalTrades: 1240,
      avgHoldTime: '45m'
    }
  },
  '2': {
    id: '2',
    name: 'Momentum Prime',
    type: 'momentum',
    status: 'training',
    description: 'Trend following system utilizing multi-timeframe breakout logic on high relative volume tech stocks.',
    equity: 62400,
    config: {
      riskPerTrade: 2.0,
      maxPositions: 5,
      stopLoss: -5.0,
      takeProfit: 15.0,
      tradingHours: '9:30 AM - 4:00 PM EST',
      universe: ['QQQ', 'NVDA', 'AMD', 'TSLA', 'META', 'AMZN']
    },
    metrics: {
      totalPnL: 12400,
      winRate: 42.0,
      sharpe: 1.8,
      maxDrawdown: -12.5,
      totalTrades: 315,
      avgHoldTime: '3d 4h'
    }
  },
  '3': {
    id: '3',
    name: 'Macro Sentinel',
    type: 'macro',
    status: 'paused',
    description: 'Global macro strategy adjusting exposure based on yield curve inversions and economic calendar events.',
    equity: 48800,
    config: {
      riskPerTrade: 1.0,
      maxPositions: 3,
      stopLoss: -3.0,
      takeProfit: 8.0,
      tradingHours: 'Global Sessions',
      universe: ['SPY', 'TLT', 'GLD', 'UUP', 'VIX']
    },
    metrics: {
      totalPnL: -1200,
      winRate: 45.0,
      sharpe: 0.9,
      maxDrawdown: -8.0,
      totalTrades: 42,
      avgHoldTime: '14d'
    }
  }
};

// Generate Agent Specific Positions
const generateStrategyPositions = (agentId: string): Position[] => {
  return [
    { id: '1', symbol: 'NVDA', name: 'NVIDIA Corp.', quantity: 120, avgPrice: 840.50, currentPrice: 890.25, pl: 5970.00, plPercent: 5.92, weight: 12.5, assetType: 'Stock' },
    { id: '2', symbol: 'BTC', name: 'Bitcoin', quantity: 1.5, avgPrice: 62000.00, currentPrice: 67500.00, pl: 8250.00, plPercent: 8.87, weight: 8.2, assetType: 'Crypto' },
    { id: '3', symbol: 'ETH', name: 'Ethereum', quantity: 20, avgPrice: 3500.00, currentPrice: 3850.50, pl: 7010.00, plPercent: 10.01, weight: 5.4, assetType: 'Crypto' },
  ];
};

// Generate Trade History
const generateTradeHistory = () => {
  return Array.from({ length: 10 }).map((_, i) => ({
    id: `TRD-${i}`,
    timestamp: new Date(Date.now() - i * 1000 * 60 * 60 * 4),
    symbol: ['NVDA', 'BTC', 'COIN', 'MSTR'][i % 4],
    direction: i % 2 === 0 ? 'Long' : 'Short',
    pnl: (Math.random() - 0.4) * 1000,
    outcome: Math.random() > 0.4 ? 'Profit' : 'Loss'
  }));
};

const generateSignals = (count: number) => {
  return Array.from({ length: count }).map((_, i) => ({
    id: i.toString(),
    timestamp: new Date(Date.now() - i * 1000 * 60 * 30),
    symbol: ['BTC', 'ETH', 'NVDA', 'TSLA'][i % 4],
    direction: i % 2 === 0 ? 'Long' : 'Short',
    confidence: 60 + Math.random() * 35,
    action: Math.random() > 0.3 ? 'Executed' : (Math.random() > 0.5 ? 'Rejected' : 'Pending'),
    reason: Math.random() > 0.5 ? 'Position limit reached' : 'Confidence below threshold'
  }));
};

const generateLogs = (count: number) => {
  return Array.from({ length: count }).map((_, i) => ({
    id: i.toString(),
    timestamp: new Date(Date.now() - i * 1000 * 60 * 5).toISOString(),
    level: i === 4 ? 'WARN' : i === 12 ? 'ERROR' : 'INFO',
    message: i === 4 ? 'Latency spike detected > 200ms' : i === 12 ? 'API Rate limit exceeded on data provider' : `Processed tick data batch #${2340 + i}. No signal generated.`
  }));
};

const generateEquityData = (startEquity: number) => {
  let equity = startEquity;
  return Array.from({ length: 30 }).map((_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (29 - i));
    equity = equity * (1 + (Math.random() - 0.45) * 0.02);
    return {
      date: date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      value: equity
    };
  });
};

// --- Component ---

export const StrategyDetailPage = () => {
  const { selectedStrategyId, clearSelectedStrategy, openPositionDrawer } = useDashboard();
  const [logFilter, setLogFilter] = useState('');

  // Guard clause if no strategy selected
  if (!selectedStrategyId || !mockStrategies[selectedStrategyId]) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <div className="p-4 rounded-full bg-deep-teal-800/5 dark:bg-white/5">
           <Cpu className="w-8 h-8 text-obsidian-400/40 dark:text-paper-100/40" />
        </div>
        <p className="text-obsidian-400/60 dark:text-paper-100/60 font-sans">Strategy not found or removed.</p>
        <Button onClick={clearSelectedStrategy} variant="secondary">Return to Dashboard</Button>
      </div>
    );
  }

  const strategy = mockStrategies[selectedStrategyId];
  const positions = useMemo(() => generateStrategyPositions(strategy.id), [strategy.id]);
  const trades = useMemo(() => generateTradeHistory(), [strategy.id]);
  const signals = useMemo(() => generateSignals(15), []);
  const logs = useMemo(() => generateLogs(25), []);
  const equityData = useMemo(() => generateEquityData(strategy.equity * 0.8), [strategy]);

  const filteredLogs = logs.filter(l => 
    l.message.toLowerCase().includes(logFilter.toLowerCase()) || 
    l.level.toLowerCase().includes(logFilter.toLowerCase())
  );

  // --- Table Configurations ---

  const signalColumns: Column<any>[] = [
    { 
      key: 'timestamp', 
      header: 'Time', 
      render: (val: Date) => <span className="text-xs font-mono opacity-70">{val.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span> 
    },
    { 
      key: 'symbol', 
      header: 'Signal', 
      render: (val, row) => (
        <div className="flex items-center gap-1.5 font-bold text-sm">
          <span className={row.direction === 'Long' ? 'text-gain' : 'text-loss'}>{row.direction}</span>
          <span>{val}</span>
        </div>
      ) 
    },
    { 
      key: 'confidence', 
      header: 'Conf.', 
      render: (val) => <span className="font-mono text-xs">{val.toFixed(1)}%</span> 
    },
    { 
      key: 'action', 
      header: 'Status', 
      align: 'right',
      render: (val, row) => (
        <Badge 
          variant={val === 'Executed' ? 'success' : val === 'Rejected' ? 'danger' : 'neutral'} 
          size="sm"
          className="text-[10px]"
        >
          {val}
        </Badge>
      ) 
    }
  ];

  const tradeColumns: Column<any>[] = [
    { 
      key: 'timestamp', 
      header: 'Time', 
      render: (val: Date) => <span className="text-xs font-mono opacity-70">{val.toLocaleDateString([], { month: 'short', day: 'numeric' })}</span> 
    },
    {
      key: 'symbol',
      header: 'Trade',
      render: (val, row) => (
        <span className={cn("font-bold text-sm", row.direction === 'Long' ? 'text-gain' : 'text-loss')}>
          {row.direction} {val}
        </span>
      )
    },
    {
      key: 'pnl',
      header: 'P&L',
      align: 'right',
      render: (val) => (
        <span className={cn("font-mono text-sm font-medium", val >= 0 ? "text-gain" : "text-loss")}>
          {val >= 0 ? '+' : ''}{formatCurrency(val)}
        </span>
      )
    }
  ];

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="space-y-6 pt-2 pb-10"
    >
      {/* 1. Header */}
      <PageHeader
        title={strategy.name}
        description={strategy.description}
        breadcrumbs={[
          { label: 'Agents', href: '#' },
          { label: strategy.name }
        ]}
        actions={
          <div className="flex items-center gap-3">
            <Button variant="ghost" leftIcon={<ArrowLeft className="w-4 h-4" />} onClick={clearSelectedStrategy}>
              Back
            </Button>
            {strategy.status === 'active' || strategy.status === 'training' ? (
               <Button variant="secondary" leftIcon={<Pause className="w-4 h-4" />} className="text-warning border-warning/30 hover:bg-warning/10">
                 Pause Agent
               </Button>
            ) : (
               <Button variant="secondary" leftIcon={<Play className="w-4 h-4" />} className="text-gain border-gain/30 hover:bg-gain/10">
                 Resume Agent
               </Button>
            )}
            <Button variant="primary" leftIcon={<Settings className="w-4 h-4" />}>
              Configure
            </Button>
          </div>
        }
      />

      {/* 2. Status Banner (Conditional) */}
      {strategy.status !== 'active' && (
        <motion.div variants={fadeInUp}>
           <div className={cn(
             "w-full p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4",
             strategy.status === 'paused' ? "bg-warning/5 border-warning/20 text-warning" :
             strategy.status === 'error' ? "bg-loss/5 border-loss/20 text-loss" :
             "bg-info/5 border-info/20 text-info"
           )}>
              <div className="flex items-center gap-3">
                 {strategy.status === 'paused' ? <AlertTriangle className="w-5 h-5" /> : 
                  strategy.status === 'error' ? <XCircle className="w-5 h-5" /> : 
                  <RefreshCw className="w-5 h-5 animate-spin" />}
                 <div>
                    <h4 className="font-bold text-sm uppercase tracking-wide">{strategy.status}</h4>
                    <p className="text-xs opacity-80">
                       {strategy.status === 'paused' ? "Execution halted by user. Monitoring mode only." : 
                        strategy.status === 'error' ? "Critical error in data feed connection." : 
                        "Retraining model on latest market regime."}
                    </p>
                 </div>
              </div>
              {strategy.status === 'error' && (
                 <div className="flex gap-2">
                    <Button variant="secondary" size="sm" className="bg-loss/10 border-loss/20 text-loss hover:bg-loss/20 h-8 text-xs">View Logs</Button>
                    <Button variant="secondary" size="sm" className="bg-loss/10 border-loss/20 text-loss hover:bg-loss/20 h-8 text-xs" leftIcon={<Power className='w-3 h-3'/>} >Restart</Button>
                 </div>
              )}
              {strategy.status === 'training' && <div className="text-xs font-mono font-bold bg-info/10 px-2 py-1 rounded">ETA: 45m</div>}
           </div>
        </motion.div>
      )}

      {/* 3. Performance Metrics */}
      <motion.div variants={fadeInUp} className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
         <MetricCard title="Total Equity" value={strategy.equity} prefix="$" variant="subtle" className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent" />
         <MetricCard title="Total P&L" value={strategy.metrics.totalPnL} prefix="$" change={12.5} changeLabel="All time" variant="subtle" className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent" />
         <MetricCard title="Win Rate" value={strategy.metrics.winRate} suffix="%" format="raw" icon={CheckCircle2} variant="subtle" className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent" />
         <MetricCard title="Sharpe Ratio" value={strategy.metrics.sharpe} format="raw" icon={Activity} variant="subtle" className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent" />
         <MetricCard title="Max Drawdown" value={strategy.metrics.maxDrawdown} suffix="%" format="raw" icon={TrendingDown} variant="subtle" className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent" />
         <MetricCard title="Total Trades" value={strategy.metrics.totalTrades} format="raw" icon={Terminal} variant="subtle" className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent" />
      </motion.div>

      {/* 4. Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
         
         {/* Left Column (2/3): Equity, Positions, Trades */}
         <div className="xl:col-span-2 space-y-6">
            
            {/* Equity Curve */}
            <motion.div variants={fadeInUp}>
               <GlassCard className="flex flex-col h-[350px] p-0 overflow-hidden" padding="none">
                  <div className="px-6 py-5 border-b border-deep-teal-800/5 dark:border-white/5 flex items-center justify-between">
                     <div className="flex items-center gap-2">
                        <Activity className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
                        <h3 className="font-display text-lg">Equity Curve</h3>
                     </div>
                     <div className="flex bg-deep-teal-800/5 dark:bg-white/5 p-1 rounded-lg">
                        {['1W', '1M', '3M', 'ALL'].map(t => (
                           <button key={t} className={cn("px-3 py-1 text-xs rounded-md transition-colors", t === '1M' ? "bg-white dark:bg-obsidian-300 shadow-sm font-medium" : "opacity-60 hover:opacity-100")}>{t}</button>
                        ))}
                     </div>
                  </div>
                  <div className="flex-1 w-full px-4 pt-4">
                     <AreaChart data={equityData} height={250} showGrid={true} />
                  </div>
               </GlassCard>
            </motion.div>

            {/* Current Positions */}
            <motion.div variants={fadeInUp}>
               <PositionsTable 
                 data={positions} 
                 title="Current Positions" 
                 compact={true}
                 onPositionClick={(p) => openPositionDrawer(p as any)}
               />
            </motion.div>

            {/* Trade History (Recent) */}
            <motion.div variants={fadeInUp}>
               <GlassCard className="flex flex-col" padding="none">
                  <div className="px-6 py-4 border-b border-deep-teal-800/5 dark:border-white/5 flex items-center justify-between">
                     <h3 className="font-display text-lg">Recent Trades</h3>
                     <Button variant="ghost" size="sm" className="text-xs">View All</Button>
                  </div>
                  <DataTable columns={tradeColumns} data={trades} />
               </GlassCard>
            </motion.div>

         </div>

         {/* Right Column (1/3): Config & Signals */}
         <div className="space-y-6">
            
            {/* Config Panel */}
            <motion.div variants={fadeInUp}>
               <GlassCard variant="subtle" className="flex flex-col gap-4">
                  <div className="flex items-center justify-between border-b border-deep-teal-800/5 dark:border-white/5 pb-3">
                     <div className="flex items-center gap-2">
                        <Settings className="w-4 h-4 text-obsidian-400 dark:text-paper-100" />
                        <h3 className="font-display text-base font-medium">Configuration</h3>
                     </div>
                     <Button variant="ghost" size="sm" className="h-6 px-2 text-xs text-turquoise-mist hover:text-turquoise-bright">Edit</Button>
                  </div>
                  <div className="space-y-3 font-sans">
                     <div className="flex justify-between items-center py-1 border-b border-dashed border-deep-teal-800/5 dark:border-white/5 last:border-0">
                        <span className="text-xs opacity-60">Risk Per Trade</span>
                        <span className="font-mono text-sm font-bold">{strategy.config.riskPerTrade}%</span>
                     </div>
                     <div className="flex justify-between items-center py-1 border-b border-dashed border-deep-teal-800/5 dark:border-white/5 last:border-0">
                        <span className="text-xs opacity-60">Max Positions</span>
                        <span className="font-mono text-sm font-bold">{strategy.config.maxPositions}</span>
                     </div>
                     <div className="flex justify-between items-center py-1 border-b border-dashed border-deep-teal-800/5 dark:border-white/5 last:border-0">
                        <span className="text-xs opacity-60">Stop Loss</span>
                        <span className="font-mono text-sm font-bold text-loss">{strategy.config.stopLoss}%</span>
                     </div>
                     <div className="flex justify-between items-center py-1 border-b border-dashed border-deep-teal-800/5 dark:border-white/5 last:border-0">
                        <span className="text-xs opacity-60">Take Profit</span>
                        <span className="font-mono text-sm font-bold text-gain">+{strategy.config.takeProfit}%</span>
                     </div>
                     <div className="flex flex-col gap-2 pt-2">
                        <span className="text-xs opacity-60">Trading Universe</span>
                        <div className="flex flex-wrap gap-1.5">
                           {strategy.config.universe.slice(0,5).map(s => <Badge key={s} size="sm" variant="neutral" className="h-5 px-1.5 bg-paper-200 dark:bg-white/10">{s}</Badge>)}
                           {strategy.config.universe.length > 5 && <Badge size="sm" variant="neutral" className="h-5 px-1.5">+{strategy.config.universe.length - 5}</Badge>}
                        </div>
                     </div>
                  </div>
               </GlassCard>
            </motion.div>

            {/* Signals Feed */}
            <motion.div variants={fadeInUp}>
               <GlassCard className="flex flex-col h-[500px]" padding="none">
                  <div className="p-4 border-b border-deep-teal-800/5 dark:border-white/5 flex justify-between items-center bg-deep-teal-800/5 dark:bg-white/5">
                     <div className="flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-deep-teal-800 dark:text-turquoise-mist" />
                        <h3 className="font-display text-base font-medium">Live Signals</h3>
                     </div>
                     <Badge variant="success" dot pulsing size="sm">Online</Badge>
                  </div>
                  <div className="flex-1 overflow-auto custom-scrollbar">
                     <DataTable columns={signalColumns} data={signals} />
                  </div>
               </GlassCard>
            </motion.div>

         </div>
      </div>

      {/* 5. Logs - Collapsible Full Width */}
      <motion.div variants={fadeInUp} className="pt-6">
         <Section collapsible title="System Logs" defaultCollapsed={false} className="border-t border-deep-teal-800/10 dark:border-white/10">
            <GlassCard className="flex flex-col gap-0 overflow-hidden bg-[#0F1115] border-deep-teal-800/20" padding="none" variant="dark">
               <div className="px-4 py-3 flex items-center justify-between border-b border-white/5 bg-white/5">
                  <div className="flex items-center gap-2 text-paper-100">
                     <Database className="w-4 h-4 text-turquoise-mist" />
                     <h3 className="font-mono text-sm tracking-wide">CONSOLE OUTPUT</h3>
                  </div>
                  <div className="flex gap-2">
                     <div className="relative">
                        <Search className="absolute left-2 top-1.5 w-3 h-3 text-white/40" />
                        <input 
                           placeholder="Filter..." 
                           value={logFilter} 
                           onChange={e => setLogFilter(e.target.value)} 
                           className="h-6 w-32 bg-black/40 border border-white/10 rounded pl-6 text-[10px] text-white focus:outline-none focus:border-turquoise-mist/50 font-mono"
                        />
                     </div>
                     <button className="text-[10px] px-2 py-1 bg-white/10 rounded hover:bg-white/20 transition-colors text-white font-mono">EXPORT</button>
                  </div>
               </div>
               <div className="h-48 overflow-y-auto custom-scrollbar p-4 font-mono text-[11px] space-y-1 bg-[#090A0C]">
                  {filteredLogs.map(log => (
                     <div key={log.id} className="flex gap-3 hover:bg-white/5 p-0.5 rounded transition-colors">
                        <span className="text-white/30 shrink-0 select-none">{log.timestamp.split('T')[1].replace('Z','')}</span>
                        <span className={cn(
                           "font-bold w-10 shrink-0 text-center rounded-[2px]",
                           log.level === 'INFO' ? "text-blue-400 bg-blue-400/10" : log.level === 'WARN' ? "text-yellow-400 bg-yellow-400/10" : "text-red-400 bg-red-400/10"
                        )}>{log.level}</span>
                        <span className="text-white/80 break-all">{log.message}</span>
                     </div>
                  ))}
                  {filteredLogs.length === 0 && <div className="text-white/30 italic">No logs match your filter.</div>}
               </div>
            </GlassCard>
         </Section>
      </motion.div>

    </motion.div>
  );
};