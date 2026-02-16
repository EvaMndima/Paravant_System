# SESSION 7B: CORE PAGES — DASHBOARD DEVELOPMENT
## Weeks 14-15 | 10 Tasks | ~38 Hours | Data Integration & UI Assembly
**Objective:** Build all 10 core dashboard pages with real data integration, loading states, and responsive layouts.

**Duration:** ~38 hours
**Delivery:** All pages render with real backend data, all interactions work
**Tool Strategy:** Antigravity for page layouts (visual scaffolding) → Claude Code for data integration (API hooks, interactions)

---

## ⚡ QUICK START

```bash
# Recommended execution order:
# 7.2.1 (Cockpit) first — it's the showcase page
# Then 7.2.3 (Strategies List) and 7.2.4 (Strategy Detail) — these form a unit
# Then 7.2.2 (Portfolio) — reuses charts built for Cockpit
# Then remaining pages (Risk, Orders, Alerts, Accounts, Settings, Backtest)

# Parallel opportunities:
#   - 7.2.2 (Portfolio) can start while 7.2.1 completes
#   - 7.2.3 + 7.2.4 can run in parallel (both use same data)
#   - Other pages (Orders, Alerts, Accounts) are independent
```

---

## TASK 7.2.1: Build Cockpit Page (Main Dashboard)

**Effort:** 5 hours
**Status:** Not Started
**Dependencies:** [7.1.2, 7.1.3, 7.1.6]
**Tool:** Antigravity (layout) → Claude Code (data integration)

### Page Layout

The Cockpit is the landing page `/` — shows all critical metrics at a glance.

**Required PRD §6.2.2 widgets (ALL must be present):**

1. **Hero Metrics Row** — 4-6 MetricCards in responsive grid
   - Portfolio Value (with 7-day sparkline)
   - Daily P&L (green/red based on sign)
   - Open Positions (count with max indicator)
   - Win Rate (7D) (percentage with trend arrow)
   - Active Strategies (count)
   - Current Drawdown (percentage with gauge fill)

2. **Risk Status Widget** — GlassCard with status indicators
   - Overall status badge: NORMAL (green) / WARNING (yellow) / CRITICAL (red)
   - Progress bars: Drawdown, Daily Loss, Position Count
   - Circuit breaker states: CLOSED (green) / WARNING (yellow) / OPEN (red)

3. **Regime Indicators Widget** — Market state snapshot
   - Trend: direction + ADX confidence
   - Volatility: current ATR vs average
   - Momentum: RSI value + zone
   - Regime dropdown selector (mutable via `PUT /api/v1/system/regime`)

4. **Positions Widget** — DataTable with live P&L
   - Columns: Symbol, Side, Qty, Entry, Current, P&L, Duration, Strategy
   - Close button per position (confirmation modal)
   - Unrealized P&L color-coded

5. **Strategies Widget** — Compact strategy list
   - Name, status badge, return %, position count
   - Click → navigate to strategy detail
   - "View All" link to strategies page

6. **Recent Alerts Widget** — Alert feed
   - Severity emoji + timestamp + message
   - Last 5 alerts
   - "View All" link to alerts page

### Implementation Pattern

```typescript
// CockpitPage.tsx
export function CockpitPage() {
  const dashboard = useDashboardSummary()
  const positions = usePositions()
  const strategies = useStrategies()
  const alerts = useAlerts(5)
  const risk = useRiskStatus()
  const regime = useRegime()

  if (dashboard.isLoading) return <CockpitSkeleton />
  if (dashboard.error) return <ErrorCard error={dashboard.error} />

  return (
    <div className="space-y-6">
      {/* Hero Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard label="Portfolio Value" value={formatCurrency(dashboard.data.portfolio_value)} sparkline={dashboard.data.sparkline_7d} />
        <MetricCard label="Daily P&L" value={formatCurrency(dashboard.data.daily_pnl)} change={{ value: dashboard.data.daily_return_pct, isPositive: dashboard.data.daily_pnl > 0 }} />
        {/* ... more metric cards ... */}
      </div>

      {/* Risk + Regime widgets in 2-column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RiskStatusWidget risk={risk.data} />
        <RegimeIndicators regime={regime.data} onChangeRegime={regime.setRegime} />
      </div>

      {/* Positions table */}
      <GlassCard variant="elevated">
        <h2 className="text-xl font-serif mb-4">Open Positions</h2>
        <PositionsTable positions={positions.data} onClosePosition={handleClosePosition} />
      </GlassCard>

      {/* Strategies + Alerts in 2-column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StrategiesWidget strategies={strategies.data} />
        <AlertsWidget alerts={alerts.data} />
      </div>
    </div>
  )
}
```

### Acceptance Criteria

- [ ] All 6 PRD §6.2.2 widgets present and populated with real data
- [ ] Hero MetricCards display correct values from `useDashboardSummary()`
- [ ] Sparklines render in MetricCards
- [ ] Risk gauges update instantly via SSE (no visible polling delay)
- [ ] Regime dropdown changes regime via `api.system.setRegime()`
- [ ] Positions table updates instantly via SSE on fill/close events
- [ ] Close position button triggers confirmation modal and calls API
- [ ] Strategies list links to detail page (`/strategies/:id`)
- [ ] Alerts feed updates instantly via SSE when new alert fires
- [ ] Loading skeletons on first load (matching layout)
- [ ] Error states for failed API calls
- [ ] Responsive grid: 3 columns on desktop, 1 on mobile
- [ ] No console warnings or errors

---

## TASK 7.2.2: Build Portfolio Page

**Effort:** 4 hours
**Status:** Not Started
**Dependencies:** [7.1.6, 7.2.1]
**Tool:** Antigravity (chart layout) → Claude Code (data + Recharts config)

### PRD §6.3 required charts (ALL must be present)

1. **Equity Curve** (PRD §6.3.1)
   - Line chart with area fill
   - Benchmark overlay (Buy-and-hold BTC, dashed line)
   - Drawdown underwater chart below (synchronized)
   - Time range selector: 1W / 1M / 3M / 6M / 1Y / ALL
   - Data from: `useEquityCurve(range)`

2. **Monthly Returns Heatmap** (PRD §6.3.2)
   - Rows = years, columns = months
   - Color scale: red (negative) → white (zero) → green (positive)
   - Each cell shows return % and trade count
   - Data from: `usePnlHeatmap()`

3. **Trade Distribution Histogram** (PRD §6.3.3)
   - Histogram of return % per trade
   - Mean line overlay
   - Median line overlay
   - Expectancy annotation
   - Data from: P&L endpoint

### Additional portfolio metrics section

- Total return, Sharpe ratio, Sortino ratio, max drawdown
- Win rate, average win/loss, profit factor
- P&L breakdown by strategy (donut chart)
- P&L breakdown by symbol (horizontal bar chart)

### Implementation

```typescript
// PortfolioPage.tsx
export function PortfolioPage() {
  const [range, setRange] = useState('1M')
  const equityCurve = useEquityCurve(range)
  const heatmap = usePnlHeatmap()
  const pnlByStrategy = usePnlByStrategy()

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-serif">Portfolio Performance</h1>
        <div className="flex gap-2">
          {['1W', '1M', '3M', '6M', '1Y', 'ALL'].map(r => (
            <Button
              key={r}
              variant={range === r ? 'primary' : 'secondary'}
              onClick={() => setRange(r)}
              size="sm"
            >
              {r}
            </Button>
          ))}
        </div>
      </div>

      {/* Equity curve + drawdown */}
      <GlassCard variant="elevated">
        <EquityCurveChart data={equityCurve.data} range={range} />
      </GlassCard>

      {/* Summary metrics row */}
      <PortfolioMetrics metrics={equityCurve.data?.metrics} />

      {/* Heatmap */}
      <GlassCard variant="elevated">
        <h2 className="text-xl font-serif mb-4">Monthly Returns</h2>
        <MonthlyHeatmap data={heatmap.data} />
      </GlassCard>

      {/* Trade histogram + breakdowns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard variant="elevated">
          <TradeDistributionHistogram />
        </GlassCard>
        <GlassCard variant="elevated">
          <PnLBreakdownCharts byStrategy={pnlByStrategy.data} />
        </GlassCard>
      </div>
    </div>
  )
}
```

### Acceptance Criteria

- [ ] Equity curve renders with real data from backend
- [ ] Benchmark overlay shows comparison curve
- [ ] Drawdown underwater chart synchronized with equity curve
- [ ] Time range selector switches data correctly
- [ ] Monthly heatmap renders with correct color scale (red/white/green)
- [ ] Trade histogram shows distribution with mean/median overlay
- [ ] All charts responsive (resize with container)
- [ ] Loading states for each section independently
- [ ] Charts use DESIGN_GUIDE §4.7 color palette
- [ ] No console errors or warnings

---

## TASK 7.2.3: Build Strategies List Page

**Effort:** 3 hours
**Status:** Not Started
**Dependencies:** [7.1.6]
**Tool:** Antigravity (layout) → Claude Code (data + interactions)

### Layout

Grid of strategy cards (default) or table view (toggle).

```
Strategy card:
┌──────────────────────────────┐
│ EMA Trend BTC          LIVE  │
│ Template: EMA Trend + RSI     │
│                              │
│ Return: +12.5%  Sharpe: 1.8  │
│ Win Rate: 62%   Trades: 47   │
│ Drawdown: -3.2% Since: Jan 15│
│                              │
│ [Pause] [Backtest] [Details]│
└──────────────────────────────┘
```

### Features

- **Grid/table view toggle**
- **Filters:** by status (All / Live / Paper / Paused / Draft), by template
- **Sort:** by return, by Sharpe, by name, by creation date
- **Quick actions:** Pause/Resume/Backtest buttons
- **"Create New Strategy" button**

### Implementation

```typescript
// StrategiesListPage.tsx
export function StrategiesListPage() {
  const strategies = useStrategies()
  const [view, setView] = useState<'grid' | 'table'>('grid')
  const [statusFilter, setStatusFilter] = useState('All')
  const [sortBy, setSortBy] = useState('return')

  const filtered = useMemo(() => {
    let result = strategies.data || []
    if (statusFilter !== 'All') result = result.filter(s => s.status === statusFilter)
    return result.sort((a, b) => {
      switch (sortBy) {
        case 'return': return (b.return_pct || 0) - (a.return_pct || 0)
        case 'sharpe': return (b.sharpe_ratio || 0) - (a.sharpe_ratio || 0)
        case 'name': return a.name.localeCompare(b.name)
        default: return 0
      }
    })
  }, [strategies.data, statusFilter, sortBy])

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-serif">Strategies</h1>
        <Button variant="primary" onClick={() => openCreateModal()}>Create New Strategy</Button>
      </div>

      {/* Controls */}
      <div className="flex justify-between items-center bg-glass-panel p-4 rounded-lg">
        <div className="flex gap-2">
          {['All', 'Live', 'Paper', 'Paused', 'Draft'].map(status => (
            <Button
              key={status}
              variant={statusFilter === status ? 'primary' : 'secondary'}
              onClick={() => setStatusFilter(status)}
              size="sm"
            >
              {status}
            </Button>
          ))}
        </div>
        <div className="flex gap-2">
          <Button variant={view === 'grid' ? 'primary' : 'secondary'} onClick={() => setView('grid')} size="sm">Grid</Button>
          <Button variant={view === 'table' ? 'primary' : 'secondary'} onClick={() => setView('table')} size="sm">Table</Button>
        </div>
      </div>

      {/* Grid or Table view */}
      {view === 'grid' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(strategy => (
            <StrategyCard key={strategy.id} strategy={strategy} />
          ))}
        </div>
      )}
      {view === 'table' && (
        <StrategiesTable strategies={filtered} />
      )}
    </div>
  )
}
```

### Acceptance Criteria

- [ ] All strategies displayed with correct data
- [ ] Status badges color-coded (LIVE=green, PAPER=blue, PAUSED=yellow)
- [ ] Grid/table view toggle works
- [ ] Filters by status functional
- [ ] Sort options work correctly
- [ ] Click card navigates to `/strategies/:id`
- [ ] Quick actions (pause/resume) work via API
- [ ] "Create New" button present (actual creation can be Phase 8)
- [ ] Loading skeletons on initial load
- [ ] Responsive grid (3 cols → 2 cols → 1 col)

---

## TASK 7.2.4: Build Strategy Detail Page

**Effort:** 5 hours
**Status:** Not Started
**Dependencies:** [7.1.6, 7.2.2]
**Tool:** Antigravity (layout) → Claude Code (data + parameter editing)

### PRD §6.4 required sections (ALL 7 must be present)

1. **Overview** — Strategy metadata, current status, key metrics, recommendations
2. **Parameters** — All strategy parameters grouped by `ui_group`, editable with min/max validation
3. **Backtest Results** — Metrics table, equity curve, trade list
4. **Paper Trading Results** — Same metrics for paper period
5. **Live Results** — Real performance metrics
6. **Recommendations** — System-generated suggestions (if any)
7. **Lifecycle** — Status history timeline with timestamps

### Parameter editor

```
┌──────────────────────────────────────────┐
│ ENTRY PARAMETERS                          │
│                                          │
│ Fast EMA Period    ──[●]──────  12       │
│                    min: 5  max: 50       │
│                                          │
│ Slow EMA Period    ────[●]────  26       │
│                    min: 10  max: 200     │
│                                          │
│ [Save Changes]  [Reset to Template]      │
└──────────────────────────────────────────┘
```

### Implementation

```typescript
// StrategyDetailPage.tsx
export function StrategyDetailPage() {
  const { id } = useParams<{ id: string }>()
  const strategy = useStrategy(id!)
  const [tab, setTab] = useState('overview')
  const [paramValues, setParamValues] = useState(strategy.data?.parameters || {})
  const [isSaving, setIsSaving] = useState(false)

  const handleSaveParams = async () => {
    setIsSaving(true)
    try {
      await api.strategies.update(id!, { parameters: paramValues })
      addToast({ type: 'success', title: 'Parameters saved' })
    } catch (error) {
      addToast({ type: 'error', title: 'Failed to save parameters' })
    } finally {
      setIsSaving(false)
    }
  }

  if (strategy.isLoading) return <StrategyDetailSkeleton />
  if (strategy.error) return <ErrorCard error={strategy.error} />

  const data = strategy.data!

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-serif">{data.name}</h1>
          <p className="text-obsidian-600 dark:text-obsidian-300 mt-2">{data.template_type}</p>
        </div>
        <Badge variant={data.status === 'LIVE' ? 'success' : 'info'}>{data.status}</Badge>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-deep-teal-200 dark:border-deep-teal-800">
        {['overview', 'parameters', 'backtest', 'paper', 'live', 'recommendations', 'lifecycle'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn('px-4 py-2 border-b-2 font-medium transition', tab === t ? 'border-deep-teal-500' : 'border-transparent')}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'overview' && <StrategyOverview strategy={data} />}
      {tab === 'parameters' && (
        <GlassCard variant="elevated">
          <ParameterEditor
            parameters={data.parameters}
            template={data.template}
            values={paramValues}
            onChange={setParamValues}
          />
          <div className="mt-4 flex gap-2">
            <Button variant="primary" isLoading={isSaving} onClick={handleSaveParams}>
              Save Changes
            </Button>
            <Button variant="secondary" onClick={() => setParamValues(data.parameters)}>
              Reset to Template
            </Button>
          </div>
        </GlassCard>
      )}
      {tab === 'backtest' && <BacktestResultsSection data={data.backtest_results} />}
      {tab === 'paper' && <PaperTradingSection data={data.paper_results} />}
      {tab === 'live' && <LiveResultsSection data={data.live_results} />}
      {tab === 'recommendations' && <RecommendationsSection recommendations={data.recommendations} />}
      {tab === 'lifecycle' && <LifecycleTimeline history={data.lifecycle_history} />}
    </div>
  )
}
```

### Acceptance Criteria

- [ ] All 7 PRD §6.4 sections present and populated
- [ ] Tabbed navigation between sections works
- [ ] Parameters grouped by `ui_group` with correct layout
- [ ] Parameter editing validates against template ranges (min/max/step)
- [ ] Save changes calls PUT API endpoint
- [ ] Charts render correctly with strategy-specific data
- [ ] Lifecycle timeline shows status transitions with timestamps
- [ ] Back navigation returns to strategy list
- [ ] Parameter sliders work correctly (dragging, clicking, keyboard)
- [ ] Loading skeletons for async data sections

---

## TASK 7.2.5: Build Risk Page

**Effort:** 4 hours
**Status:** Not Started
**Dependencies:** [7.1.6]
**Tool:** Antigravity (layout) → Claude Code (data + interactions)

### Layout

```
RISK OVERVIEW
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  DRAWDOWN   │ │ DAILY LOSS  │ │  POSITIONS  │
│   [GAUGE]   │ │   [GAUGE]   │ │   [GAUGE]   │
│  3.2% / 15% │ │  0.8% / 5%  │ │   3 / 10    │
└─────────────┘ └─────────────┘ └─────────────┘

CIRCUIT BREAKERS
┌───────────────┬────────────┬────────────┬────────────┐
│ Breaker       │ Status     │ Threshold  │ Current    │
│ Drawdown      │ ● CLOSED   │ 15%        │ 3.2%      │
│ Loss Rate     │ ● CLOSED   │ 70%        │ 38%       │
│ Error Rate    │ ● WARNING  │ 10/hr      │ 7/hr      │
└───────────────┴────────────┴────────────┴────────────┘

KILL SWITCH
Status: ● INACTIVE
[🚨 ACTIVATE KILL SWITCH]

PORTFOLIO EXPOSURE
BTC Exposure: 35% / 40% max  [████████░░]
ETH Exposure: 20% / 30% max  [██████░░░░]

KILL SWITCH HISTORY
┌───────────┬───────────┬───────────────────┬─────────────┐
│ Action    │ Time      │ Reason            │ Duration    │
│ ACTIVATED │ Feb 14    │ "Manual: market   │ 2h 15m      │
│           │ 10:30 AM  │  flash crash"     │             │
└───────────┴───────────┴───────────────────┴─────────────┘
```

### Features

- **Risk Gauges** — Custom SVG component with color zones
- **Circuit Breakers** — Table showing status of each circuit breaker
- **Kill Switch Control** — Large emergency button with confirmation
- **Portfolio Exposure** — Progress bars for correlation limits
- **Kill Switch Audit History** — Table of activations/deactivations with reason and duration

### Implementation

```typescript
// RiskPage.tsx
export function RiskPage() {
  const risk = useRiskStatus()
  const killSwitch = useKillSwitch()
  const [showKillSwitchModal, setShowKillSwitchModal] = useState(false)
  const [killSwitchReason, setKillSwitchReason] = useState('')

  const handleActivateKillSwitch = async () => {
    await api.risk.activateKillSwitch(killSwitchReason)
    setShowKillSwitchModal(false)
    addToast({ type: 'critical', title: 'Kill switch activated' })
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-serif">Risk Management</h1>

      {/* Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <GaugeChart
          value={risk.data?.current_drawdown_pct || 0}
          max={risk.data?.max_drawdown_limit || 15}
          label="Drawdown"
        />
        <GaugeChart
          value={risk.data?.daily_loss_pct || 0}
          max={risk.data?.daily_loss_limit || 5}
          label="Daily Loss"
        />
        <GaugeChart
          value={risk.data?.open_positions || 0}
          max={risk.data?.max_positions || 10}
          label="Positions"
        />
      </div>

      {/* Circuit breakers */}
      <GlassCard variant="elevated">
        <h2 className="text-xl font-serif mb-4">Circuit Breakers</h2>
        <CircuitBreakerTable breakers={risk.data?.circuit_breakers} />
      </GlassCard>

      {/* Kill switch */}
      <GlassCard variant="elevated" className="border-2 border-loss/50">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-serif">Kill Switch</h2>
          <Badge variant={killSwitch.data?.is_active ? 'danger' : 'success'}>
            {killSwitch.data?.is_active ? 'ACTIVE' : 'INACTIVE'}
          </Badge>
        </div>
        <p className="text-obsidian-600 dark:text-obsidian-300 mb-4">
          Kill switch halts ALL trading immediately. Open positions remain open but no new trades.
        </p>
        <Button
          variant={killSwitch.data?.is_active ? 'secondary' : 'emergency'}
          onClick={() => setShowKillSwitchModal(true)}
        >
          {killSwitch.data?.is_active ? '🚨 DEACTIVATE KILL SWITCH' : '🚨 ACTIVATE KILL SWITCH'}
        </Button>
      </GlassCard>

      {/* Kill switch history */}
      <GlassCard variant="elevated">
        <h2 className="text-xl font-serif mb-4">Kill Switch History</h2>
        <KillSwitchAuditTable />
      </GlassCard>

      {/* Kill Switch Modal */}
      <KillSwitchModal
        isOpen={showKillSwitchModal}
        isActive={killSwitch.data?.is_active || false}
        reason={killSwitchReason}
        onReasonChange={setKillSwitchReason}
        onConfirm={handleActivateKillSwitch}
        onCancel={() => setShowKillSwitchModal(false)}
      />
    </div>
  )
}
```

### Acceptance Criteria

- [ ] Risk gauges render with correct values and color zones (green → yellow → red)
- [ ] Circuit breakers show CLOSED/WARNING/OPEN states
- [ ] Kill switch button works with confirmation flow
- [ ] Kill switch deactivation requires typing "DEACTIVATE"
- [ ] Kill switch button uses `role="alert"` and `aria-live="assertive"` when active
- [ ] Kill switch audit history shows all activations/deactivations with reason and duration
- [ ] Portfolio exposure bars show correlation limits
- [ ] Kill switch and risk data driven by SSE (no polling delays)
- [ ] Loading states for each section
- [ ] No console warnings

---

## TASK 7.2.6: Build Accounts Page

**Effort:** 2.5 hours
**Status:** Not Started
**Dependencies:** [7.1.6]
**Tool:** Antigravity (layout) → Claude Code (data)

### Features

- List all accounts with risk profile badges
- Account detail view: balance, P&L history, risk settings
- Three risk profiles: Conservative / Balanced / Aggressive
- Settings inheritance display: Portfolio → Account → Strategy

### Acceptance Criteria

- [ ] All accounts listed with risk profile badges
- [ ] Account detail shows balance from exchange
- [ ] P&L history chart per account
- [ ] Risk profile settings visible
- [ ] Settings inheritance chain displayed

---

## TASK 7.2.7: Build Orders Page

**Effort:** 2.5 hours
**Status:** Not Started
**Dependencies:** [7.1.6]
**Tool:** Antigravity (table layout) → Claude Code (data + filters)

### Features

- DataTable with all order fields
- Filters: by status, by symbol, by strategy
- Sort by any column
- Pending orders: cancel button
- Click row → order detail panel (drawer/modal)

### Acceptance Criteria

- [ ] All orders displayed with correct data
- [ ] Status badges color-coded
- [ ] Filters functional
- [ ] Cancel pending orders via API
- [ ] Order detail shows full information

---

## TASK 7.2.8: Build Alerts Page

**Effort:** 2.5 hours
**Status:** Not Started
**Dependencies:** [7.1.6]
**Tool:** Antigravity (layout) → Claude Code (data + acknowledgment)

### Features

- Alert feed: severity icon + timestamp + title + message
- Filters: by level (INFO/WARNING/ERROR/CRITICAL), by date range
- Unacknowledged alerts highlighted
- Acknowledge button (calls escalation acknowledge API)
- Alert detail panel on click

### Acceptance Criteria

- [ ] All alerts displayed chronologically
- [ ] Severity indicators with correct colors/icons
- [ ] Filters by level functional
- [ ] Acknowledge button stops escalation
- [ ] Unacknowledged alerts visually distinct
- [ ] Auto-refresh (15s) — but SSE invalidates on new alert first

---

## TASK 7.2.9: Build Settings Page

**Effort:** 2 hours
**Status:** Not Started
**Dependencies:** [7.1.4, 7.1.6]
**Tool:** Claude Code

### Settings sections

1. **Appearance** — Dark mode, accent theme, compact mode, reduced motion
2. **Notifications** — Alert level preferences, quiet hours
3. **Trading** — Default paper trading period, auto-close on shutdown
4. **System Info** — Version, uptime, database stats, API status

### Acceptance Criteria

- [ ] Theme settings persist via ThemeContext
- [ ] Notification preferences saved
- [ ] System info displays correctly
- [ ] All settings take effect immediately
- [ ] No page reload required for most settings

---

## TASK 7.2.10: Build Backtest Page

**Effort:** 3 hours
**Status:** Not Started
**Dependencies:** [7.1.6, 7.2.4]
**Tool:** Antigravity (layout) → Claude Code (backtest execution + results)

### Features

- Strategy selection (dropdown of existing strategies)
- Date range selection
- "Run Backtest" button with progress indicator
- Results display: metrics table + equity curve + trade list
- "Start Paper Trading" button to begin validation

### Implementation

```typescript
// BacktestPage.tsx
export function BacktestPage() {
  const strategies = useStrategies()
  const [selectedStrategy, setSelectedStrategy] = useState<string>('')
  const [dateRange, setDateRange] = useState({ from: '', to: '' })
  const [results, setResults] = useState(null)
  const [isRunning, setIsRunning] = useState(false)

  const handleRunBacktest = async () => {
    setIsRunning(true)
    try {
      const result = await api.strategies.runBacktest(selectedStrategy, dateRange)
      setResults(result)
      addToast({ type: 'success', title: 'Backtest complete' })
    } catch (error) {
      addToast({ type: 'error', title: 'Backtest failed' })
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-serif">Backtest</h1>

      {!results ? (
        <GlassCard variant="elevated">
          <h2 className="text-xl font-serif mb-4">Run Backtest</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Strategy</label>
              <Select value={selectedStrategy} onChange={setSelectedStrategy}>
                {strategies.data?.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">From</label>
                <Input type="date" value={dateRange.from} onChange={(e) => setDateRange({...dateRange, from: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">To</label>
                <Input type="date" value={dateRange.to} onChange={(e) => setDateRange({...dateRange, to: e.target.value})} />
              </div>
            </div>
            <Button variant="primary" isLoading={isRunning} onClick={handleRunBacktest}>
              Run Backtest
            </Button>
          </div>
        </GlassCard>
      ) : (
        <BacktestResultsDisplay results={results} />
      )}
    </div>
  )
}
```

### Acceptance Criteria

- [ ] Strategy selection from existing strategies
- [ ] Date range picker functional
- [ ] Run backtest triggers API call
- [ ] Progress indication during backtest
- [ ] Results render with metrics + chart + trade list
- [ ] "Start Paper Trading" navigates to strategy lifecycle

---

## ✅ COMPLETION CHECKLIST

**Session 7B is complete when:**

- [ ] All 10 pages render without errors
- [ ] Cockpit page shows all 6 PRD §6.2.2 widgets
- [ ] Portfolio page shows equity curve, heatmap, histogram
- [ ] Strategies list shows all strategies with filters
- [ ] Strategy detail has all 7 PRD §6.4 sections
- [ ] Risk page shows gauges, circuit breakers, kill switch, history
- [ ] Orders/Alerts/Accounts pages show real data
- [ ] Settings page works
- [ ] Backtest page runs backtests
- [ ] All pages responsive at 1920px, 1366px, 768px
- [ ] Loading skeletons on all pages
- [ ] Error states for failed API calls

**Output:** Ready for Session 7C (Operational Features, Charts, Deployment)

---

## 📊 SESSION 7B SUMMARY

| Task | Hours | Deliverable |
|------|-------|-------------|
| 7.2.1 | 5h | Cockpit page with 6 widgets |
| 7.2.2 | 4h | Portfolio page with 3 charts |
| 7.2.3 | 3h | Strategies list with filters |
| 7.2.4 | 5h | Strategy detail with 7 sections |
| 7.2.5 | 4h | Risk page with gauges + kill switch + history |
| 7.2.6 | 2.5h | Accounts page |
| 7.2.7 | 2.5h | Orders page |
| 7.2.8 | 2.5h | Alerts page |
| 7.2.9 | 2h | Settings page |
| 7.2.10 | 3h | Backtest page |
| **TOTAL** | **~38h** | **All core dashboard pages with real data** |

---

**Next Phase:** SESSION_7C_IMPLEMENTATION_PROMPT.md (Operational Features, Charts, Deployment)
**Related Files:** 07_PHASE_7_FRONTEND.md | DESIGN_GUIDE.md
