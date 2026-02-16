
import React, { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Bot, Search, Filter, Plus, Pause, Play, Download, 
  LayoutGrid, List, AlertTriangle, Zap, Activity, 
  TrendingUp, TrendingDown, RefreshCw, XCircle, CheckCircle2,
  ChevronDown, MoreHorizontal, Trophy, Clock, ArrowRight
} from 'lucide-react';

import { PageHeader } from '../layout/PageHeader';
import { GlassCard } from '../ui/GlassCard';
import { Button } from '../ui/Button';
import { SearchInput } from '../ui/SearchInput';
import { Badge } from '../ui/Badge';
import { Dropdown } from '../ui/Dropdown';
import { DataTable, Column } from '../dashboard/DataTable';
import { SparklineChart } from '../dashboard/charts/SparklineChart';
import { LoadingState } from '../ui/LoadingState';
import { EmptyState } from '../ui/EmptyState';
import { ErrorBoundary } from '../ui/ErrorBoundary';
import { ExportModal, ExportConfig } from '../dashboard/ExportModal';
import { cn, formatCurrency } from '../../lib/utils';
import { staggerContainer, fadeInUp } from '../../lib/animations';
import { useDashboard } from '../../contexts/DashboardContext';
import { StrategyStatus, StrategyType } from '../dashboard/StrategyCard';
import { useRealtimeSimulation } from '../../hooks/useRealtimeSimulation';
import { useToast } from '../../contexts/ToastContext';

// --- Mock Data Generation ---

export interface StrategySummary {
  id: string;
  name: string;
  type: StrategyType;
  status: StrategyStatus;
  pnlDay: number;
  pnlTotal: number;
  pnlMtd: number; 
  winRate: number;
  sharpe: number;
  openPositions: number;
  lastSignal: string; 
  sparkline: number[];
  errorMessage?: string;
  rank?: number; 
}

const STRATEGIES: StrategyType[] = ['arbitrage', 'momentum', 'mean-reversion', 'macro', 'ml-signal'];

const STRATEGY_NAMES_PREFIX = ['Alpha', 'Momentum', 'Quantum', 'Neural', 'Vega', 'Delta', 'Sigma', 'Orbit', 'Flux', 'Apex'];
const STRATEGY_NAMES_SUFFIX = ['Seeker', 'Prime', 'Hunter', 'Sentinel', 'Surfer', 'Scanner', 'Trader', 'Bot', 'Engine', 'Core'];

const generateStrategies = (count: number): StrategySummary[] => {
  return Array.from({ length: count }).map((_, i) => {
    // Weighted status generation to match prompt (38 active, 8 paused, 4 training, 2 error)
    // We'll approximate the distribution
    let status: StrategyStatus = 'active';
    let errorMessage: string | undefined;
    
    if (i < 2) { 
      status = 'error';
      errorMessage = i === 0 ? 'Connection timeout to broker API' : 'Latency Threshold Breached (>500ms)';
    } else if (i < 6) {
      status = 'training';
    } else if (i < 14) {
      status = 'paused';
    }

    const type = STRATEGIES[i % STRATEGIES.length];
    const name = `${STRATEGY_NAMES_PREFIX[i % STRATEGY_NAMES_PREFIX.length]} ${STRATEGY_NAMES_SUFFIX[i % STRATEGY_NAMES_SUFFIX.length]} ${['V1', 'V2', 'X', 'Pro'][i % 4]}`;
    
    const pnlDay = (Math.random() - 0.45) * 8000; 
    const pnlTotal = pnlDay * (10 + Math.random() * 50);
    const winRate = 45 + Math.random() * 40; // 45-85%
    
    // Sparkline data
    const sparkline = Array.from({ length: 7 }).map(() => (Math.random() - 0.45) * 100);

    return {
      id: (i + 1).toString(),
      name,
      type,
      status,
      pnlDay,
      pnlTotal,
      pnlMtd: pnlDay * 12,
      winRate,
      sharpe: 0.8 + Math.random() * 2.8,
      openPositions: status === 'active' ? Math.floor(Math.random() * 12) : 0,
      lastSignal: `${Math.floor(Math.random() * 59)}m ago`,
      sparkline,
      errorMessage
    };
  });
};

const initialMockStrategies = generateStrategies(52);

// --- Components ---

const StrategyCompactCard: React.FC<{ strategy: StrategySummary, onClick: () => void, isTopPerformer: boolean }> = ({ strategy, onClick, isTopPerformer }) => {
  const isProfit = strategy.pnlDay >= 0;
  const isError = strategy.status === 'error';
  const isPaused = strategy.status === 'paused';
  const isTraining = strategy.status === 'training';
  
  return (
    <motion.div variants={fadeInUp} layoutId={strategy.id}>
      <GlassCard
        variant={isError ? 'subtle' : 'default'}
        padding="none"
        enableHover
        onClick={onClick}
        className={cn(
          "relative overflow-hidden cursor-pointer h-full border-l-4 transition-all duration-300",
          // Error State
          isError && "border-l-loss bg-loss/5 shadow-[0_0_15px_rgba(231,76,60,0.1)]",
          // Training State
          isTraining && "border-l-info bg-info/5 shadow-[0_0_15px_rgba(52,152,219,0.1)]",
          // Top Performer State
          isTopPerformer && !isError && "border-l-warning bg-gradient-to-br from-warning/5 to-transparent",
          // Standard Profit/Loss
          !isError && !isTraining && !isTopPerformer && (isProfit ? "border-l-gain" : "border-l-obsidian-400/20 dark:border-l-white/20"),
          // Paused Opacity
          isPaused && "opacity-70 grayscale-[0.5]"
        )}
      >
        <div className="p-4 space-y-3">
          {/* Header */}
          <div className="flex justify-between items-start gap-2">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                 <h4 className="font-bold text-sm truncate text-obsidian-400 dark:text-paper-100" title={strategy.name}>
                    {strategy.name}
                 </h4>
                 {isTopPerformer && <Trophy className="w-3 h-3 text-warning fill-warning/20" />}
              </div>
              <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                <Badge variant="neutral" size="sm" className="h-4 px-1 text-[9px] uppercase border-obsidian-400/10 dark:border-white/10">{strategy.type}</Badge>
                {isError && <Badge variant="danger" size="sm" className="h-4 px-1 text-[9px]">ERROR</Badge>}
                {isTraining && <Badge variant="info" size="sm" className="h-4 px-1 text-[9px] animate-pulse">TRAINING</Badge>}
              </div>
            </div>
            <div className={cn(
              "w-2 h-2 rounded-full flex-shrink-0 mt-1.5",
              strategy.status === 'active' ? "bg-gain shadow-[0_0_5px_rgba(46,204,113,0.8)]" :
              strategy.status === 'paused' ? "bg-warning" :
              strategy.status === 'training' ? "bg-info" : "bg-loss animate-pulse"
            )} />
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-2 gap-2 pt-1">
            <div>
              <div className="text-[9px] uppercase tracking-wider text-obsidian-400/50 dark:text-paper-100/50 mb-0.5">Day P&L</div>
              <div className={cn("font-mono font-bold text-sm transition-colors duration-500", isProfit ? "text-gain" : "text-loss")}>
                {isProfit ? '+' : ''}{formatCurrency(strategy.pnlDay).split('.')[0]}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[9px] uppercase tracking-wider text-obsidian-400/50 dark:text-paper-100/50 mb-0.5">Win Rate</div>
              <div className="font-mono font-medium text-sm text-obsidian-400 dark:text-paper-100">{strategy.winRate.toFixed(1)}%</div>
            </div>
          </div>

          {/* Sparkline & Actions Overlay */}
          <div className="relative h-8 mt-1">
             <div className="absolute inset-0 opacity-40">
               <SparklineChart
                 data={strategy.sparkline} 
                 color={isProfit ? 'gain' : 'loss'} 
                 showArea={true} 
               />
             </div>
             
             {/* Hover Actions */}
             <div className="absolute inset-0 flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity bg-paper-100/90 dark:bg-obsidian-300/90 backdrop-blur-[2px] rounded-lg">
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0 rounded-full bg-white dark:bg-black/20">
                   {strategy.status === 'paused' ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
                </Button>
                <Button variant="secondary" size="sm" className="h-6 text-[10px] px-2">View</Button>
             </div>
          </div>
        </div>
      </GlassCard>
    </motion.div>
  );
};

export const StrategiesPage = () => {
  const { toast } = useToast();
  const { viewStrategy } = useDashboard();
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('All');
  const [filterStrategy, setFilterStrategy] = useState<string>('All');
  const [sortBy, setSortBy] = useState<string>('P&L Today');
  const [isLoading, setIsLoading] = useState(true);
  const [isExportOpen, setIsExportOpen] = useState(false);

  // Use Realtime Simulation
  const { strategies: liveStrategies } = useRealtimeSimulation([], [], initialMockStrategies, []);

  // Simulate Initial Load
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 1000);
    return () => clearTimeout(timer);
  }, []);

  // --- Derived State ---

  const filteredStrategies = useMemo(() => {
    let result = liveStrategies.filter(s => {
      const matchesSearch = s.name.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = filterStatus === 'All' || s.status === filterStatus.toLowerCase();
      const matchesStrategyType = filterStrategy === 'All' || s.type === filterStrategy.toLowerCase();
      return matchesSearch && matchesStatus && matchesStrategyType;
    });

    // Sorting Logic
    result.sort((a, b) => {
        if (sortBy === 'Name') return a.name.localeCompare(b.name);
        if (sortBy === 'P&L Today') return b.pnlDay - a.pnlDay;
        if (sortBy === 'Win Rate') return b.winRate - a.winRate;
        if (sortBy === 'Status') return a.status.localeCompare(b.status);
        return 0;
    });

    return result;
  }, [liveStrategies, search, filterStatus, filterStrategy, sortBy]);

  const metrics = useMemo(() => {
    return {
      total: liveStrategies.length,
      active: liveStrategies.filter(s => s.status === 'active').length,
      paused: liveStrategies.filter(s => s.status === 'paused').length,
      training: liveStrategies.filter(s => s.status === 'training').length,
      error: liveStrategies.filter(s => s.status === 'error').length,
      pnlToday: liveStrategies.reduce((sum, s) => sum + s.pnlDay, 0),
      openPositions: liveStrategies.reduce((sum, s) => sum + s.openPositions, 0),
    };
  }, [liveStrategies]);

  const errors = liveStrategies.filter(s => s.status === 'error');
  // Identify top 5 purely based on PnL for visual flagging
  const topPerformerIds = [...liveStrategies].sort((a, b) => b.pnlDay - a.pnlDay).slice(0, 5).map(s => s.id);
  const topPerformersList = [...liveStrategies].sort((a, b) => b.pnlDay - a.pnlDay).slice(0, 3);
  const attentionList = [...liveStrategies].sort((a, b) => a.pnlDay - b.pnlDay).slice(0, 2);

  const handleExport = (config: ExportConfig) => {
    toast({
      title: 'Export Started',
      description: `Generating ${config.format.toUpperCase()} report from ${config.startDate} to ${config.endDate}...`,
      type: 'info'
    });
  };

  // --- Table Columns ---

  const columns: Column<StrategySummary>[] = [
    {
      key: 'status',
      header: 'Status',
      width: '80px',
      render: (val) => (
        <Badge
          variant={val === 'active' ? 'success' : val === 'error' ? 'danger' : val === 'paused' ? 'warning' : 'info'}
          dot
          size="sm"
          pulsing={val === 'active' || val === 'error' || val === 'training'}
        >
          {val}
        </Badge>
      )
    },
    {
      key: 'name',
      header: 'Strategy Name',
      sortable: true,
      render: (val, row) => (
        <div className="font-bold text-obsidian-400 dark:text-paper-100 hover:text-turquoise-mist cursor-pointer" onClick={() => viewStrategy(row.id)}>
          {val}
        </div>
      )
    },
    {
      key: 'type',
      header: 'Strategy',
      render: (val) => <Badge variant="neutral" size="sm" className="font-normal">{val}</Badge>
    },
    {
      key: 'pnlDay',
      header: 'P&L Today',
      align: 'right',
      sortable: true,
      render: (val) => (
        <span className={cn("font-mono font-medium transition-colors duration-300", val >= 0 ? "text-gain" : "text-loss")}>
          {val >= 0 ? '+' : ''}{formatCurrency(val)}
        </span>
      )
    },
    {
      key: 'pnlMtd',
      header: 'P&L MTD',
      align: 'right',
      sortable: true,
      className: "hidden lg:table-cell",
      render: (val) => (
        <span className={cn("font-mono opacity-80", val >= 0 ? "text-gain" : "text-loss")}>
          {val >= 0 ? '+' : ''}{formatCurrency(val)}
        </span>
      )
    },
    {
      key: 'winRate',
      header: 'Win Rate',
      align: 'right',
      sortable: true,
      render: (val) => <span className="font-mono text-obsidian-400/80 dark:text-paper-100/80">{val.toFixed(1)}%</span>
    },
    {
      key: 'sharpe',
      header: 'Sharpe',
      align: 'right',
      sortable: true,
      className: "hidden lg:table-cell",
      render: (val) => <span className="font-mono text-obsidian-400/80 dark:text-paper-100/80">{val.toFixed(2)}</span>
    },
    {
      key: 'openPositions',
      header: 'Pos',
      align: 'right',
      sortable: true,
      render: (val) => <span className="font-mono">{val}</span>
    },
    {
      key: 'lastSignal',
      header: 'Last Signal',
      align: 'right',
      className: "hidden md:table-cell",
      render: (val) => <span className="font-mono text-xs opacity-60">{val}</span>
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (_, row) => (
        <div className="flex justify-end gap-2">
           <Button variant="ghost" size="sm" className="h-7 w-7 p-0 rounded-full hover:bg-deep-teal-800/10 dark:hover:bg-white/10" onClick={() => viewStrategy(row.id)}>
             {row.status === 'paused' ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
           </Button>
        </div>
      )
    }
  ];

  if (isLoading) {
    return <LoadingState variant="page" message="Loading Agent Fleet..." />;
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
        {/* 1. Header */}
        <PageHeader
          title="Strategy Fleet"
          description="Real-time health and performance monitoring for all trading strategies."
          actions={
            <div className="flex items-center gap-3">
              <div className="flex bg-deep-teal-800/5 dark:bg-white/5 p-1 rounded-lg">
                 <button
                   onClick={() => setViewMode('grid')}
                   className={cn("p-1.5 rounded-md transition-colors", viewMode === 'grid' ? "bg-white dark:bg-obsidian-300 shadow-sm text-deep-teal-800 dark:text-paper-100" : "text-obsidian-400/40 dark:text-paper-100/40")}
                 >
                   <LayoutGrid className="w-4 h-4" />
                 </button>
                 <button
                   onClick={() => setViewMode('table')}
                   className={cn("p-1.5 rounded-md transition-colors", viewMode === 'table' ? "bg-white dark:bg-obsidian-300 shadow-sm text-deep-teal-800 dark:text-paper-100" : "text-obsidian-400/40 dark:text-paper-100/40")}
                 >
                   <List className="w-4 h-4" />
                 </button>
              </div>
              
              <Button variant="secondary" onClick={() => setIsExportOpen(true)} leftIcon={<Download className="w-4 h-4" />}>
                 Export
              </Button>

              <Dropdown
                trigger={<Button variant="secondary" rightIcon={<ChevronDown className="w-4 h-4" />}>Bulk Actions</Button>}
                items={[
                  { label: 'Pause All Strategies', icon: Pause },
                  { label: 'Resume All Strategies', icon: Play },
                ]}
              />
            </div>
          }
        />

        {/* 2. Error Alert Section */}
        <AnimatePresence>
          {errors.length > 0 && (
            <motion.div variants={fadeInUp} className="mb-6">
               <div className="rounded-xl border border-loss/30 bg-loss/5 overflow-hidden shadow-lg shadow-loss/5">
                  <div className="px-6 py-3 border-b border-loss/10 flex items-center justify-between bg-loss/10">
                     <div className="flex items-center gap-2 text-loss">
                        <AlertTriangle className="w-5 h-5 animate-pulse" />
                        <h3 className="font-bold text-sm uppercase tracking-wide">{errors.length} Strategies Require Attention</h3>
                     </div>
                     <div className="flex gap-2">
                        <Button variant="ghost" size="sm" className="h-7 text-xs text-loss hover:bg-loss/20 hover:text-loss border border-loss/20">Restart All</Button>
                     </div>
                  </div>
                  <div className="p-4 space-y-2">
                     {errors.map(err => (
                       <div key={err.id} className="flex items-center justify-between p-3 bg-paper-100 dark:bg-obsidian-300 rounded-lg border border-loss/20">
                          <div className="flex items-center gap-3">
                             <div className="w-2 h-2 rounded-full bg-loss animate-pulse" />
                             <span className="font-bold text-sm text-obsidian-400 dark:text-paper-100">{err.name}</span>
                             <span className="text-sm text-obsidian-400/60 dark:text-paper-100/60 font-mono border-l border-obsidian-400/10 dark:border-white/10 pl-3 ml-1 flex items-center gap-2">
                                {err.errorMessage}
                                <span className="text-[10px] opacity-60 flex items-center gap-1"><Clock className="w-3 h-3" /> 15m</span>
                             </span>
                          </div>
                          <div className="flex gap-2">
                             <Button variant="secondary" size="sm" className="h-7 text-xs">View Logs</Button>
                             <Button variant="secondary" size="sm" className="h-7 text-xs text-loss hover:bg-loss/10 border-loss/20">Disable</Button>
                          </div>
                       </div>
                     ))}
                  </div>
               </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 3. System Summary Bar */}
        <motion.div variants={fadeInUp}>
           <GlassCard padding="none" className="flex flex-col md:flex-row items-stretch sticky top-20 z-30 shadow-xl overflow-hidden mb-6">
              {/* Counts Section */}
              <div className="flex-1 flex divide-x divide-deep-teal-800/5 dark:divide-white/10 bg-paper-100/50 dark:bg-white/5 backdrop-blur-md">
                 <div className="flex-1 p-3 flex flex-col items-center justify-center">
                    <span className="text-[9px] uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-1">Total</span>
                    <span className="text-xl font-mono font-medium">{metrics.total}</span>
                 </div>
                 <div className="flex-1 p-3 flex flex-col items-center justify-center bg-gain/5">
                    <span className="text-[9px] uppercase tracking-widest text-gain mb-1">Active</span>
                    <span className="text-xl font-mono font-bold text-gain">{metrics.active}</span>
                 </div>
                 <div className="flex-1 p-3 flex flex-col items-center justify-center">
                    <span className="text-[9px] uppercase tracking-widest text-warning mb-1">Paused</span>
                    <span className="text-xl font-mono font-medium text-warning">{metrics.paused}</span>
                 </div>
                 <div className="flex-1 p-3 flex flex-col items-center justify-center">
                    <span className="text-[9px] uppercase tracking-widest text-info mb-1">Training</span>
                    <span className="text-xl font-mono font-medium text-info">{metrics.training}</span>
                 </div>
                 <div className="flex-1 p-3 flex flex-col items-center justify-center">
                    <span className="text-[9px] uppercase tracking-widest text-loss mb-1">Error</span>
                    <span className={cn("text-xl font-mono font-medium text-loss", metrics.error > 0 && "animate-pulse")}>{metrics.error}</span>
                 </div>
              </div>

              {/* Financials Section */}
              <div className="flex-none flex items-center gap-6 px-6 py-3 border-t md:border-t-0 md:border-l border-deep-teal-800/5 dark:border-white/10 bg-paper-100/80 dark:bg-obsidian-300/80">
                 <div>
                    <span className="text-[9px] uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 block mb-1">Combined P&L Today</span>
                    <span className={cn("text-lg font-mono font-bold block", metrics.pnlToday >= 0 ? "text-gain" : "text-loss")}>
                       {metrics.pnlToday >= 0 ? '+' : ''}{formatCurrency(metrics.pnlToday)}
                    </span>
                 </div>
                 <div className="w-px h-8 bg-deep-teal-800/10 dark:bg-white/10" />
                 <div>
                    <span className="text-[9px] uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 block mb-1">Open Pos</span>
                    <span className="text-lg font-mono font-medium block">{metrics.openPositions}</span>
                 </div>
              </div>
           </GlassCard>
        </motion.div>

        {/* 4. Filters Row */}
        <motion.div variants={fadeInUp} className="flex flex-col md:flex-row gap-4 items-center">
           <div className="w-full md:w-auto md:flex-1">
              <SearchInput 
                 placeholder="Search by agent name..." 
                 value={search} 
                 onChange={e => setSearch(e.target.value)}
                 className="bg-paper-100 dark:bg-white/5 border-transparent h-10"
              />
           </div>
           <div className="flex gap-2 w-full md:w-auto overflow-x-auto pb-2 md:pb-0 no-scrollbar">
              <Dropdown 
                 trigger={<Button variant="secondary" className="bg-paper-100 dark:bg-white/5 border-transparent h-10 px-4 whitespace-nowrap" rightIcon={<ChevronDown className="w-4 h-4" />}>Status: {filterStatus}</Button>}
                 items={['All', 'Active', 'Paused', 'Training', 'Error'].map(s => ({ label: s, onClick: () => setFilterStatus(s) }))}
              />
              <Dropdown 
                 trigger={<Button variant="secondary" className="bg-paper-100 dark:bg-white/5 border-transparent h-10 px-4 whitespace-nowrap" rightIcon={<ChevronDown className="w-4 h-4" />}>Strategy: {filterStrategy}</Button>}
                 items={['All', ...STRATEGIES].map(s => ({ label: s.charAt(0).toUpperCase() + s.slice(1), onClick: () => setFilterStrategy(s) }))}
              />
              <Dropdown 
                 trigger={<Button variant="secondary" className="bg-paper-100 dark:bg-white/5 border-transparent h-10 px-4 whitespace-nowrap" rightIcon={<ChevronDown className="w-4 h-4" />}>Sort: {sortBy}</Button>}
                 items={['Name', 'P&L Today', 'Win Rate', 'Status'].map(s => ({ label: s, onClick: () => setSortBy(s) }))}
              />
           </div>
        </motion.div>

        {/* 5. Main Content */}
        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">

           {/* Strategy Grid/Table */}
           <div className="xl:col-span-3 space-y-6">
              {filteredStrategies.length === 0 ? (
                <EmptyState
                  title="No strategies found"
                  description="Try adjusting your filters or search terms."
                  variant="search"
                  action={
                    <Button variant="secondary" onClick={() => { setSearch(''); setFilterStatus('All'); setFilterStrategy('All'); }}>
                      Clear Filters
                    </Button>
                  }
                />
              ) : (
                <AnimatePresence mode="wait">
                   {viewMode === 'grid' ? (
                      <motion.div
                         key="grid"
                         variants={staggerContainer}
                         initial="initial"
                         animate="animate"
                         exit={{ opacity: 0 }}
                         className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4"
                      >
                         {filteredStrategies.map(strategy => (
                            <StrategyCompactCard
                               key={strategy.id}
                               strategy={strategy}
                               onClick={() => viewStrategy(strategy.id)}
                               isTopPerformer={topPerformerIds.includes(strategy.id)}
                            />
                         ))}
                      </motion.div>
                   ) : (
                      <motion.div
                         key="table"
                         initial={{ opacity: 0 }}
                         animate={{ opacity: 1 }}
                         exit={{ opacity: 0 }}
                      >
                         <GlassCard padding="none" className="overflow-hidden">
                            <DataTable columns={columns} data={filteredStrategies} onRowClick={(row) => viewStrategy(row.id)} />
                         </GlassCard>
                      </motion.div>
                   )}
                </AnimatePresence>
              )}
           </div>

           {/* Right Sidebar: Performance Summary */}
           <div className="space-y-6">
              
              {/* Top Performers */}
              <motion.div variants={fadeInUp}>
                 <GlassCard className="flex flex-col gap-0 overflow-hidden" padding="none">
                    <div className="px-5 py-4 border-b border-deep-teal-800/5 dark:border-white/5 flex items-center justify-between bg-deep-teal-800/5 dark:bg-white/5">
                       <div className="flex items-center gap-2">
                          <Trophy className="w-4 h-4 text-warning" />
                          <h3 className="font-display text-sm font-medium">Top Performers Today</h3>
                       </div>
                    </div>
                    <div className="divide-y divide-deep-teal-800/5 dark:divide-white/5">
                       {topPerformersList.map((strategy, i) => (
                          <div key={strategy.id} className="flex items-center justify-between p-4 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors cursor-pointer group" onClick={() => viewStrategy(strategy.id)}>
                             <div className="flex items-center gap-3">
                                <div className={cn(
                                   "w-6 h-6 flex items-center justify-center rounded-full text-[10px] font-bold border",
                                   i === 0 ? "bg-yellow-500/10 text-yellow-600 border-yellow-500/30" :
                                   i === 1 ? "bg-slate-400/10 text-slate-500 border-slate-400/30" :
                                   "bg-orange-700/10 text-orange-700 border-orange-700/30"
                                )}>
                                   {i + 1}
                                </div>
                                <div className="min-w-0">
                                   <div className="text-sm font-medium truncate w-32 group-hover:text-turquoise-mist transition-colors">{strategy.name}</div>
                                   <div className="text-[10px] opacity-50">{strategy.type}</div>
                                </div>
                             </div>
                             <span className="font-mono text-sm font-bold text-gain">+{formatCurrency(strategy.pnlDay)}</span>
                          </div>
                       ))}
                    </div>
                 </GlassCard>
              </motion.div>

              {/* Needs Attention */}
              <motion.div variants={fadeInUp}>
                 <GlassCard className="flex flex-col gap-0 overflow-hidden" padding="none">
                    <div className="px-5 py-4 border-b border-deep-teal-800/5 dark:border-white/5 flex items-center justify-between bg-deep-teal-800/5 dark:bg-white/5">
                       <div className="flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-loss" />
                          <h3 className="font-display text-sm font-medium">Needs Attention</h3>
                       </div>
                    </div>
                    <div className="divide-y divide-deep-teal-800/5 dark:divide-white/5">
                       {attentionList.map((strategy) => (
                          <div key={strategy.id} className="flex items-center justify-between p-4 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors cursor-pointer group" onClick={() => viewStrategy(strategy.id)}>
                             <div className="flex items-center gap-3">
                                <div className="w-6 h-6 flex items-center justify-center rounded-full bg-loss/10 text-loss">
                                   <TrendingDown className="w-3 h-3" />
                                </div>
                                <div className="min-w-0">
                                   <div className="text-sm font-medium truncate w-32 group-hover:text-loss transition-colors">{strategy.name}</div>
                                   <div className="text-[10px] opacity-50">{strategy.type}</div>
                                </div>
                             </div>
                             <span className="font-mono text-sm font-bold text-loss">{formatCurrency(strategy.pnlDay)}</span>
                          </div>
                       ))}
                    </div>
                 </GlassCard>
              </motion.div>

              {/* Quick Action - Deploy */}
              <motion.div variants={fadeInUp}>
                 <GlassCard variant="subtle" className="p-5 flex flex-col items-center text-center gap-3 border-dashed border-2 border-deep-teal-800/10 dark:border-white/10 hover:border-turquoise-mist transition-colors cursor-pointer group">
                    <div className="p-3 rounded-full bg-paper-200 dark:bg-white/5 group-hover:bg-turquoise-mist/10 group-hover:text-turquoise-mist transition-colors">
                       <Plus className="w-6 h-6 opacity-60" />
                    </div>
                    <div>
                       <h4 className="font-medium text-sm">Deploy New Strategy</h4>
                       <p className="text-xs opacity-60 mt-1">Configure strategy from template</p>
                    </div>
                 </GlassCard>
              </motion.div>

           </div>

        </div>

        <ExportModal
          isOpen={isExportOpen}
          onClose={() => setIsExportOpen(false)}
          onExport={handleExport}
          title="Export Strategy Performance"
        />

      </motion.div>
    </ErrorBoundary>
  );
};
