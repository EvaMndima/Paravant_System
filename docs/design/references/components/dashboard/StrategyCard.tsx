
import React from 'react';
import { motion } from 'framer-motion';
import { 
  Play, Pause, Settings, Activity, AlertTriangle, 
  Cpu, TrendingUp, TrendingDown, Clock 
} from 'lucide-react';
import { GlassCard } from '../ui/GlassCard';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { cn, formatCurrency } from '../../lib/utils';

export type StrategyType = 'arbitrage' | 'momentum' | 'mean-reversion' | 'macro' | 'ml-signal';
export type StrategyStatus = 'active' | 'paused' | 'error' | 'training';
export type SignalAction = 'buy' | 'sell' | 'hold';

export interface StrategyPerformance {
  pnl: number;
  winRate: number;
  sharpe: number;
}

export interface StrategySignal {
  action: SignalAction;
  symbol: string;
  time: string;
}

export interface StrategyCardProps {
  id: string;
  name: string;
  type: StrategyType;
  status: StrategyStatus;
  performance: StrategyPerformance;
  lastSignal?: StrategySignal;
  onPause?: (id: string) => void;
  onResume?: (id: string) => void;
  onConfigure?: (id: string) => void;
  onClick?: (id: string) => void;
  className?: string;
}

const statusConfig = {
  active: { color: 'bg-gain', text: 'text-gain', label: 'Active', pulse: true },
  paused: { color: 'bg-warning', text: 'text-warning', label: 'Paused', pulse: false },
  error: { color: 'bg-loss', text: 'text-loss', label: 'Error', pulse: false },
  training: { color: 'bg-info', text: 'text-info', label: 'Training', pulse: true },
};

const typeConfig = {
  arbitrage: { label: 'Arbitrage', icon: Activity },
  momentum: { label: 'Momentum', icon: TrendingUp },
  'mean-reversion': { label: 'Mean Rev.', icon: TrendingDown },
  macro: { label: 'Macro', icon: AlertTriangle }, // Using generic for now
  'ml-signal': { label: 'ML Signal', icon: Cpu },
};

export const StrategyCard: React.FC<StrategyCardProps> = ({
  id,
  name,
  type,
  status,
  performance,
  lastSignal,
  onPause,
  onResume,
  onConfigure,
  onClick,
  className,
}) => {
  const statusInfo = statusConfig[status];
  const typeInfo = typeConfig[type];

  return (
    <GlassCard 
      variant="default" 
      padding="none" 
      enableHover={true}
      className={cn("flex flex-col h-full cursor-pointer", className)}
      onClick={() => onClick?.(id)}
    >
      {/* Header */}
      <div className="p-5 pb-3 border-b border-deep-teal-800/5 dark:border-white/5 space-y-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h3 className="font-display font-medium text-lg text-obsidian-400 dark:text-paper-100 group-hover:text-deep-teal-800 dark:group-hover:text-turquoise-mist transition-colors">
              {name}
            </h3>
            <Badge variant="outline" size="sm" className="gap-1.5 opacity-80">
              {typeInfo.icon && <typeInfo.icon className="w-3 h-3" />}
              {typeInfo.label}
            </Badge>
          </div>
          
          {/* Status Indicator */}
          <div className="flex items-center gap-2">
            <div className={cn("relative flex h-2.5 w-2.5")}>
               {statusInfo.pulse && (
                 <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", statusInfo.color)}></span>
               )}
               <span className={cn("relative inline-flex rounded-full h-2.5 w-2.5", statusInfo.color)}></span>
            </div>
            <span className={cn("text-xs font-mono uppercase tracking-wider", statusInfo.text)}>
              {statusInfo.label}
            </span>
          </div>
        </div>
      </div>

      {/* Metrics Body */}
      <div className="p-5 py-4 grid grid-cols-3 gap-4 border-b border-deep-teal-800/5 dark:border-white/5">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 mb-1">
            Total P&L
          </div>
          <div className={cn(
            "font-mono font-medium text-sm md:text-base truncate",
            performance.pnl >= 0 ? "text-gain" : "text-loss"
          )}>
            {performance.pnl >= 0 ? '+' : ''}{formatCurrency(performance.pnl)}
          </div>
        </div>
        
        <div className="text-center border-l border-r border-deep-teal-800/5 dark:border-white/5 px-2">
          <div className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 mb-1">
            Win Rate
          </div>
          <div className="font-mono font-medium text-sm md:text-base text-obsidian-400 dark:text-paper-100">
            {performance.winRate}%
          </div>
        </div>

        <div className="text-right">
          <div className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 mb-1">
            Sharpe
          </div>
          <div className="font-mono font-medium text-sm md:text-base text-obsidian-400 dark:text-paper-100">
            {performance.sharpe.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Footer / Controls */}
      <div className="p-4 bg-deep-teal-800/5 dark:bg-white/5 flex-1 flex flex-col justify-end">
        <div className="flex items-center justify-between">
          
          {/* Signal Info */}
          <div className="flex-1 min-w-0 mr-4">
            {lastSignal ? (
              <div className="flex flex-col">
                <div className="flex items-center gap-2 text-xs font-mono text-obsidian-400/60 dark:text-paper-100/60 mb-0.5">
                   <Clock className="w-3 h-3" />
                   <span>{lastSignal.time}</span>
                </div>
                <div className="flex items-center gap-2 truncate">
                  <span className={cn(
                    "text-xs font-bold uppercase",
                    lastSignal.action === 'buy' ? "text-gain" : lastSignal.action === 'sell' ? "text-loss" : "text-warning"
                  )}>
                    {lastSignal.action}
                  </span>
                  <span className="text-xs font-sans text-obsidian-400 dark:text-paper-100 font-medium">
                    {lastSignal.symbol}
                  </span>
                </div>
              </div>
            ) : (
              <span className="text-xs text-obsidian-400/40 dark:text-paper-100/40 font-mono italic">
                Awaiting signal...
              </span>
            )}
          </div>

          {/* Action Buttons - Stop Propagation to prevent card click */}
          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            {status === 'active' || status === 'training' ? (
               <Button 
                 variant="ghost" 
                 size="sm" 
                 onClick={() => onPause?.(id)}
                 className="h-8 w-8 p-0 rounded-full hover:bg-warning/10 hover:text-warning"
                 aria-label="Pause Agent"
               >
                 <Pause className="w-4 h-4" fill="currentColor" />
               </Button>
            ) : (
              <Button 
                 variant="ghost" 
                 size="sm" 
                 onClick={() => onResume?.(id)}
                 className="h-8 w-8 p-0 rounded-full hover:bg-gain/10 hover:text-gain"
                 aria-label="Resume Agent"
               >
                 <Play className="w-4 h-4" fill="currentColor" />
               </Button>
            )}

            <Button 
               variant="ghost" 
               size="sm" 
               onClick={() => onConfigure?.(id)}
               className="h-8 w-8 p-0 rounded-full"
               aria-label="Configure Agent"
            >
              <Settings className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </GlassCard>
  );
};
