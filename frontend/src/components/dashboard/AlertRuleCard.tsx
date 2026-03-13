import React, { useState } from 'react';
import { Bell, BellOff, Edit2, Trash2, AlertTriangle, TrendingDown, TrendingUp, Activity } from 'lucide-react';
import { motion } from 'framer-motion';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { Toggle } from '@/components/ui/Toggle';
import { cn } from '@/lib/utils';

export type AlertRuleStatus = 'active' | 'triggered' | 'disabled';
export type AlertRuleCondition = 'price_above' | 'price_below' | 'drawdown_exceeds' | 'pnl_drops' | 'pnl_reaches' | 'system_offline';

export interface AlertRule {
  id: string;
  name: string;
  condition: AlertRuleCondition;
  symbol?: string;
  threshold: number;
  unit: string;
  status: AlertRuleStatus;
  frequency: 'once' | 'always';
  lastTriggered?: string;
  channel: 'telegram' | 'email' | 'both';
}

export interface AlertRuleCardProps {
  rule: AlertRule;
  onToggle?: (id: string, enabled: boolean) => void;
  onEdit?: (rule: AlertRule) => void;
  onDelete?: (id: string) => void;
  className?: string;
}

const conditionConfig: Record<AlertRuleCondition, { icon: React.ElementType; label: string; color: string }> = {
  price_above:      { icon: TrendingUp,    label: 'Price above',      color: 'text-gain' },
  price_below:      { icon: TrendingDown,  label: 'Price below',      color: 'text-loss' },
  drawdown_exceeds: { icon: TrendingDown,  label: 'Drawdown exceeds', color: 'text-warning' },
  pnl_drops:        { icon: TrendingDown,  label: 'P&L drops below',  color: 'text-loss' },
  pnl_reaches:      { icon: TrendingUp,    label: 'P&L reaches',      color: 'text-gain' },
  system_offline:   { icon: Activity,      label: 'System goes',      color: 'text-warning' },
};

const statusBadge: Record<AlertRuleStatus, { variant: 'success' | 'warning' | 'neutral'; label: string; pulse: boolean }> = {
  active:    { variant: 'success', label: 'Active',    pulse: true },
  triggered: { variant: 'warning', label: 'Triggered', pulse: false },
  disabled:  { variant: 'neutral', label: 'Disabled',  pulse: false },
};

export const AlertRuleCard: React.FC<AlertRuleCardProps> = ({
  rule,
  onToggle,
  onEdit,
  onDelete,
  className,
}) => {
  const [enabled, setEnabled] = useState(rule.status !== 'disabled');
  const [confirmDelete, setConfirmDelete] = useState(false);

  const cond = conditionConfig[rule.condition];
  const CondIcon = cond.icon;
  const badge = statusBadge[rule.status];

  const handleToggle = (v: boolean) => {
    setEnabled(v);
    onToggle?.(rule.id, v);
  };

  const handleDelete = () => {
    if (confirmDelete) {
      onDelete?.(rule.id);
    } else {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 3000);
    }
  };

  return (
    <GlassCard
      variant="default"
      padding="md"
      className={cn(
        'transition-opacity duration-200',
        !enabled && 'opacity-60',
        className
      )}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={cn(
          'p-2 rounded-xl shrink-0',
          enabled
            ? rule.status === 'triggered'
              ? 'bg-warning/10 text-warning'
              : 'bg-gain/10 text-gain'
            : 'bg-deep-teal-800/5 dark:bg-white/5 text-obsidian-400/30 dark:text-paper-100/30'
        )}>
          {enabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* Name + status */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-sans font-medium text-obsidian-400 dark:text-paper-100 truncate">
              {rule.name}
            </span>
            <Badge variant={badge.variant} size="sm" dot={badge.pulse}>
              {badge.label}
            </Badge>
            {rule.channel !== 'email' && (
              <Badge variant="neutral" size="sm">Telegram</Badge>
            )}
          </div>

          {/* Condition description */}
          <div className="flex items-center gap-1.5 text-xs font-mono">
            <CondIcon className={cn('w-3.5 h-3.5 shrink-0', cond.color)} />
            <span className="text-obsidian-400/60 dark:text-paper-100/60">
              {cond.label}
              {rule.symbol && <span className="text-obsidian-400 dark:text-paper-100 font-medium ml-1">{rule.symbol}</span>}
              {' '}
              <span className="text-obsidian-400 dark:text-paper-100 font-medium">
                {rule.threshold}{rule.unit}
              </span>
            </span>
          </div>

          {/* Meta row */}
          <div className="flex items-center gap-3 text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40">
            <span>Fires: {rule.frequency}</span>
            {rule.lastTriggered && (
              <span>Last: {new Date(rule.lastTriggered).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          <Toggle
            checked={enabled}
            onCheckedChange={handleToggle}
            size="sm"
          />
          <button
            onClick={() => onEdit?.(rule)}
            className="p-1.5 rounded-lg text-obsidian-400/40 dark:text-paper-100/40 hover:text-obsidian-400 dark:hover:text-paper-100 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors"
            aria-label="Edit alert"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <motion.button
            onClick={handleDelete}
            whileTap={{ scale: 0.95 }}
            className={cn(
              'p-1.5 rounded-lg transition-colors',
              confirmDelete
                ? 'bg-loss/20 text-loss'
                : 'text-obsidian-400/40 dark:text-paper-100/40 hover:text-loss hover:bg-loss/10'
            )}
            aria-label={confirmDelete ? 'Click again to confirm delete' : 'Delete alert'}
          >
            {confirmDelete ? <AlertTriangle className="w-3.5 h-3.5" /> : <Trash2 className="w-3.5 h-3.5" />}
          </motion.button>
        </div>
      </div>
    </GlassCard>
  );
};

// Mock data helper for the gallery
export const MOCK_ALERT_RULES: AlertRule[] = [
  {
    id: 'ALT-001',
    name: 'BTC Price Alert',
    condition: 'price_above',
    symbol: 'BTCUSDT',
    threshold: 50_000,
    unit: ' USDT',
    status: 'active',
    frequency: 'once',
    channel: 'telegram',
  },
  {
    id: 'ALT-002',
    name: 'Portfolio Drawdown',
    condition: 'drawdown_exceeds',
    threshold: -10,
    unit: '%',
    status: 'triggered',
    frequency: 'always',
    lastTriggered: new Date(Date.now() - 3_600_000).toISOString(),
    channel: 'both',
  },
  {
    id: 'ALT-003',
    name: 'Daily P&L Target',
    condition: 'pnl_reaches',
    threshold: 500,
    unit: ' USDT',
    status: 'disabled',
    frequency: 'once',
    channel: 'telegram',
  },
];
