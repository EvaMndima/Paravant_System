import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp, TrendingDown, Minus, Zap, HelpCircle, Check, AlertTriangle,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { cn } from '@/lib/utils';

export type MarketRegime = 'trending_up' | 'trending_down' | 'ranging' | 'volatile' | 'unknown';

export interface RegimeTagSelectorProps {
  current?: MarketRegime;
  onChange?: (regime: MarketRegime) => void;
  disabled?: boolean;
  showConfirmation?: boolean;
  className?: string;
}

interface RegimeOption {
  value: MarketRegime;
  label: string;
  description: string;
  icon: React.ElementType;
  activeClass: string;
  dotClass: string;
}

const regimeOptions: RegimeOption[] = [
  {
    value: 'trending_up',
    label: 'Trending Up',
    description: 'Strong bullish momentum with higher highs',
    icon: TrendingUp,
    activeClass: 'border-gain/40 bg-gain/10 text-gain',
    dotClass: 'bg-gain',
  },
  {
    value: 'trending_down',
    label: 'Trending Down',
    description: 'Bearish momentum with lower lows',
    icon: TrendingDown,
    activeClass: 'border-loss/40 bg-loss/10 text-loss',
    dotClass: 'bg-loss',
  },
  {
    value: 'ranging',
    label: 'Ranging',
    description: 'Price oscillating between support & resistance',
    icon: Minus,
    activeClass: 'border-info/40 bg-info/10 text-info',
    dotClass: 'bg-info',
  },
  {
    value: 'volatile',
    label: 'Volatile',
    description: 'High-volatility, unpredictable price action',
    icon: Zap,
    activeClass: 'border-warning/40 bg-warning/10 text-warning',
    dotClass: 'bg-warning',
  },
  {
    value: 'unknown',
    label: 'Unknown',
    description: 'Market conditions unclear — caution advised',
    icon: HelpCircle,
    activeClass: 'border-obsidian-400/30 bg-obsidian-400/5 text-obsidian-400 dark:border-paper-100/20 dark:bg-paper-100/5 dark:text-paper-100/60',
    dotClass: 'bg-obsidian-400/40 dark:bg-paper-100/30',
  },
];

export const RegimeTagSelector: React.FC<RegimeTagSelectorProps> = ({
  current = 'unknown',
  onChange,
  disabled = false,
  showConfirmation = true,
  className,
}) => {
  const [selected, setSelected] = useState<MarketRegime>(current);
  const [pendingRegime, setPendingRegime] = useState<MarketRegime | null>(null);
  const [saved, setSaved] = useState(false);

  const handleSelect = (regime: MarketRegime) => {
    if (disabled) return;
    if (regime === selected) return;

    if (showConfirmation) {
      setPendingRegime(regime);
    } else {
      applyRegime(regime);
    }
  };

  const applyRegime = (regime: MarketRegime) => {
    setSelected(regime);
    setPendingRegime(null);
    onChange?.(regime);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const cancelPending = () => setPendingRegime(null);

  const currentOption = regimeOptions.find(o => o.value === selected)!;
  const CurrentIcon = currentOption.icon;

  return (
    <GlassCard variant="default" padding="md" className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
            Market Regime
          </h3>
          <div className="flex items-center gap-2 mt-1">
            <div className={cn('w-2 h-2 rounded-full', currentOption.dotClass)} />
            <span className="text-sm font-medium font-sans text-obsidian-400 dark:text-paper-100">
              {currentOption.label}
            </span>
            <AnimatePresence>
              {saved && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="flex items-center gap-1 text-xs font-mono text-gain"
                >
                  <Check className="w-3 h-3" />
                  Saved
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
        <div className={cn(
          'p-2 rounded-xl',
          currentOption.activeClass
        )}>
          <CurrentIcon className="w-5 h-5" />
        </div>
      </div>

      {/* Option grid */}
      <div className="grid grid-cols-1 gap-2">
        {regimeOptions.map(option => {
          const Icon = option.icon;
          const isActive = selected === option.value;
          const isPending = pendingRegime === option.value;

          return (
            <motion.button
              key={option.value}
              onClick={() => handleSelect(option.value)}
              disabled={disabled}
              whileTap={{ scale: disabled ? 1 : 0.98 }}
              className={cn(
                'w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-200 text-left',
                'focus:outline-none focus:ring-2 focus:ring-turquoise-mist/40',
                isActive
                  ? option.activeClass
                  : 'border-deep-teal-800/10 dark:border-white/10 text-obsidian-400/70 dark:text-paper-100/60 hover:border-deep-teal-800/20 dark:hover:border-white/20 hover:bg-deep-teal-800/5 dark:hover:bg-white/5',
                disabled && 'opacity-50 cursor-not-allowed',
                isPending && 'ring-2 ring-warning/30 border-warning/40'
              )}
            >
              <div className={cn(
                'p-1.5 rounded-lg shrink-0',
                isActive
                  ? 'bg-current/20'
                  : 'bg-deep-teal-800/5 dark:bg-white/5'
              )}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium font-sans leading-none">{option.label}</span>
                  {isActive && <Check className="w-3.5 h-3.5 shrink-0" />}
                </div>
                <span className="text-[11px] font-sans opacity-60 mt-0.5 block leading-tight">
                  {option.description}
                </span>
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Confirmation prompt */}
      <AnimatePresence>
        {pendingRegime && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.2 }}
            className="p-4 rounded-xl bg-warning/10 border border-warning/30 space-y-3"
          >
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-warning shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="text-sm font-medium font-sans text-obsidian-400 dark:text-paper-100">
                  Confirm regime change
                </p>
                <p className="text-xs font-sans text-obsidian-400/60 dark:text-paper-100/60">
                  Switching to{' '}
                  <span className="font-semibold">
                    {regimeOptions.find(o => o.value === pendingRegime)?.label}
                  </span>{' '}
                  will affect active strategy filters.
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => applyRegime(pendingRegime)}
                className="flex-1 py-2 rounded-lg bg-warning text-obsidian-400 text-xs font-mono font-bold uppercase tracking-widest hover:bg-warning/90 transition-colors"
              >
                Confirm
              </button>
              <button
                onClick={cancelPending}
                className="flex-1 py-2 rounded-lg border border-deep-teal-800/10 dark:border-white/10 text-obsidian-400/70 dark:text-paper-100/60 text-xs font-mono font-bold uppercase tracking-widest hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors"
              >
                Cancel
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
};
