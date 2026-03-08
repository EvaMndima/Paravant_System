import React, { useRef, useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, X, ArrowUpRight, ArrowDownRight, Minus, Bell, Eye } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { cn, formatCurrency } from '@/lib/utils';

export interface WatchlistItem {
  id: string;
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
}

export interface WatchlistProps {
  items: WatchlistItem[];
  isLoading?: boolean;
  onSelect?: (item: WatchlistItem) => void;
  onRemove?: (id: string) => void;
  onAdd?: () => void;
  onAlert?: (item: WatchlistItem) => void;
  className?: string;
}

// --- Row sub-component ---

const WatchlistItemRow: React.FC<{
  item: WatchlistItem;
  onSelect?: (item: WatchlistItem) => void;
  onAlert?: (item: WatchlistItem) => void;
  onRemove?: (id: string) => void;
}> = ({ item, onSelect, onAlert, onRemove }) => {
  const prevPrice = useRef(item.price);
  const [flash, setFlash] = useState<'green' | 'red' | null>(null);

  useEffect(() => {
    if (item.price > prevPrice.current) {
      setFlash('green');
    } else if (item.price < prevPrice.current) {
      setFlash('red');
    }
    prevPrice.current = item.price;
    const timer = setTimeout(() => setFlash(null), 1000);
    return () => clearTimeout(timer);
  }, [item.price]);

  const isPositive = item.change >= 0;
  const Icon = item.change === 0 ? Minus : (isPositive ? ArrowUpRight : ArrowDownRight);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, height: 0, marginBottom: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'group relative rounded-lg transition-colors cursor-pointer border border-transparent',
        'hover:bg-deep-teal-800/5 dark:hover:bg-white/5',
        flash === 'green' ? 'bg-gain/5 border-gain/10' : flash === 'red' ? 'bg-loss/5 border-loss/10' : ''
      )}
      onClick={() => onSelect?.(item)}
    >
      <div className="flex items-center justify-between py-2.5 px-3">
        <div className="min-w-0 flex-1 pr-4">
          <span className="font-sans font-bold text-sm text-obsidian-400 dark:text-paper-100">
            {item.symbol}
          </span>
          <div className="text-[10px] font-sans text-obsidian-400/50 dark:text-paper-100/50 truncate max-w-[120px]">
            {item.name}
          </div>
        </div>

        <div className="text-right">
          <div className={cn(
            'font-mono font-medium text-sm transition-colors duration-500',
            flash === 'green' ? 'text-gain' : flash === 'red' ? 'text-loss' : 'text-obsidian-400 dark:text-paper-100'
          )}>
            {formatCurrency(item.price)}
          </div>
          <div className={cn(
            'flex items-center justify-end gap-0.5 text-[10px] font-mono',
            isPositive ? 'text-gain' : 'text-loss'
          )}>
            <Icon className="w-2.5 h-2.5" strokeWidth={2} />
            <span>{item.changePercent.toFixed(2)}%</span>
          </div>
        </div>
      </div>

      {/* Hover action buttons */}
      <div className="absolute inset-y-0 right-0 w-24 bg-gradient-to-l from-paper-100 via-paper-100/95 to-transparent dark:from-obsidian-300 dark:via-obsidian-300/95 flex items-center justify-end px-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 gap-1">
        {onAlert && (
          <button
            onClick={(e) => { e.stopPropagation(); onAlert(item); }}
            className="p-1.5 rounded-full bg-paper-200 dark:bg-white/10 text-obsidian-400/60 dark:text-paper-100/60 hover:text-deep-teal-800 dark:hover:text-turquoise-mist hover:bg-deep-teal-800/10 dark:hover:bg-white/20 transition-colors shadow-sm"
          >
            <Bell className="w-3.5 h-3.5" />
          </button>
        )}
        {onRemove && (
          <button
            onClick={(e) => { e.stopPropagation(); onRemove(item.id); }}
            className="p-1.5 rounded-full bg-paper-200 dark:bg-white/10 text-obsidian-400/60 dark:text-paper-100/60 hover:text-loss hover:bg-loss/10 transition-colors shadow-sm"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </motion.div>
  );
};

// --- Main Component ---

export const Watchlist: React.FC<WatchlistProps> = ({
  items,
  isLoading = false,
  onSelect,
  onRemove,
  onAdd,
  onAlert,
  className,
}) => {
  return (
    <GlassCard
      variant="default"
      padding="none"
      className={cn('flex flex-col h-full overflow-hidden', className)}
    >
      <div className="px-5 py-4 border-b border-deep-teal-800/5 dark:border-white/5 flex items-center justify-between bg-white/40 dark:bg-obsidian-400/40 backdrop-blur-md sticky top-0 z-10">
        <h3 className="text-xs font-mono font-bold uppercase tracking-widest text-obsidian-400/60 dark:text-paper-100/60">
          Watchlist
        </h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={onAdd}
          className="h-6 w-6 p-0 rounded-full hover:bg-deep-teal-800/10 dark:hover:bg-white/10"
        >
          <Plus className="w-4 h-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-2">
        {isLoading ? (
          <div className="space-y-2 p-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex justify-between items-center py-2 px-3">
                <div className="space-y-1 w-24">
                  <Skeleton variant="text" className="h-4 w-12" />
                  <Skeleton variant="text" className="h-3 w-full" />
                </div>
                <div className="space-y-1 w-16">
                  <Skeleton variant="text" className="h-4 w-full" />
                  <Skeleton variant="text" className="h-3 w-10 ml-auto" />
                </div>
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            title="Watchlist Empty"
            description="Track assets by adding them here."
            variant="default"
            icon={Eye}
            className="min-h-[200px]"
            action={
              <Button variant="ghost" size="sm" onClick={onAdd} className="text-turquoise-mist">
                Add Symbol
              </Button>
            }
          />
        ) : (
          <div className="space-y-0.5">
            <AnimatePresence initial={false} mode="popLayout">
              {items.map((item) => (
                <WatchlistItemRow
                  key={item.id}
                  item={item}
                  onSelect={onSelect}
                  onAlert={onAlert}
                  onRemove={onRemove}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </GlassCard>
  );
};
