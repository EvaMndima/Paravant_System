import React, { useState } from 'react';
import {
  TrendingUp,
  Wallet,
  Activity,
  AlertTriangle,
  Zap,
  Target,
  BarChart2,
  X as CloseIcon,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { MetricCard } from '@/components/ui/MetricCard';
import { GlassCard } from '@/components/ui/GlassCard';
import { DataTable } from '@/components/ui/DataTable';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { PositionCloseModal } from '@/components/modals/PositionCloseModal';
import { PositionDetailDrawer } from '@/components/ui/PositionDetailDrawer';
import type { PositionResponse } from '@/types/api';
import { ApiErrorDisplay } from '@/components/ui/ApiErrorDisplay';
import { formatCurrency, formatPercent } from '@/lib/utils';
import {
  useDashboardSummary,
  useEquityCurve,
  useRiskStatus,
  useRegime,
  useDashboardPositions,
  useStrategies,
  useDashboardAlerts,
} from '@/hooks';
import { Area, AreaChart, ResponsiveContainer } from 'recharts';
import type { DashboardPositionEntry } from '@/types/api';

// --- Hero Metrics ---
const HeroMetrics = () => {
  const { data: summary, isLoading: summaryLoading, isError: summaryError, error, refetch } = useDashboardSummary();
  const { data: equity, isLoading: equityLoading } = useEquityCurve();

  if (summaryLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-32 rounded-2xl" />
        ))}
      </div>
    );
  }

  if (summaryError) {
    return <ApiErrorDisplay error={error as Error} onRetry={refetch} />;
  }

  const PortfolioSparkline = equityLoading ? null : (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={equity?.data ?? []}>
        <defs>
          <linearGradient id="valueGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2A9D8F" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#2A9D8F" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="equity"
          stroke="#2A9D8F"
          strokeWidth={2}
          fill="url(#valueGradient)"
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {/* PRD §6.2.2: 6 required MetricCards */}
      <MetricCard
        title="Portfolio Value"
        value={summary?.portfolio_value ?? 0}
        format="currency"
        change={summary?.daily_change_pct ?? 0}
        icon={Wallet}
        sparkline={PortfolioSparkline}
        variant="elevated"
        delay={0}
      />
      <MetricCard
        title="Daily P&L"
        value={summary?.daily_change ?? 0}
        format="currency"
        change={summary?.daily_change_pct ?? 0}
        changeLabel="today"
        icon={TrendingUp}
        delay={0.05}
      />
      <MetricCard
        title="Open Positions"
        value={summary?.open_positions_count ?? 0}
        format="raw"
        icon={BarChart2}
        delay={0.1}
      />
      <MetricCard
        title="Win Rate (7D)"
        value={summary?.win_rate_7d ?? 0}
        format="percent"
        icon={Target}
        delay={0.15}
      />
      <MetricCard
        title="Active Strategies"
        value={summary?.active_strategies_count ?? 0}
        format="raw"
        icon={Zap}
        delay={0.2}
      />
      <MetricCard
        title="Open Risk"
        value={summary?.current_drawdown_pct ?? 0}
        format="percent"
        suffix="DD"
        change={summary?.daily_loss_used_pct ?? 0}
        changeLabel="daily loss used"
        icon={AlertTriangle}
        variant={(summary?.current_drawdown_pct ?? 0) > 10 ? 'dark' : 'default'}
        delay={0.25}
      />
    </div>
  );
};

// --- Risk Status Widget ---
const RiskStatusWidget = () => {
  const { data: risk, isLoading } = useRiskStatus();

  if (isLoading) {
    return <Skeleton className="h-64 rounded-2xl" />;
  }

  const getRiskColor = (usage: number) => {
    if (usage > 0.9) return 'bg-loss';
    if (usage > 0.7) return 'bg-warning';
    return 'bg-gain';
  };

  const drawdownPct = risk?.current_drawdown_pct ?? 0;
  const dailyLossPct = risk?.daily_loss_used_pct ?? 0;
  const maxDrawdown = 20;
  const maxDailyLoss = 100;

  return (
    <GlassCard variant="dark" className="h-full">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-sm font-mono font-bold uppercase tracking-widest text-turquoise-mist">
          Risk Management
        </h3>
        <Badge
          variant={risk?.kill_switch_active ? 'danger' : 'success'}
          dot
          pulsing={risk?.kill_switch_active}
        >
          {risk?.kill_switch_active ? 'KILL SWITCH' : risk?.risk_status ?? 'NORMAL'}
        </Badge>
      </div>

      <div className="space-y-6">
        {/* Drawdown */}
        <div>
          <div className="flex justify-between text-xs mb-2 font-mono">
            <span className="text-paper-100/60">Max Drawdown</span>
            <span className="text-paper-100">
              {formatPercent(drawdownPct)}{' '}
              <span className="text-paper-100/40">/ {maxDrawdown}%</span>
            </span>
          </div>
          <div className="h-2 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${Math.min((drawdownPct / maxDrawdown) * 100, 100)}%` }}
              className={`h-full rounded-full ${getRiskColor(drawdownPct / maxDrawdown)}`}
            />
          </div>
        </div>

        {/* Daily Loss */}
        <div>
          <div className="flex justify-between text-xs mb-2 font-mono">
            <span className="text-paper-100/60">Daily Loss Limit</span>
            <span className="text-paper-100">
              {formatPercent(dailyLossPct)}{' '}
              <span className="text-paper-100/40">used</span>
            </span>
          </div>
          <div className="h-2 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(dailyLossPct, 100)}%` }}
              className={`h-full rounded-full ${getRiskColor(dailyLossPct / maxDailyLoss)}`}
            />
          </div>
        </div>

        {/* Circuit Breakers */}
        <div className="grid grid-cols-2 gap-2 mt-4">
          {Object.entries(risk?.circuit_breakers ?? {}).length > 0 ? (
            Object.entries(risk?.circuit_breakers ?? {}).slice(0, 4).map(([key, val]) => (
              <div key={key} className="bg-white/5 p-2 rounded flex items-center gap-2">
                <div
                  className={`w-1.5 h-1.5 rounded-full ${
                    val ? 'bg-loss shadow-[0_0_5px_rgba(231,76,60,0.5)]' : 'bg-gain shadow-[0_0_5px_rgba(46,204,113,0.5)]'
                  }`}
                />
                <span className="text-[10px] font-mono uppercase text-paper-100/80">
                  {key.replace(/_/g, ' ')}
                </span>
              </div>
            ))
          ) : (
            <>
              <div className="bg-white/5 p-2 rounded flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-gain shadow-[0_0_5px_rgba(46,204,113,0.5)]" />
                <span className="text-[10px] font-mono uppercase text-paper-100/80">
                  Volatility Protection
                </span>
              </div>
              <div className="bg-white/5 p-2 rounded flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-gain shadow-[0_0_5px_rgba(46,204,113,0.5)]" />
                <span className="text-[10px] font-mono uppercase text-paper-100/80">
                  Liquidity Guard
                </span>
              </div>
            </>
          )}
        </div>
      </div>
    </GlassCard>
  );
};

// --- Regime Indicator ---
const RegimeIndicator = () => {
  const { data: regime, isLoading } = useRegime();

  if (isLoading) {
    return <Skeleton className="h-64 rounded-2xl" />;
  }

  return (
    <GlassCard variant="dark" className="h-full">
      <h3 className="text-sm font-mono font-bold uppercase tracking-widest text-turquoise-mist opacity-90 mb-6">
        Market Regime
      </h3>

      <div className="flex items-center gap-4 mb-6">
        <div className="bg-deep-teal-800/5 dark:bg-white/5 p-3 rounded-xl">
          <Activity className="w-8 h-8 text-deep-teal-800 dark:text-turquoise-mist" />
        </div>
        <div>
          <div className="text-xl font-bold font-sans text-deep-teal-800 dark:text-paper-100">
            {(regime?.regime ?? 'unknown').replace(/_/g, ' ')}
          </div>
          <div className="text-xs text-obsidian-400/60 dark:text-paper-100/60 font-mono mt-1">
            Updated: {regime?.updated_at ? new Date(regime.updated_at).toLocaleDateString() : '-'}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {[
          {
            label: 'Account',
            val: regime?.account_id ? regime.account_id.slice(0, 8) : '-',
            color: 'text-turquoise-mist',
          },
          {
            label: 'Mode',
            val: regime?.regime?.includes('trending') ? 'Trend' : regime?.regime?.includes('rang') ? 'Range' : 'Mixed',
            color: regime?.regime?.includes('trending') ? 'text-gain' : 'text-warning',
          },
          { label: 'Status', val: 'Active', color: 'text-gain' },
        ].map((i) => (
          <div
            key={i.label}
            className="bg-deep-teal-800/5 dark:bg-white/5 p-2 rounded text-center"
          >
            <div className="text-[10px] uppercase text-obsidian-400/40 dark:text-paper-100/40 font-bold mb-1">
              {i.label}
            </div>
            <div className={`text-xs font-mono font-bold ${i.color}`}>{i.val}</div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
};

// Adapt a DashboardPositionEntry to the PositionResponse shape the drawer expects
function toPositionResponse(p: DashboardPositionEntry): PositionResponse {
  const openedAt = new Date(Date.now() - p.duration_hours * 3_600_000).toISOString();
  return {
    id: p.id,
    account_id: '',
    strategy_id: null,
    symbol: p.symbol,
    side: p.side,
    size: p.quantity,
    entry_price: p.entry_price,
    current_price: p.current_price,
    unrealized_pnl: p.unrealized_pnl,
    return_pct: p.unrealized_pnl_pct,
    realized_pnl: 0,
    commission_paid: 0,
    status: 'OPEN',
    opened_at: openedAt,
    closed_at: null,
    exit_price: null,
  };
}

// --- Positions Table ---
const PositionsWidget = () => {
  const { data: positions, isLoading } = useDashboardPositions();
  const [closePosition, setClosePosition] = useState<DashboardPositionEntry | null>(null);
  const [drawerPosition, setDrawerPosition] = useState<DashboardPositionEntry | null>(null);
  const navigate = useNavigate();
  void navigate; // keep import — used for future direct nav fallback

  const columns = [
    {
      key: 'symbol',
      header: 'Instrument',
      render: (val: unknown) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-deep-teal-800/10 dark:bg-white/10 flex items-center justify-center font-bold text-[10px]">
            {(val as string).substring(0, 1)}
          </div>
          <div>
            <div className="font-bold">{val as string}</div>
            <div className="text-xs opacity-50">Perpetual</div>
          </div>
        </div>
      ),
    },
    {
      key: 'strategy_name',
      header: 'Strategy',
      className: 'hidden md:table-cell',
      render: (val: unknown) => <span>{(val as string | null) || '-'}</span>,
    },
    {
      key: 'quantity',
      header: 'Size',
      render: (val: unknown) => <span className="font-mono">{val as number}</span>,
    },
    {
      key: 'entry_price',
      header: 'Entry',
      render: (val: unknown) => <span className="font-mono">{formatCurrency(val as number)}</span>,
    },
    {
      key: 'current_price',
      header: 'Mark',
      render: (val: unknown) => <span className="font-mono">{formatCurrency(val as number)}</span>,
    },
    {
      key: 'unrealized_pnl',
      header: 'P&L',
      align: 'right' as const,
      render: (val: unknown) => (
        <span className={`font-mono font-bold ${(val as number) >= 0 ? 'text-gain' : 'text-loss'}`}>
          {(val as number) >= 0 ? '+' : ''}
          {formatCurrency(val as number)}
        </span>
      ),
    },
    {
      key: 'symbol',
      header: '',
      align: 'right' as const,
      render: (_val: unknown, row: unknown) => (
        <button
          onClick={(e) => { e.stopPropagation(); setClosePosition(row as DashboardPositionEntry); }}
          className="p-1.5 rounded-lg text-loss/60 hover:text-loss hover:bg-loss/10 transition-colors"
          title="Close position"
          aria-label="Close position"
        >
          <CloseIcon className="w-4 h-4" />
        </button>
      ),
    },
  ];

  return (
    <>
      <GlassCard variant="elevated" padding="none" className="overflow-hidden">
        <div className="px-6 py-4 border-b border-deep-teal-800/5 dark:border-white/5 flex justify-between items-center bg-paper-100/50 dark:bg-obsidian-300/50">
          <h3 className="font-display text-lg font-medium">Open Positions</h3>
          <span className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
            {positions?.length ?? 0} positions
          </span>
        </div>
        {isLoading ? (
          <div className="p-6">
            <Skeleton className="h-48 w-full" />
          </div>
        ) : positions && positions.length > 0 ? (
          <DataTable
            columns={columns}
            data={positions}
            className="border-none bg-transparent"
            onRowClick={(row) => setDrawerPosition(row as DashboardPositionEntry)}
          />
        ) : (
          <div className="text-center py-12 text-obsidian-400/40 dark:text-paper-100/40 text-sm">
            No open positions
          </div>
        )}
      </GlassCard>

      {/* Position Close Modal */}
      {closePosition && (
        <PositionCloseModal
          position={closePosition}
          isOpen={!!closePosition}
          onClose={() => setClosePosition(null)}
        />
      )}

      {/* Position Detail Drawer (slide-in from right on row click) */}
      <PositionDetailDrawer
        isOpen={!!drawerPosition}
        position={drawerPosition ? toPositionResponse(drawerPosition) : null}
        onClose={() => setDrawerPosition(null)}
      />
    </>
  );
};

// --- Strategies & Alerts Split ---
const StrategiesList = () => {
  const { data: strategies, isLoading } = useStrategies();

  if (isLoading) {
    return (
      <GlassCard variant="subtle" className="h-full">
        <Skeleton className="h-6 w-40 mb-4" />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-xl" />
          ))}
        </div>
      </GlassCard>
    );
  }

  const topStrategies = (strategies ?? []).slice(0, 3);

  return (
    <GlassCard variant="subtle" className="h-full">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-display text-lg font-medium">Active Strategies</h3>
        <span className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
          {strategies?.length ?? 0} total
        </span>
      </div>
      <div className="space-y-3">
        {topStrategies.length > 0 ? (
          topStrategies.map((strat) => (
            <div
              key={strat.id}
              className="flex items-center justify-between p-3 rounded-xl bg-paper-100/50 dark:bg-obsidian-400/50 border border-deep-teal-800/5 dark:border-white/5 hover:border-turquoise-mist/30 transition-colors cursor-pointer group"
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-2 h-2 rounded-full ${
                    strat.status === 'active' ? 'bg-gain animate-pulse' : 'bg-warning'
                  }`}
                />
                <div>
                  <div className="font-sans font-medium text-sm group-hover:text-turquoise-mist transition-colors">
                    {strat.name}
                  </div>
                  <div className="text-[10px] font-mono opacity-50">{strat.type}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10px] opacity-50 font-mono">
                  {strat.symbols?.join(', ') || '-'}
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-8 text-obsidian-400/40 dark:text-paper-100/40 text-sm">
            No strategies configured
          </div>
        )}
      </div>
    </GlassCard>
  );
};

const RecentAlerts = () => {
  const { data: alerts, isLoading } = useDashboardAlerts();

  if (isLoading) {
    return (
      <GlassCard variant="subtle" className="h-full">
        <Skeleton className="h-6 w-40 mb-4" />
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </GlassCard>
    );
  }

  const recentAlerts = (alerts ?? []).slice(0, 5);

  return (
    <GlassCard variant="subtle" className="h-full">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-display text-lg font-medium">Recent Alerts</h3>
        <span className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
          {alerts?.length ?? 0} total
        </span>
      </div>
      <div className="space-y-4 relative">
        {/* Timeline line */}
        <div className="absolute left-2.5 top-2 bottom-2 w-px bg-deep-teal-800/10 dark:bg-white/10" />

        {recentAlerts.length > 0 ? (
          recentAlerts.map((alert) => {
            const isRisk =
              alert.action.includes('kill') ||
              alert.action.includes('risk') ||
              alert.action.includes('breach');
            const isWarning =
              alert.action.includes('warn') || alert.action.includes('limit');

            return (
              <div key={alert.id} className="relative pl-8 flex flex-col gap-1">
                <div
                  className={`absolute left-0 top-1.5 w-5 h-5 rounded-full border-2 flex items-center justify-center bg-paper-100 dark:bg-obsidian-400 z-10 ${
                    isRisk
                      ? 'border-loss text-loss'
                      : isWarning
                        ? 'border-warning text-warning'
                        : 'border-info text-info'
                  }`}
                >
                  <div
                    className={`w-1.5 h-1.5 rounded-full ${
                      isRisk ? 'bg-loss' : isWarning ? 'bg-warning' : 'bg-info'
                    }`}
                  />
                </div>
                <div className="text-xs font-mono opacity-50 mb-0.5">
                  {new Date(alert.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
                <div className="text-sm font-medium leading-tight">
                  {alert.action.replace(/_/g, ' ')}
                  {alert.actor && (
                    <span className="text-xs opacity-50 ml-2">by {alert.actor}</span>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <div className="text-center py-8 text-obsidian-400/40 dark:text-paper-100/40 text-sm pl-0">
            No recent alerts
          </div>
        )}
      </div>
    </GlassCard>
  );
};

export const CockpitPage: React.FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6 pb-12"
    >
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-medium text-deep-teal-800 dark:text-paper-100 mb-1">
            Investor Cockpit
          </h1>
          <p className="text-obsidian-400/60 dark:text-paper-100/60 font-sans">
            Real-time market overview and portfolio status.
          </p>
        </div>
        <div className="flex gap-2">
          <div className="px-3 py-1 bg-deep-teal-800/5 dark:bg-white/5 rounded-lg text-xs font-mono">
            <span className="opacity-50 mr-2">LAST SYNC</span>
            <span className="font-bold text-turquoise-mist">LIVE</span>
          </div>
        </div>
      </div>

      <HeroMetrics />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RiskStatusWidget />
        <RegimeIndicator />
      </div>

      <PositionsWidget />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StrategiesList />
        <RecentAlerts />
      </div>
    </motion.div>
  );
};
