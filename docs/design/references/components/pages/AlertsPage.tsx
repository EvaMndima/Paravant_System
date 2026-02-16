
import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Bell, AlertTriangle, ShieldAlert, Activity, 
  TrendingUp, TrendingDown, Clock, Search, Filter,
  CheckCircle2, XCircle, MoreHorizontal, ArrowRight,
  Zap, Server, Wifi, Volume2, VolumeX, Trash2, Edit2,
  Eye, Download
} from 'lucide-react';

import { PageHeader } from '../layout/PageHeader';
import { GlassCard } from '../ui/GlassCard';
import { MetricCard } from '../ui/MetricCard';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/Tabs';
import { SearchInput } from '../ui/SearchInput';
import { DataTable, Column } from '../dashboard/DataTable';
import { Progress } from '../ui/Progress';
import { Dropdown } from '../ui/Dropdown';
import { EmptyState } from '../ui/EmptyState';
import { ErrorBoundary } from '../ui/ErrorBoundary';
import { ExportModal, ExportConfig } from '../dashboard/ExportModal';
import { useDashboard } from '../../contexts/DashboardContext';
import { cn, formatCurrency, formatNumber } from '../../lib/utils';
import { staggerContainer, fadeInUp, smoothSpring } from '../../lib/animations';
import { useToast } from '../../contexts/ToastContext';

// --- Types ---

interface PriceAlert {
  id: string;
  symbol: string;
  currentPrice: number;
  targetPrice: number;
  condition: 'Above' | 'Below' | 'Change %';
  status: 'Active' | 'Near Trigger' | 'Muted';
  created: string;
  agent?: string;
}

interface RiskAlert {
  id: string;
  type: 'Position Limit' | 'Drawdown' | 'Correlation' | 'Exposure';
  message: string;
  severity: 'Warning' | 'Critical';
  triggeredAt: string;
  status: 'Active' | 'Acknowledged' | 'Resolved';
}

interface SystemAlert {
  id: string;
  type: 'Connection' | 'Latency' | 'Error' | 'Maintenance';
  message: string;
  status: 'Active' | 'Resolved';
  duration: string;
  timestamp: string;
}

interface AlertHistory {
  id: string;
  timestamp: Date;
  type: string;
  details: string;
  triggerValue: string;
  actionTaken: string;
  outcome: string;
}

// --- Mock Data ---

const mockPriceAlerts: PriceAlert[] = [
  { id: '1', symbol: 'NVDA', currentPrice: 890.25, targetPrice: 900.00, condition: 'Above', status: 'Near Trigger', created: '2 hours ago', agent: 'Alpha Seeker' },
  { id: '2', symbol: 'BTC', currentPrice: 67500.00, targetPrice: 65000.00, condition: 'Below', status: 'Active', created: '1 day ago' },
  { id: '3', symbol: 'TSLA', currentPrice: 175.40, targetPrice: 185.00, condition: 'Above', status: 'Active', created: '3 days ago', agent: 'Momentum Prime' },
  { id: '4', symbol: 'AAPL', currentPrice: 172.50, targetPrice: 168.00, condition: 'Below', status: 'Muted', created: '5 days ago' },
  { id: '5', symbol: 'ETH', currentPrice: 3850.50, targetPrice: 4000.00, condition: 'Above', status: 'Active', created: '1 week ago' },
  { id: '6', symbol: 'AMD', currentPrice: 180.40, targetPrice: 190.00, condition: 'Above', status: 'Active', created: '2 days ago' },
  { id: '7', symbol: 'MSFT', currentPrice: 425.10, targetPrice: 415.00, condition: 'Below', status: 'Active', created: '4 hours ago' },
];

const mockRiskAlerts: RiskAlert[] = [
  { id: '1', type: 'Position Limit', message: 'NVDA position approaching 25% portfolio limit (currently 24.5%)', severity: 'Critical', triggeredAt: '10 mins ago', status: 'Active' },
  { id: '2', type: 'Correlation', message: 'High correlation (0.85) detected between Tech Sector and Crypto holdings', severity: 'Warning', triggeredAt: '2 hours ago', status: 'Active' },
  { id: '3', type: 'Drawdown', message: 'Momentum Prime agent daily drawdown exceeds 2% threshold', severity: 'Warning', triggeredAt: '4 hours ago', status: 'Acknowledged' },
  { id: '4', type: 'Exposure', message: 'Net long exposure increased to 85% in high volatility regime', severity: 'Warning', triggeredAt: 'Yesterday', status: 'Resolved' },
];

const mockSystemAlerts: SystemAlert[] = [
  { id: '1', type: 'Latency', message: 'Market data feed latency exceeded 100ms (peak 145ms)', status: 'Active', duration: '5 min', timestamp: 'Just now' },
  { id: '2', type: 'Connection', message: 'Reconnected to IBKR Brokerage API after intermittent packet loss', status: 'Resolved', duration: '2 min', timestamp: '1 hour ago' },
  { id: '3', type: 'Maintenance', message: 'Scheduled database maintenance completed successfully', status: 'Resolved', duration: '15 min', timestamp: 'Yesterday' },
];

const mockHistory: AlertHistory[] = Array.from({ length: 15 }).map((_, i) => ({
  id: `HIST-${i}`,
  timestamp: new Date(Date.now() - i * 1000 * 60 * 60 * 2),
  type: i % 3 === 0 ? 'Price Alert' : i % 3 === 1 ? 'Risk Warning' : 'System Event',
  details: i % 3 === 0 ? `NVDA crossed $${850 + i}` : i % 3 === 1 ? 'Portfolio Beta > 1.2' : 'API Latency Spike',
  triggerValue: i % 3 === 0 ? `$${850 + i}` : '1.25',
  actionTaken: i % 2 === 0 ? 'Notification sent' : 'Agent paused',
  outcome: 'Acknowledged'
}));

// --- Sub-Components ---

const PriceAlertCard: React.FC<{ alert: PriceAlert }> = ({ alert }) => {
  const isNear = alert.status === 'Near Trigger';
  const isMuted = alert.status === 'Muted';
  
  // Calculate percentage closeness for visual bar
  // (Simplified logic for demo visuals)
  const diff = Math.abs(alert.targetPrice - alert.currentPrice);
  const totalRange = alert.targetPrice * 0.1; // Assume range is 10% of price
  const percentClose = Math.max(0, Math.min(100, 100 - (diff / totalRange * 100)));

  return (
    <GlassCard 
      variant="subtle" 
      padding="sm" 
      className={cn(
        "group relative flex flex-col gap-3 transition-all border",
        isNear ? "border-warning/30 bg-warning/5" : isMuted ? "opacity-60 border-transparent" : "border-deep-teal-800/5 dark:border-white/5 hover:border-deep-teal-800/20 dark:hover:border-white/20"
      )}
    >
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-deep-teal-800/5 dark:bg-white/5 flex items-center justify-center font-bold text-xs">
            {alert.symbol[0]}
          </div>
          <div>
            <div className="font-bold text-sm text-obsidian-400 dark:text-paper-100 flex items-center gap-2">
              {alert.symbol}
              {alert.agent && <Badge variant="neutral" size="sm" className="h-4 px-1 text-[9px] opacity-70">Auto</Badge>}
            </div>
            <div className="text-xs font-mono opacity-60">{formatCurrency(alert.currentPrice)}</div>
          </div>
        </div>
        <div className="text-right">
           <Badge 
             variant={isNear ? 'warning' : isMuted ? 'neutral' : 'success'} 
             size="sm" 
             className="text-[10px]"
             dot={isNear || alert.status === 'Active'}
             pulsing={isNear}
           >
             {alert.status}
           </Badge>
        </div>
      </div>

      <div className="space-y-1.5">
        <div className="flex justify-between text-xs font-medium">
           <span className="opacity-70 flex items-center gap-1">
             {alert.condition === 'Above' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
             {alert.condition} {formatCurrency(alert.targetPrice)}
           </span>
           <span className="font-mono opacity-50">{percentClose.toFixed(0)}% Close</span>
        </div>
        <div className="h-1.5 w-full bg-deep-teal-800/5 dark:bg-white/5 rounded-full overflow-hidden">
           <motion.div 
             initial={{ width: 0 }}
             animate={{ width: `${percentClose}%` }}
             className={cn("h-full rounded-full", isNear ? "bg-warning" : "bg-deep-teal-800 dark:bg-turquoise-mist")}
           />
        </div>
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-deep-teal-800/5 dark:border-white/5 mt-1">
         <span className="text-[10px] opacity-40">{alert.created}</span>
         <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button className="p-1 hover:bg-deep-teal-800/10 dark:hover:bg-white/10 rounded" title="Edit"><Edit2 className="w-3 h-3" /></button>
            <button className="p-1 hover:bg-deep-teal-800/10 dark:hover:bg-white/10 rounded" title="Mute/Unmute">
               {isMuted ? <Volume2 className="w-3 h-3" /> : <VolumeX className="w-3 h-3" />}
            </button>
            <button className="p-1 hover:bg-loss/10 hover:text-loss rounded" title="Delete"><Trash2 className="w-3 h-3" /></button>
         </div>
      </div>
    </GlassCard>
  );
};

const RiskAlertRow: React.FC<{ alert: RiskAlert }> = ({ alert }) => {
  const isCritical = alert.severity === 'Critical';
  
  return (
    <div className={cn(
      "flex items-start gap-4 p-4 rounded-xl border transition-all",
      isCritical ? "bg-loss/5 border-loss/20" : "bg-warning/5 border-warning/20",
      alert.status === 'Resolved' && "opacity-60 grayscale bg-transparent border-deep-teal-800/5 dark:border-white/5"
    )}>
       <div className={cn("p-2 rounded-lg shrink-0", isCritical ? "bg-loss/10 text-loss" : "bg-warning/10 text-warning")}>
          <ShieldAlert className="w-5 h-5" />
       </div>
       <div className="flex-1 space-y-1">
          <div className="flex justify-between items-start">
             <h4 className="font-bold text-sm text-obsidian-400 dark:text-paper-100">{alert.type} Alert</h4>
             <span className="text-[10px] font-mono opacity-50">{alert.triggeredAt}</span>
          </div>
          <p className="text-xs text-obsidian-400/80 dark:text-paper-100/80 leading-relaxed">{alert.message}</p>
          <div className="flex gap-2 pt-2">
             {alert.status !== 'Resolved' && (
                <>
                  <Button size="sm" variant="ghost" className="h-6 text-[10px] bg-white/50 dark:bg-black/20 hover:bg-white dark:hover:bg-black/40">Acknowledge</Button>
                  <Button size="sm" variant="ghost" className="h-6 text-[10px] bg-white/50 dark:bg-black/20 hover:bg-white dark:hover:bg-black/40">Configure</Button>
                </>
             )}
             {alert.status === 'Resolved' && <Badge variant="neutral" size="sm" className="h-6">Resolved</Badge>}
          </div>
       </div>
    </div>
  );
};

// --- Main Component ---

export const AlertsPage = () => {
  const { openAlertModal } = useDashboard();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('price');
  const [search, setSearch] = useState('');
  const [isExportOpen, setIsExportOpen] = useState(false);

  // Filtering Logic
  const filteredPriceAlerts = mockPriceAlerts.filter(a => a.symbol.includes(search.toUpperCase()));
  const filteredHistory = mockHistory.filter(h => 
    h.details.toLowerCase().includes(search.toLowerCase()) || 
    h.type.toLowerCase().includes(search.toLowerCase())
  );

  const handleExport = (config: ExportConfig) => {
    toast({
      title: 'Export Started',
      description: `Generating ${config.format.toUpperCase()} report from ${config.startDate} to ${config.endDate}...`,
      type: 'info'
    });
  };

  const historyColumns: Column<AlertHistory>[] = [
    { key: 'timestamp', header: 'Time', render: (val: Date) => <span className="text-xs font-mono opacity-60">{val.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span> },
    { key: 'type', header: 'Type', render: (val) => <Badge variant="neutral" size="sm" className="font-normal">{val}</Badge> },
    { key: 'details', header: 'Details', render: (val) => <span className="font-medium text-sm">{val}</span> },
    { key: 'triggerValue', header: 'Trigger Value', render: (val) => <span className="font-mono text-xs">{val}</span> },
    { key: 'actionTaken', header: 'Action', render: (val) => <span className="text-xs opacity-80">{val}</span> },
    { key: 'outcome', header: 'Outcome', align: 'right', render: (val) => <span className="text-xs text-gain flex items-center justify-end gap-1"><CheckCircle2 className="w-3 h-3" /> {val}</span> },
  ];

  return (
    <ErrorBoundary>
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="space-y-6 pt-2 pb-10"
      >
        {/* 1. Header */}
        <PageHeader
          title="Alerts Center"
          description="Monitor price triggers, risk warnings, and system health notifications."
          actions={
            <div className="flex gap-3">
              <Button variant="secondary" leftIcon={<Download className="w-4 h-4" />} onClick={() => setIsExportOpen(true)}>
                Export
              </Button>
              <Button variant="primary" leftIcon={<Bell className="w-4 h-4" />} onClick={() => openAlertModal()}>
                New Alert
              </Button>
            </div>
          }
        />

        {/* 2. Stats Row */}
        <motion.div variants={fadeInUp} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
           <MetricCard 
              title="Active Alerts" 
              value={24} 
              format="raw" 
              icon={Bell} 
              variant="default" 
              className="border-transparent"
           />
           <MetricCard 
              title="Triggered Today" 
              value={8} 
              format="raw" 
              icon={Zap} 
              variant="default"
              change={2} // +2 from yesterday
              className="border-transparent"
           />
           <MetricCard 
              title="Risk Warnings" 
              value={5} 
              format="raw" 
              icon={ShieldAlert} 
              variant="default"
              className="border-transparent bg-warning/5 border-warning/10"
           />
           <MetricCard 
              title="Muted" 
              value={3} 
              format="raw" 
              icon={VolumeX} 
              variant="subtle"
              className="border-transparent opacity-70"
           />
        </motion.div>

        {/* 3. Main Content Tabs */}
        <motion.div variants={fadeInUp} className="min-h-[500px]">
           <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
              
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                 <TabsList variant="pill" className="bg-paper-200 dark:bg-white/5">
                    <TabsTrigger value="price" className="gap-2"><Activity className="w-4 h-4" /> Price Alerts</TabsTrigger>
                    <TabsTrigger value="risk" className="gap-2">
                       <ShieldAlert className="w-4 h-4" /> Risk Alerts
                       {mockRiskAlerts.filter(a => a.status === 'Active').length > 0 && (
                          <span className="w-2 h-2 rounded-full bg-loss animate-pulse" />
                       )}
                    </TabsTrigger>
                    <TabsTrigger value="system" className="gap-2"><Server className="w-4 h-4" /> System</TabsTrigger>
                    <TabsTrigger value="history" className="gap-2"><Clock className="w-4 h-4" /> History</TabsTrigger>
                 </TabsList>

                 <div className="w-full md:w-64">
                    <SearchInput 
                       placeholder="Filter alerts..." 
                       value={search}
                       onChange={(e) => setSearch(e.target.value)}
                       className="h-9"
                    />
                 </div>
              </div>

              {/* Price Alerts Grid */}
              <TabsContent value="price" className="mt-0">
                 {filteredPriceAlerts.length > 0 ? (
                   <motion.div 
                     initial={{ opacity: 0 }} 
                     animate={{ opacity: 1 }}
                     className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
                   >
                      {filteredPriceAlerts.map(alert => (
                         <PriceAlertCard key={alert.id} alert={alert} />
                      ))}
                      {/* Create New Card */}
                      <button 
                        onClick={() => openAlertModal()}
                        className="flex flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-deep-teal-800/10 dark:border-white/10 p-6 hover:border-turquoise-mist hover:bg-turquoise-mist/5 transition-all text-obsidian-400/40 dark:text-paper-100/40 hover:text-turquoise-mist"
                      >
                         <div className="p-3 rounded-full bg-current opacity-10">
                            <Bell className="w-6 h-6" />
                         </div>
                         <span className="text-sm font-medium">Create Alert</span>
                      </button>
                   </motion.div>
                 ) : (
                   <EmptyState 
                     title="No price alerts configured" 
                     description="Create a new alert to track asset movements."
                     action={<Button variant="primary" onClick={() => openAlertModal()}>Create Alert</Button>}
                   />
                 )}
              </TabsContent>

              {/* Risk Alerts List */}
              <TabsContent value="risk" className="mt-0">
                 {mockRiskAlerts.length > 0 ? (
                   <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3 max-w-4xl">
                      {mockRiskAlerts.map(alert => (
                         <RiskAlertRow key={alert.id} alert={alert} />
                      ))}
                   </motion.div>
                 ) : <EmptyState title="No active risk alerts" description="Your portfolio is within defined risk parameters." variant="default" />}
              </TabsContent>

              {/* System Alerts List */}
              <TabsContent value="system" className="mt-0">
                 {mockSystemAlerts.length > 0 ? (
                   <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3 max-w-4xl">
                      {mockSystemAlerts.map(alert => (
                         <div key={alert.id} className="flex items-center justify-between p-4 rounded-xl border border-deep-teal-800/5 dark:border-white/5 bg-paper-100 dark:bg-obsidian-300">
                            <div className="flex items-center gap-4">
                               <div className={cn(
                                  "w-10 h-10 rounded-full flex items-center justify-center",
                                  alert.type === 'Error' ? "bg-loss/10 text-loss" : 
                                  alert.type === 'Latency' ? "bg-warning/10 text-warning" : 
                                  "bg-info/10 text-info"
                               )}>
                                  {alert.type === 'Connection' ? <Wifi className="w-5 h-5" /> : <Server className="w-5 h-5" />}
                               </div>
                               <div>
                                  <div className="flex items-center gap-2">
                                     <h4 className="font-medium text-sm text-obsidian-400 dark:text-paper-100">{alert.message}</h4>
                                     {alert.status === 'Active' && <Badge variant="danger" dot size="sm">Active</Badge>}
                                  </div>
                                  <div className="text-xs opacity-60 flex items-center gap-3 mt-0.5">
                                     <span>{alert.timestamp}</span>
                                     <span>•</span>
                                     <span>Duration: {alert.duration}</span>
                                  </div>
                               </div>
                            </div>
                            {alert.status === 'Active' && (
                               <Button size="sm" variant="ghost" className="text-xs">Investigate</Button>
                            )}
                         </div>
                      ))}
                   </motion.div>
                 ) : <EmptyState title="All systems operational" description="No connectivity or infrastructure issues detected." />}
              </TabsContent>

              {/* History Table */}
              <TabsContent value="history" className="mt-0">
                 {filteredHistory.length > 0 ? (
                   <GlassCard padding="none" className="overflow-hidden">
                      <div className="flex items-center justify-between px-6 py-4 border-b border-deep-teal-800/5 dark:border-white/5 bg-deep-teal-800/5 dark:bg-white/5">
                         <h3 className="text-sm font-medium">Trigger Log</h3>
                         <Button variant="ghost" size="sm" className="h-7 text-xs">Export CSV</Button>
                      </div>
                      <DataTable 
                         columns={historyColumns} 
                         data={filteredHistory} 
                      />
                   </GlassCard>
                 ) : (
                   <EmptyState 
                     title="No trigger history" 
                     description="Past alert triggers will appear here." 
                     variant="search"
                   />
                 )}
              </TabsContent>

           </Tabs>
        </motion.div>

        <ExportModal 
          isOpen={isExportOpen} 
          onClose={() => setIsExportOpen(false)} 
          onExport={handleExport}
          title="Export Alerts Log"
        />

      </motion.div>
    </ErrorBoundary>
  );
};
