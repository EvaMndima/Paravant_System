# PHASE 7: INVESTOR COCKPIT DASHBOARD — IMPLEMENTATION GUIDE
## Master Reference for Frontend Development (111 hours, 32 tasks)

---

## 📋 QUICK NAVIGATION

### Implementation Prompts
- **[SESSION_7A_IMPLEMENTATION_PROMPT.md](./SESSION_7A_IMPLEMENTATION_PROMPT.md)** — Project Setup & Foundation (17h, 6 tasks)
- **[SESSION_7B_IMPLEMENTATION_PROMPT.md](./SESSION_7B_IMPLEMENTATION_PROMPT.md)** — Core Pages Development (38h, 10 tasks)
- **[SESSION_7C_IMPLEMENTATION_PROMPT.md](./SESSION_7C_IMPLEMENTATION_PROMPT.md)** — Operational Features & Deployment (42h, 16 tasks)

### Source Documentation
- **[07_PHASE_7_FRONTEND.md](./docs/07_PHASE_7_FRONTEND.md)** — Complete Phase 7 specification (111h breakdown)
- **[DESIGN_GUIDE.md](./docs/design/DESIGN_GUIDE.md)** — Visual design system authoritative spec
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — System architecture overview

### Design References (rename these files first)
- `docs/design/references/components/dashboard/AgentCard.tsx` → **StrategyCard.tsx**
- `docs/design/references/components/dashboard/AgentGrid.tsx` → **StrategyGrid.tsx**
- `docs/design/references/components/pages/AgentDetailPage.tsx` → **StrategyDetailPage.tsx**
- `docs/design/references/components/pages/AgentsPage.tsx` → **StrategiesPage.tsx**
- `docs/design/references/components/pages/MarketsPage.tsx` → **RegimePage.tsx**

---

## 🎯 CRITICAL INVARIANTS (DO NOT BREAK)

### 1. **Real-Time Data Architecture (SSE + Tiered Polling)**
   - **Tier 1 (SSE):** Kill switch, positions, alerts, risk status, regime → instant updates via Server-Sent Events
   - **Tier 2 (REST):** Dashboard summary (30s), equity (120s), strategies (60s), heatmap (300s) → visibility-aware polling (stops when tab hidden)
   - **Tier 3 (On-demand):** Strategy detail, account detail, backtest results → fetch once on page visit, no polling
   - **Why:** 94% reduction in backend requests (~91K → ~5K per tab per day)
   - **Enforcement:** If any Tier 1 data uses REST polling instead of SSE, architecture is broken

### 2. **Kill Switch is Untouchable Critical Control**
   - Always visible in sidebar (never hidden, never disabled)
   - Activation: one-click + mandatory reason + confirm
   - Deactivation: requires typing "DEACTIVATE" exactly (prevents accidental resume)
   - Visual state: RED + pulsing animation when active
   - Accessibility: `role="alert"` + `aria-live="assertive"` when active (screen readers announce immediately)
   - Updates instantly via SSE (no polling delay)
   - **Enforcement:** Kill switch button must exist in Sidebar component and be wired to real API

### 3. **Design System Consistency (DESIGN_GUIDE.md §2-4)**
   - All components use Tailwind colors from design system (not hardcoded colors)
   - All text uses correct font family: Cinzel (display), Inter (body), JetBrains Mono (data)
   - All spacing uses Tailwind scale (not arbitrary values)
   - Glass-morphism must use backdrop-blur-xl + specific opacity colors
   - Light/dark mode CSS variables must be applied via `prefers-color-scheme` or `data-theme` attribute
   - **Enforcement:** Running `npm run build` with dark mode OFF should use light colors, WITH dark mode ON should use dark colors

### 4. **TypeScript Strict Mode (100% Type Coverage)**
   - All components have `React.FC<PropsInterface>` or `function Component(props: Props)`
   - All function parameters have explicit types (no `any`)
   - All return types explicit (functions return `React.ReactNode`, API calls return `Promise<T>`)
   - API types match backend Pydantic models exactly
   - **Enforcement:** `tsc --strict` must pass with zero errors

### 5. **SSE Integration Pattern (from Phase 6)**
   - Backend: Task 6.2.8 — `/api/v1/events/stream?api_key={key}` endpoint
   - Frontend: `useEventStream(apiKey)` hook establishes single persistent connection
   - Event routing: SSE events → react-query cache via `setQueryData()` or `invalidateQueries()`
   - Reconnection: exponential backoff 1s → 2s → 4s → 8s → max 30s
   - **Enforcement:** Every SSE event type in backend must have matching listener in `useEventStream`

### 6. **Responsive Design Breakpoints (Mobile-First)**
   - Mobile: <768px (single column, hidden sidebar, hamburger menu)
   - Tablet: 768-1023px (sidebar icons only, 2-column grid)
   - Laptop: 1024-1439px (full sidebar, 2-3 column grid)
   - Desktop: ≥1440px (full sidebar, 3-4 column grid)
   - **No horizontal scroll at any breakpoint**
   - **Enforcement:** `npm run build` then test at 375px, 768px, 1366px, 1920px

---

## 🏗️ ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│ VITE DEV SERVER (port 3000)                                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ React App (src/App.tsx)                              │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ ThemeContext (light/dark/5 accents)                  │  │
│  │ QueryClientProvider (react-query + SSE integration)  │  │
│  │ ErrorBoundary (catch React errors)                   │  │
│  └──────────────────────────────────────────────────────┘  │
│            ↓                    ↓                             │
│  ┌─────────────────┐   ┌──────────────────────────────┐    │
│  │ useEventStream  │   │ Router (10 pages)            │    │
│  │ (SSE connection)│   │ - Cockpit (/)                │    │
│  │ - kill_switch   │   │ - Portfolio (/portfolio)      │    │
│  │ - positions     │   │ - Strategies (/strategies)    │    │
│  │ - alerts        │   │ - Risk (/risk)               │    │
│  │ - risk_status   │   │ - Orders (/orders)           │    │
│  │ - regime        │   │ - Alerts (/alerts)           │    │
│  └─────────────────┘   │ - Accounts (/accounts)       │    │
│         ↓              │ - Settings (/settings)       │    │
│  Data Hooks            │ - Backtest (/backtest)       │    │
│  (useQuery + SSE)      └──────────────────────────────┘    │
│  - Tier 1: SSE-driven                                       │
│  - Tier 2: visibility-aware polling                         │
│  - Tier 3: on-demand                                        │
│         ↓                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ UI Components (GlassCard, Button, Badge, MetricCard) │  │
│  │ Charts (EquityCurve, Heatmap, Sparkline, Gauge)      │  │
│  │ Layout (Sidebar, Header, MainLayout)                 │  │
│  └──────────────────────────────────────────────────────┘  │
│         ↓                                                    │
│  ┌─────────────────────────────────┐                        │
│  │ Vite Proxy (/api)              │                        │
│  │ Forwards to http://localhost:8000
│  └─────────────────────────────────┘                        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         ↓                                    ↓
┌─────────────────────────────────────────────────────────────┐
│ FASTAPI BACKEND (port 8000)                                 │
├─────────────────────────────────────────────────────────────┤
│ Phase 6: Orchestrator, API Layer, Alerting, SSE Stream      │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow: SSE vs REST Polling

```
TIER 1: SSE (Real-Time, One-Way Server → Client)
┌─────────────────────────────────────────┐
│ Browser tab 1                           │
│ EventSource → GET /api/v1/events/stream │
│ (persistent HTTP connection)            │
└────────────────────┬────────────────────┘
                     ↑
         ┌──────────────────────┐
         │ Backend SSE Endpoint │
         │ - kill_switch events │
         │ - position_updated   │
         │ - alert_created      │
         │ - risk_status_changed│
         │ - regime_changed     │
         └──────────────────────┘
                     ↑
         ┌──────────────────────┐
         │ React Query Cache    │
         │ (setQueryData)       │
         └──────────────────────┘

TIER 2: REST Polling (Slow-Changing Data, Visibility-Aware)
┌─────────────────────────────────────────┐
│ Browser tab 1 (VISIBLE)                 │
│ useQuery → GET /api/v1/dashboard/summary│
│ refetchInterval: 30s                    │
└────────────────────┬────────────────────┘
                     ↓
         ┌──────────────────────┐
         │ Tier 2 REST Polling  │
         │ - /dashboard/summary │
         │ - /dashboard/equity  │
         │ - /strategies        │
         │ - /pnl/heatmap       │
         └──────────────────────┘

         SAME QUERY, TAB HIDDEN
┌─────────────────────────────────────────┐
│ Browser tab 1 (HIDDEN)                  │
│ useQuery → refetchInterval: FALSE       │
│ (polling stops automatically)           │
└────────────────────┬────────────────────┘
```

---

## 🔄 KEY DATA FLOWS

### Kill Switch State Update

```
User clicks "ACTIVATE KILL SWITCH" in sidebar
    ↓
Confirmation modal shows reason field
    ↓
User enters reason + clicks confirm
    ↓
API call: POST /api/v1/risk/kill-switch/activate { reason: "..." }
    ↓
Backend: Store activation, emit SSE event
    ↓
Frontend: SSE listener receives kill_switch_changed event
    ↓
React Query: setQueryData(['risk', 'kill-switch'], newState)
    ↓
useKillSwitch() hook updates → Sidebar button turns red + pulsing
    ↓
Header shows kill switch badge
    ↓
Risk page shows "ACTIVE" badge
    ↓
All connected clients (other tabs) see update instantly
```

### Position Close Flow

```
User clicks [Close] on position row in Cockpit
    ↓
Position detail modal shows entry, current, P&L
    ↓
User confirms close type (market or limit)
    ↓
API call: POST /api/v1/positions/{id}/close { close_type: "market" }
    ↓
Backend: Create market order, update position to CLOSED, emit SSE event
    ↓
Frontend: SSE listener receives position_updated event
    ↓
React Query: invalidateQueries(['dashboard', 'positions'])
    ↓
usePositions() hook re-fetches fresh position list
    ↓
Cockpit page refreshes positions table (removed closed position)
    ↓
Success toast: "Position closed at market price"
```

### Dashboard Regime Change

```
User clicks regime dropdown in header
    ↓
Confirmation modal shows available regimes
    ↓
User selects new regime
    ↓
API call: PUT /api/v1/system/regime { regime: "trending_up", note: "..." }
    ↓
Backend: Update regime, emit SSE event, adjust strategy sizes
    ↓
Frontend: SSE listener receives regime_changed event
    ↓
React Query:
  - setQueryData(['system', 'regime'], newRegime)
  - invalidateQueries(['dashboard', 'summary'])
    ↓
Cockpit page:
  - Regime widget updates immediately (SSE)
  - All strategy sizes recalculate (dashboard re-fetches)
    ↓
Success toast: "Regime changed to trending_up"
```

---

## 📐 KEY FORMULAS & CALCULATIONS

### SSE Cost Reduction

```
BEFORE (pure REST polling):
  Kill switch:     every 3s   = 20  req/min
  System status:   every 5s   = 12  req/min
  Risk status:     every 5s   = 12  req/min
  Dashboard:       every 10s  = 6   req/min
  Positions:       every 10s  = 6   req/min
  Alerts:          every 15s  = 4   req/min
  Strategies:      every 30s  = 2   req/min
  Equity curve:    every 60s  = 1   req/min
  ─────────────────────────────────────
  TOTAL:                      = 63  req/min = ~91K req/day per tab

AFTER (SSE + Tier 2 polling):
  SSE:             1 persistent connection  = 1  connection
  Dashboard:       every 30s  = 2  req/min
  Equity curve:    every 120s = 0.5 req/min
  Strategies:      every 60s  = 1  req/min
  Heatmap:         every 300s = 0.2 req/min
  ─────────────────────────────────────
  TOTAL:                      = 3.7 req/min = ~5.3K req/day per tab

SAVINGS: 91K → 5.3K = 94.2% reduction
```

### Data Freshness Targets

```
Tier 1 (SSE-driven, must be instant):
- Kill switch:    < 100ms (life-critical)
- Positions:      < 1s    (trade-critical)
- Risk status:    < 1s    (risk-critical)
- Alerts:         < 5s    (notification)
- Regime:         < 5s    (affects strategies)

Tier 2 (REST polling, acceptable delay):
- Dashboard:      30s (expensive aggregation)
- Equity:         120s (historical, slow-changing)
- Strategies:     60s (rarely changes)
- Heatmap:        300s (daily granularity)

Tier 3 (On-demand, one-time fetch):
- Strategy detail: fetch on page visit, cache until navigation
- Account detail:  fetch on page visit, cache until navigation
- Backtest result: fetch once, `staleTime: Infinity` (immutable)
```

### Loading State Progression

```
Initial page load timeline:
  t=0ms:   Skeleton layout shows
  t=50ms:  Hero metrics load (fastest)
  t=150ms: Risk gauges load
  t=300ms: Strategies widget loads
  t=500ms: Positions table loads
  t=800ms: Charts load (slowest)

  → No single component blocks others

Polling refresh timeline:
  t=0ms:   New data available from server
  t=50ms:  React query updates cache
  t=100ms: Component re-renders (data updates in-place)

  → NO skeleton flash on polling refresh
```

---

## 📊 FILE STRUCTURE

```
frontend/
├── src/
│   ├── App.tsx                          # Main app, Router setup
│   ├── components/
│   │   ├── ui/                          # Reusable components
│   │   │   ├── GlassCard.tsx
│   │   │   ├── Button.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── MetricCard.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Toggle.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   └── DataTable.tsx
│   │   ├── layout/                      # Page layout
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── MainLayout.tsx
│   │   ├── modals/                      # Modal components
│   │   │   ├── KillSwitchModal.tsx
│   │   │   ├── RegimeChangeModal.tsx
│   │   │   ├── PositionCloseModal.tsx
│   │   │   └── ...
│   │   ├── charts/                      # Chart components
│   │   │   ├── EquityCurveChart.tsx
│   │   │   ├── MonthlyHeatmap.tsx
│   │   │   ├── SparklineChart.tsx
│   │   │   └── GaugeChart.tsx
│   │   └── pages/                       # Page components
│   │       ├── CockpitPage.tsx
│   │       ├── PortfolioPage.tsx
│   │       ├── StrategiesListPage.tsx
│   │       ├── StrategyDetailPage.tsx
│   │       ├── RiskPage.tsx
│   │       ├── OrdersPage.tsx
│   │       ├── AlertsPage.tsx
│   │       ├── AccountsPage.tsx
│   │       ├── SettingsPage.tsx
│   │       └── BacktestPage.tsx
│   ├── hooks/                           # Custom React hooks
│   │   ├── useEventStream.ts            # SSE connection
│   │   ├── useDashboardSummary.ts       # Tier 2 polling
│   │   ├── useEquityCurve.ts
│   │   ├── useStrategies.ts
│   │   ├── useKillSwitch.ts             # Tier 1, SSE-driven
│   │   ├── usePositions.ts
│   │   ├── useAlerts.ts
│   │   ├── useRegime.ts
│   │   ├── useGlobalShortcuts.ts
│   │   └── useToast.ts
│   ├── contexts/                        # Context providers
│   │   ├── ThemeContext.tsx
│   │   └── ToastContext.tsx
│   ├── lib/
│   │   ├── api.ts                       # Typed API client
│   │   ├── utils.ts                     # Format functions
│   │   └── animations.ts                # Framer-motion configs
│   ├── types/
│   │   ├── api.ts                       # TypeScript types (match Pydantic models)
│   │   └── index.ts
│   └── index.css                        # Global styles + CSS variables
│
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── package.json
└── package-lock.json
```

---

## 🎨 DESIGN SYSTEM REFERENCE

### Color Palette (CSS Variables)

```css
/* Light Mode */
--color-background: #fdfbf8      /* paper-100 */
--color-surface: #f5ebe2         /* paper-200 */
--color-text-primary: #1e404a    /* deep-teal-900 */
--color-text-secondary: #707070   /* obsidian-500 */
--color-accent: #45a3ba          /* deep-teal-500 */
--color-gain: #10b981            /* Green */
--color-loss: #ef4444            /* Red */
--color-neutral: #f59e0b         /* Amber */

/* Dark Mode */
@media (prefers-color-scheme: dark) {
  --color-background: #0a0a0a
  --color-surface: #1e404a
  --color-text-primary: #fdfbf8
  --color-accent: #6dd5ca
  --color-gain: #10b981   /* Same */
  --color-loss: #ef4444   /* Same */
  --color-neutral: #f59e0b /* Same */
}

/* 5 Accent Themes */
[data-theme="ocean"] --accent-primary: #45a3ba
[data-theme="sapphire"] --accent-primary: #0ea5e9
[data-theme="emerald"] --accent-primary: #059669
[data-theme="amber"] --accent-primary: #d97706
[data-theme="slate"] --accent-primary: #64748b
```

### Typography

```
Cinzel (serif):        Display headings (h1, h2, page titles)
Inter (sans):          Body text, descriptions, labels
JetBrains Mono (mono): Numbers, financial data, code
```

### Spacing Scale (Tailwind)

```
p-1  = 0.25rem (4px)    - tiny padding
p-2  = 0.5rem  (8px)    - small padding
p-3  = 0.75rem (12px)
p-4  = 1rem    (16px)   - default padding
p-6  = 1.5rem  (24px)   - large padding
p-8  = 2rem    (32px)   - extra large padding

gap-2 = 0.5rem (8px)    - small gap
gap-4 = 1rem   (16px)   - default gap
gap-6 = 1.5rem (24px)   - large gap
```

---

## 🚀 DEVELOPMENT WORKFLOW

### Phase 7A (Foundation) — 17 hours

```bash
1. npm create vite@latest frontend -- --template react-ts
2. Install dependencies (exact versions from SESSION_7A)
3. Configure Tailwind + CSS variables
4. Build 10 UI components
5. Create layout shell (Sidebar, Header, MainLayout)
6. Implement ThemeContext
7. Build API client (all Phase 6 endpoints typed)
8. Build data hooks (useEventStream + polling hooks)
9. Test: npm run dev → verify Tailwind, fonts, API proxy works
```

### Phase 7B (Core Pages) — 38 hours

```bash
1. Build Cockpit page (6 PRD widgets)
2. Build Portfolio page (3 charts)
3. Build Strategies list (grid/table with filters)
4. Build Strategy detail (7 PRD sections)
5. Build Risk page (gauges, circuit breakers, kill switch)
6. Build remaining pages (Orders, Alerts, Accounts, Settings, Backtest)
7. Add loading skeletons for all pages
8. Test: npm run dev → verify all pages render with real data
```

### Phase 7C (Features & Deployment) — 42 hours

```bash
1. Build kill switch modal (activation + deactivation)
2. Build regime selector
3. Build operational modals (position close, etc.)
4. Build toast notification system
5. Build keyboard shortcuts
6. Build chart components (equity curve, heatmap, sparkline, gauge)
7. Implement error handling + offline detection
8. Implement responsive design (test 375px, 768px, 1366px, 1920px)
9. Configure build + Docker
10. Test: npm run build → verify bundle < 300KB initial, < 500KB total
```

---

## ✅ QUALITY GATES (Before Handoff)

### Code Quality
- [ ] `npm run build` succeeds with zero errors
- [ ] `tsc --strict` passes (zero TypeScript errors)
- [ ] `npx eslint src` passes (if configured)
- [ ] No `console.error` or `console.warn` in normal operation
- [ ] All components accept `className` prop for composition

### Functionality
- [ ] All 10 pages render without errors
- [ ] All 6 Cockpit widgets show real data
- [ ] Kill switch works (activate + deactivate)
- [ ] Regime selector works
- [ ] All API calls succeed
- [ ] SSE connection established and receiving events
- [ ] Keyboard shortcuts work

### Performance
- [ ] Initial page load < 3s (on 4G)
- [ ] Bundle size: initial < 300KB, total < 500KB (gzipped)
- [ ] Lighthouse score > 80 (performance)
- [ ] SSE connection stable (< 5s reconnect time)

### Responsive Design
- [ ] Desktop (1920px): full layout
- [ ] Laptop (1366px): full layout
- [ ] Tablet (768px): sidebar collapsed to icons
- [ ] Mobile (375px): single column, hamburger menu
- [ ] No horizontal scroll at any breakpoint

### Accessibility
- [ ] Kill switch uses `role="alert"` + `aria-live="assertive"`
- [ ] Modal focus trapped (Tab cycles within modal only)
- [ ] All buttons keyboard accessible
- [ ] No information conveyed by color alone
- [ ] Touch targets min 44px (mobile)

---

## 🎓 RECOMMENDED READING ORDER

1. **Start here:** [SESSION_7A_IMPLEMENTATION_PROMPT.md](./SESSION_7A_IMPLEMENTATION_PROMPT.md) — Foundation setup
2. **Then:** [SESSION_7B_IMPLEMENTATION_PROMPT.md](./SESSION_7B_IMPLEMENTATION_PROMPT.md) — Build pages
3. **Then:** [SESSION_7C_IMPLEMENTATION_PROMPT.md](./SESSION_7C_IMPLEMENTATION_PROMPT.md) — Features & polish
4. **Reference:** [DESIGN_GUIDE.md](./docs/design/DESIGN_GUIDE.md) — Visual design specs
5. **Context:** [07_PHASE_7_FRONTEND.md](./docs/07_PHASE_7_FRONTEND.md) — Original Phase 7 spec

---

## 🏁 SUCCESS CRITERIA (MVP COMPLETE)

Phase 7 is complete and production-ready when:

✅ All 32 tasks finished across 3 sessions
✅ All 10 pages render with real backend data
✅ All user interactions work (kill switch, regime selector, close positions, etc.)
✅ SSE streaming provides real-time updates (< 100ms latency)
✅ Bundle optimized (< 500KB gzipped total)
✅ Responsive at 375px, 768px, 1366px, 1920px
✅ No console errors in normal operation
✅ All acceptance criteria from 32 tasks met
✅ Production build passes all quality gates

---

## 📞 KEY CONTACTS & DOCUMENTATION

- **Design Reference:** [docs/design/DESIGN_GUIDE.md](./docs/design/DESIGN_GUIDE.md)
- **Phase 6 API:** [docs/06_PHASE_6_BACKEND_INTEGRATION.md](./docs/06_PHASE_6_BACKEND_INTEGRATION.md)
- **Architecture:** [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Decision Log:** [.claude/DECISIONS.md](./.claude/DECISIONS.md)

---

## 📈 TIMELINE

- **Week 13-14:** SESSION 7A (Foundation) — 17h
- **Week 14-15:** SESSION 7B (Core Pages) — 38h
- **Week 15-16:** SESSION 7C (Features & Deployment) — 42h
- **Total:** 111 hours, 32 tasks

**Expected Completion:** End of Week 16 (MVP-ready Investor Cockpit)

---

**Last Updated:** 2026-02-15
**Status:** Ready for implementation
**Next Phase:** Production deployment & MVP launch
