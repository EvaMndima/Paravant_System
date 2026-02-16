
import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, Server, Wifi, ShieldCheck, Cpu, 
  TrendingUp, AlertTriangle, Clock, Zap, CheckCircle2,
  PieChart, Layers, Network, Pause, Play,
  Settings, Database, Download
} from 'lucide-react';

import { PageHeader } from '../layout/PageHeader';
import { GlassCard } from '../ui/GlassCard';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Progress } from '../ui/Progress';
import { DonutChart } from '../dashboard/charts/DonutChart';
import { Tabs, TabsList, TabsTrigger } from '../ui/Tabs';
import { MarketRegimePanel, MarketRegimeData } from '../dashboard/MarketRegimePanel';
import { ExportModal, ExportConfig } from '../dashboard/ExportModal';
import { useToast } from '../../contexts/ToastContext';
import { cn, formatCurrency } from '../../lib/utils';
import { staggerContainer, fadeInUp } from '../../lib/animations';

// --- Types & Mock Data ---

interface Decision {
  id: string;
  timestamp: string; // Relative time e.g., "2 hours ago"
  type: 'Allocation' | 'Agent' | 'Risk' | 'Regime';
  title: string;
  details: string;
  impact: string;
}

const systemMetrics = {
  signalsPerHour: 23,
  tradesPerDay: 47,
  avgLatency: '12ms',
  queueDepth: 0
};

const marketRegime: MarketRegimeData = {
  type: 'TRENDING BULLISH',
  confidence: 78,
  duration: 'Active for 12 days',
  indicators: {
    vix: { value: 13.5, label: 'Low Volatility', status: 'good' },
    breadth: { value: '+0.65', label: 'Positive', status: 'good' },
    trend: { value: '72/100', label: 'Strong', status: 'good' },
    correlation: { value: 0.45, label: 'Moderate', status: 'neutral' },
    putCall: { value: 0.85, label: 'Bullish', status: 'good' }
  },
  commentary: "Current regime favors momentum and trend-following strategies. Reduced allocation to mean reversion due to low volatility environment. Maintaining 15% cash reserve for potential volatility spike opportunities."
};

const allocationStrategy = [
  { name: 'Arbitrage', value: 1200000, color: '#2A9D8F' },
  { name: 'Momentum', value: 1440000, color: '#0F3D3E' },
  { name: 'Mean Rev', value: 720000, color: '#E9C46A' },
  { name: 'Macro', value: 480000, color: '#F4A261' },
  { name: 'Experimental', value: 240000, color: '#E76F51' },
  { name: 'Cash', value: 720000, color: '#9CA3AF' },
];

const allocationRisk = [
  { name: 'Conservative', value: 40, color: '#2A9D8F' },
  { name: 'Moderate', value: 35, color: '#E9C46A' },
  { name: 'Aggressive', value: 15, color: '#F4A261' },
  { name: 'Experimental', value: 10, color: '#E76F51' },
];

const decisions: Decision[] = [
  { id: '1', timestamp: '2 hours ago', type: 'Allocation', title: 'Increased Momentum allocation', details: 'Momentum strategies allocation increased from 25% to 30% based on continued trend strength.', impact: 'Affected: Momentum Prime, Trend Follower Pro' },
  { id: '2', timestamp: '5 hours ago', type: 'Agent', title: 'Paused Volatility Surfer', details: 'Agent performance degraded below Sharpe threshold (0.8) for 48h.', impact: 'Capital recycled to Cash Reserve' },
  { id: '3', timestamp: '1 day ago', type: 'Regime', title: 'Regime Shift: Neutral → Trending', details: 'Breakout detected in S&P 500 above 30-day moving average with volume confirmation.', impact: 'Activated Trend Following suite' },
  { id: '4', timestamp: '1 day ago', type: 'Risk', title: 'Tightened Stop Losses', details: 'Global volatility index (VIX) spike momentarily triggered defensive posture.', impact: 'All active positions stop-loss raised by 1.5%' },
  { id: '5', timestamp: '2 days ago', type: 'Allocation', title: 'Rebalanced Arbitrage Pools', details: 'Shifted capital from CEX-DEX arb to Cross-Exchange arb due to yield compression.', impact: 'Optimized yield +0.4% daily' },
  { id: '6', timestamp: '2 days ago', type: 'Agent', title: 'Activated Alpha Seeker V4', details: 'New model version passed sandbox validation with 82% win rate.', impact: 'Allocated $250k initial capital' },
  { id: '7', timestamp: '3 days ago', type: 'Risk', title: 'Sector Limit Reached', details: 'Technology sector exposure hit 35% soft limit.', impact: 'Halted new Tech entries' },
];

const strategyPerformance = [
  { name: 'Momentum', ytd: 32.4, sharpe: 2.1, count: 12 },
  { name: 'Arbitrage', ytd: 18.3, sharpe: 3.4, count: 8 },
  { name: 'Mean Rev', ytd: 8.7, sharpe: 1.5, count: 10 },
  { name: 'Macro', ytd: 2.1, sharpe: 0.8, count: 6 },
  { name: 'Experimental', ytd: -4.5, sharpe: 0.6, count: 4 },
];

const riskLimits = [
  { label: 'Portfolio Beta', current: 1.15, max: 1.5, unit: '' },
  { label: 'Gross Exposure', current: 85, max: 100, unit: '%' },
  { label: 'Single Pos Max', current: 4.2, max: 5, unit: '%' },
  { label: 'Sector Concentration', current: 32, max: 40, unit: '%' },
  { label: 'Daily Loss Limit', current: 12000, max: 50000, unit: '$' },
];

const scheduledEvents = [
  { time: '4:00 PM EST', event: 'Portfolio rebalance check', type: 'daily' },
  { time: 'Sun 6:00 PM', event: 'Risk parameter review', type: 'weekly' },
  { time: 'Monthly 1st', event: 'Strategy rotation analysis', type: 'monthly' },
  { time: 'Quarterly', event: 'Model retraining cycle', type: 'quarterly' },
];

// --- Sub-Components ---

const DecisionCard: React.FC<{ decision: Decision }> = ({ decision }) => {
  const typeStyles = {
    Allocation: 'bg-info/10 text-info border-info/20',
    Agent: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
    Risk: 'bg-loss/10 text-loss border-loss/20',
    Regime: 'bg-gain/10 text-gain border-gain/20',
  };

  return (
    <div className="group relative pl-6 pb-6 border-l border-deep-teal-800/10 dark:border-white/10 last:pb-0 last:border-0">
      <div className={cn(
        "absolute -left-[5px] top-0 w-2.5 h-2.5 rounded-full border-2 border-white dark:border-obsidian-300 ring-1 ring-deep-teal-800/10 dark:ring-white/10",
        decision.type === 'Risk' ? 'bg-loss' : decision.type === 'Regime' ? 'bg-gain' : 'bg-deep-teal-800 dark:bg-turquoise-mist'
      )} />
      
      <div className="flex flex-col gap-2 p-4 rounded-xl bg-deep-teal-800/5 dark:bg-white/5 border border-deep-teal-800/5 dark:border-white/5 hover:bg-deep-teal-800/10 dark:hover:bg-white/10 transition-colors">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-2">
            <Badge className={cn("text-[10px] h-5 px-1.5 border", typeStyles[decision.type])}>{decision.type}</Badge>
            <span className="text-sm font-medium text-obsidian-400 dark:text-paper-100">{decision.title}</span>
          </div>
          <span className="text-[10px] font-mono opacity-50">{decision.timestamp}</span>
        </div>
        <p className="text-xs text-obsidian-400/70 dark:text-paper-100/70 leading-relaxed">
          {decision.details}
        </p>
        <div className="flex items-center gap-1.5 text-[10px] font-mono text-obsidian-400/50 dark:text-paper-100/50 pt-1">
          <Zap className="w-3 h-3" />
          {decision.impact}
        </div>
      </div>
    </div>
  );
};

export const SystemPage = () => {
  const [activeTab, setActiveTab] = useState('All');
  const [isExportOpen, setIsExportOpen] = useState(false);
  const { toast } = useToast();

  const filteredDecisions = useMemo(() => {
    return activeTab === 'All' ? decisions : decisions.filter(d => d.type === activeTab);
  }, [activeTab]);

  const handleExport = (config: ExportConfig) => {
    toast({
      title: 'Export Started',
      description: `Generating ${config.format.toUpperCase()} report from ${config.startDate} to ${config.endDate}...`,
      type: 'info'
    });
  };

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="space-y-6 pt-2 pb-10"
    >
      {/* 1. Header */}
      <PageHeader
        title="System Overview"
        description="AI Curator decisions, capital allocation, and market regime analysis."
        actions={
          <div className="flex gap-3 items-center">
            <Button variant="secondary" size="sm" leftIcon={<Download className="w-4 h-4" />} onClick={() => setIsExportOpen(true)}>
               Export
            </Button>
            <Badge variant="success" dot pulsing className="px-4 py-1.5 h-auto text-sm bg-gain/10 text-gain border-gain/20">
              All Systems Operational
            </Badge>
          </div>
        }
      />

      {/* 2. System Health Panel (4 Cards) */}
      <motion.div variants={fadeInUp} className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        
        {/* Card 1: Uptime */}
        <GlassCard className="flex flex-col justify-between" padding="md">
           <div className="flex justify-between items-start">
              <span className="text-xs font-mono uppercase tracking-widest opacity-60">System Uptime</span>
              <div className="w-2 h-2 rounded-full bg-gain shadow-[0_0_8px_rgba(46,204,113,0.6)]" />
           </div>
           <div className="mt-2">
              <div className="text-3xl font-mono font-medium text-deep-teal-800 dark:text-paper-100">99.97%</div>
              <div className="text-xs opacity-60 mt-1">30 day rolling average</div>
           </div>
        </GlassCard>

        {/* Card 2: Connections */}
        <GlassCard className="flex flex-col justify-between" padding="md">
           <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-mono uppercase tracking-widest opacity-60">Connections</span>
              <Network className="w-4 h-4 opacity-40" />
           </div>
           <div className="space-y-2">
              {[
                { label: 'Brokerage', status: 'connected' },
                { label: 'Market Data', status: 'connected' },
                { label: 'Risk Engine', status: 'connected' }
              ].map(c => (
                <div key={c.label} className="flex items-center justify-between text-xs">
                   <span className="font-medium text-obsidian-400 dark:text-paper-100">{c.label}</span>
                   <span className="flex items-center gap-1 text-gain">
                      <CheckCircle2 className="w-3 h-3" /> Connected
                   </span>
                </div>
              ))}
           </div>
        </GlassCard>

        {/* Card 3: Trading Mode */}
        <GlassCard className="flex flex-col justify-between" padding="md">
           <div className="flex justify-between items-start">
              <span className="text-xs font-mono uppercase tracking-widest opacity-60">Trading Mode</span>
              <Settings className="w-4 h-4 opacity-40 hover:text-turquoise-mist cursor-pointer" />
           </div>
           <div className="mt-2">
              <Badge variant="success" className="mb-2 bg-gain/10 text-gain border-gain/20 justify-center w-full py-1">FULL AUTO</Badge>
              <div className="text-[10px] text-center opacity-60">Last change: 5 days ago</div>
           </div>
        </GlassCard>

        {/* Card 4: Metrics */}
        <GlassCard className="flex flex-col justify-between" padding="md">
           <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-mono uppercase tracking-widest opacity-60">Live Metrics</span>
              <Activity className="w-4 h-4 opacity-40" />
           </div>
           <div className="grid grid-cols-2 gap-2">
              <div className="p-2 rounded-lg bg-deep-teal-800/5 dark:bg-white/5 text-center">
                 <div className="text-[10px] opacity-60">Sig/Hr</div>
                 <div className="font-mono font-bold">{systemMetrics.signalsPerHour}</div>
              </div>
              <div className="p-2 rounded-lg bg-deep-teal-800/5 dark:bg-white/5 text-center">
                 <div className="text-[10px] opacity-60">Trades/D</div>
                 <div className="font-mono font-bold">{systemMetrics.tradesPerDay}</div>
              </div>
              <div className="p-2 rounded-lg bg-deep-teal-800/5 dark:bg-white/5 text-center">
                 <div className="text-[10px] opacity-60">Latency</div>
                 <div className="font-mono font-bold">{systemMetrics.avgLatency}</div>
              </div>
              <div className="p-2 rounded-lg bg-deep-teal-800/5 dark:bg-white/5 text-center">
                 <div className="text-[10px] opacity-60">Queue</div>
                 <div className="font-mono font-bold">{systemMetrics.queueDepth}</div>
              </div>
           </div>
        </GlassCard>

      </motion.div>

      {/* 3. Main Content: Allocation & Regime */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left Col (2/3): Capital Allocation */}
        <motion.div variants={fadeInUp} className="xl:col-span-2">
           <GlassCard className="h-full flex flex-col">
              <div className="flex items-center gap-2 mb-6">
                 <PieChart className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
                 <h3 className="font-display text-lg">Capital Allocation</h3>
              </div>
              
              <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
                 {/* Strategy Chart */}
                 <div className="flex flex-col items-center">
                    <h4 className="text-xs font-mono uppercase tracking-widest opacity-60 mb-4">By Strategy</h4>
                    <DonutChart 
                       data={allocationStrategy} 
                       height={220} 
                       innerRadius="65%" 
                       outerRadius="90%"
                       showLegend={false}
                       centerContent={
                          <div className="text-center">
                             <div className="text-xs opacity-50 uppercase">Deployed</div>
                             <div className="font-mono font-bold text-lg">85%</div>
                          </div>
                       }
                    />
                    {/* Compact Legend */}
                    <div className="flex flex-wrap justify-center gap-2 mt-4 px-4">
                       {allocationStrategy.slice(0, 4).map(s => (
                          <div key={s.name} className="flex items-center gap-1.5 text-[10px]">
                             <div className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color }} />
                             <span className="opacity-80">{s.name}</span>
                          </div>
                       ))}
                    </div>
                 </div>

                 {/* Risk Tier Chart */}
                 <div className="flex flex-col items-center">
                    <h4 className="text-xs font-mono uppercase tracking-widest opacity-60 mb-4">By Risk Tier</h4>
                    <DonutChart 
                       data={allocationRisk} 
                       height={220} 
                       innerRadius="65%" 
                       outerRadius="90%"
                       showLegend={false}
                       centerContent={
                          <div className="text-center">
                             <div className="text-xs opacity-50 uppercase">Max Risk</div>
                             <div className="font-mono font-bold text-lg">1.5%</div>
                          </div>
                       }
                    />
                    <div className="flex flex-wrap justify-center gap-2 mt-4 px-4">
                       {allocationRisk.map(s => (
                          <div key={s.name} className="flex items-center gap-1.5 text-[10px]">
                             <div className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color }} />
                             <span className="opacity-80">{s.name}</span>
                          </div>
                       ))}
                    </div>
                 </div>
              </div>

              <div className="mt-6 pt-4 border-t border-deep-teal-800/5 dark:border-white/5 text-center">
                 <p className="text-sm font-medium text-obsidian-400 dark:text-paper-100">
                    Total Deployed: <span className="font-mono">{formatCurrency(4080000)}</span> of <span className="font-mono opacity-70">{formatCurrency(4800000)}</span> (85%)
                 </p>
              </div>
           </GlassCard>
        </motion.div>

        {/* Right Col (1/3): Market Regime */}
        <motion.div variants={fadeInUp}>
           <MarketRegimePanel data={marketRegime} />
        </motion.div>
      </div>

      {/* 4. Bottom Grid: Decisions, Performance, Risk */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
         
         {/* Left: Curator Decisions */}
         <motion.div variants={fadeInUp} className="xl:col-span-2">
            <GlassCard className="h-[500px] flex flex-col" padding="none">
               {/* Header & Tabs */}
               <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-col h-full">
                  <div className="px-6 py-4 border-b border-deep-teal-800/5 dark:border-white/5 flex flex-wrap items-center justify-between gap-4">
                     <div className="flex items-center gap-2">
                        <Cpu className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
                        <h3 className="font-display text-lg">Curator Decision Log</h3>
                     </div>
                     <TabsList variant="pill" className="bg-deep-teal-800/5 dark:bg-white/5">
                        <TabsTrigger value="All" className="text-xs h-7 px-3">All</TabsTrigger>
                        <TabsTrigger value="Allocation" className="text-xs h-7 px-3">Allocation</TabsTrigger>
                        <TabsTrigger value="Agent" className="text-xs h-7 px-3">Agent</TabsTrigger>
                        <TabsTrigger value="Risk" className="text-xs h-7 px-3">Risk</TabsTrigger>
                        <TabsTrigger value="Regime" className="text-xs h-7 px-3">Regime</TabsTrigger>
                     </TabsList>
                  </div>

                  <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                     <div className="space-y-0 relative border-l border-deep-teal-800/10 dark:border-white/10 ml-3.5 pl-6">
                        <AnimatePresence mode="popLayout">
                           {filteredDecisions.map((decision) => (
                              <motion.div
                                 key={decision.id}
                                 layout
                                 initial={{ opacity: 0, x: -10 }}
                                 animate={{ opacity: 1, x: 0 }}
                                 exit={{ opacity: 0, scale: 0.95 }}
                                 className="mb-6 last:mb-0"
                              >
                                 <DecisionCard decision={decision} />
                              </motion.div>
                           ))}
                        </AnimatePresence>
                     </div>
                     <div className="mt-4 flex justify-center">
                        <Button variant="ghost" size="sm" className="text-xs uppercase tracking-widest opacity-60 hover:opacity-100">Load More</Button>
                     </div>
                  </div>
               </Tabs>
            </GlassCard>
         </motion.div>

         {/* Right: Strategy & Risk Stack */}
         <motion.div variants={fadeInUp} className="space-y-6">
            
            {/* Strategy Performance */}
            <GlassCard>
               <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                     <Layers className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
                     <h3 className="font-display text-base">Strategy Performance</h3>
                  </div>
                  <span className="text-[10px] font-mono text-obsidian-400/50 dark:text-paper-100/50">YTD Return</span>
               </div>
               
               <div className="space-y-4">
                  {strategyPerformance.map((strat) => (
                     <div key={strat.name} className="group">
                        <div className="flex justify-between text-xs mb-1">
                           <span className="font-medium">{strat.name}</span>
                           <span className={cn("font-mono font-bold", strat.ytd >= 0 ? "text-gain" : "text-loss")}>
                              {strat.ytd > 0 ? '+' : ''}{strat.ytd}%
                           </span>
                        </div>
                        <div className="h-1.5 w-full bg-obsidian-400/5 dark:bg-white/10 rounded-full overflow-hidden mb-1">
                           <div 
                              className={cn("h-full rounded-full", strat.ytd >= 0 ? "bg-deep-teal-600 dark:bg-turquoise-mist" : "bg-loss")} 
                              style={{ width: `${Math.min(Math.abs(strat.ytd) * 2.5, 100)}%` }} 
                           />
                        </div>
                        <div className="flex justify-between text-[10px] text-obsidian-400/40 dark:text-paper-100/40 font-mono">
                           <span>Sharpe: {strat.sharpe}</span>
                           <span>{strat.count} Agents</span>
                        </div>
                     </div>
                  ))}
               </div>
               
               <div className="mt-4 pt-3 border-t border-deep-teal-800/5 dark:border-white/5 text-[10px] text-center opacity-60">
                  Best: Momentum (+32.4%) | Worst: Experimental (-4.5%)
               </div>
            </GlassCard>

            {/* Risk Limits */}
            <GlassCard className="flex flex-col gap-4">
               <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
                  <h3 className="font-display text-base">Risk Limits</h3>
               </div>
               
               <div className="space-y-3">
                  {riskLimits.map((risk) => {
                     const pct = (risk.current / risk.max) * 100;
                     const status = pct > 80 ? 'danger' : pct > 60 ? 'warning' : 'success';
                     
                     return (
                        <div key={risk.label} className="space-y-1">
                           <div className="flex justify-between text-[10px] font-medium">
                              <span>{risk.label}</span>
                              <span className="font-mono opacity-70">
                                 {risk.unit === '$' ? formatCurrency(risk.current) : risk.current}{risk.unit} / {risk.unit === '$' ? formatCurrency(risk.max) : risk.max}{risk.unit}
                              </span>
                           </div>
                           <Progress 
                              value={risk.current} 
                              max={risk.max} 
                              variant={status} 
                              size="sm" 
                              showLabel={false} 
                           />
                        </div>
                     );
                  })}
               </div>
            </GlassCard>

            {/* Scheduled Events */}
            <GlassCard>
               <div className="flex items-center gap-2 mb-3">
                  <Clock className="w-4 h-4 text-deep-teal-800 dark:text-turquoise-mist" />
                  <h3 className="font-display text-sm font-medium">Scheduled Events</h3>
               </div>
               <div className="space-y-2">
                  {scheduledEvents.map((item, i) => (
                     <div key={i} className="flex items-center gap-3 p-2 rounded bg-deep-teal-800/5 dark:bg-white/5 border border-deep-teal-800/5 dark:border-white/5">
                        <div className="flex flex-col items-center min-w-[30px] border-r border-deep-teal-800/10 dark:border-white/10 pr-2 mr-1">
                           {i === 0 && <span className="w-1.5 h-1.5 rounded-full bg-gain animate-pulse mb-1" />}
                           <Clock className="w-3 h-3 opacity-40" />
                        </div>
                        <div className="flex-1">
                           <div className="text-xs font-medium text-obsidian-400 dark:text-paper-100">{item.event}</div>
                           <div className="text-[10px] font-mono opacity-60">{item.time}</div>
                        </div>
                     </div>
                  ))}
               </div>
               <div className="mt-2 text-[10px] text-right text-turquoise-mist font-mono">Next: Rebalance check in 2h 15m</div>
            </GlassCard>

         </motion.div>
      </div>

      <ExportModal 
        isOpen={isExportOpen} 
        onClose={() => setIsExportOpen(false)} 
        onExport={handleExport}
        title="Export System Log"
      />

    </motion.div>
  );
};
