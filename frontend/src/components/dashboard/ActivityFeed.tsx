import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp, DollarSign, ArrowDownLeft, ArrowUpRight,
  Bell, Bot, Filter, ChevronRight, Activity, Wallet,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Dropdown } from '@/components/ui/Dropdown';
import { EmptyState } from '@/components/ui/EmptyState';
import { cn } from '@/lib/utils';
import { staggerContainer, fadeInUp } from '@/lib/animations';

// --- Types ---

export type ActivityType = 'trade' | 'dividend' | 'deposit' | 'withdrawal' | 'alert' | 'agent';

export interface ActivityItem {
  id: string;
  type: ActivityType;
  title: string;
  description?: string;
  timestamp: Date;
  metadata?: Record<string, string | number>;
}

export interface ActivityFeedProps {
  items: ActivityItem[];
  maxItems?: number;
  showTimestamps?: boolean;
  onItemClick?: (item: ActivityItem) => void;
  className?: string;
}

// --- Helpers ---

const getTypeConfig = (type: ActivityType) => {
  switch (type) {
    case 'trade':
      return { icon: TrendingUp, color: 'text-turquoise-mist', borderColor: 'border-turquoise-mist/30' };
    case 'dividend':
      return { icon: DollarSign, color: 'text-gain', borderColor: 'border-gain/30' };
    case 'deposit':
      return { icon: ArrowDownLeft, color: 'text-info', borderColor: 'border-info/30' };
    case 'withdrawal':
      return { icon: ArrowUpRight, color: 'text-warning', borderColor: 'border-warning/30' };
    case 'alert':
      return { icon: Bell, color: 'text-loss', borderColor: 'border-loss/30' };
    case 'agent':
      return {
        icon: Bot,
        color: 'text-deep-teal-800 dark:text-turquoise-mist',
        borderColor: 'border-deep-teal-800/30 dark:border-white/30',
      };
    default:
      return { icon: Activity, color: 'text-obsidian-400', borderColor: 'border-obsidian-400/30' };
  }
};

const getRelativeTime = (date: Date): string => {
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return 'Just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
  return date.toLocaleDateString();
};

type FilterMode = 'all' | 'trades' | 'alerts' | 'transfers';

// --- Component ---

export const ActivityFeed: React.FC<ActivityFeedProps> = ({
  items,
  maxItems = 10,
  showTimestamps = true,
  onItemClick,
  className,
}) => {
  const [filter, setFilter] = useState<FilterMode>('all');

  const filteredItems = useMemo(() => {
    let result = items;
    if (filter === 'trades') result = items.filter(i => i.type === 'trade' || i.type === 'agent');
    if (filter === 'alerts') result = items.filter(i => i.type === 'alert');
    if (filter === 'transfers') result = items.filter(i => ['deposit', 'withdrawal', 'dividend'].includes(i.type));
    return result
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
      .slice(0, maxItems);
  }, [items, filter, maxItems]);

  const filterOptions = [
    { label: 'All Activity', icon: Activity, onClick: () => setFilter('all') },
    { label: 'Trades & Agents', icon: TrendingUp, onClick: () => setFilter('trades') },
    { label: 'Alerts', icon: Bell, onClick: () => setFilter('alerts') },
    { label: 'Transfers', icon: Wallet, onClick: () => setFilter('transfers') },
  ];

  return (
    <GlassCard className={cn('flex flex-col h-full', className)} padding="none">

      {/* Header */}
      <div className="flex items-center justify-between px-6 py-5 border-b border-deep-teal-800/5 dark:border-white/5">
        <h3 className="font-display text-lg font-medium text-obsidian-400 dark:text-paper-100">
          Recent Activity
        </h3>
        <Dropdown
          align="end"
          trigger={
            <button className="flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-obsidian-400/60 dark:text-paper-100/60 hover:text-deep-teal-800 dark:hover:text-turquoise-mist transition-colors">
              <Filter className="w-3.5 h-3.5" />
              <span>{filter === 'all' ? 'Filter' : filter}</span>
            </button>
          }
          items={filterOptions}
        />
      </div>

      {/* Timeline List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-6 relative">
        {/* Vertical timeline line */}
        {filteredItems.length > 0 && (
          <div className="absolute left-10 top-6 bottom-6 w-px bg-deep-teal-800/10 dark:bg-white/10 z-0 -translate-x-1/2" />
        )}

        <AnimatePresence mode="wait">
          {filteredItems.length > 0 ? (
            <motion.div
              key={filter}
              variants={staggerContainer}
              initial="initial"
              animate="animate"
              className="space-y-6 relative z-10"
            >
              {filteredItems.map((item) => {
                const config = getTypeConfig(item.type);
                const Icon = config.icon;

                return (
                  <motion.div
                    key={item.id}
                    variants={fadeInUp}
                    onClick={() => onItemClick?.(item)}
                    className={cn(
                      'group flex gap-4 relative',
                      onItemClick && 'cursor-pointer'
                    )}
                  >
                    {/* Icon bubble hides the timeline line behind it */}
                    <div className={cn(
                      'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border',
                      'bg-paper-100 dark:bg-obsidian-300',
                      'ring-4 ring-paper-100 dark:ring-obsidian-300',
                      config.color,
                      config.borderColor
                    )}>
                      <Icon className="w-4 h-4" strokeWidth={2} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0 pt-1">
                      <div className="flex justify-between items-start gap-4">
                        <div className="space-y-0.5">
                          <p className="text-sm font-medium text-obsidian-400 dark:text-paper-100 group-hover:text-deep-teal-800 dark:group-hover:text-turquoise-mist transition-colors">
                            {item.title}
                          </p>
                          {item.description && (
                            <p className="text-xs text-obsidian-400/60 dark:text-paper-100/60 leading-relaxed line-clamp-2">
                              {item.description}
                            </p>
                          )}

                          {/* Metadata Tags */}
                          {item.metadata && (
                            <div className="flex flex-wrap gap-2 mt-2">
                              {Object.entries(item.metadata).map(([key, value]) => (
                                <span
                                  key={key}
                                  className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-deep-teal-800/5 dark:bg-white/5 text-obsidian-400/70 dark:text-paper-100/70 border border-deep-teal-800/10 dark:border-white/10"
                                >
                                  <span className="opacity-50 mr-1 uppercase">{key}:</span>
                                  {String(value)}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>

                        {showTimestamps && (
                          <span className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40 whitespace-nowrap">
                            {getRelativeTime(item.timestamp)}
                          </span>
                        )}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          ) : (
            <EmptyState
              title="No recent activity"
              description="Events and transactions will appear here."
              variant="default"
              icon={Activity}
            />
          )}
        </AnimatePresence>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-deep-teal-800/5 dark:border-white/5 bg-deep-teal-800/[0.02] dark:bg-white/[0.02]">
        <button className="w-full flex items-center justify-center gap-2 text-xs font-mono uppercase tracking-widest text-obsidian-400/60 dark:text-paper-100/60 hover:text-deep-teal-800 dark:hover:text-turquoise-mist transition-colors group">
          View All Activity
          <ChevronRight className="w-3 h-3 transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>
    </GlassCard>
  );
};
