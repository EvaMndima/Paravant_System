# Phase 3: Chart Components + Phase 4: Layout Shell

## Phase 3: Charts (2-3 hours)

### Goal
Port the 4 chart components from the prototype. These are used in MetricCard sparklines, the Cockpit performance widget, Portfolio equity curve, and Risk/System donut charts.

### Pre-requisite
Phase 2 complete (all UI primitives working)

---

### 3.1 SparklineChart (SVG-based)
**Source:** `docs/design/references/components/dashboard/charts/SVGAreaChart.tsx` or `SparklineChart.tsx`
**Target:** `frontend/src/components/charts/SparklineChart.tsx`

**Key specs:**
- Lightweight SVG (NOT Recharts — too heavy for inline use)
- Props: `data: number[]`, `color`, `width`, `height`, `showArea`
- Auto-scales to data range
- Color based on trend (green if up, red if down)
- Gradient fill with fade
- Used inside MetricCard sparkline zone

**Validation:** Place inside a MetricCard — should show a subtle mini chart at the bottom like in cockpit.pdf.

---

### 3.2 AreaChart (Recharts-based)
**Source:** `docs/design/references/components/dashboard/charts/AreaChart.tsx`
**Target:** `frontend/src/components/charts/AreaChart.tsx`

**Key specs:**
- Recharts ResponsiveContainer + AreaChart
- Gradient fill from accent color
- Custom tooltip styled with GlassCard
- Time range selector (1D, 1W, 1M, 3M, YTD)
- Used in Cockpit "Performance" widget and Portfolio page

**Validation:** Match the cockpit.pdf "PERFORMANCE / NAV - 30 Days" chart with dark gradient fill.

---

### 3.3 DonutChart
**Source:** `docs/design/references/components/dashboard/charts/DonutChart.tsx`
**Target:** `frontend/src/components/charts/DonutChart.tsx`

**Key specs:**
- Recharts PieChart with inner radius (donut shape)
- Center text label (e.g., "DEPLOYED 85%", "TOTAL ASSETS $2.88M")
- Legend below
- Used in System page (Capital Allocation) and Portfolio page (Sector/Asset allocation)

**Validation:** Match system.pdf "BY STRATEGY" and "BY RISK TIER" donut charts.

---

### 3.4 BenchmarkChart
**Source:** `docs/design/references/components/dashboard/charts/BenchmarkChart.tsx`
**Target:** `frontend/src/components/charts/BenchmarkChart.tsx`

**Key specs:**
- Two-line chart: Portfolio vs Benchmark
- Area fill for portfolio line
- Dashed line for benchmark
- Used in Portfolio page "Performance Attribution"

---

### Charts Barrel Export
**File:** `frontend/src/components/charts/index.ts`

```typescript
export { SparklineChart } from './SparklineChart';
export { AreaChart } from './AreaChart';
export { DonutChart } from './DonutChart';
export { BenchmarkChart } from './BenchmarkChart';
```

---

## Phase 4: Layout Shell (2-3 hours)

### Goal
Build the application shell — Sidebar, Header, and MainLayout. This is where the app starts looking like the target design.

### Pre-requisite
Phase 3 complete (chart components working)

---

### 4.1 Sidebar
**Source:** `docs/design/references/components/layout/Sidebar.tsx`
**Target:** `frontend/src/components/layout/Sidebar.tsx`

**This is a direct port.** The prototype sidebar code is production-ready.

**Key specs (from prototype code + screenshots):**
- Expanded width: 280px, collapsed: 80px
- Framer Motion spring animation for collapse
- Dark bg: `bg-paper-100/80 dark:bg-obsidian-400/80 backdrop-blur-xl`
- Border right: `border-deep-teal-800/5 dark:border-white/5`
- Nav items: Cockpit, System, Agents, Portfolio, Markets, Risk, Alerts, Trade History
- Active item: animated background pill (framer-motion layoutId)
- Active icon/text: `text-deep-teal-800 dark:text-turquoise-mist`
- Inactive: `text-obsidian-400/60 dark:text-paper-100/60`
- Footer: theme toggle, collapse button, avatar with status
- Mobile: slide-in drawer with backdrop blur
- SidebarProvider context for collapse state

**Target screenshots to match:**
- `screenshots/target/sidebar/expanded-sidebar.png` — expanded with all items
- `screenshots/target/sidebar/collaped-full-sidebar.png` — collapsed icons only
- `screenshots/target/sidebar/sidebar-avatar-expanded-view.png` — avatar section
- `screenshots/target/sidebar/theme-quick-setting-dark.png` — dark mode toggle

**Adaptation for PARAVANT system:**
- Keep all nav items but rename "Agents" to "Strategies" (or keep both based on Phase 7 spec)
- "Markets" maps to "Regime" page in the real build
- Add route mapping in MainLayout

---

### 4.2 Header
**Source:** `docs/design/references/components/layout/Header.tsx`
**Target:** `frontend/src/components/layout/Header.tsx`

**Direct port.** Key specs:

- Height: 64px (h-16), sticky top-0
- Transparent by default, glass-blur on scroll
- Left: SidebarTrigger (mobile) + Breadcrumb "Platform / {page}"
- Right: SearchInput (hidden on mobile) + "New Alert" button + Emergency control button + Notifications bell + User avatar dropdown
- Emergency button: orange/red with badge count
- Notifications: bell with unread dot, opens NotificationsPanel

**Target screenshots:**
- `screenshots/target/header/header-cockpit.png`
- `screenshots/target/header/full-page-with-header-view-dark-mode.png`
- `screenshots/target/header/full-page-with-header-view-light.png`

**Adaptation:**
- Connect `onNavigate` to React Router instead of local state
- Remove mock notification data (will be replaced by API in Phase 8)
- Keep emergency button pointing to EmergencyPanel modal

---

### 4.3 Breadcrumbs
**Source:** `docs/design/references/components/layout/Breadcrumbs.tsx`
**Target:** `frontend/src/components/layout/Breadcrumbs.tsx`

Simple "Platform / PageName" breadcrumb.

---

### 4.4 PageHeader
**Source:** `docs/design/references/components/layout/PageHeader.tsx`
**Target:** `frontend/src/components/layout/PageHeader.tsx`

**Key specs:**
- Title: Cinzel font, small-caps, large
- Subtitle: Inter, muted color
- Right side: action buttons (Export, Rebalance, etc.)
- Used on every page

**Example from PDF:**
```
SYSTEM OVERVIEW
AI Curator decisions, capital allocation, and market regime analysis.     [Export] [All Systems Operational]
```

---

### 4.5 Section
**Source:** `docs/design/references/components/layout/Section.tsx`
**Target:** `frontend/src/components/layout/Section.tsx`

Content section wrapper with optional title header.

---

### 4.6 MainLayout
**Target:** `frontend/src/components/layout/MainLayout.tsx`

Composes Sidebar + Header + content area:

```
+--sidebar--+--header---------------------------------+
|            |  Platform / Cockpit    [Search] [Alert] |
|  Cockpit   +--content-------------------------------+
|  System    |                                         |
|  Agents    |   page content (scrollable)             |
|  Portfolio |   max-w-[1440px] mx-auto px-6           |
|  ...       |                                         |
|            |                                         |
|  [theme]   |                                         |
|  [avatar]  |                                         |
+------------+-----------------------------------------+
```

**Key specs:**
- Sidebar sticky, full height
- Content area scrollable
- Responsive: sidebar collapses on tablet, hidden on mobile
- Content padding: `p-4 md:p-6 lg:p-8`

---

### 4.7 React Router Setup

**File:** `frontend/src/App.tsx`

```typescript
const routes = [
  { path: '/', label: 'Cockpit', element: <CockpitPage /> },
  { path: '/system', label: 'System', element: <SystemPage /> },
  { path: '/strategies', label: 'Agents', element: <StrategiesPage /> },
  { path: '/portfolio', label: 'Portfolio', element: <PortfolioPage /> },
  { path: '/regime', label: 'Markets', element: <RegimePage /> },
  { path: '/risk', label: 'Risk', element: <RiskPage /> },
  { path: '/alerts', label: 'Alerts', element: <AlertsPage /> },
  { path: '/trade-history', label: 'Trade History', element: <TradeHistoryPage /> },
  { path: '/settings', label: 'Settings', element: <SettingsPage /> },
  { path: '/dev', label: 'Dev', element: <DevPage /> },
];
```

---

## Validation Checklist (Phase 3+4)

### Charts
- [ ] SparklineChart renders inside MetricCard
- [ ] AreaChart shows gradient fill and tooltip
- [ ] DonutChart shows center text and legend
- [ ] BenchmarkChart shows dual lines

### Layout
- [ ] Sidebar expanded matches `expanded-sidebar.png`
- [ ] Sidebar collapsed matches `collaped-full-sidebar.png`
- [ ] Sidebar collapse animation is smooth spring
- [ ] Active nav item has animated background pill
- [ ] Theme toggle in sidebar works
- [ ] Avatar with status dot visible in sidebar footer
- [ ] Header shows breadcrumb "Platform / Cockpit"
- [ ] Header shows SearchInput with Cmd+K hint
- [ ] Header has Emergency and Notifications buttons
- [ ] Header becomes glass-blur on scroll
- [ ] Mobile: sidebar opens as drawer with backdrop
- [ ] Mobile: hamburger menu in header
- [ ] Navigate between empty pages — shell stays intact
- [ ] Dark mode: near-black sidebar/header
- [ ] Light mode: cream/paper sidebar/header
