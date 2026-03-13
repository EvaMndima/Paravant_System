import React, { useState } from 'react';
import { motion } from 'framer-motion';
import type { AppTheme, ThemeMode } from '@/types';
import { useTheme } from '@/contexts/ThemeContext';
import { cn } from '@/lib/utils';
import { fadeInUp, staggerContainer } from '@/lib/animations';

// --- New UI Components ---
import { Select } from '@/components/ui/Select';
import type { SelectOption } from '@/components/ui/Select';
import { Pagination } from '@/components/ui/Pagination';
import { DateRangePicker } from '@/components/ui/DateRangePicker';
import type { DateRange } from '@/components/ui/DateRangePicker';
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';

// --- Charts ---
import { SVGAreaChart } from '@/components/charts/SVGAreaChart';
import type { AreaChartData } from '@/components/charts/AreaChart';

// --- New Dashboard Components ---
import { EquityChart } from '@/components/dashboard/EquityChart';
import { PnLSummaryStrip } from '@/components/dashboard/PnLSummaryStrip';
import { TradeHistoryTable } from '@/components/dashboard/TradeHistoryTable';
import { AlertRuleCard, MOCK_ALERT_RULES } from '@/components/dashboard/AlertRuleCard';
import type { AlertRule } from '@/components/dashboard/AlertRuleCard';
import { SettingsForm } from '@/components/dashboard/SettingsForm';

// ── Constants ─────────────────────────────────────────────────

const THEMES: { id: AppTheme; label: string }[] = [
  { id: 'ocean', label: 'Ocean' },
  { id: 'sapphire', label: 'Sapphire' },
  { id: 'emerald', label: 'Emerald' },
  { id: 'onyx', label: 'Onyx' },
];

const MODES: { id: ThemeMode; label: string }[] = [
  { id: 'light', label: 'Light' },
  { id: 'dark', label: 'Dark' },
  { id: 'system', label: 'System' },
];

const SYMBOL_OPTIONS: SelectOption[] = [
  { value: 'BTCUSDT', label: 'BTCUSDT' },
  { value: 'ETHUSDT', label: 'ETHUSDT' },
  { value: 'BNBUSDT', label: 'BNBUSDT' },
];

const STATUS_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'All Statuses' },
  { value: 'open', label: 'Open' },
  { value: 'closed', label: 'Closed' },
  { value: 'pending', label: 'Pending' },
  { value: 'cancelled', label: 'Cancelled', disabled: true },
];

const SIZE_OPTIONS: SelectOption[] = [
  { value: 'sm', label: 'Small' },
  { value: 'md', label: 'Medium' },
  { value: 'lg', label: 'Large' },
];

// ── Section wrapper ───────────────────────────────────────────

interface SectionProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}

const Section: React.FC<SectionProps> = ({ title, subtitle, children, className }) => (
  <motion.div variants={fadeInUp} className={cn('space-y-4', className)}>
    <div className="border-b border-deep-teal-800/10 dark:border-white/10 pb-3">
      <h2 className="text-base font-mono font-bold text-obsidian-400 dark:text-paper-100 uppercase tracking-widest">
        {title}
      </h2>
      {subtitle && (
        <p className="text-xs font-sans text-obsidian-400/50 dark:text-paper-100/50 mt-0.5">{subtitle}</p>
      )}
    </div>
    {children}
  </motion.div>
);

// ── Select Gallery ────────────────────────────────────────────

const SelectGallery: React.FC = () => {
  const [sym, setSym] = useState('BTCUSDT');
  const [status, setStatus] = useState('all');
  const [size, setSize] = useState('md');
  const [disabled, setDisabled] = useState('');

  return (
    <Section title="Select" subtitle="Custom dropdown — sizes, states, disabled options">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <GlassCard variant="subtle" padding="md">
          <Select
            label="Symbol"
            options={SYMBOL_OPTIONS}
            value={sym}
            onChange={setSym}
            size="md"
          />
          <p className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40 mt-2">
            Selected: {sym}
          </p>
        </GlassCard>

        <GlassCard variant="subtle" padding="md">
          <Select
            label="Status (with disabled option)"
            options={STATUS_OPTIONS}
            value={status}
            onChange={setStatus}
            size="md"
          />
          <p className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40 mt-2">
            Selected: {status}
          </p>
        </GlassCard>

        <GlassCard variant="subtle" padding="md">
          <Select
            label="Size — Small"
            options={SIZE_OPTIONS}
            value={size}
            onChange={setSize}
            size="sm"
          />
          <div className="mt-2">
            <Select
              label="Size — Large"
              options={SIZE_OPTIONS}
              value={size}
              onChange={setSize}
              size="lg"
            />
          </div>
        </GlassCard>

        <GlassCard variant="subtle" padding="md">
          <Select
            label="Disabled"
            options={SYMBOL_OPTIONS}
            value={disabled}
            onChange={setDisabled}
            disabled
          />
          <div className="mt-2">
            <Select
              label="With Error"
              options={SYMBOL_OPTIONS}
              value={disabled}
              onChange={setDisabled}
              error="This field is required"
            />
          </div>
        </GlassCard>
      </div>
    </Section>
  );
};

// ── Pagination Gallery ────────────────────────────────────────

const PaginationGallery: React.FC = () => {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const total = 247;

  return (
    <Section title="Pagination" subtitle="Smart ellipsis, page-size selector, first/last jumps">
      <GlassCard variant="subtle" padding="md" className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <span className="text-xs font-mono text-obsidian-400/60 dark:text-paper-100/60">
            {total} total records
          </span>
          <div className="flex gap-2">
            {[5, 10, 25, 50].map(n => (
              <button
                key={n}
                onClick={() => { setPageSize(n); setPage(1); }}
                className={cn(
                  'px-3 py-1 rounded-lg text-xs font-mono border transition-all',
                  pageSize === n
                    ? 'border-turquoise-mist/50 bg-turquoise-mist/10 text-deep-teal-800 dark:text-turquoise-mist'
                    : 'border-deep-teal-800/15 dark:border-white/10 text-obsidian-400/50 dark:text-paper-100/50'
                )}
              >
                {n}/page
              </button>
            ))}
          </div>
        </div>

        <Pagination
          page={page}
          pageSize={pageSize}
          total={total}
          onPageChange={setPage}
          onPageSizeChange={size => { setPageSize(size); setPage(1); }}
        />

        <p className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40 text-center">
          Page {page} of {Math.ceil(total / pageSize)}
        </p>
      </GlassCard>
    </Section>
  );
};

// ── DateRangePicker Gallery ───────────────────────────────────

const DateRangeGallery: React.FC = () => {
  const today = new Date().toISOString().split('T')[0];
  const [range, setRange] = useState<DateRange>({ from: today, to: today });
  const [rangeB, setRangeB] = useState<DateRange>({ from: today, to: today });

  return (
    <Section title="DateRangePicker" subtitle="Preset chips with custom date inputs">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <GlassCard variant="subtle" padding="md" className="space-y-3">
          <p className="text-xs font-mono font-bold text-obsidian-400/60 dark:text-paper-100/60 uppercase tracking-widest">
            Default
          </p>
          <DateRangePicker value={range} onChange={r => setRange(r)} label="Date Range" />
          <p className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40">
            {range.from} — {range.to}
          </p>
        </GlassCard>

        <GlassCard variant="subtle" padding="md" className="space-y-3">
          <p className="text-xs font-mono font-bold text-obsidian-400/60 dark:text-paper-100/60 uppercase tracking-widest">
            No label / Disabled
          </p>
          <DateRangePicker value={rangeB} onChange={r => setRangeB(r)} />
          <DateRangePicker value={rangeB} onChange={r => setRangeB(r)} label="Disabled" disabled />
        </GlassCard>
      </div>
    </Section>
  );
};

// ── EquityChart Gallery ───────────────────────────────────────

const EquityChartGallery: React.FC = () => (
  <Section title="EquityChart" subtitle="Time-range selector, animated area chart, P&L badge">
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <EquityChart title="Portfolio Equity" startingCapital={100_000} />
      <EquityChart title="Strategy Alpha" startingCapital={50_000} height={180} />
    </div>
  </Section>
);

// ── PnLSummaryStrip Gallery ───────────────────────────────────

const PnLStripGallery: React.FC = () => (
  <Section title="PnLSummaryStrip" subtitle="5-column metric strip — today, total return, unrealized, win rate, trades">
    <div className="space-y-3">
      <PnLSummaryStrip />
      <PnLSummaryStrip
        data={{
          todayPnl: -523.10,
          totalReturn: -8.2,
          unrealizedPnl: -1_450,
          winRate: 41.2,
          totalTrades: 87,
          openPositions: 1,
        }}
      />
    </div>
  </Section>
);

// ── TradeHistoryTable Gallery ─────────────────────────────────

const TradeTableGallery: React.FC = () => (
  <Section title="TradeHistoryTable" subtitle="Filterable + paginated table with drill-down modal">
    <TradeHistoryTable />
  </Section>
);

// ── AlertRuleCard Gallery ─────────────────────────────────────

const AlertCardGallery: React.FC = () => {
  const [rules, setRules] = useState<AlertRule[]>(MOCK_ALERT_RULES.slice(0, 4));

  const handleToggle = (id: string, enabled: boolean) => {
    setRules(prev => prev.map(r => r.id === id ? { ...r, enabled } : r));
  };

  const handleDelete = (id: string) => {
    setRules(prev => prev.filter(r => r.id !== id));
  };

  return (
    <Section title="AlertRuleCard" subtitle="Enable/disable toggle, two-click delete, condition badges">
      {rules.length === 0 ? (
        <GlassCard variant="subtle" padding="md" className="text-center py-8">
          <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 uppercase tracking-widest">
            All rules deleted — refresh to reset
          </p>
        </GlassCard>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {rules.map(rule => (
            <AlertRuleCard
              key={rule.id}
              rule={rule}
              onToggle={handleToggle}
              onEdit={id => console.info('edit', id)}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </Section>
  );
};

// ── SettingsForm Gallery ──────────────────────────────────────

const SettingsFormGallery: React.FC = () => (
  <Section title="SettingsForm" subtitle="API keys, trading mode, risk limits, Telegram notifications">
    <div className="max-w-2xl">
      <SettingsForm
        onSave={values => console.info('settings saved', values)}
      />
    </div>
  </Section>
);

// ── SVGAreaChart Gallery ──────────────────────────────────────

function makeCurve(points: number, start: number, drift: number): AreaChartData[] {
  const now = new Date();
  let val = start;
  return Array.from({ length: points }, (_, i) => {
    val += (Math.random() - 0.5 + drift) * start * 0.012;
    val = Math.max(start * 0.6, val);
    const d = new Date(now);
    d.setDate(d.getDate() - (points - 1 - i));
    return { date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), value: Math.round(val) };
  });
}

const SVGAreaChartGallery: React.FC = () => (
  <Section
    title="SVGAreaChart"
    subtitle="Pure-SVG area chart — no Recharts; theme-aware accent, bezier curves, animated draw, hover crosshair + tooltip"
  >
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <GlassCard variant="default" padding="md" className="space-y-3">
        <div>
          <p className="text-xs font-mono font-bold text-obsidian-400/60 dark:text-paper-100/60 uppercase tracking-widest">
            90-day equity (uptrend)
          </p>
          <p className="text-[10px] font-sans text-obsidian-400/40 dark:text-paper-100/40">
            showGrid=true, curveTension=0.2
          </p>
        </div>
        <SVGAreaChart
          data={makeCurve(90, 100_000, 0.04)}
          height={220}
          showGrid
          gradientId="svg-up"
        />
      </GlassCard>

      <GlassCard variant="default" padding="md" className="space-y-3">
        <div>
          <p className="text-xs font-mono font-bold text-obsidian-400/60 dark:text-paper-100/60 uppercase tracking-widest">
            30-day strategy P&L (volatile)
          </p>
          <p className="text-[10px] font-sans text-obsidian-400/40 dark:text-paper-100/40">
            showGrid=false, curveTension=0.35
          </p>
        </div>
        <SVGAreaChart
          data={makeCurve(30, 50_000, -0.01)}
          height={220}
          showGrid={false}
          curveTension={0.35}
          gradientId="svg-vol"
        />
      </GlassCard>

      <GlassCard variant="default" padding="md" className="space-y-3 lg:col-span-2">
        <div>
          <p className="text-xs font-mono font-bold text-obsidian-400/60 dark:text-paper-100/60 uppercase tracking-widest">
            365-day full-width view
          </p>
          <p className="text-[10px] font-sans text-obsidian-400/40 dark:text-paper-100/40">
            Theme accent color updates when you switch palette above
          </p>
        </div>
        <SVGAreaChart
          data={makeCurve(365, 100_000, 0.02)}
          height={200}
          gradientId="svg-full"
        />
      </GlassCard>
    </div>
  </Section>
);

// ── Theme Controls ────────────────────────────────────────────

const ThemeControls: React.FC = () => {
  const { appTheme, mode, setAppTheme, setMode } = useTheme();

  return (
    <div className="flex flex-wrap items-center gap-2 pb-6 border-b border-deep-teal-800/10 dark:border-white/10">
      <span className="text-xs font-mono text-obsidian-400/50 dark:text-paper-100/50 uppercase tracking-widest mr-2">
        Theme:
      </span>
      {THEMES.map(t => (
        <button
          key={t.id}
          onClick={() => setAppTheme(t.id)}
          className={cn(
            'px-3 py-1.5 rounded-lg text-xs font-mono border transition-all',
            appTheme === t.id
              ? 'border-turquoise-mist/50 bg-turquoise-mist/10 text-deep-teal-800 dark:text-turquoise-mist font-bold'
              : 'border-deep-teal-800/15 dark:border-white/10 text-obsidian-400/60 dark:text-paper-100/60 hover:border-deep-teal-800/30'
          )}
        >
          {t.label}
        </button>
      ))}
      <span className="text-xs font-mono text-obsidian-400/50 dark:text-paper-100/50 uppercase tracking-widest mx-2">
        Mode:
      </span>
      {MODES.map(m => (
        <button
          key={m.id}
          onClick={() => setMode(m.id)}
          className={cn(
            'px-3 py-1.5 rounded-lg text-xs font-mono border transition-all',
            mode === m.id
              ? 'border-turquoise-mist/50 bg-turquoise-mist/10 text-deep-teal-800 dark:text-turquoise-mist font-bold'
              : 'border-deep-teal-800/15 dark:border-white/10 text-obsidian-400/60 dark:text-paper-100/60 hover:border-deep-teal-800/30'
          )}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
};

// ── Page ──────────────────────────────────────────────────────

const Dev3PageInner: React.FC = () => {
  return (
    <div className="min-h-screen bg-paper-100 dark:bg-obsidian-400 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">

        {/* Header */}
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono text-turquoise-mist uppercase tracking-widest">
              PARAVANT / DEV
            </span>
            <span className="text-obsidian-400/20 dark:text-paper-100/20 text-xs">—</span>
            <span className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40">
              Session 3 Components
            </span>
          </div>
          <h1 className="text-2xl font-mono font-bold text-obsidian-400 dark:text-paper-100">
            Component Gallery — Phase 3
          </h1>
          <p className="text-sm font-sans text-obsidian-400/60 dark:text-paper-100/60">
            UI primitives (Select, Pagination, DateRangePicker), dashboard components
            (EquityChart, PnLSummaryStrip, TradeHistoryTable, AlertRuleCard, SettingsForm),
            and SVGAreaChart — pure-SVG theme-aware equity chart.
          </p>
        </div>

        <ThemeControls />

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="space-y-12"
        >
          {/* UI Primitives */}
          <div className="space-y-10">
            <div>
              <span className="text-[10px] font-mono text-turquoise-mist/70 uppercase tracking-widest">
                UI Primitives
              </span>
            </div>
            <SelectGallery />
            <PaginationGallery />
            <DateRangeGallery />
          </div>

          {/* Dashboard Components */}
          <div className="space-y-10">
            <div className="border-t border-deep-teal-800/10 dark:border-white/10 pt-8">
              <span className="text-[10px] font-mono text-turquoise-mist/70 uppercase tracking-widest">
                Dashboard Components
              </span>
            </div>
            <EquityChartGallery />
            <PnLStripGallery />
            <TradeTableGallery />
            <AlertCardGallery />
            <SettingsFormGallery />
            <SVGAreaChartGallery />
          </div>
        </motion.div>

        {/* Footer */}
        <div className="border-t border-deep-teal-800/10 dark:border-white/10 pt-6 flex items-center justify-between flex-wrap gap-4">
          <p className="text-[10px] font-mono text-obsidian-400/30 dark:text-paper-100/30">
            PARAVANT Dev Gallery — Phase 3 — 8 new components
          </p>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => window.history.back()}>
              Back
            </Button>
            <Button variant="secondary" size="sm" onClick={() => window.open('/dev', '_blank')}>
              Phase 1
            </Button>
            <Button variant="secondary" size="sm" onClick={() => window.open('/dev2', '_blank')}>
              Phase 2
            </Button>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Dev3PageInner;
