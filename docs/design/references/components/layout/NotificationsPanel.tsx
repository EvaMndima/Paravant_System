
import React, { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Bell, Check, X, TrendingUp, TrendingDown, 
  Bot, ShieldAlert, Zap, Filter, ChevronRight, Activity,
  Settings, Volume2, VolumeX, MoreHorizontal, Trash2,
  Inbox, Eye
} from 'lucide-react';
import { GlassCard } from '../ui/GlassCard';
import { cn } from '../../lib/utils';
import { smoothSpring } from '../../lib/animations';
import { Dropdown } from '../ui/Dropdown';

export type NotificationType = 'trade' | 'alert' | 'system' | 'curator';

export interface NotificationItem {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  actionUrl?: string;
}

interface NotificationsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  notifications: NotificationItem[];
  onMarkRead: (id: string) => void;
  onMarkAllRead: () => void;
  onNavigate?: (view: string) => void;
  onOpenSettings?: () => void;
  className?: string;
}

// --- Sub-components ---

const EmptyState = ({ type }: { type: string }) => {
  const config = {
    all: { icon: Inbox, text: "You're all caught up" },
    trade: { icon: TrendingUp, text: "No trade notifications" },
    alert: { icon: Bell, text: "No active alerts" },
    system: { icon: ShieldAlert, text: "System is quiet" },
    curator: { icon: Bot, text: "No curator insights" },
  }[type] || { icon: Inbox, text: "No notifications" };

  const Icon = config.icon;

  return (
    <div className="flex flex-col items-center justify-center h-64 text-obsidian-400/40 dark:text-paper-100/40 animate-fade-in">
      <div className="p-4 bg-deep-teal-800/5 dark:bg-white/5 rounded-full mb-3">
        <Icon className="w-6 h-6 opacity-60" strokeWidth={1.5} />
      </div>
      <p className="text-sm font-medium">{config.text}</p>
    </div>
  );
};

export const NotificationsPanel: React.FC<NotificationsPanelProps> = ({
  isOpen,
  onClose,
  notifications,
  onMarkRead,
  onMarkAllRead,
  onNavigate,
  onOpenSettings,
  className
}) => {
  const [filter, setFilter] = useState<'all' | NotificationType>('all');
  const [soundEnabled, setSoundEnabled] = useState(() => localStorage.getItem('paravant_notif_sound') !== 'false');
  const panelRef = useRef<HTMLDivElement>(null);

  // Persist sound preference
  useEffect(() => {
    localStorage.setItem('paravant_notif_sound', String(soundEnabled));
  }, [soundEnabled]);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node) && isOpen) {
        onClose();
      }
    };
    if (isOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  // Derived State
  const unreadCount = useMemo(() => notifications.filter(n => !n.read).length, [notifications]);
  
  const counts = useMemo(() => {
    const c: Record<string, number> = { all: 0, trade: 0, alert: 0, system: 0, curator: 0 };
    notifications.forEach(n => {
      if (!n.read) {
        c.all++;
        c[n.type] = (c[n.type] || 0) + 1;
      }
    });
    return c;
  }, [notifications]);

  const filteredNotifications = useMemo(() => {
    return notifications
      .filter(n => filter === 'all' ? true : n.type === filter)
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }, [notifications, filter]);

  // Navigation Helper
  const handleItemClick = (item: NotificationItem) => {
    if (!item.read) onMarkRead(item.id);
    
    if (onNavigate) {
      switch (item.type) {
        case 'trade': onNavigate('Trade History'); break;
        case 'alert': onNavigate('Alerts'); break;
        case 'system': onNavigate('System'); break;
        case 'curator': onNavigate('System'); break; // Curator decisions live in System
        default: break;
      }
    }
    onClose();
  };

  // Helpers
  const getRelativeTime = (date: Date) => {
    const diff = Math.floor((new Date().getTime() - date.getTime()) / 1000);
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    return `${Math.floor(diff / 86400)}d`;
  };

  const getIcon = (type: NotificationType) => {
    switch (type) {
      case 'trade': return <TrendingUp className="w-4 h-4" />;
      case 'alert': return <Bell className="w-4 h-4" />;
      case 'system': return <ShieldAlert className="w-4 h-4" />;
      case 'curator': return <Bot className="w-4 h-4" />;
      default: return <Activity className="w-4 h-4" />;
    }
  };

  const getTypeStyles = (type: NotificationType) => {
    switch (type) {
      case 'trade': return 'text-gain bg-gain/10 border-gain/20';
      case 'alert': return 'text-warning bg-warning/10 border-warning/20';
      case 'system': return 'text-loss bg-loss/10 border-loss/20';
      case 'curator': return 'text-deep-teal-800 dark:text-turquoise-mist bg-deep-teal-800/10 dark:bg-turquoise-mist/10 border-deep-teal-800/20 dark:border-turquoise-mist/20';
      default: return 'text-obsidian-400 bg-obsidian-400/10 border-obsidian-400/20';
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={panelRef}
          initial={{ opacity: 0, y: 10, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.98 }}
          transition={smoothSpring}
          className={cn(
            "absolute right-0 top-16 w-full md:w-[400px] z-[60] px-2 md:px-0",
            className
          )}
        >
          <GlassCard 
            variant="elevated" 
            padding="none" 
            className="overflow-hidden flex flex-col max-h-[85vh] shadow-2xl ring-1 ring-black/5 dark:ring-white/10"
          >
            {/* --- Header --- */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-deep-teal-800/5 dark:border-white/5 bg-paper-100/50 dark:bg-obsidian-300/50 backdrop-blur-md">
              <div className="flex items-center gap-2.5">
                <div className="relative">
                  <Bell className="w-4 h-4 text-obsidian-400 dark:text-paper-100" />
                  {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 w-2 h-2 bg-loss rounded-full ring-2 ring-paper-100 dark:ring-obsidian-300" />
                  )}
                </div>
                <h3 className="font-display font-medium text-sm text-obsidian-400 dark:text-paper-100">Notifications</h3>
                {unreadCount > 0 && (
                  <span className="bg-deep-teal-800/5 dark:bg-white/10 text-obsidian-400 dark:text-paper-100 text-[10px] px-1.5 py-0.5 rounded-md font-mono">
                    {unreadCount}
                  </span>
                )}
              </div>
              
              <div className="flex items-center gap-1">
                <button 
                  onClick={() => setSoundEnabled(!soundEnabled)}
                  className="p-1.5 rounded-md text-obsidian-400/40 dark:text-paper-100/40 hover:text-deep-teal-800 dark:hover:text-paper-100 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                  title={soundEnabled ? "Mute sounds" : "Enable sounds"}
                >
                  {soundEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
                </button>
                <button 
                  onClick={() => {
                    if (onOpenSettings) onOpenSettings();
                    if (onNavigate) onNavigate('Settings');
                    onClose();
                  }}
                  className="p-1.5 rounded-md text-obsidian-400/40 dark:text-paper-100/40 hover:text-deep-teal-800 dark:hover:text-paper-100 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                  title="Notification Settings"
                >
                  <Settings className="w-3.5 h-3.5" />
                </button>
                <div className="w-px h-4 bg-deep-teal-800/10 dark:bg-white/10 mx-1" />
                <button 
                  onClick={onMarkAllRead}
                  className="text-[10px] uppercase tracking-widest text-turquoise-mist hover:text-turquoise-bright transition-colors font-mono px-1"
                >
                  Mark all read
                </button>
              </div>
            </div>

            {/* --- Filter Tabs --- */}
            <div className="flex gap-1 px-4 py-2 border-b border-deep-teal-800/5 dark:border-white/5 overflow-x-auto no-scrollbar bg-paper-50 dark:bg-black/20">
              {(['all', 'trade', 'alert', 'curator', 'system'] as const).map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap capitalize border",
                    filter === f 
                      ? "bg-white dark:bg-white/10 border-black/5 dark:border-white/5 shadow-sm text-deep-teal-800 dark:text-paper-100" 
                      : "bg-transparent border-transparent text-obsidian-400/50 dark:text-paper-100/50 hover:text-obsidian-400 dark:hover:text-paper-100 hover:bg-black/5 dark:hover:bg-white/5"
                  )}
                >
                  <span>{f}</span>
                  {counts[f] > 0 && (
                    <span className={cn(
                      "text-[9px] px-1 rounded-sm font-mono leading-none",
                      filter === f 
                        ? "bg-deep-teal-800/10 dark:bg-black/20" 
                        : "bg-black/5 dark:bg-white/10"
                    )}>
                      {counts[f]}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* --- List Content --- */}
            <div className="flex-1 overflow-y-auto custom-scrollbar min-h-[300px] bg-paper-50/30 dark:bg-obsidian-300/30">
              {filteredNotifications.length === 0 ? (
                <EmptyState type={filter} />
              ) : (
                <div className="divide-y divide-deep-teal-800/5 dark:divide-white/5">
                  {filteredNotifications.map((notification) => (
                    <motion.div
                      layout
                      key={notification.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className={cn(
                        "group relative p-4 flex gap-3 transition-colors cursor-pointer",
                        "hover:bg-deep-teal-800/5 dark:hover:bg-white/5",
                        !notification.read ? "bg-white dark:bg-white/[0.03]" : "opacity-80 hover:opacity-100"
                      )}
                      onClick={() => handleItemClick(notification)}
                    >
                      {/* Unread Indicator */}
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-transparent group-hover:bg-deep-teal-800/5 dark:group-hover:bg-white/10 transition-colors" />
                      {!notification.read && (
                        <div className="absolute left-1.5 top-6 w-1.5 h-1.5 rounded-full bg-turquoise-mist shadow-[0_0_8px_rgba(42,157,143,0.5)]" />
                      )}

                      {/* Icon */}
                      <div className={cn(
                        "flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center border mt-0.5",
                        getTypeStyles(notification.type)
                      )}>
                        {getIcon(notification.type)}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-start gap-2">
                          <h4 className={cn(
                            "text-sm font-sans leading-tight pr-6",
                            notification.read 
                              ? "text-obsidian-400/80 dark:text-paper-100/80 font-medium" 
                              : "text-obsidian-400 dark:text-paper-100 font-bold"
                          )}>
                            {notification.title}
                          </h4>
                          <span className="text-[10px] text-obsidian-400/40 dark:text-paper-100/40 whitespace-nowrap font-mono mt-0.5">
                            {getRelativeTime(notification.timestamp)}
                          </span>
                        </div>
                        <p className="text-xs text-obsidian-400/60 dark:text-paper-100/60 mt-1 leading-relaxed line-clamp-2 pr-4">
                          {notification.message}
                        </p>
                      </div>

                      {/* Actions (Hover) */}
                      <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1 bg-paper-100 dark:bg-obsidian-300 rounded-lg shadow-sm border border-black/5 dark:border-white/10 p-0.5" onClick={e => e.stopPropagation()}>
                         {!notification.read && (
                           <button 
                             onClick={(e) => { e.stopPropagation(); onMarkRead(notification.id); }}
                             className="p-1.5 hover:bg-black/5 dark:hover:bg-white/10 rounded-md text-obsidian-400/60 dark:text-paper-100/60 hover:text-turquoise-mist transition-colors"
                             title="Mark as read"
                           >
                             <Check className="w-3.5 h-3.5" />
                           </button>
                         )}
                         <Dropdown 
                           align="end"
                           trigger={
                             <button className="p-1.5 hover:bg-black/5 dark:hover:bg-white/10 rounded-md text-obsidian-400/60 dark:text-paper-100/60 transition-colors">
                               <MoreHorizontal className="w-3.5 h-3.5" />
                             </button>
                           }
                           items={[
                             { label: 'View Details', icon: Eye, onClick: () => handleItemClick(notification) },
                             { label: 'Delete', icon: Trash2, danger: true, onClick: () => console.log('Delete', notification.id) }
                           ]}
                         />
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>

            {/* --- Footer --- */}
            <div className="p-3 border-t border-deep-teal-800/5 dark:border-white/5 bg-paper-50 dark:bg-white/5 backdrop-blur-md sticky bottom-0 z-10">
              <button 
                onClick={() => {
                  if (onNavigate) onNavigate('Notifications'); // UPDATED: Navigates to full page
                  onClose();
                }}
                className="w-full flex items-center justify-center gap-2 py-2 text-xs font-mono uppercase tracking-widest text-obsidian-400/60 dark:text-paper-100/60 hover:text-deep-teal-800 dark:hover:text-turquoise-mist hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all group"
              >
                View Full History
                <ChevronRight className="w-3 h-3 transition-transform group-hover:translate-x-0.5" />
              </button>
            </div>
          </GlassCard>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
