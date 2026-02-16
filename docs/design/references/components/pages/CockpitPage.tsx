
import React, { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BarChart3, Activity, Zap, ShieldAlert, AlertTriangle, 
  Cpu, Terminal, ArrowRight, Signal, Layers, PieChart,
  Calendar, Clock, Server, Wifi, CheckCircle2, AlertOctagon,
  Radio, TrendingUp, Hand, Lock, Download
} from 'lucide-react';
import { GlassCard } from '../ui/GlassCard';
import { Badge } from '../ui/Badge';
import { MetricCard } from '../ui/MetricCard';
import { Button } from '../ui/Button';
import { Tooltip } from '../ui/Tooltip';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/Tabs';
import { MarketTicker, MarketItem } from '../dashboard/MarketTicker';
import { SVGAreaChart } from '../dashboard/charts/SVGAreaChart';
import { PositionsTable, Position } from '../dashboard/PositionsTable';
import { Watchlist, WatchlistItem } from '../dashboard/Watchlist';
import { ActivityFeed, ActivityItem } from '../dashboard/ActivityFeed';
import { DonutChart } from '../dashboard/charts/DonutChart';
import { LoadingState } from '../ui/LoadingState';
import { ErrorBoundary } from '../ui/ErrorBoundary';
import { Skeleton } from '../ui/Skeleton';
import { ExportModal, ExportConfig } from '../dashboard/ExportModal';
import { cn, formatCurrency } from '../../lib/utils';
import { fadeInUp, staggerContainer } from '../../lib/animations';
import { useDashboard, PositionDetails } from '../../contexts/DashboardContext';
import { useRealtimeSimulation } from '../../hooks/useRealtimeSimulation';
import { useToast } from '../../contexts/ToastContext';

// --- MOCK DATA ---

const initialTickerItems: MarketItem[] = [
  { symbol: 'SPY', value: 512.30, change: 4.20, changePercent: 0.82 },
  { symbol: 'QQQ', value: 440.15, change: 5.50, changePercent: 1.25 },
  { symbol: 'IWM', value: 205.40, change: -1.20, changePercent: -0.58 },
  { symbol: 'BTC', value: 67500.00, change: 2100.00, changePercent: 3.20 },
  { symbol: 'ETH', value: 3850.50, change: 120.00, changePercent: 3.10 },
  { symbol: 'VIX', value: 16.50, change: 2.10, changePercent: 14.60 }, 
  { symbol: 'GLD', value: 195.00, change: 1.50, changePercent: 0.77 },
];

const initialWatchlistItems: WatchlistItem[] = [
  { id: '1', symbol: 'NVDA', name: 'NVIDIA Corp', price: 890.25, change: 15.50, changePercent: 1.77 },
  { id: '2', symbol: 'AMD', name: 'Advanced Micro', price: 180.40, change: -2.10, changePercent: -1.15 },
  { id: '3', symbol: 'COIN', name: 'Coinbase Global', price: 245.00, change: 12.00, changePercent: 5.15 },
  { id: '4', symbol: 'PLTR', name: 'Palantir Tech', price: 24.50, change: 0.80, changePercent: 3.38 },
  { id: '5', symbol: 'TSLA', name: 'Tesla Inc', price: 175.40, change: -3.20, changePercent: -1.79 },
  { id: '6', symbol: 'SMCI', name: 'Super Micro', price: 950.00, change: 45.00, changePercent: 4.97 },
];

const initialActivityItems: ActivityItem[] = [
  { id: '1', type: 'agent', title: 'Curator Decision', description: 'Curator increased Momentum allocation by 5%', timestamp: new Date(Date.now() - 1000 * 60 * 2) },
  { id: '2', type: 'alert', title: 'Risk Alert', description: 'Position TSLA approaching max loss threshold', timestamp: new Date(Date.now() - 1000 * 60 * 15) },
  { id: '3', type: 'trade', title: 'Trade Executed', description: 'Momentum Prime opened LONG AAPL x500', timestamp: new Date(Date.now() - 1000 * 60 * 45) },
  { id: '4', type: 'agent', title: 'Signal Generated', description: 'Alpha Seeker generated BUY signal for NVDA (87% confidence)', timestamp: new Date(Date.now() - 1000 * 60 * 60) },
];

const agentFleet = Array.from({ length: 52 }).map((_, i) => {
  const r = Math.random();
  let status: 'active' | 'paused' | 'training' | 'error' = 'active';
  if (i < 2) status = 'error'; // Fixed 2 errors
  else if (i < 10) status = 'paused';
  else if (i < 14) status = 'training';
  
  return {
    id: `agent-${i}`,
    name: `Agent ${i + 1}`,
    status
  };
}).sort(() => Math.random() - 0.5);

const generateChartData = () => {
  const data = [];
  let value = 1000000;
  for (let i = 0; i < 30; i++) {
    const date = new Date();
    date.setDate(date.getDate() - (29 - i));
    const change = (Math.random() - 0.45) * 20000; 
    value += change;
    data.push({
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: value
    });
  }
  return data;
};
const portfolioData = generateChartData();

const curatorDecisions = [
  { id: 1, time: '10:42 AM', action: 'Allocation Change', reason: 'Reduced Momentum allocation 25%→20% (volatility spike)', impact: 'Risk OFF' },
  { id: 2, time: '09:15 AM', action: 'Strategy Activation', reason: 'Activated Arbitrage Suite overnight mode', impact: 'Yield +' },
  { id: 3, time: 'Yesterday', action: 'Paused Strategy', reason: 'Paused Experimental group (drawdown limit)', impact: 'Safety' },
];

const sectorData = [
  { name: 'Technology', value: 45 },
  { name: 'Financials', value: 20 },
  { name: 'Crypto', value: 15 },
  { name: 'Energy', value: 10 },
  { name: 'Cash', value: 10 },
];

// --- COMPONENT ---

export const CockpitPage = () => {
  const { openAlertModal, openPositionDrawer, viewStrategy, openEmergencyPanel } = useDashboard();
  const [isLoading, setIsLoading] = useState(true);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const { toast } = useToast();

  // Hook into simulation (Passing empty agents array as Cockpit uses simpler agentFleet for now)
  const { marketData, watchlist, activity, lastSync } = useRealtimeSimulation(
    initialTickerItems, 
    initialWatchlistItems, 
    [], 
    initialActivityItems
  );

  // Simulate initial data fetch
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 1200);
    return () => clearTimeout(timer);
  }, []);

  const handlePositionClick = (pos: Position) => {
    const details: PositionDetails = {
      id: pos.id,
      symbol: pos.symbol,
      name: pos.name,
      sector: pos.sector || 'Unknown',
      assetType: pos.assetType || 'Stock',
      quantity: pos.quantity,
      avgCost: pos.avgPrice,
      price: pos.currentPrice,
      value: pos.currentPrice * pos.quantity,
      pnl: pos.pl,
      pnlPercent: pos.plPercent,
      weight: pos.weight
    };
    openPositionDrawer(details);
  };

  const fleetStats = useMemo(() => ({
    active: agentFleet.filter(a => a.status === 'active').length,
    paused: agentFleet.filter(a => a.status === 'paused').length,
    training: agentFleet.filter(a => a.status === 'training').length,
    error: agentFleet.filter(a => a.status === 'error').length,
  }), []);

  const manualOverrides = 0;
  const isHighVolatility = true;

  const handleExport = (config: ExportConfig) => {
    toast({
      title: 'Export Started',
      description: `Generating ${config.format.toUpperCase()} report from ${config.startDate} to ${config.endDate}...`,
      type: 'info'
    });
  };

  if (isLoading) {
    return <LoadingState variant="page" message="Synchronizing Cockpit Data..." />;
  }

  return (
    <ErrorBoundary>
      <motion.div
        initial="initial"
        animate="animate"
        exit={{ opacity: 0 }}
        variants={staggerContainer}
        className="space-y-6 pt-2 pb-10"
      >
        {/* 1. System Alert Banner */}
        <AnimatePresence>
          {(fleetStats.error > 0 || isHighVolatility) && (
            <motion.div variants={fadeInUp}>
               {/* Critical Errors */}
               {fleetStats.error > 0 && (
                  <div className="mb-3 rounded-xl border border-loss/20 bg-loss/5 p-3 flex items-center justify-between gap-4">
                     <div className="flex items-center gap-3">
                        <div className="p-1.5 bg-loss/10 rounded-lg text-loss animate-pulse">
                           <AlertTriangle className="w-4 h-4" />
                        </div>
                        <span className="text-sm font-medium text-loss">
                           Attention: {fleetStats.error} agents currently in error state.
                        </span>
                     </div>
                     <button className="text-xs font-bold text-loss hover:underline">View Issues</button>
                  </div>
               )}
               
               {/* Volatility Warning */}
               {isHighVolatility && fleetStats.error === 0 && (
                  <div className="mb-3 rounded-xl border border-warning/20 bg-warning/5 p-3 flex items-center justify-between gap-4">
                     <div className="flex items-center gap-3">
                        <div className="p-1.5 bg-warning/10 rounded-lg text-warning">
                           <Zap className="w-4 h-4" />
                        </div>
                        <span className="text-sm font-medium text-warning">
                           High volatility detected. Curator has reduced leverage exposure.
                        </span>
                     </div>
                     <button className="text-xs font-bold text-warning hover:underline">Dismiss</button>
                  </div>
               )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* 2. Header & Overview */}
        <motion.div variants={fadeInUp} className="space-y-6">
          <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 px-1">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                  <h2 className="font-display text-4xl font-medium text-obsidian-400 dark:text-paper-100 tracking-tight">
                    System <span className="text-deep-teal-600 dark:text-turquoise-mist">Status</span>
                  </h2>
                  <Badge variant="success" dot pulsing className="h-7 px-3 text-xs tracking-wider bg-gain/10 text-gain border-gain/20">LIVE</Badge>
              </div>
              
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-obsidian-400/60 dark:text-paper-100/60 font-mono text-sm">
                 <span className="flex items-center gap-1.5 text-gain">
                    <CheckCircle2 className="w-4 h-4" />
                    Fully Operational
                 </span>
                 <span className="hidden sm:inline w-1 h-1 rounded-full bg-current opacity-30" />
                 <span>Last sync: {lastSync}s ago</span>
                 <span className="hidden sm:inline w-1 h-1 rounded-full bg-current opacity-30" />
                 <span className="text-obsidian-400 dark:text-paper-100 font-medium">52 agents • 12 open positions • $4.8M deployed</span>
              </div>
            </div>
            
            <div className="flex flex-wrap items-center gap-3">
               <Button variant="secondary" onClick={() => setIsExportOpen(true)} leftIcon={<Download className="w-4 h-4" />}>
                  Export
               </Button>
               <button
                  onClick={openEmergencyPanel}
                  className="group flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-red-500/10 to-orange-500/10 border border-red-500/20 hover:border-red-500/40 transition-all"
               >
                  <div className="relative">
                     <ShieldAlert className="w-5 h-5 text-red-500" />
                     <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full animate-ping" />
                  </div>
                  <div className="flex flex-col items-start">
                     <span className="text-[10px] uppercase font-bold text-red-500/70 tracking-wider leading-none">Emergency</span>
                     <span className="text-sm font-bold text-red-500 leading-none mt-0.5 group-hover:text-red-400">12 Open Positions</span>
                  </div>
               </button>
            </div>
          </div>
          
          <div className="rounded-xl overflow-hidden shadow-lg shadow-deep-teal-900/5">
            <MarketTicker items={marketData} speed="slow" />
          </div>
        </motion.div>

        {/* 3. KPI Cards */}
        <motion.div variants={fadeInUp} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
             <MetricCard 
               variant="dark" 
               title="Net Liquidity" 
               value={portfolioData[portfolioData.length - 1].value} 
               prefix="$"
               className="border-transparent"
             />
             <MetricCard 
               variant="default" 
               title="Day P&L" 
               value={14203.12} 
               prefix="+$" 
               change={1.24} 
               className="border-transparent"
             />
             <MetricCard 
               variant="default" 
               title="Signals Today" 
               value={156} 
               format="raw"
               icon={Signal}
               change={12}
               className="border-transparent"
             />
             <MetricCard 
               variant="default" 
               title="Trades Today" 
               value={23} 
               format="raw"
               icon={Zap}
               suffix=" Executed"
               className="border-transparent"
             />
        </motion.div>

        {/* System Health Row */}
        <motion.div variants={fadeInUp} className="w-full">
           <GlassCard padding="sm" className="flex flex-wrap items-center justify-between gap-4 border-deep-teal-800/10 dark:border-white/10 bg-paper-100/50 dark:bg-white/5">
              <div className="flex items-center gap-6 text-xs font-mono">
                 <div className="flex items-center gap-2">
                    <span className="uppercase tracking-wider opacity-50">API Status</span>
                    <span className="flex items-center gap-1 text-gain font-bold"><Wifi className="w-3 h-3" /> Connected</span>
                 </div>
                 <div className="w-px h-3 bg-current opacity-10 hidden sm:block" />
                 <div className="hidden sm:flex items-center gap-2">
                    <span className="uppercase tracking-wider opacity-50">Last Trade</span>
                    <span className="font-bold text-obsidian-400 dark:text-paper-100">NVDA +500 @ $890.25 (2m ago)</span>
                 </div>
                 <div className="w-px h-3 bg-current opacity-10 hidden sm:block" />
                 <div className="flex items-center gap-2">
                    <span className="uppercase tracking-wider opacity-50">Pending</span>
                    <span className="font-bold text-warning">3 Signals</span>
                 </div>
              </div>
              
              <div className="flex items-center gap-4 text-xs">
                 <div className="flex items-center gap-2">
                    <span className="uppercase tracking-wider opacity-50">Overrides</span>
                    <span className={cn("font-bold flex items-center gap-1", manualOverrides > 0 ? "text-loss" : "text-gain")}>
                       {manualOverrides > 0 ? <Hand className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
                       {manualOverrides}
                    </span>
                 </div>
                 <div className="w-px h-3 bg-current opacity-10" />
                 <div className="flex items-center gap-2">
                    <span className="uppercase tracking-wider opacity-50">Risk Status</span>
                    <Badge variant="success" size="sm" className="h-5 px-1.5 text-[9px]">Normal</Badge>
                 </div>
              </div>
           </GlassCard>
        </motion.div>

        {/* 4. Main Dashboard Grid */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
          
          {/* Left Column */}
          <div className="xl:col-span-2 space-y-6">
            <motion.div variants={fadeInUp}>
              <GlassCard variant="default" className="p-0 overflow-hidden flex flex-col h-[420px]">
                <div className="px-6 py-5 border-b border-deep-teal-800/5 dark:border-white/5 flex flex-col md:flex-row gap-4 justify-between items-start md:items-center bg-white/40 dark:bg-white/5 backdrop-blur-md">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-deep-teal-800/5 dark:bg-turquoise-mist/10 rounded-lg text-deep-teal-800 dark:text-turquoise-mist">
                      <BarChart3 className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-display text-lg text-obsidian-400 dark:text-paper-100">Performance</h3>
                      <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-mono">NAV • 30 Days</p>
                    </div>
                  </div>
                  <div className="flex bg-deep-teal-800/5 dark:bg-white/5 rounded-lg p-1">
                     {['1D', '1W', '1M', '3M', 'YTD'].map((tf, i) => (
                       <button key={tf} className={cn(
                         "px-3 py-1 text-xs font-mono rounded-md transition-all text-center",
                         i === 2 ? "bg-white dark:bg-obsidian-300 shadow-sm text-deep-teal-800 dark:text-paper-100" : "text-obsidian-400/60 dark:text-paper-100/60 hover:text-deep-teal-800 dark:hover:text-paper-100"
                       )}>{tf}</button>
                     ))}
                  </div>
                </div>
                <div className="flex-1 w-full px-6 pt-6 pb-2">
                  <SVGAreaChart 
                    data={portfolioData} 
                    height={300} 
                    showGrid={true} 
                    gradientId="portfolioMain"
                  />
                </div>
              </GlassCard>
            </motion.div>

            <motion.div variants={fadeInUp}>
               <GlassCard padding="none" className="min-h-[400px] flex flex-col">
                  <Tabs defaultValue="activity" className="flex flex-col h-full">
                     <div className="px-6 py-4 border-b border-deep-teal-800/5 dark:border-white/5 flex flex-wrap gap-4 items-center justify-between bg-white/40 dark:bg-white/5 backdrop-blur-md">
                        <div className="flex items-center gap-2">
                           <Layers className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
                           <h3 className="font-display text-lg text-obsidian-400 dark:text-paper-100">Live Data</h3>
                        </div>
                        <TabsList variant="pill">
                           <TabsTrigger value="activity">System Activity</TabsTrigger>
                           <TabsTrigger value="positions">Positions</TabsTrigger>
                           <TabsTrigger value="allocation">Allocation</TabsTrigger>
                        </TabsList>
                     </div>

                     <div className="flex-1 overflow-hidden">
                        <TabsContent value="positions" className="mt-0 h-full">
                           <PositionsTable limit={5} onPositionClick={handlePositionClick} />
                        </TabsContent>
                        
                        <TabsContent value="activity" className="mt-0 h-full">
                           <ActivityFeed items={activity} className="border-0 shadow-none bg-transparent" />
                        </TabsContent>

                        <TabsContent value="allocation" className="mt-0 h-full p-6 flex items-center justify-center">
                           <div className="w-full max-w-md">
                              <DonutChart 
                                 data={sectorData.map((d, i) => ({ ...d, color: '' }))} 
                                 height={300} 
                                 innerRadius="60%"
                                 outerRadius="80%"
                                 centerContent={
                                    <div className="text-center">
                                       <PieChart className="w-8 h-8 mx-auto mb-2 text-obsidian-400/30 dark:text-paper-100/30" />
                                       <div className="text-sm font-bold">Diverse</div>
                                    </div>
                                 }
                              />
                           </div>
                        </TabsContent>
                     </div>
                  </Tabs>
               </GlassCard>
            </motion.div>
          </div>

          {/* Right Column */}
          <div className="space-y-6 flex flex-col justify-start">
              
              {/* Agent Fleet Status */}
              <motion.div variants={fadeInUp}>
                 <GlassCard className="flex flex-col gap-4">
                    <div className="flex items-center justify-between pb-2 border-b border-deep-teal-800/5 dark:border-white/5">
                       <div className="flex items-center gap-2">
                          <Cpu className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
                          <h3 className="font-display text-lg">Agent Fleet Status</h3>
                       </div>
                       <Badge variant="outline" className="text-[10px]">{agentFleet.length} Units</Badge>
                    </div>
                    
                    <div className="grid grid-cols-10 gap-2 min-h-[100px]">
                       {agentFleet.map((agent, i) => (
                          <Tooltip key={agent.id} content={`${agent.name}: ${agent.status}`} side="top">
                             <motion.div 
                               initial={{ scale: 0 }}
                               animate={{ scale: 1 }}
                               transition={{ delay: i * 0.005 }}
                               className={cn(
                                 "w-2.5 h-2.5 rounded-full cursor-pointer hover:scale-150 transition-all duration-300",
                                 agent.status === 'active' ? "bg-gain shadow-[0_0_5px_rgba(46,204,113,0.4)]" : 
                                 agent.status === 'paused' ? "bg-warning opacity-70" :
                                 agent.status === 'training' ? "bg-info opacity-70" :
                                 "bg-loss animate-pulse shadow-[0_0_8px_rgba(231,76,60,0.8)]"
                               )}
                               onClick={() => viewStrategy('1')}
                             />
                          </Tooltip>
                       ))}
                    </div>

                    <div className="flex flex-wrap justify-between items-center gap-2 pt-3 border-t border-deep-teal-800/5 dark:border-white/5 text-[10px] font-mono uppercase tracking-wide text-obsidian-400/60 dark:text-paper-100/60">
                        <div>
                           <span className="text-gain">{fleetStats.active} Active</span>
                           <span className="mx-1.5 opacity-30">•</span>
                           <span className="text-warning">{fleetStats.paused} Paused</span>
                           <span className="mx-1.5 opacity-30">•</span>
                           <span className="text-info">{fleetStats.training} Training</span>
                           <span className="mx-1.5 opacity-30">•</span>
                           <span className="text-loss">{fleetStats.error} Errors</span>
                        </div>
                        <button className="text-turquoise-mist hover:underline">View All Agents →</button>
                    </div>
                 </GlassCard>
              </motion.div>

              {/* Curator Intelligence Feed */}
              <motion.div variants={fadeInUp}>
                 <GlassCard className="flex flex-col gap-4">
                    <div className="flex items-center justify-between pb-2 border-b border-deep-teal-800/5 dark:border-white/5">
                       <div className="flex items-center gap-2">
                          <Terminal className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
                          <h3 className="font-display text-lg">Curator Intelligence</h3>
                       </div>
                       <button className="text-xs font-mono uppercase tracking-widest text-turquoise-mist hover:underline">
                          View System Overview →
                       </button>
                    </div>
                    
                    <div className="space-y-4">
                       {curatorDecisions.map((decision) => (
                          <div key={decision.id} className="relative pl-4 border-l border-deep-teal-800/10 dark:border-white/10 group">
                             <div className="absolute -left-[5px] top-1.5 w-2.5 h-2.5 rounded-full bg-paper-100 dark:bg-obsidian-300 border-2 border-deep-teal-800 dark:border-turquoise-mist group-hover:scale-110 transition-transform" />
                             <div className="text-[10px] font-mono opacity-50 mb-0.5">{decision.time}</div>
                             <div className="text-sm font-medium text-obsidian-400 dark:text-paper-100">{decision.reason}</div>
                             <div className="flex items-center gap-2 mt-1">
                                <Badge variant="outline" size="sm" className="h-4 px-1.5 text-[9px] opacity-70">{decision.impact}</Badge>
                             </div>
                          </div>
                       ))}
                    </div>
                 </GlassCard>
              </motion.div>

              {/* Watchlist */}
              <motion.div variants={fadeInUp}>
                 <Watchlist 
                   items={watchlist} 
                   className="h-auto max-h-[400px]" 
                   onAlert={(item) => openAlertModal(item.symbol, item.price)}
                 />
              </motion.div>

          </div>
        </div>

        <ExportModal 
          isOpen={isExportOpen} 
          onClose={() => setIsExportOpen(false)} 
          onExport={handleExport}
          title="Export Dashboard Report"
        />

      </motion.div>
    </ErrorBoundary>
  );
};
