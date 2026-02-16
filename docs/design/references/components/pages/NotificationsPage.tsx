
import React, { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Bell, BellOff, TrendingUp, ShieldAlert, Bot, Activity, 
  Search, Filter, Trash2, Check, Download, ChevronDown, 
  Settings, CheckSquare, Square, Inbox, Clock, ChevronRight,
  ArrowRight, X
} from 'lucide-react';

import { PageHeader } from '../layout/PageHeader';
import { GlassCard } from '../ui/GlassCard';
import { Button } from '../ui/Button';
import { SearchInput } from '../ui/SearchInput';
import { Badge } from '../ui/Badge';
import { Dropdown } from '../ui/Dropdown';
import { MetricCard } from '../ui/MetricCard';
import { EmptyState } from '../ui/EmptyState';
import { ExportModal, ExportConfig } from '../dashboard/ExportModal';
import { useToast } from '../../contexts/ToastContext';
import { useDashboard } from '../../contexts/DashboardContext';
import { cn, formatCurrency } from '../../lib/utils';
import { staggerContainer, fadeInUp, smoothSpring } from '../../lib/animations';

// --- Types ---

type NotificationType = 'trade' | 'alert' | 'system' | 'curator';

interface NotificationRecord {
  id: string;
  type: NotificationType;
  title: string;
  description: string;
  timestamp: Date;
  read: boolean;
  metadata?: {
    agent?: string;
    strategy?: string;
    symbol?: string;
    price?: number;
    severity?: 'info' | 'warning' | 'critical';
  };
}

// --- Mock Data ---

const generateNotifications = (count: number): NotificationRecord[] => {
  const types: NotificationType[] = ['trade', 'alert', 'system', 'curator'];
  const agents = ['Alpha Seeker', 'Momentum Prime', 'Macro Sentinel', 'Arb Hunter'];
  
  return Array.from({ length: count }).map((_, i) => {
    const type = i % 10 < 5 ? 'trade' : types[Math.floor(Math.random() * types.length)];
    const isRead = Math.random() > 0.3;
    const date = new Date(Date.now() - Math.floor(Math.random() * 1000 * 60 * 60 * 24 * 7)); // Last 7 days

    let title = '';
    let description = '';
    let metadata: NotificationRecord['metadata'] = {};

    switch (type) {
      case 'trade':
        const symbol = ['NVDA', 'BTC', 'ETH', 'TSLA', 'AAPL'][Math.floor(Math.random() * 5)];
        const action = Math.random() > 0.5 ? 'OPENED LONG' : 'CLOSED SHORT';
        title = `${agents[Math.floor(Math.random() * agents.length)]} ${action} ${symbol}`;
        description = `Executed market order for 150 units @ ${formatCurrency(100 + Math.random() * 1000)}. Signal confidence: ${(85 + Math.random() * 14).toFixed(1)}%.`;
        metadata = { agent: agents[0], symbol, price: 150.20 };
        break;
      case 'alert':
        title = 'Price Alert Triggered: BTC > $68,000';
        description = 'Bitcoin has crossed the resistance level of 68k with significant volume spike (3x avg).';
        metadata = { symbol: 'BTC', severity: 'warning' };
        break;
      case 'curator':
        title = 'Allocation Adjustment Recommendation';
        description = 'Regime shift detected to "High Volatility". Suggest reducing leverage by 15% across momentum strategies.';
        metadata = { severity: 'info' };
        break;
      case 'system':
        title = 'API Latency Warning';
        description = 'Connection to primary data feed experiencing intermittent latency > 200ms. Switched to backup provider.';
        metadata = { severity: 'critical' };
        break;
    }

    return {
      id: `NOTIF-${i}-${Math.random().toString(36).substr(2, 5)}`,
      type,
      title,
      description,
      timestamp: date,
      read: isRead,
      metadata
    };
  });
};

const initialNotifications = generateNotifications(50).sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

// --- Components ---

const NotificationCard: React.FC<{
  item: NotificationRecord;
  isSelected: boolean;
  onSelect: () => void;
  onMarkRead: () => void;
  onDelete: () => void;
}> = ({ item, isSelected, onSelect, onMarkRead, onDelete }) => {
  const [expanded, setExpanded] = useState(false);

  const icons = {
    trade: TrendingUp,
    alert: Bell,
    system: ShieldAlert,
    curator: Bot
  };
  const Icon = icons[item.type] || Activity;

  const colors = {
    trade: 'text-gain bg-gain/10 border-gain/20',
    alert: 'text-warning bg-warning/10 border-warning/20',
    system: 'text-loss bg-loss/10 border-loss/20',
    curator: 'text-deep-teal-800 dark:text-turquoise-mist bg-deep-teal-800/10 dark:bg-turquoise-mist/10 border-deep-teal-800/20 dark:border-turquoise-mist/20'
  };

  const getRelativeTime = (date: Date) => {
    const diff = Math.floor((new Date().getTime() - date.getTime()) / 1000);
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  return (
    <motion.div 
      layout
      className={cn(
        "group relative rounded-xl border transition-all duration-200 overflow-hidden",
        expanded ? "bg-paper-100 dark:bg-obsidian-300 border-deep-teal-800/10 dark:border-white/10 shadow-lg" : 
        "bg-white/50 dark:bg-white/[0.02] border-transparent hover:bg-white dark:hover:bg-white/5 hover:border-deep-teal-800/5 dark:hover:border-white/5",
        isSelected && "bg-deep-teal-800/5 dark:bg-white/10 border-deep-teal-800/20 dark:border-white/20"
      )}
    >
      <div 
        className="flex gap-4 p-4 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Checkbox Area */}
        <div className="flex items-center justify-center pt-1" onClick={(e) => { e.stopPropagation(); onSelect(); }}>
           <div className={cn("text-obsidian-400/30 dark:text-paper-100/30 transition-colors", isSelected && "text-deep-teal-800 dark:text-turquoise-mist")}>
              {isSelected ? <CheckSquare className="w-5 h-5" /> : <Square className="w-5 h-5" />}
           </div>
        </div>

        {/* Unread Indicator */}
        <div className="pt-2.5">
           <div className={cn("w-2 h-2 rounded-full", !item.read ? "bg-turquoise-mist" : "bg-transparent")} />
        </div>

        {/* Icon */}
        <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center border shrink-0", colors[item.type])}>
           <Icon className="w-5 h-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
           <div className="flex justify-between items-start gap-4">
              <h4 className={cn("text-sm font-medium leading-tight", !item.read ? "text-obsidian-400 dark:text-paper-100 font-bold" : "text-obsidian-400/80 dark:text-paper-100/80")}>
                 {item.title}
              </h4>
              <span className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 whitespace-nowrap">
                 {getRelativeTime(item.timestamp)}
              </span>
           </div>
           
           <p className={cn("text-xs mt-1 text-obsidian-400/60 dark:text-paper-100/60 leading-relaxed", !expanded && "line-clamp-1")}>
              {item.description}
           </p>

           {/* Expanded Metadata */}
           <AnimatePresence>
             {expanded && (
                <motion.div 
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="mt-3 pt-3 border-t border-deep-teal-800/5 dark:border-white/5"
                >
                   <div className="flex flex-wrap gap-2 text-[10px] font-mono uppercase tracking-wide text-obsidian-400/50 dark:text-paper-100/50 mb-3">
                      <span>ID: {item.id}</span>
                      <span>•</span>
                      <span>{item.timestamp.toLocaleString()}</span>
                      {item.metadata?.agent && (
                        <>
                          <span>•</span>
                          <span>Agent: {item.metadata.agent}</span>
                        </>
                      )}
                   </div>
                   
                   <div className="flex gap-3">
                      <Button size="sm" variant="secondary" className="h-8 text-xs">View Details</Button>
                      {!item.read && <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={(e) => { e.stopPropagation(); onMarkRead(); }}>Mark as Read</Button>}
                      <Button size="sm" variant="ghost" className="h-8 text-xs text-loss hover:text-loss hover:bg-loss/10" onClick={(e) => { e.stopPropagation(); onDelete(); }}>Delete</Button>
                   </div>
                </motion.div>
             )}
           </AnimatePresence>
        </div>

        {/* Hover Actions (Desktop) */}
        {!expanded && (
           <div className="hidden md:flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity self-center">
              {!item.read && (
                 <button 
                   onClick={(e) => { e.stopPropagation(); onMarkRead(); }}
                   className="p-2 rounded-lg hover:bg-deep-teal-800/5 dark:hover:bg-white/10 text-obsidian-400/50 dark:text-paper-100/50 hover:text-turquoise-mist transition-colors"
                   title="Mark as read"
                 >
                    <Check className="w-4 h-4" />
                 </button>
              )}
              <button 
                 onClick={(e) => { e.stopPropagation(); onDelete(); }}
                 className="p-2 rounded-lg hover:bg-loss/10 text-obsidian-400/50 dark:text-paper-100/50 hover:text-loss transition-colors"
                 title="Delete"
              >
                 <Trash2 className="w-4 h-4" />
              </button>
           </div>
        )}
      </div>
    </motion.div>
  );
};

export const NotificationsPage = () => {
  const { toast } = useToast();
  const { navigateToSettingsTab } = useDashboard();
  const [items, setItems] = useState<NotificationRecord[]>(initialNotifications);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('All');
  const [filterStatus, setFilterStatus] = useState<'All' | 'Unread' | 'Read'>('All');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isExportOpen, setIsExportOpen] = useState(false);

  // Derived State
  const filteredItems = useMemo(() => {
    return items.filter(item => {
      const matchesSearch = item.title.toLowerCase().includes(search.toLowerCase()) || 
                            item.description.toLowerCase().includes(search.toLowerCase());
      const matchesType = filterType === 'All' || item.type === filterType.toLowerCase();
      const matchesStatus = filterStatus === 'All' || (filterStatus === 'Unread' ? !item.read : item.read);
      return matchesSearch && matchesType && matchesStatus;
    });
  }, [items, search, filterType, filterStatus]);

  const stats = {
    total: items.length,
    unread: items.filter(i => !i.read).length,
    thisWeek: items.filter(i => (Date.now() - i.timestamp.getTime()) < 1000 * 60 * 60 * 24 * 7).length,
    alerts: items.filter(i => i.type === 'alert').length
  };

  // Actions
  const handleSelectAll = () => {
    if (selectedIds.size === filteredItems.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredItems.map(i => i.id)));
    }
  };

  const handleSelect = (id: string) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedIds(newSet);
  };

  const handleMarkRead = (ids: string[]) => {
    setItems(prev => prev.map(i => ids.includes(i.id) ? { ...i, read: true } : i));
    setSelectedIds(new Set());
    toast({ title: 'Marked as read', description: `${ids.length} notifications updated.`, type: 'success' });
  };

  const handleDelete = (ids: string[]) => {
    setItems(prev => prev.filter(i => !ids.includes(i.id)));
    setSelectedIds(new Set());
    toast({ title: 'Deleted', description: `${ids.length} notifications removed.`, type: 'info' });
  };

  const handleExport = (config: ExportConfig) => {
    toast({
      title: 'Export Started',
      description: `Generating ${config.format.toUpperCase()} report...`,
      type: 'info'
    });
  };

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="space-y-6 pt-2 pb-10 relative"
    >
      {/* 1. Header */}
      <PageHeader
        title="Notifications"
        description="All system notifications, trade alerts, and curator insights."
        actions={
          <div className="flex items-center gap-3">
             <Button variant="secondary" leftIcon={<Download className="w-4 h-4" />} onClick={() => setIsExportOpen(true)}>
                Export
             </Button>
             <Button 
                variant="secondary" 
                leftIcon={<Check className="w-4 h-4" />} 
                onClick={() => handleMarkRead(items.map(i => i.id))}
                disabled={stats.unread === 0}
             >
                Mark All Read
             </Button>
             <Button 
                variant="ghost" 
                size="sm" 
                className="h-10 w-10 p-0 rounded-xl bg-deep-teal-800/5 dark:bg-white/5"
                onClick={() => navigateToSettingsTab('notifications')}
             >
                <Settings className="w-5 h-5" />
             </Button>
          </div>
        }
      />

      {/* 2. Stats Row */}
      <motion.div variants={fadeInUp} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
         <MetricCard title="Total Notifications" value={stats.total} format="raw" icon={Inbox} variant="subtle" className="border-transparent bg-deep-teal-800/5 dark:bg-white/5" />
         <MetricCard title="Unread" value={stats.unread} format="raw" icon={Bell} variant="subtle" className="border-transparent bg-deep-teal-800/5 dark:bg-white/5" />
         <MetricCard title="This Week" value={stats.thisWeek} format="raw" icon={Clock} variant="subtle" className="border-transparent bg-deep-teal-800/5 dark:bg-white/5" />
         <MetricCard title="Alerts Triggered" value={stats.alerts} format="raw" icon={ShieldAlert} variant="subtle" className="border-transparent bg-deep-teal-800/5 dark:bg-white/5" />
      </motion.div>

      {/* 3. Filters & List */}
      <motion.div variants={fadeInUp} className="space-y-4">
         {/* Filters Bar */}
         <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-white/50 dark:bg-white/[0.02] p-2 rounded-xl backdrop-blur-sm border border-deep-teal-800/5 dark:border-white/5">
            <div className="w-full md:w-80">
               <SearchInput 
                  placeholder="Search notifications..." 
                  value={search} 
                  onChange={e => setSearch(e.target.value)}
                  className="bg-transparent border-transparent"
               />
            </div>
            
            <div className="flex gap-2 w-full md:w-auto overflow-x-auto pb-2 md:pb-0 no-scrollbar">
               <Dropdown 
                  trigger={<Button variant="ghost" size="sm" rightIcon={<ChevronDown className="w-4 h-4"/>}>Type: {filterType}</Button>}
                  items={['All', 'Trade', 'Alert', 'Curator', 'System'].map(t => ({ label: t, onClick: () => setFilterType(t) }))}
               />
               <Dropdown 
                  trigger={<Button variant="ghost" size="sm" rightIcon={<ChevronDown className="w-4 h-4"/>}>Status: {filterStatus}</Button>}
                  items={['All', 'Unread', 'Read'].map(s => ({ label: s, onClick: () => setFilterStatus(s as any) }))}
               />
               <div className="w-px h-6 bg-deep-teal-800/10 dark:bg-white/10 mx-1 self-center" />
               <button 
                 onClick={handleSelectAll} 
                 className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-obsidian-400 dark:text-paper-100 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 rounded-lg transition-colors"
               >
                  {selectedIds.size === filteredItems.length && filteredItems.length > 0 ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4 opacity-50" />}
                  Select All
               </button>
            </div>
         </div>

         {/* Notifications List */}
         <div className="space-y-2">
            <AnimatePresence initial={false}>
               {filteredItems.length > 0 ? (
                  filteredItems.map(item => (
                     <NotificationCard 
                        key={item.id} 
                        item={item} 
                        isSelected={selectedIds.has(item.id)}
                        onSelect={() => handleSelect(item.id)}
                        onMarkRead={() => handleMarkRead([item.id])}
                        onDelete={() => handleDelete([item.id])}
                     />
                  ))
               ) : (
                  <EmptyState 
                     title="No notifications found" 
                     description="Try adjusting filters or you're all caught up!" 
                     icon={BellOff} 
                     variant="search"
                  />
               )}
            </AnimatePresence>
         </div>
      </motion.div>

      {/* 4. Bulk Actions Bar (Sticky) */}
      <AnimatePresence>
         {selectedIds.size > 0 && (
            <motion.div 
               initial={{ y: 50, opacity: 0 }}
               animate={{ y: 0, opacity: 1 }}
               exit={{ y: 50, opacity: 0 }}
               className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 px-6 py-3 bg-obsidian-400 dark:bg-paper-100 text-paper-100 dark:text-obsidian-400 rounded-2xl shadow-2xl border border-white/10"
            >
               <div className="flex items-center gap-2 text-sm font-medium border-r border-white/20 dark:border-black/10 pr-4 mr-2">
                  <span className="bg-white/20 dark:bg-black/10 px-2 py-0.5 rounded text-xs font-mono">{selectedIds.size}</span>
                  Selected
               </div>
               
               <div className="flex items-center gap-2">
                  <Button size="sm" variant="ghost" className="hover:bg-white/10 dark:hover:bg-black/5 text-current" onClick={() => handleMarkRead(Array.from(selectedIds))}>
                     Mark Read
                  </Button>
                  <Button size="sm" variant="ghost" className="hover:bg-white/10 dark:hover:bg-black/5 text-current hover:text-loss" onClick={() => handleDelete(Array.from(selectedIds))}>
                     Delete
                  </Button>
               </div>
               
               <button 
                  onClick={() => setSelectedIds(new Set())} 
                  className="ml-2 p-1 rounded-full hover:bg-white/10 dark:hover:bg-black/5 transition-colors"
               >
                  <X className="w-4 h-4" />
               </button>
            </motion.div>
         )}
      </AnimatePresence>

      <ExportModal 
        isOpen={isExportOpen} 
        onClose={() => setIsExportOpen(false)} 
        onExport={handleExport}
        title="Export Notifications"
      />

    </motion.div>
  );
};
