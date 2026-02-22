
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  Lock,
  Unlock,
  AlertOctagon,
  ShieldAlert,
  BarChart2,
  History,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { DataTable } from '@/components/ui/DataTable';
import { Skeleton } from '@/components/ui/Skeleton';
import { GaugeChart } from '@/components/charts/GaugeChart';
import { ApiErrorDisplay } from '@/components/ui/ApiErrorDisplay';
import { formatPercent } from '@/lib/utils';
import type { DerivedRiskStatus, RiskLimits, AlertEntry, DashboardPositionEntry } from '@/types/api';
import {
  useKillSwitch,
  useRiskStatus,
  useDashboardAlerts,
  useDashboardPositions,
} from '@/hooks';
import {
  useRiskLimits,
  useDashboardSummary,
} from '@/hooks';
import {
  useActivateKillSwitch,
  useDeactivateKillSwitch,
  useGetDeactivationCode,
} from '@/hooks';
import { useToast } from '@/contexts/ToastContext';

// ---------------------------------------------------------------------------
// Utility: derive circuit breaker rows from risk status + limits
// ---------------------------------------------------------------------------

interface CircuitBreakerRow {
  name: string;
  threshold: string;
  current: string;
  usedPct: number;
  status: 'CLOSED' | 'WARNING' | 'OPEN';
}

function deriveCircuitBreakers(
  riskStatus: DerivedRiskStatus | undefined,
  limits: RiskLimits | undefined,
): CircuitBreakerRow[] {
  if (!riskStatus || !limits) return [];

  const toStatus = (pct: number): 'CLOSED' | 'WARNING' | 'OPEN' => {
    if (pct >= 100) return 'OPEN';
    if (pct >= 80) return 'WARNING';
    return 'CLOSED';
  };

  const toUsedPct = (current: number, limit: number): number =>
    limit > 0 ? Math.min((current / limit) * 100, 100) : 0;

  const dailyPct = toUsedPct(riskStatus.daily_loss_used_pct, limits.max_daily_loss_pct);
  const drawdownPct = toUsedPct(riskStatus.current_drawdown_pct, limits.max_total_drawdown_pct);
  const positionPct = toUsedPct(riskStatus.open_positions, limits.max_positions);

  return [
    {
      name: 'Daily Loss Limit',
      threshold: formatPercent(limits.max_daily_loss_pct),
      current: formatPercent(riskStatus.daily_loss_used_pct),
      usedPct: dailyPct,
      status: toStatus(dailyPct),
    },
    {
      name: 'Max Drawdown',
      threshold: formatPercent(limits.max_total_drawdown_pct),
      current: formatPercent(riskStatus.current_drawdown_pct),
      usedPct: drawdownPct,
      status: toStatus(drawdownPct),
    },
    {
      name: 'Position Count',
      threshold: String(limits.max_positions),
      current: String(riskStatus.open_positions),
      usedPct: positionPct,
      status: toStatus(positionPct),
    },
    {
      name: 'Kill Switch',
      threshold: 'Manual',
      current: riskStatus.kill_switch_active ? 'ACTIVE' : 'INACTIVE',
      usedPct: riskStatus.kill_switch_active ? 100 : 0,
      status: riskStatus.kill_switch_active ? 'OPEN' : 'CLOSED',
    },
  ];
}

// ---------------------------------------------------------------------------
// Kill Switch Component
// ---------------------------------------------------------------------------

const KillSwitch = () => {
  const { data: killSwitch, isLoading, isError, error, refetch } = useKillSwitch();
  const activateMutation = useActivateKillSwitch();
  const deactivateMutation = useDeactivateKillSwitch();
  const deactivationCodeMutation = useGetDeactivationCode();
  const { addToast } = useToast();

  const [showActivateModal, setShowActivateModal] = useState(false);
  const [showDeactivateModal, setShowDeactivateModal] = useState(false);
  const [activateReason, setActivateReason] = useState('');
  const [deactivateInput, setDeactivateInput] = useState('');
  const [deactivationCode, setDeactivationCode] = useState('');

  const isActive = killSwitch?.active ?? false;

  const handleActivate = () => {
    if (!activateReason.trim()) return;
    activateMutation.mutate(activateReason, {
      onSuccess: () => {
        addToast('warning', 'Kill Switch Activated', 'All trading has been halted.');
        setShowActivateModal(false);
        setActivateReason('');
      },
      onError: (error) => {
        addToast('error', 'Activation Failed', error.message);
      },
    });
  };

  const handleRequestDeactivation = () => {
    deactivationCodeMutation.mutate(undefined, {
      onSuccess: (data) => {
        setDeactivationCode(data.code);
        setShowDeactivateModal(true);
      },
      onError: (error) => {
        addToast('error', 'Failed to get deactivation code', error.message);
      },
    });
  };

  const handleDeactivate = () => {
    if (deactivateInput !== 'DEACTIVATE') return;
    deactivateMutation.mutate(deactivationCode, {
      onSuccess: () => {
        addToast('success', 'Kill Switch Deactivated', 'Trading has been resumed.');
        setShowDeactivateModal(false);
        setDeactivateInput('');
        setDeactivationCode('');
      },
      onError: (error) => {
        addToast('error', 'Deactivation Failed', error.message);
      },
    });
  };

  if (isLoading) {
    return <Skeleton className="h-28 w-full rounded-2xl" />;
  }

  if (isError) {
    return <ApiErrorDisplay error={error as Error} onRetry={refetch} />;
  }

  return (
    <>
      <GlassCard
        variant="elevated"
        className={isActive ? 'border-loss/50 bg-loss/10' : 'border-loss/30 bg-loss/5'}
      >
        <div
          role={isActive ? 'alert' : undefined}
          aria-live={isActive ? 'assertive' : undefined}
          className="flex flex-col md:flex-row items-center justify-between gap-6"
        >
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-full ${isActive ? 'bg-loss/20' : 'bg-loss/10'} text-loss`}>
              {isActive ? (
                <motion.div
                  animate={{ scale: [1, 1.15, 1] }}
                  transition={{ repeat: Infinity, duration: 1.5 }}
                >
                  <ShieldAlert className="w-8 h-8" />
                </motion.div>
              ) : (
                <AlertOctagon className="w-8 h-8" />
              )}
            </div>
            <div>
              <h3 className="text-xl font-display font-bold text-loss">
                Global Kill Switch
                {isActive && (
                  <Badge variant="danger" dot pulsing className="ml-3 align-middle">
                    ACTIVE
                  </Badge>
                )}
              </h3>
              <p className="text-obsidian-400 dark:text-paper-100/70 text-sm">
                {isActive
                  ? `Activated: ${killSwitch?.reason || 'No reason provided'}. All trading is halted.`
                  : 'Immediately stop all strategies and cancel all open orders.'}
              </p>
              {isActive && killSwitch?.activated_at && (
                <p className="text-xs font-mono text-loss/70 mt-1">
                  Since {new Date(killSwitch.activated_at).toLocaleString()}
                  {killSwitch.duration_seconds != null && (
                    <> ({Math.round(killSwitch.duration_seconds / 60)}m ago)</>
                  )}
                </p>
              )}
            </div>
          </div>

          {isActive ? (
            <Button
              variant="secondary"
              size="lg"
              className="w-full md:w-auto gap-2"
              onClick={handleRequestDeactivation}
              isLoading={deactivationCodeMutation.isPending}
            >
              <Unlock className="w-5 h-5" />
              DEACTIVATE
            </Button>
          ) : (
            <Button
              variant="danger"
              size="lg"
              className="w-full md:w-auto gap-2 shadow-lg shadow-loss/20"
              onClick={() => setShowActivateModal(true)}
            >
              <Lock className="w-5 h-5" />
              ENGAGE KILL SWITCH
            </Button>
          )}
        </div>
      </GlassCard>

      {/* Activate Confirmation Modal */}
      <Modal
        isOpen={showActivateModal}
        onClose={() => setShowActivateModal(false)}
        title="Activate Kill Switch"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-obsidian-400/80 dark:text-paper-100/80">
            This will immediately halt all trading activity, cancel pending orders,
            and prevent new orders from being placed.
          </p>
          <Input
            label="Reason for activation"
            placeholder="e.g. Market crash, suspicious activity..."
            value={activateReason}
            onChange={(e) => setActivateReason(e.target.value)}
          />
          <div className="flex gap-3 justify-end">
            <Button variant="ghost" onClick={() => setShowActivateModal(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleActivate}
              disabled={!activateReason.trim()}
              isLoading={activateMutation.isPending}
            >
              Confirm Activation
            </Button>
          </div>
        </div>
      </Modal>

      {/* Deactivate Confirmation Modal */}
      <Modal
        isOpen={showDeactivateModal}
        onClose={() => {
          setShowDeactivateModal(false);
          setDeactivateInput('');
        }}
        title="Deactivate Kill Switch"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-obsidian-400/80 dark:text-paper-100/80">
            This will resume trading. Type <strong>DEACTIVATE</strong> to confirm.
          </p>
          <Input
            label="Confirmation"
            placeholder="Type DEACTIVATE"
            value={deactivateInput}
            onChange={(e) => setDeactivateInput(e.target.value)}
          />
          <div className="flex gap-3 justify-end">
            <Button
              variant="ghost"
              onClick={() => {
                setShowDeactivateModal(false);
                setDeactivateInput('');
              }}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleDeactivate}
              disabled={deactivateInput !== 'DEACTIVATE'}
              isLoading={deactivateMutation.isPending}
            >
              Resume Trading
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
};

// ---------------------------------------------------------------------------
// Risk Gauges Section (replaces flat progress bar cards)
// ---------------------------------------------------------------------------

const RiskGaugesSection = () => {
  const { data: riskStatus, isLoading: statusLoading } = useRiskStatus();
  const { data: limits, isLoading: limitsLoading } = useRiskLimits();

  if (statusLoading || limitsLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-48 w-full rounded-2xl" />
        ))}
      </div>
    );
  }

  const maxDailyLoss = limits?.max_daily_loss_pct ?? 0;
  const maxDrawdown = limits?.max_total_drawdown_pct ?? 0;
  const maxPosSizePct = limits?.max_position_size_pct ?? 0;
  const maxPositions = limits?.max_positions ?? 0;

  const currentDailyLoss = riskStatus?.daily_loss_used_pct ?? 0;
  const currentDrawdown = riskStatus?.current_drawdown_pct ?? 0;
  const currentPositions = riskStatus?.open_positions ?? 0;

  const usedPct = (current: number, limit: number) =>
    limit > 0 ? Math.min((current / limit) * 100, 100) : 0;

  const gauges = [
    {
      label: 'Daily Loss',
      value: usedPct(currentDailyLoss, maxDailyLoss),
      currentDisplay: formatPercent(currentDailyLoss),
      limitDisplay: formatPercent(maxDailyLoss),
    },
    {
      label: 'Drawdown',
      value: usedPct(currentDrawdown, maxDrawdown),
      currentDisplay: formatPercent(currentDrawdown),
      limitDisplay: formatPercent(maxDrawdown),
    },
    {
      label: 'Position Size',
      // No live current exposure tracked — show 0
      value: 0,
      currentDisplay: '—',
      limitDisplay: formatPercent(maxPosSizePct),
    },
    {
      label: 'Position Count',
      value: usedPct(currentPositions, maxPositions),
      currentDisplay: String(currentPositions),
      limitDisplay: String(maxPositions),
    },
  ];

  return (
    <GlassCard variant="default">
      <div className="flex items-center gap-2 mb-6">
        <Activity className="w-5 h-5 text-deep-teal-800/60 dark:text-paper-100/60" />
        <h3 className="font-display text-lg font-medium">Risk Utilisation</h3>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        {gauges.map((g) => (
          <GaugeChart
            key={g.label}
            value={g.value}
            label={g.label}
            currentDisplay={g.currentDisplay}
            limitDisplay={g.limitDisplay}
          />
        ))}
      </div>
    </GlassCard>
  );
};

// ---------------------------------------------------------------------------
// Circuit Breakers Table
// ---------------------------------------------------------------------------

const CircuitBreakerTable = () => {
  const { data: riskStatus, isLoading: statusLoading } = useRiskStatus();
  const { data: limits, isLoading: limitsLoading } = useRiskLimits();

  if (statusLoading || limitsLoading) {
    return (
      <GlassCard variant="default">
        <Skeleton className="h-8 w-48 mb-4" />
        <Skeleton className="h-48 w-full" />
      </GlassCard>
    );
  }

  const rows = deriveCircuitBreakers(riskStatus, limits);

  const statusVariant = (s: CircuitBreakerRow['status']) => {
    if (s === 'OPEN') return 'danger' as const;
    if (s === 'WARNING') return 'warning' as const;
    return 'success' as const;
  };

  const columns = [
    {
      key: 'name',
      header: 'Breaker',
      render: (val: unknown) => (
        <span className="font-medium text-sm">{val as string}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (val: unknown) => {
        const s = val as CircuitBreakerRow['status'];
        return (
          <Badge variant={statusVariant(s)} dot={s === 'OPEN'} pulsing={s === 'OPEN'}>
            {s}
          </Badge>
        );
      },
    },
    {
      key: 'threshold',
      header: 'Threshold',
      render: (val: unknown) => (
        <span className="font-mono text-sm">{val as string}</span>
      ),
    },
    {
      key: 'current',
      header: 'Current Value',
      render: (val: unknown) => (
        <span className="font-mono text-sm">{val as string}</span>
      ),
    },
    {
      key: 'usedPct',
      header: 'Usage',
      render: (val: unknown) => {
        const pct = val as number;
        const color =
          pct >= 80 ? 'bg-loss' : pct >= 50 ? 'bg-warning' : 'bg-success';
        return (
          <div className="flex items-center gap-2 min-w-[100px]">
            <div className="flex-1 h-1.5 bg-deep-teal-800/10 dark:bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className={`h-full rounded-full ${color}`}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.8, delay: 0.2 }}
              />
            </div>
            <span className="text-xs font-mono opacity-60 w-8 text-right">
              {pct.toFixed(0)}%
            </span>
          </div>
        );
      },
    },
  ];

  return (
    <GlassCard variant="default" className="space-y-4">
      <div className="flex items-center gap-2">
        <ShieldAlert className="w-5 h-5 text-deep-teal-800/60 dark:text-paper-100/60" />
        <h3 className="font-display text-lg font-medium">Circuit Breakers</h3>
      </div>
      <DataTable columns={columns} data={rows} />
    </GlassCard>
  );
};

// ---------------------------------------------------------------------------
// Kill Switch Audit History Table
// ---------------------------------------------------------------------------

const KillSwitchAuditTable = () => {
  const { data: alerts, isLoading } = useDashboardAlerts();

  if (isLoading) {
    return (
      <GlassCard variant="default">
        <Skeleton className="h-8 w-56 mb-4" />
        <Skeleton className="h-40 w-full" />
      </GlassCard>
    );
  }

  // Filter audit log for kill switch related events
  const killSwitchEvents = (alerts ?? []).filter(
    (a: AlertEntry) =>
      a.action.includes('kill_switch') ||
      a.action.includes('trading_halted') ||
      a.action.includes('trading_resumed'),
  );

  const columns = [
    {
      key: 'action',
      header: 'Action',
      render: (val: unknown) => {
        const action = val as string;
        const isActivation =
          action.includes('activated') || action.includes('halt');
        return (
          <Badge variant={isActivation ? 'danger' : 'success'}>
            {action.replace(/_/g, ' ').toUpperCase()}
          </Badge>
        );
      },
    },
    {
      key: 'timestamp',
      header: 'Time',
      render: (val: unknown) => (
        <span className="font-mono text-xs opacity-60">
          {new Date(val as string).toLocaleString()}
        </span>
      ),
    },
    {
      key: 'actor',
      header: 'Actor',
      render: (val: unknown) => (
        <span className="font-mono text-xs">{val as string}</span>
      ),
    },
    {
      key: 'details',
      header: 'Reason / Duration',
      className: 'w-full',
      render: (val: unknown) => {
        const details = val as Record<string, unknown> | null;
        if (!details) return <span className="opacity-40">—</span>;
        const reason = details.reason as string | undefined;
        const duration = details.duration_seconds as number | undefined;
        return (
          <span className="text-sm">
            {reason ?? '—'}
            {duration != null && (
              <span className="ml-2 opacity-50 font-mono text-xs">
                ({Math.round(duration / 60)}m)
              </span>
            )}
          </span>
        );
      },
    },
  ];

  return (
    <GlassCard variant="default" className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-deep-teal-800/60 dark:text-paper-100/60" />
          <h3 className="font-display text-lg font-medium">Kill Switch History</h3>
        </div>
        <span className="text-xs font-mono opacity-40">
          {killSwitchEvents.length} events
        </span>
      </div>
      {killSwitchEvents.length > 0 ? (
        <DataTable columns={columns} data={killSwitchEvents} />
      ) : (
        <div className="text-center py-10 opacity-40 text-sm">
          No kill switch events recorded
        </div>
      )}
    </GlassCard>
  );
};

// ---------------------------------------------------------------------------
// Portfolio Exposure Progress Bars
// ---------------------------------------------------------------------------

const PortfolioExposureSection = () => {
  const { data: positions, isLoading: positionsLoading } = useDashboardPositions();
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();
  const { data: limits, isLoading: limitsLoading } = useRiskLimits();

  if (positionsLoading || summaryLoading || limitsLoading) {
    return (
      <GlassCard variant="default">
        <Skeleton className="h-8 w-48 mb-4" />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </GlassCard>
    );
  }

  const positionList = positions ?? [];
  const portfolioValue = summary?.portfolio_value ?? 0;
  const maxPosSizePct = limits?.max_position_size_pct ?? 0;
  // Maximum allowed exposure per symbol in USDT
  const maxExposureUsdt = portfolioValue * (maxPosSizePct / 100);

  return (
    <GlassCard variant="default" className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart2 className="w-5 h-5 text-deep-teal-800/60 dark:text-paper-100/60" />
          <h3 className="font-display text-lg font-medium">Portfolio Exposure</h3>
        </div>
        {maxPosSizePct > 0 && (
          <span className="text-xs font-mono opacity-50">
            Max per position: {formatPercent(maxPosSizePct)}
          </span>
        )}
      </div>

      {positionList.length === 0 ? (
        <div className="text-center py-10 opacity-40 text-sm">
          No open positions
        </div>
      ) : (
        <div className="space-y-3">
          {positionList.map((pos: DashboardPositionEntry) => {
            const exposureUsdt = pos.quantity * pos.current_price;
            const usedPct =
              maxExposureUsdt > 0
                ? Math.min((exposureUsdt / maxExposureUsdt) * 100, 100)
                : 0;
            const barColor =
              usedPct >= 80 ? 'bg-loss' : usedPct >= 50 ? 'bg-warning' : 'bg-success';

            return (
              <div key={pos.id} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium">
                    {pos.symbol}
                    <span className="ml-2 font-mono text-xs opacity-50">
                      {pos.side}
                    </span>
                  </span>
                  <span className="font-mono text-xs opacity-70">
                    ${exposureUsdt.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    {maxExposureUsdt > 0 && (
                      <span className="opacity-50">
                        {' '}/ ${maxExposureUsdt.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                      </span>
                    )}
                  </span>
                </div>
                <div className="h-1.5 w-full bg-deep-teal-800/10 dark:bg-white/10 rounded-full overflow-hidden">
                  <motion.div
                    className={`h-full rounded-full ${barColor}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${usedPct}%` }}
                    transition={{ duration: 0.8, delay: 0.1 }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </GlassCard>
  );
};

// ---------------------------------------------------------------------------
// Recent Risk Events (general audit log)
// ---------------------------------------------------------------------------

const RiskAlertsTable = () => {
  const { data: alerts, isLoading } = useDashboardAlerts();

  if (isLoading) {
    return (
      <GlassCard variant="default">
        <Skeleton className="h-8 w-48 mb-4" />
        <Skeleton className="h-64 w-full" />
      </GlassCard>
    );
  }

  const riskAlerts = (alerts ?? []).slice(0, 20);

  const columns = [
    {
      key: 'timestamp',
      header: 'Time',
      render: (val: unknown) => (
        <span className="text-xs font-mono opacity-60">
          {new Date(val as string).toLocaleTimeString()}
        </span>
      ),
    },
    {
      key: 'action',
      header: 'Action',
      render: (val: unknown) => {
        const action = val as string;
        const isRisk =
          action.includes('kill_switch') ||
          action.includes('risk') ||
          action.includes('breach');
        return (
          <Badge variant={isRisk ? 'danger' : 'info'}>
            {action.replace(/_/g, ' ').toUpperCase()}
          </Badge>
        );
      },
    },
    {
      key: 'actor',
      header: 'Actor',
      render: (val: unknown) => (
        <span className="font-mono text-xs">{val as string}</span>
      ),
    },
    {
      key: 'details',
      header: 'Details',
      className: 'w-full',
      render: (val: unknown) => {
        const details = val as Record<string, unknown> | null;
        return (
          <span className="text-sm truncate block max-w-md">
            {details && typeof details === 'object'
              ? Object.entries(details)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(', ')
              : '-'}
          </span>
        );
      },
    },
  ];

  return (
    <GlassCard variant="default" className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-display text-lg font-medium">Recent Risk Events</h3>
        <span className="text-xs font-mono opacity-40">
          {riskAlerts.length} events
        </span>
      </div>
      {riskAlerts.length > 0 ? (
        <DataTable columns={columns} data={riskAlerts} />
      ) : (
        <div className="text-center py-12 opacity-40 text-sm">
          No risk events recorded
        </div>
      )}
    </GlassCard>
  );
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export const RiskPage: React.FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-8 pb-12"
    >
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-medium text-deep-teal-800 dark:text-paper-100 mb-1">
          Risk & Compliance
        </h1>
        <p className="text-obsidian-400/60 dark:text-paper-100/60 font-sans">
          Monitor exposure, enforce limits, and manage emergency controls.
        </p>
      </div>

      <KillSwitch />
      <RiskGaugesSection />
      <CircuitBreakerTable />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PortfolioExposureSection />
        <KillSwitchAuditTable />
      </div>
      <RiskAlertsTable />
    </motion.div>
  );
};
