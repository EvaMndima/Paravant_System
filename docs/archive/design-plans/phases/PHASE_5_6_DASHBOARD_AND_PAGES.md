# Phase 5: Dashboard Components + Phase 6: Pages

## Phase 5: Dashboard Components (3-4 hours)

### Goal
Port the complex dashboard-specific components. These are composed from UI primitives and are the building blocks of pages.

### Pre-requisite
Phase 4 complete (layout shell working, navigation functional)

---

### 5.1 MarketTicker
**Source:** `docs/design/references/components/dashboard/MarketTicker.tsx`
**Target:** `frontend/src/components/dashboard/MarketTicker.tsx`

**From cockpit.pdf:** The horizontal scrolling ticker at top showing:
```
SPY 510.36 +0.45%  |  QQQ 438.98 +1.00%  |  BTC 67,763.74 +3.61%  |  ...
```
- Auto-scroll or overflow-x
- Green/red for positive/negative
- Monospace numbers

---

### 5.2 ActivityFeed
**Source:** `docs/design/references/components/dashboard/ActivityFeed.tsx`
**Target:** `frontend/src/components/dashboard/ActivityFeed.tsx`

**From cockpit.pdf:** The "LIVE DATA / System Activity" section:
- Tabbed: System Activity | Positions | Allocation
- Each activity: icon + title + description + timestamp
- Color-coded severity icons (red warning, blue info, green trade, orange curator)
- "VIEW ALL ACTIVITY" link at bottom
- Filter button

---

### 5.3 Watchlist
**Source:** `docs/design/references/components/dashboard/Watchlist.tsx`
**Target:** `frontend/src/components/dashboard/Watchlist.tsx`

**From cockpit.pdf:** Right sidebar watchlist:
```
WATCHLIST  [+]
NVDA  $894.04  +2.20%
AMD   $179.56  -1.61%
COIN  $243.90  +4.68%
```

---

### 5.4 PositionsTable
**Source:** `docs/design/references/components/dashboard/PositionsTable.tsx`
**Target:** `frontend/src/components/dashboard/PositionsTable.tsx`

**From portfolio.pdf:** The "CURRENT HOLDINGS" table:
- Columns: Instrument, Sector, Qty, Avg Cost, Price, Mkt Value, P&L, Weight
- Color-coded P&L (green positive, red negative)
- Percentage bar for weight
- Avatar/initial badge for instrument
- Searchable

---

### 5.5 MarketRegimePanel
**Source:** `docs/design/references/components/dashboard/MarketRegimePanel.tsx`
**Target:** `frontend/src/components/dashboard/MarketRegimePanel.tsx`

**From system.pdf:** The "CURRENT ASSESSMENT" panel:
- "TRENDING BULLISH" badge with confidence %
- VIX, Breadth, Trend, Correlation, PutCall indicators
- Each with value + status label + sparkline

---

### 5.6 StrategyCard
**Source:** `docs/design/references/components/dashboard/StrategyCard.tsx`
**Target:** `frontend/src/components/dashboard/StrategyCard.tsx`

**From agents page PDF:** Individual agent/strategy card:
```
+----------------------------------+
| Apex Core Pro      [ML-SIGNAL] * |
| DAY P&L    WIN RATE              |
| +$4,152    58.9%                 |
| [sparkline chart]                |
+----------------------------------+
```
- Status dot (green=active, yellow=paused, red=error, blue=training)
- Strategy type badge
- Day P&L and Win Rate
- Mini sparkline
- Click to view detail

---

### 5.7 StrategyGrid
**Source:** `docs/design/references/components/dashboard/StrategyGrid.tsx`
**Target:** `frontend/src/components/dashboard/StrategyGrid.tsx`

Grid layout for StrategyCards with:
- Search bar
- Status filter
- Strategy filter
- Sort options (P&L Today, Win Rate, etc.)
- Summary stats bar (Total, Active, Paused, Training, Error counts)

---

### 5.8 EmergencyPanel
**Source:** `docs/design/references/components/dashboard/EmergencyPanel.tsx`
**Target:** `frontend/src/components/dashboard/EmergencyPanel.tsx`

**Critical safety component.** Slide-out panel:
- Kill switch (big red button)
- Close all positions
- Disable strategies
- System status indicators
- Confirmation modals for destructive actions

---

### 5.9 NotificationsPanel
**Source:** `docs/design/references/components/layout/NotificationsPanel.tsx`
**Target:** `frontend/src/components/layout/NotificationsPanel.tsx`

Dropdown from header bell:
- Tabs: All, Trade, Alert, Curator, System
- Each notification: icon + title + message + timestamp
- Mark as read
- Mark all read
- "VIEW FULL HISTORY" link

---

### 5.10 AlertModal
**Source:** `docs/design/references/components/dashboard/AlertModal.tsx`
**Target:** `frontend/src/components/dashboard/AlertModal.tsx`

Create new alert modal:
- Asset selector
- Condition (above/below/cross)
- Price target
- Alert type (price/technical/risk)

---

### 5.11 PositionDrawer
**Source:** `docs/design/references/components/dashboard/PositionDrawer.tsx`
**Target:** `frontend/src/components/dashboard/PositionDrawer.tsx`

Slide-out from right when clicking a position:
- Full position details
- Entry/current/target prices
- P&L chart since entry
- Close position button
- Strategy info link

---

## Phase 6: Pages — One at a Time (6-8 hours)

### Goal
Build each page using the components from Phases 2-5, with MOCK DATA. Match the target PDFs exactly.

### Critical Rule
**Use hardcoded mock data matching the PDFs.** Do NOT connect to any API. The goal is pure visual accuracy.

---

### 6.1 CockpitPage (Main Dashboard)
**Source:** `docs/design/references/components/pages/CockpitPage.tsx`
**Target:** `frontend/src/pages/CockpitPage.tsx`
**Target visual:** `docs/design/pdf/cockpit.pdf`

**Layout (from PDF, top to bottom):**
1. Alert banner: "Attention: 2 agents currently in error state" (amber)
2. System Status header: "SYSTEM STATUS [LIVE]" + stats + Export/Emergency buttons
3. MarketTicker: SPY, QQQ, IWM, BTC, ETH, VIX, GLD
4. MetricCards row: Net Liquidity, Day P&L, Signals Today, Trades Today
5. Status bar: API Status, Last Trade, Pending, Overrides, Risk Status
6. Two-column layout:
   - Left: Performance chart (AreaChart with time range tabs)
   - Right: Agent Fleet Status (dot grid) + Curator Intelligence
7. Live Data section (Tabs: System Activity | Positions | Allocation)
8. Bottom right: Watchlist

**Mock data to use (from PDF):**
- Net Liquidity: $994,272.52
- Day P&L: +$14,203.12 (+1.24%)
- Signals Today: 156 (+12%)
- Trades Today: 23

---

### 6.2 SystemPage
**Source:** `docs/design/references/components/pages/SystemPage.tsx`
**Target:** `frontend/src/pages/SystemPage.tsx`
**Target visual:** `docs/design/pdf/system.pdf`

**Layout:**
1. PageHeader: "SYSTEM OVERVIEW" + subtitle + Export + "All Systems Operational"
2. MetricCards row: System Uptime (99.97%), Connections, Trading Mode, Live Metrics
3. Two-column:
   - Left: Capital Allocation (2 DonutCharts: By Strategy, By Risk Tier)
   - Right: Current Assessment (MarketRegimePanel) + Curator Commentary
4. Two-column:
   - Left: Curator Decision Log (filterable feed)
   - Right: Strategy Performance table + Risk Limits progress bars
5. Scheduled Events list

---

### 6.3 PortfolioPage
**Source:** `docs/design/references/components/pages/PortfolioPage.tsx`
**Target:** `frontend/src/pages/PortfolioPage.tsx`
**Target visual:** `docs/design/pdf/portfolio.pdf`

**Layout:**
1. PageHeader: "PORTFOLIO ANALYSIS" + Rebalance + Export Report
2. MetricCards: Total Net Liquidity, Total Unrealized P&L, Active Positions, Cash Available
3. Two-column: Sector Allocation (DonutChart) + Asset Class Allocation (DonutChart)
4. Current Holdings (PositionsTable — full-width)
5. Performance Attribution (BenchmarkChart with time range tabs)

---

### 6.4 StrategiesPage (Agent Fleet)
**Source:** `docs/design/references/components/pages/StrategiesPage.tsx`
**Target:** `frontend/src/pages/StrategiesPage.tsx`
**Target visual:** `docs/design/pdf/agent page - renamed to strategies pages.pdf`

**Layout:**
1. PageHeader: "AGENT FLEET" + Export + Bulk Actions
2. Alert banner: "2 AGENTS REQUIRE ATTENTION" (expandable)
3. Stats bar: Total, Active, Paused, Training, Error, Combined P&L, Open Positions
4. StrategyGrid (full-width grid of StrategyCards)
5. Right sidebar: Top Performers + Needs Attention + Deploy New Agent

---

### 6.5 RiskPage
**Source:** `docs/design/references/components/pages/RiskPage.tsx`
**Target:** `frontend/src/pages/RiskPage.tsx`
**Target visual:** `docs/design/pdf/risk management.pdf`

**Layout:**
1. PageHeader: "RISK MANAGEMENT" + Export + Stress Test + Risk Level badge
2. MetricCards: Portfolio Beta, Sharpe Ratio, Sortino Ratio, Max Drawdown, VaR (95%)
3. Two-column:
   - Left: Portfolio Composition (DonutChart with Sector/Geography tabs)
   - Right: Concentration bars (holding weight vs limit)
4. Two-column:
   - Left: Correlation Matrix (custom grid)
   - Right: Active Alerts list

---

### 6.6 AlertsPage
**Source:** `docs/design/references/components/pages/AlertsPage.tsx`
**Target:** `frontend/src/pages/AlertsPage.tsx`
**Target visual:** `docs/design/pdf/alerts.pdf`

**Layout:**
1. PageHeader: "ALERTS CENTER" + Export + New Alert
2. MetricCards: Active Alerts (24), Triggered Today (8), Risk Warnings (5), Muted (3)
3. Tabs: Price Alerts | Risk Alerts | System | History
4. Alert cards grid (each with asset, price, condition, progress, status)
5. "Create Alert" empty card

---

### 6.7 TradeHistoryPage
**Source:** `docs/design/references/components/pages/TradeHistoryPage.tsx`
**Target:** `frontend/src/pages/TradeHistoryPage.tsx`
**Target visual:** `docs/design/pdf/trade history.pdf`

**Layout:**
1. PageHeader: "TRADE HISTORY" + Export
2. Summary MetricCards: Total Trades, Win Rate, Avg P&L, Total P&L
3. Full-width DataTable with trade entries

---

### 6.8 SettingsPage
**Source:** `docs/design/references/components/pages/SettingsPage.tsx`
**Target:** `frontend/src/pages/SettingsPage.tsx`
**Target visual:** `docs/design/pdf/system settings and menu to access and avatar.pdf`

**Layout:**
1. Left nav: Appearance, Notifications, Connections, Security, Access & Sharing, Help
2. Content area based on selected section
3. Appearance: Color Theme (Ocean/Sapphire/Emerald/Onyx cards), Display Mode (Light/Dark/System), Interface Density (Compact/Reduced Motion toggles)

---

### 6.9 RegimePage (Markets)
**Source:** `docs/design/references/components/pages/RegimePage.tsx`
**Target:** `frontend/src/pages/RegimePage.tsx`
**Target visual:** `docs/design/pdf/markets - renames to regime in the real build.pdf`

**Layout:**
1. MetricCards: S&P 500, NASDAQ, DOW JONES, RUSSELL 2000, VIX
2. Morning Briefing card (AI summary)
3. Two-column: Sector Performance + Market News
4. Market Movers table

---

## Page Validation Method

For EACH page:

1. Build with mock data
2. `npm run dev` and navigate to the page
3. Take screenshot in dark mode
4. Take screenshot in light mode
5. Open corresponding PDF side by side
6. Compare every element:
   - Layout/spacing correct?
   - Typography correct (Cinzel titles, mono numbers)?
   - Colors correct (glass panels, accents)?
   - Components rendering correctly?
7. Fix any visual discrepancies
8. Commit only when page matches PDF
9. Move to next page

---

## Validation Checklist (Phase 5+6)

### Dashboard Components
- [ ] MarketTicker scrolls with colored prices
- [ ] ActivityFeed shows categorized events
- [ ] Watchlist shows assets with prices
- [ ] PositionsTable shows sortable holdings
- [ ] StrategyCard shows P&L, win rate, status
- [ ] EmergencyPanel opens with kill switch
- [ ] NotificationsPanel opens from header bell

### Pages
- [ ] CockpitPage matches cockpit.pdf (dark mode)
- [ ] CockpitPage matches cockpit.pdf (light mode — themes.pdf page 7/16)
- [ ] SystemPage matches system.pdf
- [ ] PortfolioPage matches portfolio.pdf
- [ ] StrategiesPage matches agent page PDF
- [ ] RiskPage matches risk management.pdf
- [ ] AlertsPage matches alerts.pdf
- [ ] SettingsPage matches settings PDF (themes.pdf page 8/17)
- [ ] All pages have Cinzel small-caps titles
- [ ] All number values use JetBrains Mono
- [ ] All MetricCards have consistent styling
- [ ] Glass-panel cards have blur effect on all pages
