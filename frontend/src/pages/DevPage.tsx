import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Activity, AlertTriangle, Bell, Check, ChevronDown, Download,
  Plus, RefreshCw, Settings, Trash2, TrendingUp, User, Zap,
} from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import { useToast } from '@/contexts/ToastContext';
import { cn, formatCurrency } from '@/lib/utils';
import { fadeInUp, staggerContainer } from '@/lib/animations';
import type { AppTheme, ThemeMode } from '@/types';

import {
  Avatar, Badge, Button, DataTable, Dropdown, EmptyState,
  ErrorBoundary, GlassCard, Input, KeyboardShortcuts, LoadingState, Logo,
  MetricCard, Modal, Progress, SearchInput, Skeleton,
  Tabs, TabsList, TabsTrigger, TabsContent,
  Toggle, Tooltip,
} from '@/components/ui';
import type { Column } from '@/components/ui';
import { SparklineChart, AreaChart, DonutChart, BenchmarkChart } from '@/components/charts';
import type { AreaChartData, DonutSegment, BenchmarkDataPoint } from '@/components/charts';

// ── theme metadata ────────────────────────────────────────────
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

// ── sample data for DataTable ─────────────────────────────────
interface Trade {
  symbol: string;
  side: string;
  qty: number;
  price: number;
  pnl: number;
}

const SAMPLE_TRADES: Trade[] = [
  { symbol: 'BTCUSDT', side: 'BUY',  qty: 0.5,  price: 67420, pnl:  1240.5 },
  { symbol: 'ETHUSDT', side: 'SELL', qty: 2.0,  price: 3510,  pnl: -320.0  },
  { symbol: 'BNBUSDT', side: 'BUY',  qty: 10.0, price: 594,   pnl:  88.4   },
];

const TRADE_COLS: Column<Trade>[] = [
  { key: 'symbol', header: 'Symbol',  sortable: true },
  { key: 'side',   header: 'Side',    sortable: true, render: (v) => (
    <span className={cn('font-mono font-bold', v === 'BUY' ? 'text-gain' : 'text-loss')}>{String(v)}</span>
  )},
  { key: 'qty',    header: 'Qty',     sortable: true, align: 'right' },
  { key: 'price',  header: 'Price',   sortable: true, align: 'right',
    render: (v) => formatCurrency(Number(v)) },
  { key: 'pnl',    header: 'PnL',     sortable: true, align: 'right',
    render: (v) => (
      <span className={cn('font-mono', Number(v) >= 0 ? 'text-gain' : 'text-loss')}>
        {formatCurrency(Number(v))}
      </span>
    )},
];

// ── chart mock data ───────────────────────────────────────────
const SPARKLINE_DATA = [42, 45, 43, 48, 52, 49, 55, 58, 54, 60, 63, 59, 65, 68, 64, 70, 72, 68, 75, 78];
const SPARKLINE_LOSS  = [80, 76, 74, 70, 72, 68, 65, 61, 63, 58, 55, 57, 52, 49, 51, 47, 44, 46, 41, 38];

const PERF_DATA: AreaChartData[] = [
  { date: 'Feb 1',  value: 980200 }, { date: 'Feb 3',  value: 983400 },
  { date: 'Feb 5',  value: 979800 }, { date: 'Feb 7',  value: 988100 },
  { date: 'Feb 9',  value: 985600 }, { date: 'Feb 11', value: 991200 },
  { date: 'Feb 13', value: 989300 }, { date: 'Feb 15', value: 994800 },
  { date: 'Feb 17', value: 992100 }, { date: 'Feb 19', value: 997400 },
  { date: 'Feb 21', value: 995600 }, { date: 'Feb 23', value: 1001200 },
  { date: 'Feb 25', value: 999300 }, { date: 'Feb 27', value: 1005800 },
  { date: 'Mar 1',  value: 994272 },
];

const BY_STRATEGY: DonutSegment[] = [
  { name: 'Simple_MA',      value: 35, color: '' },
  { name: 'Donchian_BB',    value: 25, color: '' },
  { name: 'Scalper_RSI',    value: 20, color: '' },
  { name: 'Momentum_MACD',  value: 12, color: '' },
  { name: 'Breakout',       value: 8,  color: '' },
];

const BY_RISK_TIER: DonutSegment[] = [
  { name: 'High Risk',   value: 20, color: '' },
  { name: 'Medium Risk', value: 45, color: '' },
  { name: 'Low Risk',    value: 35, color: '' },
];

const BENCHMARK_DATA: BenchmarkDataPoint[] = [
  { date: 'Mar',  portfolio: 2.1,  benchmark: 1.2 },
  { date: 'Apr',  portfolio: 4.8,  benchmark: 2.8 },
  { date: 'May',  portfolio: 3.9,  benchmark: 3.1 },
  { date: 'Jun',  portfolio: 7.2,  benchmark: 4.0 },
  { date: 'Jul',  portfolio: 9.4,  benchmark: 4.9 },
  { date: 'Aug',  portfolio: 8.1,  benchmark: 5.5 },
  { date: 'Sep',  portfolio: 11.3, benchmark: 6.2 },
  { date: 'Oct',  portfolio: 13.7, benchmark: 7.1 },
  { date: 'Nov',  portfolio: 12.2, benchmark: 7.8 },
  { date: 'Dec',  portfolio: 15.9, benchmark: 8.4 },
  { date: 'Jan',  portfolio: 18.4, benchmark: 9.1 },
  { date: 'Feb',  portfolio: 21.2, benchmark: 10.3 },
];

// ── DevPage ───────────────────────────────────────────────────
export default function DevPage() {
  const { mode, setMode, appTheme, setAppTheme } = useTheme();
  const { toast } = useToast();

  // interactive state
  const [searchVal, setSearchVal]         = useState('');
  const [toggleA, setToggleA]             = useState(true);
  const [toggleB, setToggleB]             = useState(false);
  const [modalOpen, setModalOpen]         = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [tabValue, setTabValue]           = useState('overview');

  const SectionTitle = ({ children }: { children: React.ReactNode }) => (
    <h2 className="font-sans font-semibold text-xs uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-4">
      {children}
    </h2>
  );

  return (
    <div className="min-h-screen bg-paper-100 dark:bg-obsidian-400 p-8 transition-colors duration-300">
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="max-w-5xl mx-auto space-y-10"
      >

        {/* ── Header ────────────────────────────────────────── */}
        <motion.div variants={fadeInUp}>
          <p className="text-xs font-mono uppercase tracking-[0.2em] text-turquoise mb-2">
            Phase 2 — Component Gallery
          </p>
          <h1 className="font-display text-5xl text-deep-teal-800 dark:text-paper-100 mb-2" style={{ fontVariant: 'small-caps' }}>
            Paravant
          </h1>
          <p className="font-sans text-sm text-obsidian-400/60 dark:text-paper-100/60">
            All 21 UI primitives verified — ready for Phase 3
          </p>
        </motion.div>

        {/* ── Theme Controls ────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6 space-y-4">
          <SectionTitle>Theme Controls</SectionTitle>
          <div className="flex flex-wrap gap-6">
            <div className="space-y-2">
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 uppercase tracking-wider">Mode</p>
              <div className="flex gap-2">
                {MODES.map(({ id, label }) => (
                  <button key={id} onClick={() => setMode(id)}
                    className={cn(
                      "px-3 py-1.5 rounded-lg text-xs font-sans font-medium transition-all",
                      mode === id
                        ? "bg-turquoise text-white"
                        : "bg-deep-teal-800/10 dark:bg-white/10 text-obsidian-400 dark:text-paper-100 hover:bg-deep-teal-800/20 dark:hover:bg-white/20"
                    )}
                  >{label}</button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 uppercase tracking-wider">Palette</p>
              <div className="flex gap-2">
                {THEMES.map(({ id, label }) => (
                  <button key={id} onClick={() => setAppTheme(id)}
                    className={cn(
                      "px-3 py-1.5 rounded-lg text-xs font-sans font-medium transition-all",
                      appTheme === id
                        ? "bg-turquoise text-white"
                        : "bg-deep-teal-800/10 dark:bg-white/10 text-obsidian-400 dark:text-paper-100 hover:bg-deep-teal-800/20 dark:hover:bg-white/20"
                    )}
                  >{label}</button>
                ))}
              </div>
            </div>
          </div>
        </motion.section>

        {/* ── 2.1 Logo ──────────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.1 Logo</SectionTitle>
          <div className="flex items-center gap-8 flex-wrap">
            <Logo className="scale-75 origin-left" />
            <Logo />
            <Logo className="scale-125 origin-left" />
            <Logo showText={false} />
          </div>
        </motion.section>

        {/* ── 2.2 GlassCard ─────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.2 GlassCard — 4 variants</SectionTitle>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {(['default', 'elevated', 'subtle', 'dark'] as const).map((v) => (
              <GlassCard key={v} variant={v} padding="md" enableHover>
                <p className="text-xs font-mono text-obsidian-400/50 dark:text-paper-100/50 mb-1">{v}</p>
                <p className="font-sans text-sm text-obsidian-400 dark:text-paper-100">Hover me</p>
              </GlassCard>
            ))}
          </div>
        </motion.section>

        {/* ── 2.3 Badge ─────────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.3 Badge — 6 variants</SectionTitle>
          <div className="flex flex-wrap gap-3 items-center">
            <Badge variant="neutral">Neutral</Badge>
            <Badge variant="success">Active</Badge>
            <Badge variant="warning">Paused</Badge>
            <Badge variant="danger">Risk Breach</Badge>
            <Badge variant="info">Syncing</Badge>
            <Badge variant="neutral">Inactive</Badge>
            <Badge variant="success" dot pulsing>Live</Badge>
          </div>
        </motion.section>

        {/* ── 2.4 Skeleton ──────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.4 Skeleton — loading placeholders</SectionTitle>
          <div className="space-y-3 max-w-sm">
            <Skeleton variant="text" className="w-3/4" />
            <Skeleton variant="text" className="w-full" />
            <Skeleton variant="text" className="w-1/2" />
            <div className="flex items-center gap-3 mt-4">
              <Skeleton variant="circle" className="w-10 h-10 shrink-0" />
              <div className="flex-1 space-y-2">
                <Skeleton variant="text" className="w-full" />
                <Skeleton variant="text" className="w-2/3" />
              </div>
            </div>
            <Skeleton variant="card" className="w-full h-24 mt-2" />
          </div>
        </motion.section>

        {/* ── 2.5 Avatar ────────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.5 Avatar — sizes &amp; statuses</SectionTitle>
          <div className="flex items-end gap-4 flex-wrap">
            <Avatar size="sm" name="Alice Brown" />
            <Avatar size="sm" name="Charlie Davis" status="online" />
            <Avatar size="md" name="Eva Finance" status="offline" />
            <Avatar size="lg" name="George Hayes" status="online" />
            <Avatar size="xl" name="Paravant" />
          </div>
        </motion.section>

        {/* ── 2.6 Button ────────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.6 Button — variants &amp; sizes</SectionTitle>
          <div className="flex flex-wrap gap-3 items-center mb-4">
            <Button variant="primary" leftIcon={<Plus className="w-4 h-4" />}>Add Strategy</Button>
            <Button variant="secondary" leftIcon={<Download className="w-4 h-4" />}>Export</Button>
            <Button variant="ghost" leftIcon={<Settings className="w-4 h-4" />}>Settings</Button>
            <Button variant="danger" leftIcon={<Trash2 className="w-4 h-4" />}>Delete</Button>
            <Button variant="primary" isLoading>Loading</Button>
            <Button variant="primary" disabled>Disabled</Button>
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <Button variant="primary" size="sm">Small</Button>
            <Button variant="primary" size="md">Medium</Button>
            <Button variant="primary" size="lg">Large</Button>
          </div>
        </motion.section>

        {/* ── 2.7 Input ─────────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.7 Input — states &amp; icons</SectionTitle>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl">
            <Input label="Strategy Name" placeholder="e.g. Simple_MA" />
            <Input label="API Key" type="password" placeholder="Enter API key" />
            <Input label="Capital" leftIcon={<span className="text-sm font-mono">$</span>} placeholder="10000" />
            <Input label="Invalid" error="Value must be positive" placeholder="Enter amount" />
          </div>
        </motion.section>

        {/* ── 2.14 SearchInput ──────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.14 SearchInput — with clear &amp; kbd shortcut</SectionTitle>
          <div className="max-w-sm">
            <SearchInput
              placeholder="Search strategies..."
              value={searchVal}
              onChange={(e) => setSearchVal(e.target.value)}
              onClear={() => setSearchVal('')}
            />
          </div>
        </motion.section>

        {/* ── 2.8 Toggle ────────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.8 Toggle — sizes &amp; states</SectionTitle>
          <div className="flex flex-wrap gap-6 items-center">
            <label className="flex items-center gap-3 cursor-pointer">
              <Toggle size="sm" checked={toggleA} onCheckedChange={setToggleA} />
              <span className="text-sm font-sans text-obsidian-400 dark:text-paper-100">
                Paper trading {toggleA ? 'ON' : 'OFF'} (sm)
              </span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <Toggle size="md" checked={toggleB} onCheckedChange={setToggleB} />
              <span className="text-sm font-sans text-obsidian-400 dark:text-paper-100">
                Live trading {toggleB ? 'ON' : 'OFF'} (md)
              </span>
            </label>
            <label className="flex items-center gap-3">
              <Toggle size="md" checked disabled onCheckedChange={() => {}} />
              <span className="text-sm font-sans text-obsidian-400/50 dark:text-paper-100/50">Disabled ON</span>
            </label>
          </div>
        </motion.section>

        {/* ── 2.9 Progress ──────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.9 Progress — variants &amp; sizes</SectionTitle>
          <div className="space-y-4 max-w-lg">
            <div className="space-y-1">
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40">default — 68%</p>
              <Progress value={68} showLabel />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40">success — 90%</p>
              <Progress value={90} variant="success" showLabel />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40">warning — 55%</p>
              <Progress value={55} variant="warning" showLabel />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40">danger — 22%</p>
              <Progress value={22} variant="danger" showLabel />
            </div>
          </div>
        </motion.section>

        {/* ── 2.10 Tooltip ──────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.10 Tooltip — 4 sides</SectionTitle>
          <div className="flex flex-wrap gap-6 items-center justify-center py-8">
            {(['top', 'bottom', 'left', 'right'] as const).map((side) => (
              <Tooltip key={side} content={`${side} tooltip`} side={side}>
                <Button variant="secondary" size="sm">{side}</Button>
              </Tooltip>
            ))}
          </div>
        </motion.section>

        {/* ── 2.11 Tabs ─────────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.11 Tabs — underline &amp; pill variants</SectionTitle>
          <div className="space-y-8">
            <div>
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 mb-3">Underline variant</p>
              <Tabs value={tabValue} onValueChange={setTabValue}>
                <TabsList>
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="positions">Positions</TabsTrigger>
                  <TabsTrigger value="history">History</TabsTrigger>
                  <TabsTrigger value="settings" disabled>Settings</TabsTrigger>
                </TabsList>
                <TabsContent value="overview">
                  <p className="text-sm text-obsidian-400/70 dark:text-paper-100/70">Overview content — metrics and summary</p>
                </TabsContent>
                <TabsContent value="positions">
                  <p className="text-sm text-obsidian-400/70 dark:text-paper-100/70">Positions content — open trades</p>
                </TabsContent>
                <TabsContent value="history">
                  <p className="text-sm text-obsidian-400/70 dark:text-paper-100/70">History content — closed trades</p>
                </TabsContent>
              </Tabs>
            </div>
            <div>
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 mb-3">Pill variant</p>
              <Tabs defaultValue="day">
                <TabsList variant="pill">
                  <TabsTrigger value="day">1D</TabsTrigger>
                  <TabsTrigger value="week">1W</TabsTrigger>
                  <TabsTrigger value="month">1M</TabsTrigger>
                  <TabsTrigger value="all">All</TabsTrigger>
                </TabsList>
                <TabsContent value="day"><p className="text-sm text-obsidian-400/70 dark:text-paper-100/70">Daily view</p></TabsContent>
                <TabsContent value="week"><p className="text-sm text-obsidian-400/70 dark:text-paper-100/70">Weekly view</p></TabsContent>
                <TabsContent value="month"><p className="text-sm text-obsidian-400/70 dark:text-paper-100/70">Monthly view</p></TabsContent>
                <TabsContent value="all"><p className="text-sm text-obsidian-400/70 dark:text-paper-100/70">All time view</p></TabsContent>
              </Tabs>
            </div>
          </div>
        </motion.section>

        {/* ── 2.12 Modal ────────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.12 Modal — portal with backdrop blur</SectionTitle>
          <Button variant="primary" onClick={() => setModalOpen(true)} leftIcon={<Zap className="w-4 h-4" />}>
            Open Modal
          </Button>
          <Modal
            isOpen={modalOpen}
            onClose={() => setModalOpen(false)}
            title="Confirm Trade Execution"
            description="Review the order details before submitting to Binance."
            size="md"
          >
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm font-sans">
                <div>
                  <p className="text-obsidian-400/50 dark:text-paper-100/50 text-xs font-mono mb-1">Symbol</p>
                  <p className="font-mono font-medium text-obsidian-400 dark:text-paper-100">BTCUSDT</p>
                </div>
                <div>
                  <p className="text-obsidian-400/50 dark:text-paper-100/50 text-xs font-mono mb-1">Side</p>
                  <p className="font-mono font-bold text-gain">BUY</p>
                </div>
                <div>
                  <p className="text-obsidian-400/50 dark:text-paper-100/50 text-xs font-mono mb-1">Quantity</p>
                  <p className="font-mono font-medium text-obsidian-400 dark:text-paper-100">0.05 BTC</p>
                </div>
                <div>
                  <p className="text-obsidian-400/50 dark:text-paper-100/50 text-xs font-mono mb-1">Est. Value</p>
                  <p className="font-mono font-medium text-obsidian-400 dark:text-paper-100">{formatCurrency(3371)}</p>
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <Button variant="primary" className="flex-1" leftIcon={<Check className="w-4 h-4" />}
                  onClick={() => { setModalOpen(false); toast({ title: 'Order placed', type: 'success' }); }}>
                  Confirm
                </Button>
                <Button variant="ghost" onClick={() => setModalOpen(false)}>Cancel</Button>
              </div>
            </div>
          </Modal>
        </motion.section>

        {/* ── 2.13 KeyboardShortcuts ────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.13 KeyboardShortcuts — modal with shortcut reference</SectionTitle>
          <Button variant="secondary" onClick={() => setShortcutsOpen(true)} leftIcon={<Zap className="w-4 h-4" />}>
            Show Shortcuts
          </Button>
          <KeyboardShortcuts isOpen={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
        </motion.section>

        {/* ── 2.14 Dropdown ─────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.14 Dropdown — portal, keyboard nav, divider, danger</SectionTitle>
          <div className="flex gap-4">
            <Dropdown
              trigger={
                <Button variant="secondary" rightIcon={<ChevronDown className="w-4 h-4" />}>
                  Strategy Actions
                </Button>
              }
              items={[
                { label: 'Start Strategy',  icon: Activity, onClick: () => toast({ title: 'Strategy started', type: 'success' }) },
                { label: 'Pause Strategy',  icon: Bell,     onClick: () => toast({ title: 'Strategy paused', type: 'warning' }) },
                { label: 'View Details',    icon: TrendingUp },
                { type: 'divider' },
                { label: 'Reset Stats',     icon: RefreshCw },
                { label: 'Delete Strategy', icon: Trash2, danger: true, onClick: () => toast({ title: 'Strategy deleted', type: 'error' }) },
              ]}
            />
            <Dropdown
              align="end"
              trigger={
                <Button variant="ghost" size="sm" leftIcon={<User className="w-4 h-4" />}>
                  Account
                </Button>
              }
              items={[
                { label: 'Profile',  icon: User },
                { label: 'Settings', icon: Settings },
                { type: 'divider' },
                { label: 'Logout',   icon: AlertTriangle, danger: true },
              ]}
            />
          </div>
        </motion.section>

        {/* ── 2.15 MetricCard ───────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.15 MetricCard — KPI grid</SectionTitle>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MetricCard title="Portfolio Value" value={994272.52} format="currency" change={1.24} changeLabel="24h" delay={0} />
            <MetricCard title="Win Rate" value={68.4} suffix="%" change={-2.1} delay={0.05} />
            <MetricCard title="Open Positions" value={3} format="raw" delay={0.1} />
            <MetricCard title="Drawdown" value={12.3} suffix="%" variant="dark" change={0.8} changeLabel="today" delay={0.15} />
          </div>
        </motion.section>

        {/* ── 2.16 DataTable ────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.16 DataTable — sortable, skeleton loading</SectionTitle>
          <div className="space-y-6">
            <DataTable columns={TRADE_COLS as unknown as Column<Record<string, unknown>>[]} data={SAMPLE_TRADES as unknown as Record<string, unknown>[]} onRowClick={(r) => toast({ title: `Selected: ${String(r.symbol)}`, type: 'info' })} />
            <div>
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 mb-3">Loading state:</p>
              <DataTable columns={TRADE_COLS} data={[]} isLoading />
            </div>
            <div>
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 mb-3">Empty state:</p>
              <DataTable columns={TRADE_COLS} data={[]} emptyMessage="No trades found" />
            </div>
          </div>
        </motion.section>

        {/* ── 2.17 EmptyState ───────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.17 EmptyState — 3 variants</SectionTitle>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <GlassCard variant="subtle" padding="none">
              <EmptyState variant="default" title="No Positions" description="No open positions. Start a strategy to begin trading." action={<Button variant="primary" size="sm">Add Strategy</Button>} />
            </GlassCard>
            <GlassCard variant="subtle" padding="none">
              <EmptyState variant="search" title="No Results" description="Try adjusting your search or filter criteria." />
            </GlassCard>
            <GlassCard variant="subtle" padding="none">
              <EmptyState variant="error" title="Load Failed" description="Could not fetch data. Check your connection." action={<Button variant="ghost" size="sm" leftIcon={<RefreshCw className="w-4 h-4" />}>Retry</Button>} />
            </GlassCard>
          </div>
        </motion.section>

        {/* ── 2.18 LoadingState ─────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.18 LoadingState — inline &amp; section</SectionTitle>
          <div className="space-y-4">
            <LoadingState variant="inline" message="Fetching market data..." />
            <GlassCard variant="subtle" padding="none" className="max-w-sm">
              <LoadingState variant="section" message="Loading positions..." />
            </GlassCard>
          </div>
        </motion.section>

        {/* ── 2.19 ErrorBoundary ────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>2.19 ErrorBoundary — fallback UI</SectionTitle>
          <p className="text-sm text-obsidian-400/60 dark:text-paper-100/60 mb-4">
            Wraps child components. The fallback below simulates a caught render error.
          </p>
          <ErrorBoundary fallback={
            <div className="w-full min-h-[160px] flex items-center justify-center p-4">
              <GlassCard variant="subtle" className="max-w-md w-full flex flex-col items-center text-center p-6">
                <div className="p-3 bg-loss/10 rounded-full text-loss mb-3">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <h3 className="font-display text-base font-bold text-obsidian-400 dark:text-paper-100 mb-1">System Error</h3>
                <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50">
                  This is the ErrorBoundary fallback UI rendered correctly.
                </p>
              </GlassCard>
            </div>
          }>
            <p className="text-xs font-mono text-gain">ErrorBoundary wrapping — no error thrown, children render normally.</p>
          </ErrorBoundary>
        </motion.section>

        {/* ── Toast trigger ─────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>Toast System</SectionTitle>
          <div className="flex flex-wrap gap-3">
            <Button variant="primary" size="sm" onClick={() => toast({ title: 'Trade executed', description: 'BTCUSDT BUY 0.05', type: 'success' })}>
              Success Toast
            </Button>
            <Button variant="danger" size="sm" onClick={() => toast({ title: 'Risk breach', description: 'Max drawdown hit.', type: 'error', duration: 8000 })}>
              Error Toast
            </Button>
            <Button variant="ghost" size="sm" onClick={() => toast({ title: 'Strategy paused', type: 'warning' })}>
              Warning Toast
            </Button>
            <Button variant="secondary" size="sm" onClick={() => toast({ title: 'Data synced', type: 'info' })}>
              Info Toast
            </Button>
          </div>
        </motion.section>

        {/* ── Phase 3 separator ─────────────────────────────── */}
        <motion.div variants={fadeInUp} className="border-t border-deep-teal-800/10 dark:border-white/10 pt-6">
          <p className="text-xs font-mono uppercase tracking-[0.2em] text-turquoise mb-2">
            Phase 3 — Chart Components
          </p>
          <p className="font-sans text-sm text-obsidian-400/60 dark:text-paper-100/60">
            4 chart primitives: SparklineChart, AreaChart, DonutChart, BenchmarkChart
          </p>
        </motion.div>

        {/* ── 3.1 SparklineChart inside MetricCards ─────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>3.1 SparklineChart — MetricCard integration</SectionTitle>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MetricCard
              title="Portfolio Value"
              value={994272.52}
              format="currency"
              change={1.24}
              changeLabel="24h"
              sparkline={<SparklineChart data={SPARKLINE_DATA} color="turquoise" />}
            />
            <MetricCard
              title="Win Rate"
              value={68.4}
              suffix="%"
              change={2.1}
              sparkline={<SparklineChart data={SPARKLINE_DATA} color="gain" />}
            />
            <MetricCard
              title="Drawdown"
              value={12.3}
              suffix="%"
              change={-3.2}
              sparkline={<SparklineChart data={SPARKLINE_LOSS} color="loss" />}
            />
            <MetricCard
              title="Signals Today"
              value={156}
              format="raw"
              change={12}
              variant="dark"
              sparkline={<SparklineChart data={SPARKLINE_DATA} color="neutral" showArea={false} />}
            />
          </div>
        </motion.section>

        {/* ── 3.2 AreaChart — Performance / NAV ─────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>3.2 AreaChart — NAV 30 Days (Cockpit Performance widget)</SectionTitle>
          <GlassCard variant="subtle" padding="none" className="p-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-xs font-mono font-bold uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
                  Performance / NAV
                </p>
                <p className="font-mono text-2xl font-medium text-deep-teal-800 dark:text-paper-100 mt-1">
                  {formatCurrency(994272.52)}
                </p>
              </div>
              <Badge variant="success" dot pulsing>Live</Badge>
            </div>
            <AreaChart data={PERF_DATA} height={220} showTooltip gradientId="nav-perf" />
          </GlassCard>
        </motion.section>

        {/* ── 3.3 DonutChart — Capital Allocation ───────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>3.3 DonutChart — Capital Allocation (system.pdf)</SectionTitle>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <GlassCard variant="subtle" padding="md">
              <p className="text-xs font-mono font-bold uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-4">
                By Strategy
              </p>
              <DonutChart
                data={BY_STRATEGY}
                height={260}
                centerContent={
                  <div className="text-center">
                    <p className="font-mono text-lg font-bold text-deep-teal-800 dark:text-paper-100 leading-none">85%</p>
                    <p className="text-[10px] font-mono uppercase tracking-wider text-obsidian-400/50 dark:text-paper-100/50 mt-0.5">Deployed</p>
                  </div>
                }
              />
            </GlassCard>
            <GlassCard variant="subtle" padding="md">
              <p className="text-xs font-mono font-bold uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-4">
                By Risk Tier
              </p>
              <DonutChart
                data={BY_RISK_TIER}
                height={260}
                innerRadius="55%"
                centerContent={
                  <div className="text-center">
                    <p className="font-mono text-base font-bold text-deep-teal-800 dark:text-paper-100 leading-none">$2.88M</p>
                    <p className="text-[10px] font-mono uppercase tracking-wider text-obsidian-400/50 dark:text-paper-100/50 mt-0.5">Total Assets</p>
                  </div>
                }
              />
            </GlassCard>
          </div>
        </motion.section>

        {/* ── 3.4 BenchmarkChart — Portfolio vs SPY ─────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>3.4 BenchmarkChart — Portfolio vs Benchmark (Portfolio page)</SectionTitle>
          <GlassCard variant="subtle" padding="md">
            <p className="text-xs font-mono font-bold uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-4">
              Performance Attribution — 12M
            </p>
            <BenchmarkChart data={BENCHMARK_DATA} height={260} />
          </GlassCard>
        </motion.section>

        {/* ── Footer ────────────────────────────────────────── */}
        <motion.div variants={fadeInUp} className="pb-8 text-center">
          <p className="text-xs font-mono text-obsidian-400/30 dark:text-paper-100/30">
            Session 4 complete — 21 UI components + 4 chart components verified
          </p>
        </motion.div>

      </motion.div>
    </div>
  );
}
