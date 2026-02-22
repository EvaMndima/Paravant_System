
import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Play,
  Pause,
  StopCircle,
  Settings,
  Activity,
  Shield,
  TrendingUp,
  Save,
  FlaskConical,
  Zap,
  Lightbulb,
  GitBranch,
  CheckCircle,
  XCircle,
  FileText,
  Archive,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/DataTable';
import { Input } from '@/components/ui/Input';
import { Skeleton } from '@/components/ui/Skeleton';
import { Modal } from '@/components/ui/Modal';
import { ApiErrorDisplay } from '@/components/ui/ApiErrorDisplay';
import { formatCurrency, formatPercent, cn } from '@/lib/utils';
import {
  useStrategy,
  useTransitionStrategy,
  useUpdateStrategyParameters,
  useRunBacktest,
  usePaperTradingStatus,
  useStartPaperTrading,
  useStopPaperTrading,
  useStrategyTransitions,
} from '@/hooks';
import { useToast } from '@/contexts/ToastContext';
import type {
  TradeEntry,
  BacktestResponse,
  StrategyDetailResponse,
} from '@/types/api';

// ========== Tab Configuration — PRD §6.4: 7 tabbed sections ==========

const TABS = [
  { id: 'overview', label: 'Overview', icon: FileText },
  { id: 'parameters', label: 'Parameters', icon: Settings },
  { id: 'backtest', label: 'Backtest', icon: FlaskConical },
  { id: 'paper', label: 'Paper', icon: Activity },
  { id: 'live', label: 'Live', icon: Zap },
  { id: 'recommendations', label: 'Suggestions', icon: Lightbulb },
  { id: 'lifecycle', label: 'Lifecycle', icon: GitBranch },
] as const;

type TabId = (typeof TABS)[number]['id'];

// ========== Shared: Single metric row for metric lists ==========

interface MetricRowProps {
  label: string;
  value: string;
  /** undefined = neutral colour, true = gain, false = loss */
  positive?: boolean;
}

const MetricRow: React.FC<MetricRowProps> = ({ label, value, positive }) => (
  <div className="flex justify-between items-center py-2 border-b border-deep-teal-800/5 dark:border-white/5 last:border-0">
    <span className="text-xs font-mono uppercase tracking-wider text-obsidian-400/60 dark:text-paper-100/60">
      {label}
    </span>
    <span
      className={cn(
        'text-sm font-mono font-medium',
        positive === true && 'text-gain',
        positive === false && 'text-loss',
      )}
    >
      {value}
    </span>
  </div>
);

// ========== Tab 1: Overview (PRD §6.4.1) ==========

const OverviewSection: React.FC<{ strategy: StrategyDetailResponse }> = ({ strategy }) => (
  <div className="space-y-6">
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <GlassCard variant="subtle" padding="sm">
        <div className="flex items-center gap-2 text-obsidian-400/50 dark:text-paper-100/50 mb-2">
          <Settings className="w-4 h-4" />
          <span className="text-xs font-mono uppercase tracking-widest">Template</span>
        </div>
        <p className="font-display font-medium text-sm truncate">{strategy.template_id}</p>
      </GlassCard>

      <GlassCard variant="subtle" padding="sm">
        <div className="flex items-center gap-2 text-obsidian-400/50 dark:text-paper-100/50 mb-2">
          <Activity className="w-4 h-4" />
          <span className="text-xs font-mono uppercase tracking-widest">Version</span>
        </div>
        <p className="font-display font-medium text-sm">{strategy.template_version}</p>
      </GlassCard>

      <GlassCard variant="subtle" padding="sm">
        <div className="flex items-center gap-2 text-obsidian-400/50 dark:text-paper-100/50 mb-2">
          <TrendingUp className="w-4 h-4" />
          <span className="text-xs font-mono uppercase tracking-widest">Symbols</span>
        </div>
        <p className="font-display font-medium text-sm">
          {strategy.symbols?.join(', ') || '—'}
        </p>
      </GlassCard>

      <GlassCard variant="subtle" padding="sm">
        <div className="flex items-center gap-2 text-obsidian-400/50 dark:text-paper-100/50 mb-2">
          <Shield className="w-4 h-4" />
          <span className="text-xs font-mono uppercase tracking-widest">Status</span>
        </div>
        <p
          className={cn(
            'font-display font-medium text-sm uppercase',
            strategy.status === 'active' && 'text-gain',
            strategy.status === 'paused' && 'text-warning',
            strategy.status !== 'active' && strategy.status !== 'paused' && 'text-loss',
          )}
        >
          {strategy.status}
        </p>
      </GlassCard>
    </div>

    {strategy.description && (
      <GlassCard variant="default">
        <h4 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/60 dark:text-paper-100/60 mb-2">
          Description
        </h4>
        <p className="text-sm">{strategy.description}</p>
      </GlassCard>
    )}

    <GlassCard variant="default">
      <h4 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/60 dark:text-paper-100/60 mb-2">
        Strategy Type
      </h4>
      <p className="text-sm font-mono">{strategy.type}</p>
    </GlassCard>
  </div>
);

// ========== Tab 2: Parameters (PRD §6.4.2) ==========

interface ConfigPanelProps {
  parameters: Record<string, unknown>;
  onSave: (newParams: Record<string, unknown>) => void;
}

const ConfigPanel: React.FC<ConfigPanelProps> = ({ parameters, onSave }) => {
  const [editedParams, setEditedParams] = useState(parameters);
  const [showSaveModal, setShowSaveModal] = useState(false);

  const handleSave = () => {
    onSave(editedParams);
    setShowSaveModal(false);
  };

  return (
    <>
      <GlassCard variant="subtle">
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-display text-lg font-medium">Strategy Parameters</h3>
          <Button
            variant="ghost"
            size="sm"
            className="gap-2"
            onClick={() => setShowSaveModal(true)}
          >
            <Save className="w-4 h-4" /> Save Changes
          </Button>
        </div>

        {Object.keys(editedParams).length === 0 ? (
          <p className="text-sm text-obsidian-400/60 dark:text-paper-100/60">
            No configurable parameters for this strategy.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(editedParams).map(([key, value]) => (
              <div key={key} className="space-y-1">
                <label className="text-xs font-mono font-medium text-obsidian-400/60 dark:text-paper-100/60 uppercase">
                  {key.replace(/_/g, ' ')}
                </label>
                <Input
                  value={String(value)}
                  onChange={(e) =>
                    setEditedParams({ ...editedParams, [key]: e.target.value })
                  }
                  className="font-mono text-sm"
                />
              </div>
            ))}
          </div>
        )}
      </GlassCard>

      <Modal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        title="Save Parameter Changes"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-obsidian-400/80 dark:text-paper-100/80">
            Are you sure you want to save these parameter changes? The strategy will use
            these new values for future signals.
          </p>
          <div className="flex gap-3 justify-end">
            <Button variant="ghost" onClick={() => setShowSaveModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleSave}>
              Save Parameters
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
};

// ========== Tab 3: Backtest Results (PRD §6.4.3) ==========

interface BacktestSectionProps {
  strategyId: string;
  /** Notifies parent when results arrive so Recommendations tab can use them */
  onResult: (result: BacktestResponse) => void;
}

const BacktestSection: React.FC<BacktestSectionProps> = ({ strategyId, onResult }) => {
  const [initialCapital, setInitialCapital] = useState('10000');
  const [lookbackDays, setLookbackDays] = useState('90');
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const backtest = useRunBacktest();
  const { addToast } = useToast();

  const handleRun = () => {
    backtest.mutate(
      {
        strategyId,
        request: {
          initial_capital: Number(initialCapital),
          lookback_days: Number(lookbackDays),
        },
      },
      {
        onSuccess: (data) => {
          setResult(data);
          onResult(data);
          const passed = data.metrics.passed_validation ? 'Passed' : 'Failed';
          addToast('success', 'Backtest Complete', `${passed} validation`);
        },
        onError: (error) => {
          addToast('error', 'Backtest Failed', error.message);
        },
      },
    );
  };

  return (
    <div className="space-y-6">
      {/* Configuration form */}
      <GlassCard variant="subtle">
        <h3 className="font-display text-lg font-medium mb-4">Run Backtest</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div className="space-y-1">
            <label className="text-xs font-mono uppercase tracking-wider text-obsidian-400/60 dark:text-paper-100/60">
              Initial Capital (USDT)
            </label>
            <Input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(e.target.value)}
              className="font-mono"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-mono uppercase tracking-wider text-obsidian-400/60 dark:text-paper-100/60">
              Lookback Days
            </label>
            <Input
              type="number"
              value={lookbackDays}
              onChange={(e) => setLookbackDays(e.target.value)}
              className="font-mono"
            />
          </div>
        </div>
        <Button
          variant="primary"
          onClick={handleRun}
          isLoading={backtest.isPending}
          disabled={backtest.isPending}
          className="gap-2"
        >
          <FlaskConical className="w-4 h-4" />
          {backtest.isPending ? 'Running...' : 'Run Backtest'}
        </Button>
      </GlassCard>

      {/* Results — only shown after a successful run */}
      {result && (
        <GlassCard variant="elevated">
          <div className="flex justify-between items-start mb-6">
            <h3 className="font-display text-lg font-medium">Results</h3>
            {result.metrics.passed_validation ? (
              <span className="flex items-center gap-1.5 text-xs font-mono text-gain">
                <CheckCircle className="w-4 h-4" /> Passed Validation
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-mono text-loss">
                <XCircle className="w-4 h-4" /> Failed Validation
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-6">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-obsidian-400/50 dark:text-paper-100/50 mb-3">
                Capital
              </p>
              <MetricRow
                label="Initial Capital"
                value={formatCurrency(result.initial_capital)}
              />
              <MetricRow
                label="Final Capital"
                value={formatCurrency(result.final_capital)}
                positive={result.final_capital >= result.initial_capital}
              />
              <MetricRow
                label="Period"
                value={`${result.start_date} to ${result.end_date}`}
              />
            </div>

            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-obsidian-400/50 dark:text-paper-100/50 mb-3">
                Returns
              </p>
              {/* win_rate_pct, total_return_pct are already percentage values (0-100) */}
              <MetricRow
                label="Total Return"
                value={formatPercent(result.metrics.total_return_pct)}
                positive={result.metrics.total_return_pct >= 0}
              />
              <MetricRow
                label="Annualized Return"
                value={formatPercent(result.metrics.annualized_return_pct)}
                positive={result.metrics.annualized_return_pct >= 0}
              />
              <MetricRow
                label="Sharpe Ratio"
                value={result.metrics.sharpe_ratio.toFixed(2)}
                positive={result.metrics.sharpe_ratio >= 1}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-obsidian-400/50 dark:text-paper-100/50 mb-3">
                Risk
              </p>
              <MetricRow
                label="Sortino Ratio"
                value={result.metrics.sortino_ratio.toFixed(2)}
                positive={result.metrics.sortino_ratio >= 1}
              />
              <MetricRow
                label="Max Drawdown"
                value={formatPercent(result.metrics.max_drawdown_pct)}
                positive={false}
              />
              <MetricRow
                label="Profit Factor"
                value={result.metrics.profit_factor.toFixed(2)}
                positive={result.metrics.profit_factor >= 1.5}
              />
            </div>

            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-obsidian-400/50 dark:text-paper-100/50 mb-3">
                Trades
              </p>
              <MetricRow label="Total Trades" value={String(result.metrics.total_trades)} />
              <MetricRow
                label="Win Rate"
                value={formatPercent(result.metrics.win_rate_pct)}
                positive={result.metrics.win_rate_pct >= 50}
              />
              <MetricRow
                label="Expectancy"
                value={`$${result.metrics.expectancy.toFixed(2)}`}
                positive={result.metrics.expectancy >= 0}
              />
            </div>
          </div>

          {result.metrics.validation_errors.length > 0 && (
            <div className="mt-6 p-4 bg-loss/10 rounded-xl">
              <p className="text-xs font-mono font-medium text-loss uppercase mb-2">
                Validation Errors
              </p>
              <ul className="space-y-1">
                {result.metrics.validation_errors.map((err, i) => (
                  <li key={i} className="text-xs text-loss flex items-start gap-2">
                    <XCircle className="w-3 h-3 mt-0.5 shrink-0" />
                    {err}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </GlassCard>
      )}
    </div>
  );
};

// ========== Tab 4: Paper Trading Results (PRD §6.4.4) ==========

const PaperSection: React.FC<{ strategyId: string }> = ({ strategyId }) => {
  const { data: paperStatus, isLoading } = usePaperTradingStatus(strategyId);
  const startPaper = useStartPaperTrading();
  const stopPaper = useStopPaperTrading();
  const [initialCapital, setInitialCapital] = useState('10000');
  const { addToast } = useToast();

  if (isLoading) return <Skeleton className="h-64 rounded-2xl" />;

  const handleStart = () => {
    startPaper.mutate(
      { strategyId, initialCapital: Number(initialCapital) },
      {
        onSuccess: () =>
          addToast('success', 'Paper Trading Started', 'Simulated trading is now active'),
        onError: (error) => addToast('error', 'Failed to Start', error.message),
      },
    );
  };

  const handleStop = () => {
    stopPaper.mutate(strategyId, {
      onSuccess: () =>
        addToast('success', 'Paper Trading Stopped', 'Session has ended'),
      onError: (error) => addToast('error', 'Failed to Stop', error.message),
    });
  };

  return (
    <GlassCard variant="subtle">
      <div className="flex justify-between items-center mb-6">
        <h3 className="font-display text-lg font-medium">Paper Trading</h3>
        {paperStatus?.is_running ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={handleStop}
            isLoading={stopPaper.isPending}
            className="gap-2 text-warning"
          >
            <StopCircle className="w-4 h-4" /> Stop Session
          </Button>
        ) : (
          <div className="flex items-center gap-3">
            <Input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(e.target.value)}
              className="font-mono w-36 text-sm"
              placeholder="Capital (USDT)"
            />
            <Button
              variant="primary"
              size="sm"
              onClick={handleStart}
              isLoading={startPaper.isPending}
              className="gap-2"
            >
              <Play className="w-4 h-4" /> Start Session
            </Button>
          </div>
        )}
      </div>

      {paperStatus ? (
        <div>
          <MetricRow
            label="Status"
            value={paperStatus.is_running ? 'RUNNING' : 'STOPPED'}
            positive={paperStatus.is_running}
          />
          <MetricRow
            label="Current Equity"
            value={formatCurrency(paperStatus.current_equity)}
            positive={paperStatus.current_pnl_pct >= 0}
          />
          {/* current_pnl_pct is a percentage value (e.g. 3.5 = 3.5%) */}
          <MetricRow
            label="P&L"
            value={formatPercent(paperStatus.current_pnl_pct)}
            positive={paperStatus.current_pnl_pct >= 0}
          />
          <MetricRow label="Total Trades" value={String(paperStatus.num_trades)} />
          <MetricRow label="Days Elapsed" value={String(paperStatus.days_elapsed)} />
          <MetricRow
            label="Validation"
            value={
              paperStatus.validation_passed === null
                ? 'Pending'
                : paperStatus.validation_passed
                  ? 'Passed'
                  : 'Failed'
            }
            positive={
              paperStatus.validation_passed === true
                ? true
                : paperStatus.validation_passed === false
                  ? false
                  : undefined
            }
          />
          {paperStatus.started_at && (
            <MetricRow
              label="Started At"
              value={new Date(paperStatus.started_at).toLocaleString()}
            />
          )}
          {paperStatus.stopped_at && (
            <MetricRow
              label="Stopped At"
              value={new Date(paperStatus.stopped_at).toLocaleString()}
            />
          )}
        </div>
      ) : (
        <p className="text-sm text-obsidian-400/60 dark:text-paper-100/60">
          No paper trading session data. Start a session to begin simulated trading.
        </p>
      )}
    </GlassCard>
  );
};

// ========== Tab 5: Live Results (PRD §6.4.5) ==========

const tradeColumns = [
  {
    key: 'executed_at',
    header: 'Time',
    render: (val: unknown) => (
      <span className="text-xs font-mono opacity-60">
        {new Date(val as string).toLocaleTimeString()}
      </span>
    ),
  },
  {
    key: 'side',
    header: 'Side',
    render: (val: unknown) => (
      <span
        className={`text-xs font-bold px-2 py-0.5 rounded ${
          val === 'BUY' ? 'bg-gain/20 text-gain' : 'bg-loss/20 text-loss'
        }`}
      >
        {val as string}
      </span>
    ),
  },
  {
    key: 'price',
    header: 'Price',
    render: (val: unknown) => (
      <span className="font-mono">{formatCurrency(val as number)}</span>
    ),
  },
  {
    key: 'quantity',
    header: 'Size',
    render: (val: unknown) => <span className="font-mono">{val as number}</span>,
  },
];

const LiveSection: React.FC<{ strategy: StrategyDetailResponse }> = ({ strategy }) => {
  const metrics = strategy.performance_metrics;

  return (
    <div className="space-y-6">
      {metrics ? (
        <GlassCard variant="subtle">
          <h3 className="font-display text-lg font-medium mb-4">Live Performance Metrics</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-obsidian-400/50 dark:text-paper-100/50 mb-3">
                Returns
              </p>
              {/* win_rate is decimal (0-1), multiply by 100 before formatPercent */}
              <MetricRow
                label="Win Rate"
                value={formatPercent(metrics.win_rate * 100)}
                positive={metrics.win_rate >= 0.5}
              />
              {/* _pct fields are already percentage values (e.g. 8.1 = 8.1%) */}
              <MetricRow
                label="Total Return"
                value={formatPercent(metrics.total_return_pct)}
                positive={metrics.total_return_pct >= 0}
              />
              <MetricRow
                label="Max Drawdown"
                value={formatPercent(metrics.max_drawdown_pct)}
                positive={false}
              />
              <MetricRow
                label="Profit Factor"
                value={metrics.profit_factor.toFixed(2)}
                positive={metrics.profit_factor >= 1.5}
              />
            </div>

            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-obsidian-400/50 dark:text-paper-100/50 mb-3">
                Trade Statistics
              </p>
              <MetricRow label="Total Trades" value={String(metrics.total_trades)} />
              <MetricRow
                label="Winning Trades"
                value={String(metrics.winning_trades)}
                positive={true}
              />
              <MetricRow
                label="Losing Trades"
                value={String(metrics.losing_trades)}
                positive={false}
              />
              <MetricRow
                label="Avg Win"
                value={formatPercent(metrics.avg_win_pct)}
                positive={true}
              />
              <MetricRow
                label="Avg Loss"
                value={formatPercent(metrics.avg_loss_pct)}
                positive={false}
              />
            </div>
          </div>
        </GlassCard>
      ) : (
        <GlassCard variant="subtle">
          <p className="text-sm text-obsidian-400/60 dark:text-paper-100/60">
            No live performance data available yet.
          </p>
        </GlassCard>
      )}

      <GlassCard variant="default" padding="none" className="overflow-hidden">
        <div className="px-6 py-4 border-b border-deep-teal-800/5 dark:border-white/5">
          <h3 className="font-display text-lg font-medium">Recent Activity</h3>
        </div>
        {(strategy.recent_trades ?? []).length > 0 ? (
          <DataTable
            columns={tradeColumns}
            data={strategy.recent_trades as TradeEntry[]}
            className="border-none"
          />
        ) : (
          <div className="p-8 text-center text-obsidian-400/40 dark:text-paper-100/40 text-sm">
            No trades recorded
          </div>
        )}
      </GlassCard>
    </div>
  );
};

// ========== Tab 6: Recommendations (PRD §6.4.6) ==========

interface Recommendation {
  type: 'warning' | 'info' | 'success';
  title: string;
  description: string;
}

/** Derive actionable suggestions from backtest results and live performance data. */
function deriveRecommendations(
  strategy: StrategyDetailResponse,
  backtestResult: BacktestResponse | null,
): Recommendation[] {
  const recs: Recommendation[] = [];
  const metrics = strategy.performance_metrics;

  if (backtestResult) {
    if (!backtestResult.metrics.passed_validation) {
      recs.push({
        type: 'warning',
        title: 'Backtest Validation Failed',
        description:
          'Strategy did not meet validation criteria. Review errors and adjust parameters.',
      });
    }
    if (backtestResult.metrics.max_drawdown_pct > 15) {
      recs.push({
        type: 'warning',
        title: 'High Maximum Drawdown',
        description: `Backtest drawdown of ${backtestResult.metrics.max_drawdown_pct.toFixed(1)}% exceeds the recommended 15% threshold. Consider tightening stop losses.`,
      });
    }
    if (backtestResult.metrics.profit_factor < 1.2) {
      recs.push({
        type: 'warning',
        title: 'Low Profit Factor',
        description: `Profit factor of ${backtestResult.metrics.profit_factor.toFixed(2)} is below 1.2. This strategy may not be viable under live conditions.`,
      });
    }
    if (backtestResult.metrics.total_trades < 20) {
      recs.push({
        type: 'info',
        title: 'Limited Trade Sample',
        description: `Only ${backtestResult.metrics.total_trades} trades in backtest. Increase lookback period for statistically significant results.`,
      });
    }
    if (
      backtestResult.metrics.passed_validation &&
      backtestResult.metrics.profit_factor >= 1.5
    ) {
      recs.push({
        type: 'success',
        title: 'Ready for Paper Trading',
        description:
          'Backtest results are strong. Consider running paper trading to validate in live market conditions before deploying capital.',
      });
    }
    backtestResult.metrics.validation_errors.forEach((err) => {
      recs.push({ type: 'warning', title: 'Validation Error', description: err });
    });
  } else {
    recs.push({
      type: 'info',
      title: 'Run a Backtest First',
      description:
        'Navigate to the Backtest tab to validate this strategy against historical data. Recommendations will update based on results.',
    });
  }

  // Live performance-derived suggestions
  if (metrics) {
    if (metrics.win_rate < 0.4) {
      recs.push({
        type: 'warning',
        title: 'Low Live Win Rate',
        description: `Current live win rate is ${formatPercent(metrics.win_rate * 100)}. Review entry signal parameters for better trade selectivity.`,
      });
    }
    if (metrics.max_drawdown_pct > 10) {
      recs.push({
        type: 'warning',
        title: 'Elevated Live Drawdown',
        description: `Live drawdown of ${formatPercent(metrics.max_drawdown_pct)} is elevated. Monitor closely and consider pausing if it continues to increase.`,
      });
    }
    if (metrics.profit_factor >= 2 && metrics.win_rate >= 0.55) {
      recs.push({
        type: 'success',
        title: 'Strong Live Performance',
        description: `Profit factor of ${metrics.profit_factor.toFixed(2)} and win rate of ${formatPercent(metrics.win_rate * 100)} indicate a healthy strategy.`,
      });
    }
  }

  if (recs.length === 0) {
    recs.push({
      type: 'success',
      title: 'No Issues Detected',
      description:
        'Strategy parameters and performance are within acceptable ranges. Continue monitoring.',
    });
  }

  return recs;
}

const recBgClass: Record<Recommendation['type'], string> = {
  warning: 'bg-warning/10 border-warning/30',
  info: 'bg-deep-teal-600/10 border-deep-teal-600/30',
  success: 'bg-gain/10 border-gain/30',
};

const recTextClass: Record<Recommendation['type'], string> = {
  warning: 'text-warning',
  info: 'text-deep-teal-600 dark:text-paper-100/80',
  success: 'text-gain',
};

interface RecommendationsSectionProps {
  strategy: StrategyDetailResponse;
  backtestResult: BacktestResponse | null;
}

const RecommendationsSection: React.FC<RecommendationsSectionProps> = ({
  strategy,
  backtestResult,
}) => {
  const recommendations = deriveRecommendations(strategy, backtestResult);

  return (
    <div className="space-y-3">
      {recommendations.map((rec, i) => (
        <div key={i} className={cn('p-4 rounded-2xl border', recBgClass[rec.type])}>
          <p className={cn('text-sm font-medium mb-1', recTextClass[rec.type])}>
            {rec.title}
          </p>
          <p className="text-sm text-obsidian-400/80 dark:text-paper-100/70">
            {rec.description}
          </p>
        </div>
      ))}
    </div>
  );
};

// ========== Tab 7: Lifecycle (PRD §6.4.7 — status history timeline) ==========

interface LifecycleSectionProps {
  strategyId: string;
  currentStatus: string;
}

const LifecycleSection: React.FC<LifecycleSectionProps> = ({
  strategyId,
  currentStatus,
}) => {
  // This query only fires when LifecycleSection mounts (lifecycle tab active)
  const { data: transitions, isLoading } = useStrategyTransitions(strategyId);

  if (isLoading) return <Skeleton className="h-48 rounded-2xl" />;

  return (
    <div className="space-y-6">
      {/* Current state indicator */}
      <GlassCard variant="elevated">
        <h3 className="font-display text-lg font-medium mb-4">Current State</h3>
        <div className="flex items-center gap-3 mb-4">
          <div
            className={cn(
              'w-3 h-3 rounded-full',
              currentStatus === 'active' && 'bg-gain',
              currentStatus === 'paused' && 'bg-warning',
              currentStatus !== 'active' && currentStatus !== 'paused' && 'bg-loss',
            )}
          />
          <span className="font-mono font-medium text-lg uppercase">{currentStatus}</span>
        </div>

        {transitions?.[currentStatus] && (
          <div>
            <p className="text-xs font-mono uppercase tracking-wider text-obsidian-400/60 dark:text-paper-100/60 mb-2">
              Available Transitions
            </p>
            <div className="flex gap-2 flex-wrap">
              {(transitions[currentStatus] as string[]).map((next) => (
                <span
                  key={next}
                  className="text-xs font-mono px-2 py-1 rounded-lg bg-deep-teal-800/5 dark:bg-white/5"
                >
                  {`\u2192 ${next}`}
                </span>
              ))}
            </div>
          </div>
        )}
      </GlassCard>

      {/* State machine topology map */}
      {transitions && Object.keys(transitions).length > 0 && (
        <GlassCard variant="subtle">
          <h3 className="font-display text-lg font-medium mb-4">State Machine</h3>
          <div className="space-y-3">
            {Object.entries(transitions).map(([state, nextStates]) => (
              <div key={state} className="flex items-center gap-3 flex-wrap">
                <span
                  className={cn(
                    'text-xs font-mono px-3 py-1.5 rounded-lg font-medium min-w-[80px] text-center',
                    state === currentStatus
                      ? 'bg-deep-teal-600 text-white dark:bg-deep-teal-500'
                      : 'bg-deep-teal-800/5 dark:bg-white/5',
                  )}
                >
                  {state}
                </span>
                <span className="text-obsidian-400/40 dark:text-paper-100/30">{'\u2192'}</span>
                <div className="flex gap-2 flex-wrap">
                  {(nextStates as string[]).length > 0 ? (
                    (nextStates as string[]).map((next) => (
                      <span
                        key={next}
                        className="text-xs font-mono px-2 py-1 rounded bg-deep-teal-800/5 dark:bg-white/5"
                      >
                        {next}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/30 italic">
                      terminal
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
          {/* Full history logged server-side. PRD §6.4.7 */}
          <p className="text-xs text-obsidian-400/40 dark:text-paper-100/30 mt-4">
            Full status-change history is stored server-side. PRD §6.4.7.
          </p>
        </GlassCard>
      )}

      {(!transitions || Object.keys(transitions).length === 0) && (
        <GlassCard variant="subtle">
          <p className="text-sm text-obsidian-400/60 dark:text-paper-100/60">
            No transition data available for this strategy.
          </p>
        </GlassCard>
      )}
    </div>
  );
};

// ========== Main Page Component ==========

export const StrategyDetailPage: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: strategy, isLoading, isError, error, refetch } = useStrategy(id ?? '');
  const transitionMutation = useTransitionStrategy();
  const updateParamsMutation = useUpdateStrategyParameters();
  const { addToast } = useToast();

  const [activeTab, setActiveTab] = useState<TabId>('overview');
  // Stored at page level so RecommendationsSection can consume backtest results
  const [backtestResult, setBacktestResult] = useState<BacktestResponse | null>(null);
  // Retire confirmation: user must type strategy name to confirm
  const [retireDialogOpen, setRetireDialogOpen] = useState(false);
  const [retireConfirmText, setRetireConfirmText] = useState('');

  const handleTransition = (newStatus: string) => {
    if (!id) return;
    transitionMutation.mutate(
      { strategyId: id, newStatus },
      {
        onSuccess: () =>
          addToast('success', 'Strategy Updated', `Status changed to ${newStatus}`),
        onError: (error) => addToast('error', 'Transition Failed', error.message),
      },
    );
  };

  const handleRetire = () => {
    if (!id || !strategy) return;
    if (retireConfirmText !== strategy.name) return;
    transitionMutation.mutate(
      { strategyId: id, newStatus: 'retired' },
      {
        onSuccess: () => {
          addToast('success', 'Strategy Retired', `"${strategy.name}" has been archived.`);
          setRetireDialogOpen(false);
          navigate('/strategies');
        },
        onError: (error) => addToast('error', 'Retire Failed', error.message),
      },
    );
  };

  const handleSaveParameters = (newParams: Record<string, unknown>) => {
    if (!id) return;
    updateParamsMutation.mutate(
      { strategyId: id, parameters: newParams },
      {
        onSuccess: () =>
          addToast(
            'success',
            'Parameters Saved',
            'Strategy parameters updated successfully',
          ),
        onError: (error) => addToast('error', 'Save Failed', error.message),
      },
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-6 pb-12">
        <Skeleton className="h-20 w-full rounded-2xl" />
        <Skeleton className="h-12 w-full rounded-2xl" />
        <Skeleton className="h-96 w-full rounded-2xl" />
      </div>
    );
  }

  if (isError) {
    return <ApiErrorDisplay error={error as Error} onRetry={refetch} />;
  }

  if (!strategy) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <p className="text-obsidian-400/60 dark:text-paper-100/60 mb-4">
            Strategy not found
          </p>
          <Button onClick={() => navigate('/strategies')}>Back to Strategies</Button>
        </div>
      </div>
    );
  }

  return (
    <>
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6 pb-12"
    >
      {/* Page Header — always visible above tabs */}
      <div className="flex flex-col md:flex-row justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            className="w-9 px-0"
            onClick={() => navigate('/strategies')}
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-display font-medium text-deep-teal-800 dark:text-paper-100">
                {strategy.name}
              </h1>
              <Badge
                variant={
                  strategy.status === 'active'
                    ? 'success'
                    : strategy.status === 'paused'
                      ? 'warning'
                      : 'neutral'
                }
                dot
                pulsing={strategy.status === 'active'}
              >
                {strategy.status.toUpperCase()}
              </Badge>
            </div>
            <div className="flex items-center gap-2 mt-1 text-xs font-mono opacity-60">
              <span>{strategy.type}</span>
              <span>•</span>
              <span>{strategy.template_id}</span>
              <span>•</span>
              <span>ID: {id}</span>
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          {strategy.status === 'active' ? (
            <Button
              variant="secondary"
              className="gap-2 text-warning hover:text-warning-bright"
              onClick={() => handleTransition('paused')}
              isLoading={transitionMutation.isPending}
            >
              <Pause className="w-4 h-4" /> Pause Strategy
            </Button>
          ) : (
            <Button
              variant="primary"
              className="gap-2"
              onClick={() => handleTransition('active')}
              isLoading={transitionMutation.isPending}
            >
              <Play className="w-4 h-4" /> Start Strategy
            </Button>
          )}
          <Button
            variant="danger"
            size="sm"
            className="w-9 px-0"
            onClick={() => handleTransition('stopped')}
            isLoading={transitionMutation.isPending}
          >
            <StopCircle className="w-4 h-4" />
          </Button>
          {/* Retire: destructive — requires type-name confirmation */}
          {strategy.status !== 'retired' && (
            <Button
              variant="ghost"
              size="sm"
              className="gap-1.5 text-obsidian-400/50 dark:text-paper-100/30 hover:text-loss dark:hover:text-loss"
              onClick={() => { setRetireConfirmText(''); setRetireDialogOpen(true); }}
              title="Retire (archive) this strategy"
            >
              <Archive className="w-4 h-4" />
              <span className="hidden md:inline">Retire</span>
            </Button>
          )}
        </div>
      </div>

      {/* Tab Navigation — PRD §6.4: 7 sections */}
      <div className="border-b border-deep-teal-800/10 dark:border-white/5">
        <div className="flex gap-1 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap',
                activeTab === tab.id
                  ? 'text-deep-teal-600 dark:text-paper-100 border-b-2 border-deep-teal-600 dark:border-paper-100'
                  : 'text-obsidian-400/60 dark:text-paper-100/50 hover:text-obsidian-400 dark:hover:text-paper-100/80',
              )}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content — each section only mounts when its tab is active.
          This means React Query hooks inside them only fire on demand. */}
      <div>
        {activeTab === 'overview' && <OverviewSection strategy={strategy} />}

        {activeTab === 'parameters' && (
          <ConfigPanel
            parameters={strategy.parameters ?? {}}
            onSave={handleSaveParameters}
          />
        )}

        {activeTab === 'backtest' && (
          <BacktestSection strategyId={id ?? ''} onResult={setBacktestResult} />
        )}

        {activeTab === 'paper' && <PaperSection strategyId={id ?? ''} />}

        {activeTab === 'live' && <LiveSection strategy={strategy} />}

        {activeTab === 'recommendations' && (
          <RecommendationsSection strategy={strategy} backtestResult={backtestResult} />
        )}

        {activeTab === 'lifecycle' && (
          <LifecycleSection strategyId={id ?? ''} currentStatus={strategy.status} />
        )}
      </div>
    </motion.div>

      {/* Retire Confirmation Dialog — user must type strategy name exactly */}
      <Modal
        isOpen={retireDialogOpen}
        onClose={() => setRetireDialogOpen(false)}
        title="Retire Strategy"
      >
        <div className="space-y-4 p-1">
          <p className="text-sm text-obsidian-400/80 dark:text-paper-100/70">
            This will permanently archive{' '}
            <span className="font-bold font-mono">{strategy?.name}</span>. It cannot be
            reactivated. Type the strategy name to confirm.
          </p>
          <Input
            value={retireConfirmText}
            onChange={(e) => setRetireConfirmText(e.target.value)}
            placeholder={strategy?.name ?? ''}
            aria-label="Strategy name confirmation"
            autoFocus
          />
          <div className="flex gap-2">
            <Button
              variant="ghost"
              className="flex-1"
              onClick={() => setRetireDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              className="flex-1 gap-2"
              onClick={handleRetire}
              isLoading={transitionMutation.isPending}
              disabled={retireConfirmText !== (strategy?.name ?? '') || transitionMutation.isPending}
            >
              <Archive className="w-4 h-4" />
              Retire Strategy
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
};
