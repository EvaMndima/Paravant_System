
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Cpu,
  Play,
  Pause,
  StopCircle,
  TrendingUp,
  Activity,
  Plus,
  Search,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { MetricCard } from '@/components/ui/MetricCard';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Skeleton } from '@/components/ui/Skeleton';
import { ApiErrorDisplay } from '@/components/ui/ApiErrorDisplay';
import { useStrategies, useTransitionStrategy } from '@/hooks';
import { useToast } from '@/contexts/ToastContext';
import type { StrategyResponse } from '@/types/api';

// Pending confirmation shape
interface PendingTransition {
  newStatus: string;
  label: string;
}

const StrategyCard = ({
  strategy,
  onClick,
}: {
  strategy: StrategyResponse;
  onClick: () => void;
}) => {
  const transitionMutation = useTransitionStrategy();
  const { addToast } = useToast();
  const [pending, setPending] = useState<PendingTransition | null>(null);

  const handleTransition = async (
    e: React.MouseEvent,
    newStatus: string,
  ) => {
    e.stopPropagation();
    try {
      await transitionMutation.mutateAsync({ strategyId: strategy.id, newStatus });
      addToast('success', `Strategy ${newStatus}`, `${strategy.name} is now ${newStatus}.`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Transition failed';
      addToast('error', 'Transition failed', msg);
    } finally {
      setPending(null);
    }
  };

  const requestTransition = (e: React.MouseEvent, newStatus: string, label: string) => {
    e.stopPropagation();
    setPending({ newStatus, label });
  };

  const isBusy = transitionMutation.isPending;

  return (
    <motion.div whileHover={{ y: -5 }} transition={{ duration: 0.2 }}>
      <GlassCard
        variant="elevated"
        className="cursor-pointer group relative overflow-hidden h-full flex flex-col"
        onClick={onClick}
      >
        {/* Status Indicator Line */}
        <div
          className={`absolute top-0 left-0 w-1 h-full ${
            strategy.status === 'active'
              ? 'bg-gain'
              : strategy.status === 'paused'
                ? 'bg-warning'
                : 'bg-loss'
          }`}
        />

        <div className="pl-2 flex justify-between items-start mb-4">
          <div>
            <h3 className="font-display text-lg font-medium group-hover:text-turquoise-mist transition-colors">
              {strategy.name}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="neutral" size="sm">
                {strategy.type}
              </Badge>
              <Badge variant="info" size="sm">
                {strategy.template_id}
              </Badge>
            </div>
          </div>
          <div
            className={`p-2 rounded-lg bg-white/5 ${
              strategy.status === 'active'
                ? 'text-gain'
                : strategy.status === 'paused'
                  ? 'text-warning'
                  : 'text-obsidian-400'
            }`}
          >
            {strategy.status === 'active' && <Play className="w-5 h-5 fill-current" />}
            {strategy.status === 'paused' && <Pause className="w-5 h-5 fill-current" />}
            {strategy.status === 'stopped' && <StopCircle className="w-5 h-5" />}
          </div>
        </div>

        <div className="pl-2 grid grid-cols-2 gap-4 mb-6 flex-1">
          <div>
            <div className="text-xs text-obsidian-400/60 dark:text-paper-100/60 font-mono mb-1">
              Symbols
            </div>
            <div className="font-mono text-sm text-paper-100">
              {strategy.symbols?.join(', ') || '-'}
            </div>
          </div>
          <div>
            <div className="text-xs text-obsidian-400/60 dark:text-paper-100/60 font-mono mb-1">
              Version
            </div>
            <div className="font-mono text-sm text-paper-100">
              {strategy.template_version}
            </div>
          </div>
          <div className="col-span-2">
            <div className="text-xs text-obsidian-400/60 dark:text-paper-100/60 font-mono mb-1">
              Description
            </div>
            <div className="text-sm text-paper-100/70 line-clamp-2">
              {strategy.description || 'No description'}
            </div>
          </div>
        </div>

        {/* Quick Actions + Status */}
        <div className="pl-2 pt-4 border-t border-deep-teal-800/5 dark:border-white/5 space-y-3">
          {/* Status badge row */}
          <div className="flex justify-between items-center">
            <span className="text-xs font-mono opacity-40">
              {strategy.created_at
                ? `Since ${new Date(strategy.created_at).toLocaleDateString()}`
                : `ID: ${strategy.id.split('-')[0]}`}
            </span>
            <Badge
              variant={
                strategy.status === 'active'
                  ? 'success'
                  : strategy.status === 'paused'
                    ? 'warning'
                    : 'danger'
              }
              dot
              pulsing={strategy.status === 'active'}
              size="sm"
            >
              {strategy.status.toUpperCase()}
            </Badge>
          </div>

          {/* Quick action buttons — stop propagation so they don't trigger navigation */}
          <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
            {pending ? (
              /* Inline confirmation strip */
              <div className="flex items-center gap-2 w-full">
                <span className="text-xs text-obsidian-400 dark:text-paper-100/60 flex-1">
                  {pending.label}?
                </span>
                <button
                  onClick={(e) => handleTransition(e, pending.newStatus)}
                  disabled={isBusy}
                  className="px-2 py-1 rounded-md text-xs font-medium bg-loss text-white hover:bg-loss/80 transition-colors disabled:opacity-50"
                >
                  {isBusy ? '…' : 'Confirm'}
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); setPending(null); }}
                  className="px-2 py-1 rounded-md text-xs font-medium border border-obsidian-400/20 hover:bg-deep-teal-800/5 transition-colors"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <>
                {strategy.status === 'active' && (
                  <button
                    onClick={(e) => requestTransition(e, 'paused', 'Pause this strategy')}
                    disabled={isBusy}
                    className="flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-warning/10 text-warning border border-warning/20 hover:bg-warning/20 transition-colors disabled:opacity-50"
                    title="Pause strategy"
                  >
                    <Pause className="w-3 h-3" /> Pause
                  </button>
                )}
                {strategy.status === 'paused' && (
                  <button
                    onClick={(e) => handleTransition(e, 'active')}
                    disabled={isBusy}
                    className="flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-gain/10 text-gain border border-gain/20 hover:bg-gain/20 transition-colors disabled:opacity-50"
                    title="Resume strategy"
                  >
                    <Play className="w-3 h-3" /> Resume
                  </button>
                )}
                {strategy.status !== 'stopped' && (
                  <button
                    onClick={(e) => requestTransition(e, 'stopped', 'Stop this strategy')}
                    disabled={isBusy}
                    className="flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-loss/10 text-loss border border-loss/20 hover:bg-loss/20 transition-colors disabled:opacity-50"
                    title="Stop strategy"
                  >
                    <StopCircle className="w-3 h-3" /> Stop
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </GlassCard>
    </motion.div>
  );
};

export const StrategiesPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: strategies, isLoading, isError, error, refetch } = useStrategies();

  const [filter, setFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'active' | 'paused' | 'stopped'>(
    'ALL'
  );

  const filteredStrategies = (strategies ?? []).filter((s) => {
    const matchesSearch = s.name.toLowerCase().includes(filter.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || s.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const activeCount = (strategies ?? []).filter((s) => s.status === 'active').length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-8 pb-12"
    >
      {isError && <ApiErrorDisplay error={error as Error} onRetry={refetch} />}
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-medium text-deep-teal-800 dark:text-paper-100 mb-1">
            Strategies
          </h1>
          <p className="text-obsidian-400/60 dark:text-paper-100/60 font-sans">
            Manage and monitor trading algorithms.
          </p>
        </div>
        <Button onClick={() => {}} className="gap-2" disabled>
          <Plus className="w-4 h-4" /> New Strategy
        </Button>
      </div>

      {/* Metrics Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-2xl" />
          ))
        ) : (
          <>
            <MetricCard
              title="Total Strategies"
              value={strategies?.length ?? 0}
              format="raw"
              icon={TrendingUp}
            />
            <MetricCard title="Active Strategies" value={activeCount} format="raw" icon={Activity} />
            <MetricCard
              title="Templates"
              value={new Set(strategies?.map((s) => s.template_id)).size ?? 0}
              format="raw"
              icon={Cpu}
            />
          </>
        )}
      </div>

      {/* Controls & Grid */}
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row gap-4 justify-between">
          {/* Status Filter Tabs */}
          <div className="flex bg-deep-teal-800/5 dark:bg-white/5 p-1 rounded-lg self-start">
            {(['ALL', 'active', 'paused', 'stopped'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setStatusFilter(t)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                  statusFilter === t
                    ? 'bg-white shadow-sm text-deep-teal-800'
                    : 'text-obsidian-400/60 dark:text-paper-100/60 hover:text-deep-teal-800 dark:hover:text-paper-100'
                }`}
              >
                {t.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative w-full md:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-obsidian-400/50" />
            <Input
              placeholder="Search strategies..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-64 rounded-2xl" />
            ))}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredStrategies.map((strategy) => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  onClick={() => navigate(`/strategies/${strategy.id}`)}
                />
              ))}
            </div>

            {filteredStrategies.length === 0 && (
              <div className="text-center py-20 opacity-50">
                <p className="font-mono text-sm">
                  No strategies found matching your filters.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </motion.div>
  );
};
