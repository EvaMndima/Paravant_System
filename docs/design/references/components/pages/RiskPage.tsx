
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  ShieldAlert, AlertTriangle, Activity, 
  TrendingDown, TrendingUp, PieChart, Layers, 
  Info, CheckCircle2, Zap, Download
} from 'lucide-react';

import { PageHeader } from '../layout/PageHeader';
import { GlassCard } from '../ui/GlassCard';
import { MetricCard } from '../ui/MetricCard';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Progress } from '../ui/Progress';
import { SparklineChart } from '../dashboard/charts/SparklineChart';
import { DonutChart } from '../dashboard/charts/DonutChart';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/Tabs';
import { ExportModal, ExportConfig } from '../dashboard/ExportModal';
import { useToast } from '../../contexts/ToastContext';
import { cn } from '../../lib/utils';
import { staggerContainer, fadeInUp } from '../../lib/animations';

// --- Types ---

interface RiskMetric {
  title: string;
  value: number;
  suffix?: string;
  prefix?: string;
  trend: number;
  data: number[];
  format: 'number' | 'percent' | 'currency';
  inverse?: boolean;
}

interface ConcentrationItem {
  symbol: string;
  name: string;
  weight: number;
  riskLevel: 'low' | 'medium' | 'high';
}

// --- Mock Data ---

const riskMetrics: RiskMetric[] = [
  {
    title: 'Portfolio Beta',
    value: 1.15,
    trend: 0.05,
    data: [1.10, 1.12, 1.08, 1.14, 1.15, 1.18, 1.15],
    format: 'number',
    inverse: true 
  },
  {
    title: 'Sharpe Ratio',
    value: 2.42,
    trend: 0.12,
    data: [2.1, 2.2, 2.15, 2.3, 2.35, 2.4, 2.42],
    format: 'number',
    inverse: false
  },
  {
    title: 'Sortino Ratio',
    value: 3.15,
    trend: -0.05,
    data: [3.3, 3.25, 3.2, 3.18, 3.15, 3.12, 3.15],
    format: 'number',
    inverse: false
  },
  {
    title: 'Max Drawdown',
    value: -12.5,
    suffix: '%',
    trend: -1.2, 
    data: [-15, -14.5, -14, -13.2, -12.8, -12.5, -12.5],
    format: 'number',
    inverse: false 
  },
  {
    title: 'Value at Risk (95%)',
    value: 15200,
    prefix: '$',
    trend: 450,
    data: [14000, 14200, 14500, 14800, 15000, 15100, 15200],
    format: 'currency',
    inverse: true
  }
];

const sectorExposure = [
  { name: 'Technology', value: 45, color: '#2A9D8F' }, 
  { name: 'Financials', value: 20, color: '#0F3D3E' }, 
  { name: 'Healthcare', value: 15, color: '#E9C46A' }, 
  { name: 'Consumer', value: 10, color: '#F4A261' },   
  { name: 'Crypto', value: 10, color: '#E76F51' },     
];

const geoExposure = [
  { name: 'North America', value: 65, color: '#2A9D8F' },
  { name: 'Europe', value: 20, color: '#264653' },
  { name: 'Emerging Mkts', value: 10, color: '#E9C46A' },
  { name: 'Asia Pacific', value: 5, color: '#F4A261' },
];

const topConcentration: ConcentrationItem[] = [
  { symbol: 'NVDA', name: 'NVIDIA Corp', weight: 24.5, riskLevel: 'high' },
  { symbol: 'MSFT', name: 'Microsoft Corp', weight: 18.2, riskLevel: 'high' },
  { symbol: 'BTC', name: 'Bitcoin', weight: 15.8, riskLevel: 'high' },
  { symbol: 'AAPL', name: 'Apple Inc', weight: 12.1, riskLevel: 'medium' },
  { symbol: 'USD', name: 'US Dollar', weight: 10.5, riskLevel: 'medium' },
  { symbol: 'TSLA', name: 'Tesla Inc', weight: 8.5, riskLevel: 'medium' },
  { symbol: 'GOOGL', name: 'Alphabet Inc', weight: 5.4, riskLevel: 'low' },
];

const correlationMatrix = {
  labels: ['NVDA', 'MSFT', 'BTC', 'AAPL', 'TSLA', 'GOOGL'],
  values: [
    [1.00, 0.78, 0.45, 0.65, 0.55, 0.72],
    [0.78, 1.00, 0.32, 0.72, 0.48, 0.81],
    [0.45, 0.32, 1.00, 0.25, 0.60, 0.35],
    [0.65, 0.72, 0.25, 1.00, 0.42, 0.68],
    [0.55, 0.48, 0.60, 0.42, 1.00, 0.45],
    [0.72, 0.81, 0.35, 0.68, 0.45, 1.00],
  ]
};

const riskAlerts = [
  { id: 1, type: 'danger', message: 'Portfolio concentration in Technology exceeds 40% limit.', time: '2h ago' },
  { id: 2, type: 'danger', message: 'NVDA position weight (24.5%) violates single-asset limit of 20%.', time: '4h ago' },
  { id: 3, type: 'warning', message: 'Correlation between BTC and Tech sector is rising (0.65).', time: '1d ago' },
  { id: 4, type: 'info', message: 'Portfolio Beta increased by 0.05 this week, indicating higher sensitivity.', time: '2d ago' },
];

// --- Sub-Components ---

const CorrelationHeatmap = () => {
  return (
    <div className="overflow-x-auto custom-scrollbar">
      <div className="min-w-[400px]">
        {/* Header Row */}
        <div className="grid grid-cols-7 gap-1 mb-1">
          <div className="h-8"></div> {/* Empty corner */}
          {correlationMatrix.labels.map(label => (
            <div key={label} className="h-8 flex items-center justify-center font-bold font-sans text-[10px] text-obsidian-400 dark:text-paper-100">
              {label}
            </div>
          ))}
        </div>

        {/* Matrix Rows */}
        {correlationMatrix.values.map((row, i) => (
          <div key={i} className="grid grid-cols-7 gap-1 mb-1">
            {/* Row Label */}
            <div className="h-8 flex items-center justify-start pl-2 font-bold font-sans text-[10px] text-obsidian-400 dark:text-paper-100">
              {correlationMatrix.labels[i]}
            </div>
            
            {/* Cells */}
            {row.map((value, j) => {
              const isDiagonal = i === j;
              let bgStyle = {};
              let textClass = "";

              if (isDiagonal) {
                bgStyle = { backgroundColor: 'transparent', border: '1px solid rgba(15, 61, 62, 0.1)' };
                textClass = "text-obsidian-400/20 dark:text-paper-100/20 font-light";
              } else {
                if (value > 0.7) {
                   const opacity = (value - 0.5) * 2;
                   bgStyle = { backgroundColor: `rgba(231, 76, 60, ${opacity * 0.3})` };
                   textClass = "text-loss font-bold";
                } else if (value < 0.3) {
                   const opacity = (0.5 - value) * 2;
                   bgStyle = { backgroundColor: `rgba(46, 204, 113, ${opacity * 0.3})` };
                   textClass = "text-gain font-bold";
                } else {
                   bgStyle = { backgroundColor: `rgba(243, 156, 18, 0.1)` };
                   textClass = "text-warning";
                }
              }

              return (
                <div 
                  key={j} 
                  className={cn(
                    "h-8 flex items-center justify-center rounded-md text-[10px] font-mono transition-all hover:scale-105 cursor-default",
                    textClass
                  )}
                  style={bgStyle}
                >
                  {value.toFixed(2)}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};

// --- Main Component ---

export const RiskPage = () => {
  const [isExportOpen, setIsExportOpen] = useState(false);
  const { toast } = useToast();

  const handleExport = (config: ExportConfig) => {
    toast({
      title: 'Export Started',
      description: `Generating ${config.format.toUpperCase()} report from ${config.startDate} to ${config.endDate}...`,
      type: 'info'
    });
  };

  return (
    <motion.div
      initial="initial"
      animate="animate"
      exit={{ opacity: 0 }}
      variants={staggerContainer}
      className="space-y-8 pt-2 pb-10"
    >
      {/* 1. Header */}
      <PageHeader
        title="Risk Management"
        description="Comprehensive analysis of portfolio exposure, volatility, and concentration risks."
        actions={
          <div className="flex gap-3">
             <Button variant="secondary" size="sm" leftIcon={<Download className="w-4 h-4" />} onClick={() => setIsExportOpen(true)}>
               Export
             </Button>
             <Button variant="secondary" size="sm" leftIcon={<Zap className="w-4 h-4" />}>
               Stress Test
             </Button>
             <Badge variant="outline" className="gap-2 px-3 py-1.5 h-auto border-warning/30 bg-warning/5 text-warning">
                <ShieldAlert className="w-4 h-4" />
                <span className="text-sm font-medium">Risk Level: Elevated</span>
             </Badge>
          </div>
        }
      />

      {/* 2. Metrics Row - Adjusted Grid for Better Fit */}
      <motion.div variants={fadeInUp} className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        {riskMetrics.map((metric, i) => (
          <MetricCard
            key={metric.title}
            title={metric.title}
            value={metric.value}
            suffix={metric.suffix}
            prefix={metric.prefix}
            change={metric.trend}
            changeLabel="30d trend"
            variant="default"
            delay={i * 0.05}
            format={metric.format as any}
            sparkline={
              <SparklineChart 
                data={metric.data} 
                color={metric.inverse 
                  ? (metric.trend > 0 ? 'loss' : 'gain') 
                  : (metric.trend >= 0 ? 'gain' : 'loss')
                } 
                height="100%"
                showArea={true}
              />
            }
          />
        ))}
      </motion.div>

      {/* 3. Main Layout: Two Column Stack (Masonry Style) */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
        
        {/* Left Column Stack */}
        <div className="space-y-6 flex flex-col">
            
            {/* Portfolio Composition */}
            <motion.div variants={fadeInUp} className="w-full">
               <GlassCard className="flex flex-col" padding="none">
                 <Tabs defaultValue="sector" className="flex flex-col">
                   <div className="px-6 py-5 border-b border-deep-teal-800/5 dark:border-white/5 flex items-center justify-between">
                     <div className="flex items-center gap-2">
                       <PieChart className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
                       <h3 className="font-display text-lg font-medium text-obsidian-400 dark:text-paper-100">Portfolio Composition</h3>
                     </div>
                     <TabsList variant="pill">
                       <TabsTrigger value="sector">Sector</TabsTrigger>
                       <TabsTrigger value="geo">Geography</TabsTrigger>
                     </TabsList>
                   </div>
                   
                   <div className="p-6">
                      <TabsContent value="sector" className="mt-0 grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
                         <div className="h-[200px] flex items-center justify-center">
                            <DonutChart 
                                data={sectorExposure} 
                                height={200} 
                                innerRadius="65%" 
                                outerRadius="90%" 
                                showLegend={false} 
                            />
                         </div>
                         <div className="space-y-1">
                            <div className="flex justify-between items-center px-3 mb-2 text-[10px] font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
                                 <span>Category</span>
                                 <span>Allocation</span>
                            </div>
                            <div className="space-y-1">
                               {sectorExposure.map(item => (
                                  <div key={item.name} className="flex items-center justify-between p-2 rounded-lg hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors group cursor-default">
                                     <div className="flex items-center gap-3">
                                        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: item.color }} />
                                        <span className="text-sm font-sans font-medium text-obsidian-400 dark:text-paper-100">{item.name}</span>
                                     </div>
                                     <span className="font-mono text-sm font-bold text-obsidian-400 dark:text-paper-100 group-hover:text-deep-teal-800 dark:group-hover:text-turquoise-mist transition-colors">{item.value}%</span>
                                  </div>
                               ))}
                            </div>
                         </div>
                      </TabsContent>
    
                      <TabsContent value="geo" className="mt-0 grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
                         <div className="h-[200px] flex items-center justify-center">
                            <DonutChart 
                                data={geoExposure} 
                                height={200} 
                                innerRadius="65%" 
                                outerRadius="90%" 
                                showLegend={false} 
                            />
                         </div>
                         <div className="space-y-1">
                            <div className="flex justify-between items-center px-3 mb-2 text-[10px] font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
                                 <span>Region</span>
                                 <span>Allocation</span>
                            </div>
                            <div className="space-y-1">
                               {geoExposure.map(item => (
                                  <div key={item.name} className="flex items-center justify-between p-2 rounded-lg hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors group cursor-default">
                                     <div className="flex items-center gap-3">
                                        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: item.color }} />
                                        <span className="text-sm font-sans font-medium text-obsidian-400 dark:text-paper-100">{item.name}</span>
                                     </div>
                                     <span className="font-mono text-sm font-bold text-obsidian-400 dark:text-paper-100 group-hover:text-deep-teal-800 dark:group-hover:text-turquoise-mist transition-colors">{item.value}%</span>
                                  </div>
                               ))}
                            </div>
                         </div>
                      </TabsContent>
                   </div>
                 </Tabs>
               </GlassCard>
            </motion.div>

            {/* Correlation Matrix - Stacked under Composition */}
            <motion.div variants={fadeInUp} className="w-full">
               <GlassCard className="flex flex-col">
                  <div className="mb-4 flex items-start justify-between">
                     <div>
                        <div className="flex items-center gap-2 mb-1">
                          <Activity className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
                          <h3 className="font-display text-lg text-obsidian-400 dark:text-paper-100">Correlation Matrix</h3>
                        </div>
                        <p className="text-sm text-obsidian-400/60 dark:text-paper-100/60">
                          Pearson correlation coefficients (30D rolling)
                        </p>
                     </div>
                  </div>
                  <div className="flex justify-center">
                     <CorrelationHeatmap />
                  </div>
               </GlassCard>
            </motion.div>
        </div>

        {/* Right Column Stack */}
        <div className="space-y-6 flex flex-col">
            
            {/* Concentration Risk */}
            <motion.div variants={fadeInUp} className="w-full">
              <GlassCard className="flex flex-col gap-6">
                 <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Layers className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
                      <h3 className="font-display text-lg text-obsidian-400 dark:text-paper-100">Concentration</h3>
                    </div>
                    <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50">
                       Holding weight vs 10% soft limit
                    </p>
                 </div>
    
                 <div className="space-y-5">
                   {topConcentration.map((item, i) => {
                     const isHighRisk = item.weight > 15;
                     const isMedRisk = item.weight > 10;
                     const variant = isHighRisk ? 'danger' : isMedRisk ? 'warning' : 'success';
                     
                     return (
                       <div key={item.symbol} className="space-y-1.5">
                         <div className="flex justify-between items-end text-sm">
                           <div className="flex items-center gap-2">
                              <span className="font-bold font-mono text-obsidian-400 dark:text-paper-100">{item.symbol}</span>
                           </div>
                           <div className="flex items-center gap-2">
                               <span className={cn(
                                   "text-xs font-bold", 
                                   isHighRisk ? "text-loss" : isMedRisk ? "text-warning" : "text-gain"
                               )}>
                                   {isHighRisk ? 'High' : isMedRisk ? 'Med' : 'OK'}
                               </span>
                               <span className="font-mono font-medium w-10 text-right">{item.weight}%</span>
                           </div>
                         </div>
                         <Progress value={item.weight} max={25} variant={variant} size="sm" showLabel={false} />
                       </div>
                     );
                   })}
                 </div>
                 
                 <div className="pt-2 flex justify-between items-center text-xs text-obsidian-400/50 dark:text-paper-100/50 border-t border-deep-teal-800/5 dark:border-white/5 mt-2">
                    <span>HHI Index</span>
                    <span className="font-mono">1,420 (Moderate)</span>
                 </div>
              </GlassCard>
            </motion.div>

            {/* Active Alerts - Stacked under Concentration */}
            <motion.div variants={fadeInUp} className="w-full">
               <GlassCard className="flex flex-col" padding="none">
                  <div className="px-5 py-4 border-b border-deep-teal-800/5 dark:border-white/5 flex items-center justify-between bg-deep-teal-800/5 dark:bg-white/5">
                     <h3 className="font-display text-base font-medium text-obsidian-400 dark:text-paper-100">Active Alerts</h3>
                     <Badge variant="danger" dot pulsing>4 Issues</Badge>
                  </div>
                  
                  <div className="p-4 space-y-3">
                     {riskAlerts.map(alert => (
                       <div key={alert.id} className="group relative p-3 rounded-xl border border-deep-teal-800/5 dark:border-white/5 bg-paper-100 dark:bg-obsidian-300 hover:bg-paper-200 dark:hover:bg-obsidian-300/80 transition-colors">
                          <div className="flex gap-3">
                              <div className="mt-0.5 shrink-0">
                                  {alert.type === 'danger' ? (
                                      <AlertTriangle className="w-4 h-4 text-loss" />
                                  ) : alert.type === 'warning' ? (
                                      <AlertTriangle className="w-4 h-4 text-warning" />
                                  ) : (
                                      <Info className="w-4 h-4 text-info" />
                                  )}
                              </div>
                              <div className="space-y-1">
                                  <p className="text-xs text-obsidian-400 dark:text-paper-100 font-medium leading-relaxed">
                                      {alert.message}
                                  </p>
                                  <div className="flex items-center gap-2">
                                     <span className={cn(
                                         "text-[10px] font-bold uppercase tracking-wider",
                                         alert.type === 'danger' ? 'text-loss' : alert.type === 'warning' ? 'text-warning' : 'text-info'
                                     )}>
                                         {alert.type === 'danger' ? 'Critical' : alert.type === 'warning' ? 'Warning' : 'Info'}
                                     </span>
                                     <span className="text-[10px] text-obsidian-400/40 dark:text-paper-100/40 font-mono">
                                         {alert.time}
                                     </span>
                                  </div>
                              </div>
                          </div>
                       </div>
                     ))}
                  </div>
               </GlassCard>
            </motion.div>
        </div>

      </div>

      <ExportModal 
        isOpen={isExportOpen} 
        onClose={() => setIsExportOpen(false)} 
        onExport={handleExport}
        title="Export Risk Analysis"
      />

    </motion.div>
  );
};
