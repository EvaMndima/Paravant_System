# PHASE 7: FRONTEND — INVESTOR COCKPIT DASHBOARD
## Weeks 13-16 | 32 Tasks | ~111 Hours

**Goal:** Build a production-grade investor cockpit dashboard that connects to all Phase 6 API endpoints. The dashboard provides full operational visibility — portfolio metrics, strategy management, risk monitoring, and emergency controls — with the "quiet luxury" aesthetic established in DESIGN_GUIDE.md.

**Start Conditions:** Phase 6 complete (all API endpoints functional, alerting working)  
**Exit Conditions:** All dashboard pages render with real data, all user interactions work (kill switch, regime change, strategy management), responsive on desktop/tablet, all acceptance criteria pass

**Architecture:** React 18 + TypeScript + Vite + Tailwind CSS + Recharts + SSE (Server-Sent Events)  
**Design Reference:** `docs/design/DESIGN_GUIDE.md` (authoritative visual spec)  
**Prototype Reference:** `docs/design/reference/` (AI Studio prototype files for visual direction)

---

## 📊 PHASE 7 PROGRESS

```
Section 7.1 Project Setup & Foundation  [░░░░░░░░░░] 0/6 tasks   (~17 hours)
Section 7.2 Core Pages                  [░░░░░░░░░░] 0/10 tasks  (~38 hours)
Section 7.3 Operational Features        [░░░░░░░░░░] 0/8 tasks   (~28 hours)
Section 7.4 Charts & Visualization      [░░░░░░░░░░] 0/4 tasks   (~14 hours)
Section 7.5 Polish & Deployment         [░░░░░░░░░░] 0/4 tasks   (~14 hours)
──────────────────────────────────────────────────────────────────────────────
PHASE 7 TOTAL                           [░░░░░░░░░░] 0/32 tasks  (~111 hours)
```

---

## 🛠 TOOL STRATEGY

Each task specifies which tool to use. The general pattern:

| Task Type | Tool | Why |
|-----------|------|-----|
| Project init, config, tooling | **Claude Code** | Infrastructure, no visual |
| UI component library | **Antigravity** | Fast visual scaffolding from design reference |
| Layout shell, navigation | **Antigravity** | Visual + interaction patterns |
| Theme system, contexts | **Claude Code** | React logic, state management |
| API client, data hooks | **Claude Code** | TypeScript, async logic |
| Page layouts with placeholder data | **Antigravity** | Visual composition |
| API integration (replacing placeholders) | **Claude Code** | Async data, error handling |
| Charts and data visualization | **Antigravity** → **Claude Code** | Scaffold visual → wire data |
| Emergency/safety features | **Claude Code** | Critical logic, confirmation flows |
| Build, deployment, optimization | **Claude Code** | Tooling, config |

**The Pattern for Most Pages:**
1. **Antigravity:** "Build the [Page] layout using glass-panel cards, Cinzel headings, JetBrains Mono for numbers. Reference `docs/design/reference/components/pages/[Page].tsx`. Use placeholder data."
2. **Claude Code:** "Wire up the [Page] to the FastAPI backend. Replace placeholder data with `use[Hook]()` calls to `/api/v1/[endpoint]`. Add loading skeletons, error states, and auto-refresh."

---

## SECTION 7.1: PROJECT SETUP & FOUNDATION
*Estimated: 17 hours*

Foundation work that everything else depends on. No visual output yet — pure infrastructure, design system configuration, and API connectivity.

### Task 7.1.1: Initialize Frontend Project
- [ ] **Status:** Not Started
- **Description:** Set up React + Vite + TypeScript + Tailwind project with complete design system
- **Dependencies:** [None — can start parallel with Phase 6]
- **Effort:** 2 hours
- **Tool:** Claude Code

**File:** `frontend/` directory at project root

**Setup checklist (order matters):**
```bash
# 1. Create project
npm create vite@latest frontend -- --template react-ts

# 2. Install dependencies (exact versions from DESIGN_GUIDE §11)
cd frontend
npm install react-router-dom@6 lucide-react@0.263.1 clsx tailwind-merge \
  framer-motion recharts @tanstack/react-query

# 3. Install dev dependencies
npm install -D tailwindcss postcss autoprefixer @types/react @types/react-dom
npx tailwindcss init -p
```

**Configuration files to create:**

1. **`tailwind.config.js`** — Full color system from DESIGN_GUIDE §2.4
   - All custom colors: deep-teal, obsidian, paper, turquoise-mist, etc.
   - Font families: Cinzel (display), Inter (body), JetBrains Mono (data)
   - Custom utilities: glass-panel variants

2. **`src/index.css`** — CSS variables from DESIGN_GUIDE §2.1
   - Light mode variables (default)
   - Dark mode variables
   - All 5 theme variant CSS blocks (Ocean, Sapphire, Emerald, Amber, Slate)
   - Glass-panel utility classes per DESIGN_GUIDE §4.1
   - Custom scrollbar styles per DESIGN_GUIDE §6
   - Google Fonts import (Cinzel, Inter, JetBrains Mono)

3. **`vite.config.ts`** — Proxy configuration
   ```typescript
   export default defineConfig({
     plugins: [react()],
     server: {
       port: 3000,
       proxy: {
         '/api': {
           target: 'http://localhost:8000',
           changeOrigin: true,
         },
       },
     },
   });
   ```

4. **`src/lib/utils.ts`** — Utility functions from DESIGN_GUIDE
   ```typescript
   import { type ClassValue, clsx } from 'clsx';
   import { twMerge } from 'tailwind-merge';
   
   export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
   export function formatCurrency(value: number): string { /* Intl.NumberFormat USD */ }
   export function formatNumber(value: number): string { /* with commas, max 2 decimals */ }
   export function formatPercent(value: number): string { /* Intl.NumberFormat percent */ }
   export function formatDuration(hours: number): string { /* "2h 30m" format */ }
   ```

5. **`src/lib/animations.ts`** — Shared animation configs
   ```typescript
   export const smoothSpring = { type: "spring", stiffness: 300, damping: 30 };
   export const gentleFade = { initial: { opacity: 0 }, animate: { opacity: 1 }, transition: { duration: 0.3 } };
   ```

**Acceptance Criteria:**
- [ ] `npm run dev` starts on port 3000
- [ ] Tailwind classes render correctly (test with a glass-panel div)
- [ ] CSS variables resolve in both light and dark mode
- [ ] All 3 fonts load (Cinzel, Inter, JetBrains Mono)
- [ ] Glass-panel utility classes work (4 variants: default/elevated/subtle/dark)
- [ ] API proxy works (`/api/v1/health` forwards to backend)
- [ ] `cn()` helper merges classes correctly
- [ ] Format functions produce correct output

---

### Task 7.1.2: Create UI Component Library — Foundation
- [ ] **Status:** Not Started
- **Description:** Build core UI primitives that match DESIGN_GUIDE exactly
- **Dependencies:** [7.1.1]
- **Effort:** 3.5 hours
- **Tool:** Antigravity (visual generation from design reference)

**Components to build (each in `src/components/ui/`):**

1. **GlassCard** — Glass-morphism surface container
   - 4 variants: default, elevated, subtle, dark (DESIGN_GUIDE §4.1)
   - Props: `variant`, `className`, `children`, `padding` (sm/md/lg)
   - Light: `bg-paper-100/80 backdrop-blur-xl border border-deep-teal-800/10`
   - Dark: `dark:bg-deep-teal-900/60 dark:border-turquoise-mist/10`
   - Elevated: adds `shadow-lg shadow-deep-teal-800/5`
   - Subtle: `bg-paper-100/40 border-transparent`
   - Reference: `docs/design/reference/components/ui/GlassCard.tsx`

2. **Button** — All interaction variants
   - Variants: primary, secondary, danger, ghost, emergency (DESIGN_GUIDE §4.4)
   - Sizes: sm, md, lg
   - States: default, hover (scale 1.02, y: -1 via framer-motion), disabled, loading
   - Emergency: `bg-loss text-white animate-pulse` for kill switch
   - Corner radius: `rounded-xl` (confirmed from reference)
   - Reference: `docs/design/reference/components/ui/Button.tsx`

3. **Badge** — Status indicators
   - Soft translucent backgrounds (not solid) for premium feel
   - Variants: success (`bg-gain/10 text-gain`), danger, warning, info, neutral
   - Dot indicator option (small colored circle before text)
   - Reference: `docs/design/reference/components/ui/Badge.tsx`

4. **MetricCard** — Financial data display (the signature component)
   - Layout: label (top) + value (large) + change indicator (right) + sparkline (bottom)
   - Label: `text-xs font-mono font-bold uppercase tracking-widest`
   - Value: `font-mono font-medium tracking-tighter tabular-nums text-3xl`
   - Sparkline zone: absolute bottom, h-20, opacity 30-40% with gradient mask
   - Icon container option: `p-1.5 rounded-lg backdrop-blur-sm`
   - Min height: 140px
   - Reference: `docs/design/reference/components/ui/MetricCard.tsx`

5. **Input** — Text input with glass styling
   - Glass background matching card style
   - Focus ring: `ring-2 ring-turquoise-mist/30`
   - Error state: `ring-loss/50`
   - Monospace option for numeric inputs

6. **Select** — Dropdown with glass styling
   - Custom styled dropdown matching glass aesthetic
   - Used for regime selector, time range picker

7. **Toggle** — Switch component
   - For dark mode, compact mode settings
   - Smooth animation

8. **Modal** — Overlay + panel pattern
   - Backdrop: `bg-black/50 backdrop-blur-sm`
   - Panel: glass-card elevated variant
   - Framer-motion enter/exit animation
   - Reference: `docs/design/reference/components/ui/Modal.tsx`

9. **Skeleton** — Loading placeholder
   - Matches MetricCard, GlassCard, table row shapes
   - Pulse animation: `animate-pulse bg-deep-teal-800/5`
   - Dark mode: `dark:bg-white/5`

10. **DataTable** — Sortable table for positions, trades, orders
    - Glass-panel container
    - Header: sticky, subtle background
    - Rows: hover highlight
    - Monospace for all numbers
    - Sortable columns
    - Reference: `docs/design/reference/components/dashboard/PositionsTable.tsx`

**Acceptance Criteria:**
- [ ] All 10 components built with correct Tailwind classes from DESIGN_GUIDE
- [ ] Components support light and dark mode
- [ ] Framer-motion hover animations on Button (scale 1.02, y: -1)
- [ ] MetricCard renders with sparkline zone
- [ ] GlassCard 4 variants visually distinct
- [ ] Badge uses translucent backgrounds (not solid)
- [ ] All components accept `className` prop for composition
- [ ] Modal traps focus on open (Tab cycles within modal only) and returns focus to trigger on close
- [ ] No information conveyed by color alone — Badge uses icon/dot + text + color together
- [ ] All interactive components have visible focus indicators for keyboard navigation

---

### Task 7.1.3: Create Layout Shell
- [ ] **Status:** Not Started
- **Description:** Main application layout — sidebar navigation + header + scrollable content area
- **Dependencies:** [7.1.2]
- **Effort:** 3 hours
- **Tool:** Antigravity (visual) → Claude Code (routing)

**Layout structure:**
```
┌──────────────────────────────────────────────────────────┐
│ SIDEBAR (280px)  │  HEADER (64px)                        │
│                  │  [Regime] [Mode] [Alerts🔔] [⚙️] [🌓]│
│ 🏠 Cockpit      ├──────────────────────────────────────── │
│ 📊 Portfolio     │                                        │
│ 🎯 Strategies    │  MAIN CONTENT AREA                     │
│ ⚠️ Risk          │  (scrollable, max-w-7xl centered)      │
│ 📋 Orders        │                                        │
│ 🔔 Alerts        │                                        │
│ ⚙️ Settings      │                                        │
│                  │                                        │
│ [COLLAPSE BTN]   │                                        │
│ ──────────────   │                                        │
│ 🚨 KILL SWITCH   │                                        │
└──────────────────────────────────────────────────────────┘
```

**Components to build:**

1. **Sidebar** (`src/components/layout/Sidebar.tsx`)
   - Width: 280px expanded, 80px collapsed
   - Animated collapse with framer-motion spring
   - Navigation items with icons (lucide-react)
   - Active state highlighting
   - Kill switch button always visible at bottom
   - Logo/brand at top: "PARAVANT" in Cinzel
   - Collapse/expand toggle
   - Reference: `docs/design/reference/components/layout/Sidebar.tsx`

2. **Header** (`src/components/layout/Header.tsx`)
   - Height: 64px, sticky
   - Left: breadcrumb or page title
   - Right: regime badge, trading mode badge, notification bell, settings gear, dark mode toggle
   - Reference: `docs/design/reference/components/layout/Header.tsx`

3. **MainLayout** (`src/components/layout/MainLayout.tsx`)
   - Wraps Sidebar + Header + content area
   - Content area: `p-4 md:p-8 lg:p-10 max-w-7xl mx-auto`
   - Responsive: sidebar collapses to icons on tablet

4. **React Router setup** (`src/App.tsx`)
   ```typescript
   const routes = [
     { path: '/', element: <CockpitPage /> },
     { path: '/portfolio', element: <PortfolioPage /> },
     { path: '/strategies', element: <StrategiesListPage /> },
     { path: '/strategies/:id', element: <StrategyDetailPage /> },
     { path: '/risk', element: <RiskPage /> },
     { path: '/orders', element: <OrdersPage /> },
     { path: '/alerts', element: <AlertsPage /> },
     { path: '/settings', element: <SettingsPage /> },
     { path: '/accounts', element: <AccountsPage /> },
     { path: '/backtest', element: <BacktestPage /> },
   ];
   ```

**Acceptance Criteria:**
- [ ] Sidebar renders with all navigation items
- [ ] Sidebar collapse/expand animates smoothly
- [ ] Active route highlighted in sidebar
- [ ] Header displays regime badge + mode badge + notification bell
- [ ] Dark mode toggle in header works
- [ ] Content area scrollable, max-width constrained
- [ ] Kill switch button always visible at sidebar bottom
- [ ] React Router navigates between all pages
- [ ] Responsive: sidebar collapses on smaller screens

---

### Task 7.1.4: Implement Theme System
- [ ] **Status:** Not Started
- **Description:** Dark/light/system mode + 5 accent theme variants
- **Dependencies:** [7.1.1, 7.1.3]
- **Effort:** 1.5 hours
- **Tool:** Claude Code

**ThemeContext** (`src/contexts/ThemeContext.tsx`):
```typescript
interface ThemeState {
  mode: 'light' | 'dark' | 'system';      // Color mode
  accent: 'ocean' | 'sapphire' | 'emerald' | 'amber' | 'slate';  // Accent theme
  compactMode: boolean;                     // Condensed layout
  reducedMotion: boolean;                   // Accessibility
}

const ThemeProvider: React.FC = ({ children }) => {
  // 1. Persist to localStorage
  // 2. Apply mode class to <html> element
  // 3. Apply accent theme CSS class
  // 4. Respect prefers-reduced-motion
  // 5. Respect prefers-color-scheme for 'system' mode
};
```

**Theme switching mechanics:**
- Mode: Toggles `dark` class on `<html>` element
- System mode: Uses `window.matchMedia('(prefers-color-scheme: dark)')` with listener
- Accent: Applies `data-theme="ocean"` attribute on `<html>`
- Each theme overrides CSS accent variables
- Persisted to localStorage

**Acceptance Criteria:**
- [ ] Light/dark mode toggles correctly
- [ ] System mode follows OS preference
- [ ] System mode responds to OS changes in real-time
- [ ] 5 accent themes change accent colors
- [ ] Compact mode reduces padding/spacing
- [ ] Reduced motion disables framer-motion animations
- [ ] All preferences persist across page reloads
- [ ] No flash of wrong theme on initial load

---

### Task 7.1.5: Build API Client Layer
- [ ] **Status:** Not Started
- **Description:** Typed API client for all Phase 6 endpoints
- **Dependencies:** [7.1.1]
- **Effort:** 2.5 hours
- **Tool:** Claude Code

**File:** `src/lib/api.ts`

**API client architecture:**
```typescript
// Base client with error handling
class ApiClient {
  private baseUrl = '/api/v1';
  
  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`, window.location.origin);
    if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
    
    const response = await fetch(url.toString());
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new ApiError(response.status, error.detail);
    }
    return response.json();
  }
  
  async post<T>(path: string, body?: unknown): Promise<T> { /* ... */ }
  async put<T>(path: string, body?: unknown): Promise<T> { /* ... */ }
  async delete<T>(path: string): Promise<T> { /* ... */ }
}

// Typed API methods (one per endpoint group)
export const api = {
  // System
  system: {
    getStatus: () => client.get<SystemStatus>('/system/status'),
    start: () => client.post<void>('/system/start'),
    stop: (reason: string) => client.post<void>('/system/stop', { reason }),
    getRegime: () => client.get<RegimeInfo>('/system/regime'),
    setRegime: (data: SetRegimeRequest) => client.put<RegimeUpdateResult>('/system/regime', data),
    getRegimeHistory: (limit?: number) => client.get<RegimeHistory>('/system/regime/history', { limit: String(limit ?? 20) }),
  },
  
  // Dashboard
  dashboard: {
    getSummary: () => client.get<DashboardSummary>('/dashboard/summary'),
    getEquity: (range: string) => client.get<EquityCurve>('/dashboard/equity', { range }),
    getPerformance: () => client.get<PerformanceMetrics>('/dashboard/performance'),
    getRecentTrades: (limit?: number) => client.get<Trade[]>('/dashboard/recent-trades', { limit: String(limit ?? 20) }),
    getAlerts: (limit?: number) => client.get<AlertItem[]>('/dashboard/alerts', { limit: String(limit ?? 20) }),
    getPositions: () => client.get<Position[]>('/dashboard/positions'),
  },
  
  // Strategies
  strategies: {
    list: () => client.get<Strategy[]>('/strategies'),
    get: (id: string) => client.get<StrategyDetail>(`/strategies/${id}`),
    create: (data: CreateStrategy) => client.post<Strategy>('/strategies', data),
    update: (id: string, data: Partial<Strategy>) => client.put<Strategy>(`/strategies/${id}`, data),
    pause: (id: string) => client.post<void>(`/strategies/${id}/pause`),
    resume: (id: string) => client.post<void>(`/strategies/${id}/resume`),
  },
  
  // Accounts
  accounts: {
    list: () => client.get<Account[]>('/accounts'),
    get: (id: string) => client.get<AccountDetail>(`/accounts/${id}`),
    getBalance: (id: string) => client.get<Balance>(`/accounts/${id}/balance`),
    getPnl: (id: string, period?: string) => client.get<PnlData>(`/accounts/${id}/pnl`, { period: period ?? 'daily' }),
  },
  
  // Risk
  risk: {
    getStatus: () => client.get<RiskStatus>('/risk/status'),
    getKillSwitch: () => client.get<KillSwitchStatus>('/risk/kill-switch'),
    activateKillSwitch: (reason: string) => client.post<void>('/risk/kill-switch/activate', { reason }),
    deactivateKillSwitch: (confirm: string) => client.post<void>('/risk/kill-switch/deactivate', { confirm }),
    getCircuitBreakers: () => client.get<CircuitBreaker[]>('/risk/circuit-breakers'),
  },
  
  // P&L
  pnl: {
    daily: (from?: string, to?: string) => client.get<DailyPnl[]>('/pnl/daily', { from, to }),
    monthly: () => client.get<MonthlyPnl[]>('/pnl/monthly'),
    byStrategy: () => client.get<StrategyPnl[]>('/pnl/by-strategy'),
    heatmap: () => client.get<HeatmapData>('/pnl/heatmap'),
  },
  
  // Health
  health: {
    quick: () => client.get<{ overall_status: string }>('/health'),
    detailed: () => client.get<DetailedHealth>('/health/detailed'),
  },
};
```

**TypeScript types** (`src/types/api.ts`):
- Define types for every API response model
- Match the Pydantic models from Phase 6 exactly
- Export all types for use in components and hooks

**Error handling:**
```typescript
class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(`API Error ${status}: ${detail}`);
  }
}
```

**Acceptance Criteria:**
- [ ] All Phase 6 endpoints have typed API methods
- [ ] Error handling produces clear ApiError objects
- [ ] TypeScript types match backend Pydantic models
- [ ] Base URL configurable via environment variable
- [ ] Works with Vite proxy in development
- [ ] Works with relative URLs in production

---

### Task 7.1.6: Build Data Hooks (SSE + Tiered Polling)
- [ ] **Status:** Not Started
- **Description:** Real-time data layer using Server-Sent Events (SSE) for critical state changes and reduced REST polling for historical/aggregated data. Replaces aggressive polling (~91K requests/day) with an SSE stream + slow polls (~5K requests/day) — a 94% reduction in backend request volume.
- **Dependencies:** [7.1.5, Phase 6 Task 6.2.8]
- **Effort:** 4 hours
- **Tool:** Claude Code

**Architecture: Two-tier data strategy**

The dashboard gets data through two channels:
1. **SSE stream (Tier 1):** Single persistent HTTP connection for real-time events — kill switch, positions, alerts, risk changes, regime changes. Zero polling overhead.
2. **REST polling (Tier 2):** Slow polls for aggregated/historical data that's expensive to compute and changes slowly. Visibility-aware — stops when browser tab is hidden.
3. **On-demand (Tier 3):** No polling at all — fetch once on page visit, cache until navigated away.

**Cost comparison:**
```
BEFORE (pure polling):
  Kill switch 3s + System 5s + Risk 5s + Dashboard 10s + Positions 10s
  + Alerts 15s + Strategies 30s + Equity 60s
  = ~63 req/min = ~91K req/day per open tab

AFTER (SSE + tiered polling):
  SSE: 1 persistent connection (near-zero overhead)
  Dashboard summary 30s + Equity 120s + Strategies 60s + P&L heatmap 300s
  = ~3.7 req/min = ~5.3K req/day per open tab
```

**Tier 1: SSE hook** (`src/hooks/useEventStream.ts`):
```typescript
import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

type SSEStatus = 'connecting' | 'connected' | 'disconnected';

export function useEventStream(apiKey: string) {
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number>();
  const reconnectAttemptRef = useRef(0);
  const [status, setStatus] = useState<SSEStatus>('connecting');

  const connect = useCallback(() => {
    // Close existing connection
    eventSourceRef.current?.close();
    
    const url = `${import.meta.env.VITE_API_URL ?? ''}/api/v1/events/stream?api_key=${apiKey}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setStatus('connected');
      reconnectAttemptRef.current = 0; // Reset backoff on successful connect
    };

    es.onerror = () => {
      setStatus('disconnected');
      es.close();
      // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
      const delay = Math.min(1000 * 2 ** reconnectAttemptRef.current, 30000);
      reconnectAttemptRef.current += 1;
      reconnectTimeoutRef.current = window.setTimeout(connect, delay);
    };

    // Route SSE events into react-query cache
    es.addEventListener('kill_switch_changed', (e) => {
      const data = JSON.parse(e.data);
      queryClient.setQueryData(['risk', 'kill-switch'], data);
    });

    es.addEventListener('system_status_changed', (e) => {
      const data = JSON.parse(e.data);
      queryClient.setQueryData(['system', 'status'], data);
    });

    es.addEventListener('position_updated', (e) => {
      const data = JSON.parse(e.data);
      // Invalidate positions query so next access fetches fresh list
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'positions'] });
    });

    es.addEventListener('alert_created', (e) => {
      const data = JSON.parse(e.data);
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'alerts'] });
    });

    es.addEventListener('risk_status_changed', (e) => {
      const data = JSON.parse(e.data);
      queryClient.setQueryData(['risk', 'status'], data);
    });

    es.addEventListener('regime_changed', (e) => {
      const data = JSON.parse(e.data);
      queryClient.setQueryData(['system', 'regime'], data);
      // Also invalidate dashboard since regime affects strategy sizing
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] });
    });
  }, [apiKey, queryClient]);

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
      clearTimeout(reconnectTimeoutRef.current);
    };
  }, [connect]);

  return { status };
}
```

**Key design decisions:**
- `EventSource` (browser built-in) — auto-reconnects on network drops, no library needed
- SSE events update react-query cache directly via `setQueryData` (for full state pushes) or `invalidateQueries` (for partial updates that need a fresh fetch)
- Exponential backoff on disconnect: 1s → 2s → 4s → 8s → max 30s
- Connection status exposed for the health banner (Task 7.5.1)

**Tier 2: Slow REST polling hooks** (`src/hooks/`):

```typescript
// Dashboard summary — aggregated metrics, expensive to compute
function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => api.dashboard.getSummary(),
    refetchInterval: (query) => document.hidden ? false : 30_000,  // 30s, stops when tab hidden
    staleTime: 15_000,
  });
}

// Equity curve — historical daily data, barely changes
function useEquityCurve(range: string) {
  return useQuery({
    queryKey: ['dashboard', 'equity', range],
    queryFn: () => api.dashboard.getEquity(range),
    refetchInterval: (query) => document.hidden ? false : 120_000, // 2 min
    staleTime: 60_000,
  });
}

// Strategy list — rarely changes
function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: () => api.strategies.list(),
    refetchInterval: (query) => document.hidden ? false : 60_000,  // 60s
    staleTime: 30_000,
  });
}

// P&L heatmap — daily granularity, very slow changing
function usePnlHeatmap() {
  return useQuery({
    queryKey: ['pnl', 'heatmap'],
    queryFn: () => api.pnl.heatmap(),
    refetchInterval: (query) => document.hidden ? false : 300_000, // 5 min
    staleTime: 120_000,
  });
}

// P&L by strategy — slow changing
function usePnlByStrategy() {
  return useQuery({
    queryKey: ['pnl', 'by-strategy'],
    queryFn: () => api.pnl.byStrategy(),
    refetchInterval: (query) => document.hidden ? false : 300_000, // 5 min
    staleTime: 120_000,
  });
}
```

**Tier 3: On-demand hooks (no polling):**

```typescript
// Strategy detail — fetch on page visit, no background refresh
function useStrategy(id: string) {
  return useQuery({
    queryKey: ['strategies', id],
    queryFn: () => api.strategies.get(id),
    staleTime: 30_000,
    // No refetchInterval — only fetches on mount or manual refetch
  });
}

// Account detail — fetch on visit
function useAccount(id: string) {
  return useQuery({
    queryKey: ['accounts', id],
    queryFn: () => api.accounts.get(id),
    staleTime: 30_000,
  });
}

// Backtest results — immutable, cache indefinitely
function useBacktestResult(id: string) {
  return useQuery({
    queryKey: ['backtest', id],
    queryFn: () => api.strategies.getBacktest(id),
    staleTime: Infinity,  // Never stale — backtest results don't change
  });
}
```

**Hooks driven by SSE (Tier 1 — no polling, data arrives via event stream):**

```typescript
// Kill switch — populated by SSE, initial fetch on mount only
function useKillSwitch() {
  return useQuery({
    queryKey: ['risk', 'kill-switch'],
    queryFn: () => api.risk.getKillSwitch(),
    // No refetchInterval — SSE pushes updates via setQueryData
    staleTime: Infinity,  // Trust SSE to keep this current
    refetchOnWindowFocus: true,  // Re-sync when tab regains focus (safety)
  });
}

// System status — populated by SSE
function useSystemStatus() {
  return useQuery({
    queryKey: ['system', 'status'],
    queryFn: () => api.risk.getStatus(),
    staleTime: Infinity,
    refetchOnWindowFocus: true,
  });
}

// Risk status — populated by SSE
function useRiskStatus() {
  return useQuery({
    queryKey: ['risk', 'status'],
    queryFn: () => api.risk.getStatus(),
    staleTime: Infinity,
    refetchOnWindowFocus: true,
  });
}

// Positions — invalidated by SSE on fill/close, fetches fresh list
function usePositions() {
  return useQuery({
    queryKey: ['dashboard', 'positions'],
    queryFn: () => api.dashboard.getPositions(),
    staleTime: 10_000,
    refetchOnWindowFocus: true,
  });
}

// Alerts — invalidated by SSE on new alert
function useAlerts(limit?: number) {
  return useQuery({
    queryKey: ['dashboard', 'alerts', limit],
    queryFn: () => api.dashboard.getAlerts(limit),
    staleTime: 10_000,
    refetchOnWindowFocus: true,
  });
}

// Market regime — populated by SSE
function useRegime() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['system', 'regime'],
    queryFn: () => api.system.getRegime(),
    staleTime: Infinity,
    refetchOnWindowFocus: true,
  });
  
  const setRegime = useMutation({
    mutationFn: (data: { regime: string; note: string }) => api.system.setRegime(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system', 'regime'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] });
    },
  });
  
  return { ...query, setRegime: setRegime.mutateAsync };
}
```

**Polling tier summary:**
| Hook | Source | Interval | Visibility-Aware | Rationale |
|------|--------|----------|-------------------|-----------|
| useKillSwitch | SSE push | None (initial fetch only) | refetchOnWindowFocus | Safety-critical, pushed immediately on change |
| useSystemStatus | SSE push | None | refetchOnWindowFocus | State changes pushed via SSE |
| useRiskStatus | SSE push | None | refetchOnWindowFocus | Threshold crosses pushed via SSE |
| usePositions | SSE invalidate | None (re-fetches on SSE event) | refetchOnWindowFocus | Fills/closes pushed, then fresh fetch |
| useAlerts | SSE invalidate | None (re-fetches on SSE event) | refetchOnWindowFocus | New alerts pushed, then fresh fetch |
| useRegime | SSE push | None | refetchOnWindowFocus | Regime changes pushed via SSE |
| useDashboardSummary | REST poll | 30s | Yes — stops when hidden | Aggregated metrics, not worth streaming |
| useEquityCurve | REST poll | 120s | Yes — stops when hidden | Historical data, slow-changing |
| useStrategies | REST poll | 60s | Yes — stops when hidden | Strategy list rarely changes |
| usePnlHeatmap | REST poll | 300s | Yes — stops when hidden | Daily granularity |
| usePnlByStrategy | REST poll | 300s | Yes — stops when hidden | Slow-changing aggregation |
| useStrategy | On-demand | None | N/A | Fetched on page visit |
| useAccount | On-demand | None | N/A | Fetched on page visit |
| useBacktestResult | On-demand | Never stale | N/A | Immutable results |

**QueryClient provider** (`src/App.tsx`):
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
      refetchOnWindowFocus: false,  // Default off; SSE hooks opt-in explicitly
    },
  },
});

// Initialize SSE connection at app level
function App() {
  const { status: sseStatus } = useEventStream(API_KEY);
  
  return (
    <QueryClientProvider client={queryClient}>
      <SSEStatusContext.Provider value={sseStatus}>
        <Router>
          {/* ... */}
        </Router>
      </SSEStatusContext.Provider>
    </QueryClientProvider>
  );
}
```

**SSE fallback behavior:**
- If SSE disconnects, the `useEventStream` hook sets `status = 'disconnected'`
- Task 7.5.1 (error handling) uses this status to show a "Live connection lost" banner
- While SSE is disconnected, Tier 1 hooks continue to serve cached data from their initial fetch
- `refetchOnWindowFocus: true` on Tier 1 hooks means regaining focus triggers a fresh REST fetch — this acts as a natural recovery mechanism when the user returns to the tab after an SSE dropout

**Acceptance Criteria:**
- [ ] SSE connection established on app mount via `useEventStream`
- [ ] Kill switch, system status, risk status update instantly via SSE (no polling)
- [ ] Position and alert queries invalidated and re-fetched on SSE events
- [ ] Tier 2 polls stop when browser tab is hidden (`document.hidden` check)
- [ ] Tier 2 polls resume when tab becomes visible
- [ ] Tier 3 hooks fetch once on mount, no background polling
- [ ] SSE reconnects with exponential backoff on disconnect (1s → 2s → 4s → max 30s)
- [ ] SSE connection status exposed for health banner
- [ ] All hooks return { data, loading, error } consistently
- [ ] Loading states transition correctly (initial load vs SSE update vs refetch)
- [ ] Mutations invalidate relevant queries (e.g., setRegime invalidates regime + dashboard)
- [ ] No memory leaks — EventSource closed on unmount

---

## SECTION 7.2: CORE PAGES
*Estimated: 38 hours*

Each page is built in two passes: (1) Antigravity for layout with placeholder data, (2) Claude Code to wire up API hooks and add interaction logic.

### Task 7.2.1: Build Cockpit Page (Main Dashboard)
- [ ] **Status:** Not Started
- **Description:** The default landing page — all PRD §6.2.2 dashboard widgets on one screen
- **Dependencies:** [7.1.2, 7.1.3, 7.1.6]
- **Effort:** 5 hours
- **Tool:** Antigravity (layout) → Claude Code (data integration)

**PRD §6.2.2 required widgets (ALL must be present):**

```
┌─────────────────────────────────────────────────────────────────┐
│ HERO METRICS ROW (MetricCards)                                  │
│ [Portfolio Value] [Daily P&L] [Open Positions] [Win Rate 7D]   │
│ [Active Strategies] [Current Drawdown]                          │
├──────────────────────────────────┬──────────────────────────────┤
│ RISK STATUS WIDGET               │ REGIME INDICATORS WIDGET     │
│ ○ Overall: NORMAL                │ Trend: BULLISH (ADX: 28)     │
│ ○ Drawdown: 3.2% / 15% max     │ Volatility: NORMAL           │
│ ○ Daily Loss: 0.8% / 5% max    │ Momentum: RSI 54 (NEUTRAL)   │
│ ○ Positions: 3 / 10 max        │ Regime: RANGING              │
│ ○ Circuit Breakers: ALL CLOSED  │ [CHANGE REGIME ▾]            │
├──────────────────────────────────┴──────────────────────────────┤
│ POSITIONS WIDGET                                                 │
│ Symbol │ Side │ Qty │ Entry │ Current │ P&L │ Duration │ Strat │
│ BTCUSDT│ LONG │ 0.1 │ 65000 │ 67500  │+2500│ 4h 30m  │ EMA   │
│ ETHUSDT│ SHORT│ 2.0 │ 3200  │ 3150   │ +100│ 2h 15m  │ BB    │
│                                                    [Close] btns │
├──────────────────────────────────┬──────────────────────────────┤
│ STRATEGIES WIDGET                │ RECENT ALERTS WIDGET         │
│ ○ EMA Trend BTC    LIVE  +12%  │ ⚠️ 14:25 - Daily loss 60%   │
│ ○ BB Squeeze ETH   PAPER +3%   │ ℹ️ 14:20 - Order filled BTC │
│ ○ VWAP Pullback    PAUSED      │ ℹ️ 14:10 - Signal generated │
│               [View All →]      │              [View All →]     │
└──────────────────────────────────┴──────────────────────────────┘
```

**Widget specifications:**

1. **Hero Metrics Row** — 4-6 MetricCards in responsive grid
   - Portfolio Value: with 7-day sparkline
   - Daily P&L: green/red based on sign
   - Open Positions: count with max indicator
   - Win Rate (7D): percentage with trend arrow
   - Active Strategies: count
   - Current Drawdown: percentage with gauge fill

2. **Risk Status Widget** — GlassCard with status indicators
   - Overall status badge: NORMAL (green) / WARNING (yellow) / CRITICAL (red)
   - Progress bars for drawdown, daily loss, position count
   - Circuit breaker states: CLOSED (green) / WARNING (yellow) / OPEN (red)
   - Data from: `useDashboardSummary()` + `useRiskStatus()`

3. **Regime Indicators Widget** — GlassCard with market state
   - Trend: direction + ADX confidence
   - Volatility: current ATR vs average
   - Momentum: RSI value + zone
   - Composite regime: calculated label
   - Regime dropdown selector (triggers `PUT /api/v1/system/regime`)
   - Data from: `useRegime()`

4. **Positions Widget** — DataTable with live P&L
   - All PRD §6.2.2 position fields
   - Close button per position (confirmation modal)
   - Unrealized P&L color-coded
   - Data from: `usePositions()`

5. **Strategies Widget** — Compact strategy list
   - Name, status badge, return %, position count
   - Click → navigate to strategy detail
   - "View All" link to strategies page
   - Data from: `useStrategies()`

6. **Recent Alerts Widget** — Alert feed
   - Severity emoji + timestamp + message
   - Last 5 alerts
   - "View All" link to alerts page
   - Data from: `useAlerts(5)`

**Acceptance Criteria:**
- [ ] All 6 PRD §6.2.2 widgets present and populated
- [ ] MetricCards show real portfolio data with sparklines
- [ ] Risk progress bars update instantly via SSE (no visible polling delay)
- [ ] Regime dropdown changes regime via API
- [ ] Positions table updates via SSE on fill/close events
- [ ] Close position button triggers confirmation modal
- [ ] Strategies list links to detail pages
- [ ] Alerts feed updates instantly via SSE when new alert fires
- [ ] Loading skeletons during initial load
- [ ] Error states for failed API calls
- [ ] Responsive grid (2 columns on desktop, 1 on tablet)

---

### Task 7.2.2: Build Portfolio Page
- [ ] **Status:** Not Started
- **Description:** Performance visualization — equity curve, monthly returns heatmap, trade distribution
- **Dependencies:** [7.1.6, 7.2.1]
- **Effort:** 4 hours
- **Tool:** Antigravity (chart layout) → Claude Code (data + Recharts config)

**PRD §6.3 required charts (ALL must be present):**

1. **Equity Curve** (PRD §6.3.1)
   - Line chart with area fill
   - Benchmark overlay (Buy-and-hold BTC)
   - Drawdown underwater chart below
   - Time range selector: 1W / 1M / 3M / 6M / 1Y / ALL
   - Trade entry/exit markers (optional dots on curve)
   - Data from: `useEquityCurve(range)`

2. **Monthly Returns Heatmap** (PRD §6.3.2)
   - Rows = years, columns = months
   - Color scale: red (negative) → white (zero) → green (positive)
   - Each cell shows return % and trade count
   - Data from: `usePnlHeatmap()`

3. **Trade Distribution Histogram** (PRD §6.3.3)
   - Histogram of return per trade
   - Mean line overlay
   - Median line overlay
   - Expectancy annotation
   - Data from: P&L endpoint

**Additional portfolio metrics:**
- Total return, Sharpe ratio, Sortino ratio, max drawdown
- Win rate, average win/loss, profit factor
- P&L breakdown by strategy (donut chart)
- P&L breakdown by symbol (horizontal bar chart)

**Acceptance Criteria:**
- [ ] Equity curve renders with real data
- [ ] Benchmark overlay shows comparison
- [ ] Drawdown underwater chart synchronized with equity curve
- [ ] Time range selector switches data correctly
- [ ] Monthly heatmap renders with correct color scale
- [ ] Trade histogram shows distribution with overlay lines
- [ ] All charts responsive (resize with container)
- [ ] Loading states for each chart independently
- [ ] Charts use DESIGN_GUIDE §4.7 color palette

---

### Task 7.2.3: Build Strategies List Page
- [ ] **Status:** Not Started
- **Description:** Grid/list view of all strategies with status, performance, and quick actions
- **Dependencies:** [7.1.6]
- **Effort:** 3 hours
- **Tool:** Antigravity (layout) → Claude Code (data + interactions)

**Layout:**
- Grid of strategy cards (default) or table view (toggle)
- Each strategy card: name, template type, status badge, key metrics, quick actions
- Filters: by status (All / Live / Paper / Paused / Draft), by template
- Sort: by return, by Sharpe, by name, by creation date
- "Create New Strategy" button → modal/page for template selection

**Strategy card content:**
```
┌──────────────────────────────────┐
│ EMA Trend BTC              LIVE  │
│ Template: EMA Trend + RSI        │
│                                  │
│ Return: +12.5%    Sharpe: 1.8    │
│ Win Rate: 62%     Trades: 47     │
│ Drawdown: -3.2%   Since: Jan 15  │
│                                  │
│ [Pause] [Backtest] [Details →]   │
└──────────────────────────────────┘
```

**Acceptance Criteria:**
- [ ] All strategies displayed with correct data
- [ ] Status badges color-coded (LIVE=green, PAPER=blue, PAUSED=yellow)
- [ ] Grid/table view toggle works
- [ ] Filters by status functional
- [ ] Sort options work correctly
- [ ] Click card navigates to strategy detail
- [ ] Quick actions (pause/resume) work via API
- [ ] "Create New" button present (actual creation can be Phase 8)

---

### Task 7.2.4: Build Strategy Detail Page
- [ ] **Status:** Not Started
- **Description:** Full strategy view with all PRD §6.4 sections
- **Dependencies:** [7.1.6, 7.2.2]
- **Effort:** 5 hours
- **Tool:** Antigravity (layout) → Claude Code (data + parameter editing)

**PRD §6.4 required sections (ALL 7 must be present):**

1. **Overview** — Strategy metadata, current status, key metrics, recommendations
2. **Parameters** — All strategy parameters grouped by `ui_group`, editable with min/max/step validation
3. **Backtest Results** — Metrics table, equity curve, trade list
4. **Paper Trading Results** — Same metrics for paper period
5. **Live Results** — Real performance metrics
6. **Recommendations** — System-generated suggestions (if any)
7. **Lifecycle** — Status history timeline with timestamps

**Additional features:**
- Tab navigation between sections
- Parameter editor with template range validation
- Equity curve chart (reuse from Portfolio page)
- Lifecycle timeline visualization
- Back navigation to strategy list

**Parameter editor:**
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
│ RSI Threshold      ─────────[●]  70     │
│                    min: 50  max: 90      │
│                                          │
│ [Save Changes]  [Reset to Template]      │
└──────────────────────────────────────────┘
```

**Acceptance Criteria:**
- [ ] All 7 PRD §6.4 sections present
- [ ] Tabbed navigation between sections
- [ ] Parameters grouped by ui_group
- [ ] Parameter editing validates against template ranges (min/max/step)
- [ ] Save changes calls PUT API endpoint
- [ ] Charts render correctly with strategy-specific data
- [ ] Lifecycle timeline shows status transitions with timestamps
- [ ] Back navigation returns to strategy list

---

### Task 7.2.5: Build Risk Page
- [ ] **Status:** Not Started
- **Description:** Comprehensive risk monitoring with gauges, circuit breakers, and controls
- **Dependencies:** [7.1.6]
- **Effort:** 4 hours
- **Tool:** Antigravity (layout) → Claude Code (data + interactions)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ RISK OVERVIEW                                                │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│ │  DRAWDOWN   │ │ DAILY LOSS  │ │  POSITIONS  │            │
│ │   [GAUGE]   │ │   [GAUGE]   │ │   [GAUGE]   │            │
│ │  3.2% / 15% │ │  0.8% / 5%  │ │   3 / 10    │            │
│ └─────────────┘ └─────────────┘ └─────────────┘            │
├─────────────────────────────────────────────────────────────┤
│ CIRCUIT BREAKERS                                             │
│ ┌───────────────┬────────────┬────────────┬────────────┐   │
│ │ Breaker       │ Status     │ Threshold  │ Current    │   │
│ │ Drawdown      │ ● CLOSED   │ 15%        │ 3.2%      │   │
│ │ Loss Rate     │ ● CLOSED   │ 70%        │ 38%       │   │
│ │ Error Rate    │ ● WARNING  │ 10/hr      │ 7/hr      │   │
│ └───────────────┴────────────┴────────────┴────────────┘   │
├─────────────────────────────────────────────────────────────┤
│ KILL SWITCH                                                  │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Status: ● INACTIVE                                       │ │
│ │                                                          │ │
│ │ [🚨 ACTIVATE KILL SWITCH]                                │ │
│ │                                                          │ │
│ │ Kill switch halts ALL trading immediately.               │ │
│ │ Open positions remain open but no new trades.            │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ PORTFOLIO EXPOSURE                                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ BTC Exposure: 35% / 40% max  [████████░░]              │ │
│ │ ETH Exposure: 20% / 30% max  [██████░░░░]              │ │
│ │ Correlated:   45% / 60% max  [███████░░░]              │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Gauge component:**
- Semi-circular gauge (custom SVG or Recharts)
- Color zones: green (0-50%), yellow (50-80%), red (80-100%)
- Current value as large center text
- Max value as subtitle

**Kill switch section:**
- Large, prominent emergency button
- Current status with timestamp of last change
- Activation requires confirmation modal with reason text
- Deactivation requires typing "DEACTIVATE" (safety measure)
- **Kill Switch button uses `role="alert"` and `aria-live="assertive"` when active** — screen readers announce state changes immediately

**Kill switch audit history (new — below kill switch controls):**
```
┌─────────────────────────────────────────────────────────────┐
│ KILL SWITCH HISTORY                                          │
│ ┌───────────┬───────────┬───────────────────┬─────────────┐ │
│ │ Action    │ Time      │ Reason            │ Duration    │ │
│ │ ACTIVATED │ Feb 14    │ "Manual: market   │ 2h 15m      │ │
│ │           │ 10:30 AM  │  flash crash"     │             │ │
│ │ DEACTIVATED│ Feb 14   │ —                 │ —           │ │
│ │           │ 12:45 PM  │                   │             │ │
│ │ ACTIVATED │ Feb 10    │ "Daily loss limit │ 18h 30m     │ │
│ │           │ 3:15 PM   │  approaching"     │             │ │
│ └───────────┴───────────┴───────────────────┴─────────────┘ │
│ Shows transaction_id on hover. Data from kill switch audit   │
│ log (Phase 6 Task 6.2.8).                                   │
└─────────────────────────────────────────────────────────────┘
```
- Fetch audit history from backend on page visit (on-demand, not polled)
- Show action (activate/deactivate), timestamp, reason, duration
- Tooltip on each row shows `transaction_id` for debugging/audit
- Most recent entries first

**Acceptance Criteria:**
- [ ] Risk gauges render with correct values and color zones
- [ ] Circuit breakers show CLOSED/WARNING/OPEN states
- [ ] Kill switch button works with confirmation flow
- [ ] Kill switch deactivation requires "DEACTIVATE" confirmation
- [ ] Kill switch button uses `role="alert"` and `aria-live="assertive"` when active
- [ ] Kill switch audit history table shows all activations/deactivations with reason and duration
- [ ] Portfolio exposure bars show correlation limits (PRD Feature A)
- [ ] Kill switch and risk data driven by SSE (no polling) — updates appear instantly on state change
- [ ] Loading states for each section

---

### Task 7.2.6: Build Accounts Page
- [ ] **Status:** Not Started
- **Description:** Account management with risk profiles and balance display
- **Dependencies:** [7.1.6]
- **Effort:** 2.5 hours
- **Tool:** Antigravity (layout) → Claude Code (data)

**PRD §7 requirements:**
- List all accounts with risk profile badges
- Account detail view: balance, P&L history, risk settings
- Three risk profiles: Conservative / Balanced / Aggressive
- Settings inheritance display: Portfolio → Account → Strategy

**Acceptance Criteria:**
- [ ] All accounts listed with risk profile badges
- [ ] Account detail shows balance (from exchange)
- [ ] P&L history chart per account
- [ ] Risk profile settings visible
- [ ] Settings inheritance chain displayed

---

### Task 7.2.7: Build Orders Page
- [ ] **Status:** Not Started
- **Description:** Order history with filtering and status tracking
- **Dependencies:** [7.1.6]
- **Effort:** 2.5 hours
- **Tool:** Antigravity (table layout) → Claude Code (data + filters)

**Features:**
- DataTable with all order fields: ID, symbol, side, type, quantity, price, status, strategy, timestamp
- Filters: by status (Pending/Filled/Cancelled/Rejected), by symbol, by strategy
- Sort by any column
- Pending orders: cancel button
- Click row → order detail panel (drawer/modal)

**Acceptance Criteria:**
- [ ] All orders displayed with correct data
- [ ] Status badges color-coded
- [ ] Filters functional
- [ ] Cancel pending orders via API
- [ ] Order detail shows full information

---

### Task 7.2.8: Build Alerts Page
- [ ] **Status:** Not Started
- **Description:** Full alert history with filtering, acknowledgment, and detail view
- **Dependencies:** [7.1.6]
- **Effort:** 2.5 hours
- **Tool:** Antigravity (layout) → Claude Code (data + acknowledgment)

**Features:**
- Alert feed: severity icon + timestamp + title + message
- Filters: by level (INFO/WARNING/ERROR/CRITICAL), by date range
- Unacknowledged alerts highlighted
- Acknowledge button (calls escalation acknowledge API)
- Alert detail panel on click

**Acceptance Criteria:**
- [ ] All alerts displayed chronologically
- [ ] Severity indicators with correct colors/icons
- [ ] Filters by level functional
- [ ] Acknowledge button stops escalation
- [ ] Unacknowledged alerts visually distinct
- [ ] Auto-refresh (15s)

---

### Task 7.2.9: Build Settings Page
- [ ] **Status:** Not Started
- **Description:** System configuration and preferences
- **Dependencies:** [7.1.4, 7.1.6]
- **Effort:** 2 hours
- **Tool:** Claude Code

**Settings sections:**

1. **Appearance** — Dark mode, accent theme, compact mode, reduced motion
2. **Notifications** — Alert level preferences, quiet hours
3. **Trading** — Default paper trading period, auto-close on shutdown
4. **System Info** — Version, uptime, database stats, API status

**Acceptance Criteria:**
- [ ] Theme settings persist via ThemeContext
- [ ] Notification preferences saved
- [ ] System info displays correctly
- [ ] All settings take effect immediately

---

### Task 7.2.10: Build Backtest Page
- [ ] **Status:** Not Started
- **Description:** Interface for running and viewing backtests
- **Dependencies:** [7.1.6, 7.2.4]
- **Effort:** 3 hours
- **Tool:** Antigravity (layout) → Claude Code (backtest execution + results)

**Features:**
- Strategy selection (dropdown of existing strategies)
- Date range selection
- "Run Backtest" button with progress indicator
- Results display: metrics table + equity curve + trade list
- Compare multiple backtest results side-by-side (optional)

**Backtest results display:**
```
┌─────────────────────────────────────────────────────────┐
│ BACKTEST RESULTS: EMA Trend BTC                          │
│ Period: 2023-01-01 to 2024-12-31                        │
│                                                          │
│ Total Return: +45.2%    Sharpe: 1.82                    │
│ Max Drawdown: -12.4%    Win Rate: 58%                   │
│ Total Trades: 187       Profit Factor: 1.65             │
│ Avg Win: +2.3%          Avg Loss: -1.4%                 │
│                                                          │
│ [Equity Curve Chart]                                    │
│                                                          │
│ [Trade List Table]                                      │
│                                                          │
│ [Start Paper Trading] [Re-run with Different Params]    │
└─────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**
- [ ] Strategy selection from existing strategies
- [ ] Date range picker functional
- [ ] Run backtest triggers API call
- [ ] Progress indication during backtest
- [ ] Results render with metrics + chart + trade list
- [ ] "Start Paper Trading" navigates to strategy lifecycle

---

## SECTION 7.3: OPERATIONAL FEATURES
*Estimated: 28 hours*

Features that make the dashboard a real operational tool, not just a display.

### Task 7.3.1: Build Emergency Panel (Kill Switch Modal)
- [ ] **Status:** Not Started
- **Description:** Global kill switch control accessible from sidebar — the most critical UI interaction
- **Dependencies:** [7.1.2, 7.1.6]
- **Effort:** 3 hours
- **Tool:** Claude Code (safety-critical logic requires precision)

**Kill switch is the most important control in the system. It must be:**
- Always accessible (sidebar button, never hidden)
- Visually alarming (red, pulsing when active)
- Fast to activate (one click + confirm)
- Slow to deactivate (type "DEACTIVATE" to prevent accidental resume)

**Activation flow:**
```
User clicks "KILL SWITCH" in sidebar
→ Modal opens: "Activate Kill Switch?"
→ "This will halt ALL trading immediately."
→ Reason text field (required)
→ [Cancel] [ACTIVATE — HALT ALL TRADING]
→ API call: POST /risk/kill-switch/activate
→ Response includes transaction_id + server_timestamp (logged for audit)
→ Success: close modal, sidebar button turns red/pulsing
→ SSE pushes kill_switch_changed event — all connected clients update instantly
```

**Deactivation flow:**
```
User clicks pulsing "KILL SWITCH ACTIVE" in sidebar
→ Modal opens: "Deactivate Kill Switch?"
→ "Type DEACTIVATE to confirm trading can resume."
→ Text input field (must match "DEACTIVATE" exactly)
→ [Cancel] [Confirm Deactivation]
→ API call: POST /risk/kill-switch/deactivate
→ Response includes transaction_id + server_timestamp
→ Success: close modal, sidebar button returns to normal
→ SSE pushes kill_switch_changed event
```

**Visual states:**
- Inactive: subtle button in sidebar
- Active: red background, pulsing animation, bold text
- Header also shows kill switch status badge when active
- Kill switch button uses `role="alert"` and `aria-live="assertive"` when active

**Acceptance Criteria:**
- [ ] Kill switch button always visible in sidebar
- [ ] Activation: one-click + reason + confirm
- [ ] Deactivation: requires typing "DEACTIVATE" exactly
- [ ] Visual state clearly different when active (red, pulsing)
- [ ] Header shows kill switch badge when active
- [ ] Kill switch state updates instantly via SSE (no polling delay)
- [ ] API response transaction_id logged to console for audit trail
- [ ] Error handling if API call fails (don't close modal)
- [ ] Accessible via keyboard shortcut (Ctrl+K or similar)
- [ ] Uses `role="alert"` and `aria-live="assertive"` when active

---

### Task 7.3.2: Build Regime Selector
- [ ] **Status:** Not Started
- **Description:** Market regime dropdown in header per PRD Feature B
- **Dependencies:** [7.1.3, 7.1.6]
- **Effort:** 2 hours
- **Tool:** Claude Code

**Regime selector (in Header component):**
- Dropdown with current regime displayed as badge
- Options: trending_up, trending_down, ranging, volatile, unknown
- Each option color-coded
- Changing regime opens confirmation:
  - "Change regime from [current] to [new]?"
  - Optional note field
  - Shows affected strategies count
- After change: dashboard reflects new regime, strategies adjust

**Color coding:**
- trending_up: green
- trending_down: red
- ranging: yellow
- volatile: orange
- unknown: gray

**Acceptance Criteria:**
- [ ] Current regime displayed in header
- [ ] Dropdown shows all options with colors
- [ ] Change triggers confirmation with affected strategies count
- [ ] Note field in confirmation
- [ ] API call on confirm
- [ ] Dashboard updates after regime change
- [ ] Regime history accessible

---

### Task 7.3.3: Build Position Close Modal
- [ ] **Status:** Not Started
- **Description:** Confirmation flow for manually closing a position from the dashboard
- **Dependencies:** [7.1.2, 7.2.1]
- **Effort:** 1.5 hours
- **Tool:** Claude Code

**Flow:**
```
User clicks [Close] on position row
→ Modal: "Close Position: BTCUSDT LONG?"
→ Shows: quantity, entry price, current price, unrealized P&L
→ Close type: Market (immediate) or Limit (specify price)
→ [Cancel] [Close Position]
→ API call: POST /positions/{id}/close
→ Success: position removed from list, P&L recorded
```

**Acceptance Criteria:**
- [ ] Shows position details in modal
- [ ] Market close option (immediate)
- [ ] API call on confirm
- [ ] Position removed from list after close
- [ ] Error handling if close fails

---

### Task 7.3.4: Build Notification Bell
- [ ] **Status:** Not Started
- **Description:** In-app notification system with bell icon in header
- **Dependencies:** [7.1.3, 7.1.6]
- **Effort:** 2 hours
- **Tool:** Claude Code

**Features:**
- Bell icon in header with unread count badge
- Dropdown panel showing last 10 notifications
- Severity icon + relative timestamp + title
- Click notification → navigate to relevant page
- Mark individual as read
- "Mark All as Read" button
- "View All" link to Alerts page

**Notification types map to alert severities:**
- CRITICAL: red dot, stays until acknowledged
- ERROR: red dot
- WARNING: yellow dot
- INFO: blue dot, auto-dismisses after 1 hour

**Acceptance Criteria:**
- [ ] Bell icon with unread count badge
- [ ] Dropdown panel shows notifications
- [ ] Click navigates to relevant page
- [ ] Mark as read (individual + all)
- [ ] Critical notifications don't auto-dismiss
- [ ] Polling from alert API

---

### Task 7.3.5: Build Strategy Quick Actions
- [ ] **Status:** Not Started
- **Description:** Pause/resume/retire strategy actions from list and detail views
- **Dependencies:** [7.2.3, 7.2.4]
- **Effort:** 2 hours
- **Tool:** Claude Code

**Actions:**
- **Pause:** Confirmation → API call → strategy status updates
- **Resume:** Confirmation → API call → strategy status updates  
- **Retire:** Requires typing strategy name → API call → strategy archived

**Acceptance Criteria:**
- [ ] Pause/resume available in strategy list cards
- [ ] Pause/resume available in strategy detail page
- [ ] Retire requires name confirmation (destructive action)
- [ ] API calls succeed and UI updates
- [ ] Strategy list refreshes after action

---

### Task 7.3.6: Build Keyboard Shortcuts
- [ ] **Status:** Not Started
- **Description:** Power user keyboard shortcuts for fast navigation and actions
- **Dependencies:** [7.1.3, 7.3.1]
- **Effort:** 1.5 hours
- **Tool:** Claude Code

**Shortcuts:**
```
Navigation:
  G then H  → Go to Cockpit (Home)
  G then P  → Go to Portfolio
  G then S  → Go to Strategies
  G then R  → Go to Risk
  G then O  → Go to Orders

Actions:
  Ctrl+K    → Toggle kill switch modal
  Ctrl+/    → Show keyboard shortcuts help
  Escape    → Close any open modal
  
Dashboard:
  R         → Refresh current page data
  D         → Toggle dark mode
```

**Implementation:**
- Use a `useGlobalShortcuts` hook
- Key sequence detection for "G then X" patterns
- Shortcuts disabled when input/textarea is focused
- Help modal shows all shortcuts (triggered by `Ctrl+/`)

**Acceptance Criteria:**
- [ ] All navigation shortcuts work
- [ ] Kill switch shortcut opens modal
- [ ] Shortcuts disabled in input fields
- [ ] Help modal lists all shortcuts
- [ ] No conflicts with browser shortcuts

---

### Task 7.3.7: Build Position Detail Drawer
- [ ] **Status:** Not Started
- **Description:** Slide-out drawer showing full position details when clicking a position row
- **Dependencies:** [7.2.1]
- **Effort:** 2.5 hours
- **Tool:** Antigravity (layout) → Claude Code (data)

**Drawer content:**
- Position metadata: symbol, side, quantity, entry time
- Price info: entry, current, stop loss, take profit
- P&L: unrealized, with chart of price movement since entry
- Strategy info: name, link to strategy detail
- Order history for this position
- Close position button

**Acceptance Criteria:**
- [ ] Drawer slides in from right
- [ ] All position details displayed
- [ ] Price movement mini-chart
- [ ] Close position button (opens close modal)
- [ ] Link to strategy detail page
- [ ] Click outside or Escape closes drawer

---

### Task 7.3.8: Build Toast Notifications
- [ ] **Status:** Not Started
- **Description:** In-app toast system for action confirmations and transient messages
- **Dependencies:** [7.1.1]
- **Effort:** 1.5 hours
- **Tool:** Claude Code

**ToastContext and ToastContainer:**
```typescript
type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;  // ms, default 5000
}

// Usage:
const { addToast } = useToast();
addToast({ type: 'success', title: 'Kill switch deactivated' });
```

**Display:**
- Toast stack in bottom-right corner
- Auto-dismiss after duration (default 5s)
- Manual dismiss via X button
- Framer-motion enter/exit animation
- Max 3 visible at once (queue extras)

**Acceptance Criteria:**
- [ ] Toasts render in bottom-right
- [ ] Auto-dismiss after duration
- [ ] Manual dismiss works
- [ ] Animated enter/exit
- [ ] Max 3 visible (queue extras)
- [ ] Used for all user action confirmations

---

## SECTION 7.4: CHARTS & DATA VISUALIZATION
*Estimated: 14 hours*

Dedicated section for chart components that are reused across multiple pages.

### Task 7.4.1: Build Equity Curve Chart Component
- [ ] **Status:** Not Started
- **Description:** Reusable equity curve with benchmark overlay and drawdown subplot
- **Dependencies:** [7.1.6]
- **Effort:** 4 hours
- **Tool:** Antigravity (visual) → Claude Code (Recharts config + data)

**File:** `src/components/charts/EquityCurveChart.tsx`

**Features:**
- Main line: portfolio equity over time (area fill with gradient)
- Benchmark overlay: Buy-and-hold BTC (dashed line, different color)
- Drawdown underwater chart: inverted area chart below main (red fill)
- Time range selector: 1W / 1M / 3M / 6M / 1Y / ALL
- Tooltip: date, equity value, benchmark value, drawdown %
- Trade markers: optional dots at entry/exit points

**Recharts implementation:**
```typescript
<ResponsiveContainer width="100%" height={400}>
  <ComposedChart data={equityData}>
    <defs>
      <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%" stopColor="var(--color-gain)" stopOpacity={0.3} />
        <stop offset="95%" stopColor="var(--color-gain)" stopOpacity={0} />
      </linearGradient>
    </defs>
    <XAxis dataKey="date" ... />
    <YAxis ... />
    <Tooltip content={<CustomTooltip />} />
    <Area dataKey="equity" fill="url(#equityGradient)" stroke="var(--color-gain)" />
    <Line dataKey="benchmark" stroke="var(--color-accent)" strokeDasharray="5 5" />
  </ComposedChart>
</ResponsiveContainer>
```

**Props:**
```typescript
interface EquityCurveChartProps {
  data: EquityCurvePoint[];       // {date, equity, benchmark, drawdown_pct}
  range: string;                  // Current time range
  onRangeChange: (range: string) => void;
  showBenchmark?: boolean;        // Default true
  showDrawdown?: boolean;         // Default true
  showTradeMarkers?: boolean;     // Default false
  height?: number;                // Default 400
}
```

**Acceptance Criteria:**
- [ ] Equity line renders smoothly with gradient fill
- [ ] Benchmark overlay toggleable
- [ ] Drawdown chart renders below (synchronized x-axis)
- [ ] Time range selector changes data
- [ ] Custom tooltip styled per DESIGN_GUIDE §4.7
- [ ] Responsive to container width
- [ ] Handles empty data gracefully
- [ ] Chart colors from CSS variables (theme-aware)

---

### Task 7.4.2: Build Monthly Returns Heatmap Component
- [ ] **Status:** Not Started
- **Description:** Year × month grid showing returns with color coding
- **Dependencies:** [7.1.6]
- **Effort:** 3 hours
- **Tool:** Antigravity (grid layout) → Claude Code (color calculation)

**File:** `src/components/charts/MonthlyHeatmap.tsx`

**Implementation:** Custom component (not Recharts — it's a grid, not a chart)

```
         Jan    Feb    Mar    Apr    May    Jun    Jul    Aug    Sep    Oct    Nov    Dec
2023    +2.3%  -1.1%  +4.5%  +0.8%  -2.0%  +3.2%  +1.5%  -0.5%  +2.8%  +1.2%  -1.8%  +3.5%
2024    +1.8%  +3.1%  -0.3%  +2.7%  +1.4%  ...
```

**Color scale:**
- Negative: red (intensity scales with magnitude)
- Zero: white/neutral
- Positive: green (intensity scales with magnitude)
- Each cell also shows trade count in smaller text

**Acceptance Criteria:**
- [ ] Grid renders with correct year/month structure
- [ ] Color scale correctly maps to return values
- [ ] Cell shows return % and trade count
- [ ] Hover tooltip shows detailed info
- [ ] Responsive (horizontal scroll on small screens)
- [ ] Theme-aware colors

---

### Task 7.4.3: Build Sparkline Chart Component
- [ ] **Status:** Not Started
- **Description:** Inline mini chart for MetricCard and table cells
- **Dependencies:** [7.1.2]
- **Effort:** 2 hours
- **Tool:** Claude Code

**File:** `src/components/charts/SparklineChart.tsx`

**Props:**
```typescript
interface SparklineChartProps {
  data: number[];           // Array of values
  color?: string;           // Override color (default: gain/loss based on trend)
  width?: number;           // Default: fill container
  height?: number;          // Default: 40
  showArea?: boolean;       // Default: true
  animated?: boolean;       // Default: true (path draw animation)
}
```

**Implementation:** Lightweight SVG (not Recharts — too heavy for inline use)
- Simple polyline SVG with optional area fill
- Auto-scales to data range
- Color based on first-to-last trend (green if up, red if down)
- Gradient mask overlay to fade into card background

**Acceptance Criteria:**
- [ ] Renders inline within MetricCard
- [ ] Auto-scales to data range
- [ ] Color reflects overall trend
- [ ] Gradient fade at edges
- [ ] Lightweight (no Recharts overhead)
- [ ] Handles empty/single-point data

---

### Task 7.4.4: Build Risk Gauge Component
- [ ] **Status:** Not Started
- **Description:** Semi-circular gauge for risk metrics (drawdown, daily loss, position count)
- **Dependencies:** [7.1.2]
- **Effort:** 3 hours
- **Tool:** Antigravity (visual) → Claude Code (SVG math)

**File:** `src/components/charts/GaugeChart.tsx`

**Props:**
```typescript
interface GaugeChartProps {
  value: number;            // Current value
  max: number;              // Maximum value
  label: string;            // "Drawdown", "Daily Loss", etc.
  unit?: string;            // "%" default
  thresholds?: {
    warning: number;        // Yellow zone start (default: 50% of max)
    critical: number;       // Red zone start (default: 80% of max)
  };
  size?: number;            // Diameter in pixels (default: 150)
}
```

**Implementation:** Custom SVG arc
- Semi-circle (180 degrees)
- Three color zones: green → yellow → red
- Current value indicator (thick arc overlay)
- Center text: current value (large) + max value (small)
- Animated on mount (arc draws to current value)

**Acceptance Criteria:**
- [ ] Gauge renders with correct proportions
- [ ] Color zones match thresholds
- [ ] Current value displayed prominently in center
- [ ] Max value shown as reference
- [ ] Animated arc on mount
- [ ] Responsive to container
- [ ] Theme-aware colors

---

## SECTION 7.5: POLISH & DEPLOYMENT
*Estimated: 14 hours*

Final touches — error handling, loading states, responsive design, and production build.

### Task 7.5.1: Implement Global Error Handling
- [ ] **Status:** Not Started
- **Description:** Error boundaries, API error display, and offline detection
- **Dependencies:** [7.2.1-7.2.10]
- **Effort:** 2.5 hours
- **Tool:** Claude Code

**Features:**

1. **Error Boundary** — Catches React rendering errors
   ```typescript
   class ErrorBoundary extends React.Component {
     // Catches errors in child component tree
     // Shows: "Something went wrong" + error detail + "Reload" button
     // Logs error to console for debugging
   }
   ```

2. **API Error Display** — Consistent error UI for failed API calls
   - Network error: "Unable to connect to server. Check your connection."
   - 401: "Session expired. Please reload."
   - 500: "Server error. The team has been notified." (with retry button)
   - Show in a GlassCard with warning styling

3. **Offline / Disconnected Detection** — Banner when backend unreachable or SSE drops
   - **Primary signal:** SSE connection status from `useEventStream` hook (Task 7.1.6)
     - `status === 'connected'` → no banner
     - `status === 'disconnected'` → show "Live connection lost. Reconnecting..." banner with amber styling
   - **Secondary signal:** REST health endpoint ping every 30 seconds (not 10s — reduced for cost)
     - If health ping also fails → escalate to "Connection lost. Data may be stale." banner with red styling
   - Automatically hides when SSE reconnects or health ping succeeds
   - SSE reconnection attempt count shown: "Reconnecting (attempt 3)..."

4. **Stale Data Indicator** — When SSE is disconnected and data may be outdated
   - Small "Last updated: X minutes ago" text on cards driven by SSE (kill switch, positions, risk)
   - Yellow tint on stale cards (> 30 seconds since last SSE event or successful fetch)
   - Red tint on very stale cards (> 2 minutes)
   - Tier 2 REST-polled data (dashboard summary, equity curve) shows stale indicator based on last successful fetch time

**Acceptance Criteria:**
- [ ] Error boundary catches rendering crashes
- [ ] API errors show user-friendly messages
- [ ] Disconnection banner appears when SSE drops (within 30s — first missed heartbeat)
- [ ] Offline banner escalates when REST health check also fails
- [ ] Banners auto-hide when SSE reconnects
- [ ] Stale data visually indicated on cards that haven't updated
- [ ] Retry mechanisms for transient errors
- [ ] No unhandled promise rejections in console

---

### Task 7.5.2: Implement Loading States & Skeletons
- [ ] **Status:** Not Started
- **Description:** Polished loading experience for all pages and components
- **Dependencies:** [7.1.2, 7.2.1-7.2.10]
- **Effort:** 2.5 hours
- **Tool:** Antigravity (skeleton visuals) → Claude Code (loading logic)

**Loading patterns:**

1. **Initial Page Load** — Full skeleton layout matching page structure
   - Cockpit: 6 skeleton MetricCards + skeleton table + skeleton cards
   - Portfolio: skeleton chart + skeleton heatmap
   - Each skeleton matches the shape of the real component

2. **Refresh/Polling** — No skeletons, data updates in-place
   - Previous data shown while refetching
   - No "flash" of loading state on refetch

3. **Action Loading** — Button loading state
   - Spinner replaces button text
   - Button disabled during action
   - Success/error toast after completion

4. **Progressive Loading** — Components load independently
   - Hero metrics load first (fastest)
   - Charts load after (slower)
   - No component blocks another

**Acceptance Criteria:**
- [ ] Every page has a matching skeleton layout
- [ ] Skeletons match real component shapes
- [ ] No layout shift when data loads (skeletons are same size)
- [ ] Polling doesn't show skeletons (previous data persists)
- [ ] Buttons show loading spinner during actions
- [ ] Components load independently (no waterfall)

---

### Task 7.5.3: Implement Responsive Design
- [ ] **Status:** Not Started
- **Description:** Ensure dashboard works on desktop (1920px), laptop (1366px), and tablet (768px)
- **Dependencies:** [7.2.1-7.2.10]
- **Effort:** 3 hours
- **Tool:** Claude Code

**Breakpoint targets:**
| Screen | Width | Sidebar | Content Grid | Behavior |
|--------|-------|---------|-------------|----------|
| Desktop | ≥1440px | 280px expanded | 3-4 columns | Full layout |
| Laptop | 1024-1439px | 280px expanded | 2-3 columns | Full layout |
| Tablet | 768-1023px | 80px collapsed (icons) | 2 columns | Compact |
| Mobile | <768px | Hidden (hamburger) | 1 column | Stack everything |

**Key responsive adjustments:**
- MetricCards: 4 per row → 2 per row → 1 per row
- Positions table: horizontal scroll on small screens
- Charts: reduce height, simplify tooltips
- Modals: full-screen on mobile
- Sidebar: auto-collapse on tablet, hidden on mobile with hamburger

**Acceptance Criteria:**
- [ ] Dashboard usable at 1920px, 1366px, 768px
- [ ] Sidebar responsive (expanded → collapsed → hidden)
- [ ] Grid layouts adapt to screen width
- [ ] Charts resize without breaking
- [ ] Tables scroll horizontally on small screens
- [ ] Modals adapt to screen size
- [ ] No horizontal page scroll at any breakpoint

---

### Task 7.5.4: Frontend Build & Deployment Config
- [ ] **Status:** Not Started
- **Description:** Production build optimization and deployment integration
- **Dependencies:** [7.2.1-7.5.3]
- **Effort:** 2 hours
- **Tool:** Claude Code

**Build configuration:**

1. **Vite production config:**
   ```typescript
   // vite.config.ts
   export default defineConfig({
     build: {
       outDir: 'dist',
       sourcemap: true,
       rollupOptions: {
         output: {
           manualChunks: {
             vendor: ['react', 'react-dom', 'react-router-dom'],
             charts: ['recharts'],
             motion: ['framer-motion'],
           },
         },
       },
     },
   });
   ```

2. **FastAPI serves built frontend:**
   ```python
   # In production, serve frontend files
   from fastapi.staticfiles import StaticFiles
   app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
   ```

3. **Environment variable handling:**
   - `VITE_API_URL` for API base URL (defaults to relative `/api/v1`)
   - SSE endpoint uses same base URL: `${VITE_API_URL}/events/stream`
   - Build-time variable injection

4. **Docker integration:**
   ```dockerfile
   # Frontend build stage
   FROM node:18 AS frontend
   WORKDIR /app/frontend
   COPY frontend/package*.json ./
   RUN npm ci
   COPY frontend/ .
   RUN npm run build
   
   # Backend stage
   FROM python:3.11-slim
   COPY --from=frontend /app/frontend/dist /app/frontend/dist
   # ... rest of backend setup
   ```

5. **Vite dev proxy — must handle SSE stream:**
   ```typescript
   // vite.config.ts — server section
   server: {
     proxy: {
       '/api': {
         target: 'http://localhost:8000',
         changeOrigin: true,
       },
       // SSE endpoint needs special handling — no response buffering
       '/api/v1/events/stream': {
         target: 'http://localhost:8000',
         changeOrigin: true,
         // Disable response buffering for SSE
         configure: (proxy) => {
           proxy.on('proxyRes', (proxyRes) => {
             proxyRes.headers['X-Accel-Buffering'] = 'no';
             proxyRes.headers['Cache-Control'] = 'no-cache';
           });
         },
       },
     },
   }
   ```

6. **Bundle analysis (dev dependency):**
   - Install `rollup-plugin-visualizer` as dev dependency
   - Add `npm run analyze` script that builds with visualization output
   - Use to verify chunk sizes and identify unexpected large imports

**Acceptance Criteria:**
- [ ] `npm run build` produces optimized bundle
- [ ] Code splitting: vendor, charts, motion in separate chunks
- [ ] Lazy-loaded pages: Backtest, Settings, Portfolio (loaded on route visit)
- [ ] Source maps generated for debugging
- [ ] FastAPI serves frontend at root `/`
- [ ] API calls work in production (same-origin, no CORS issues)
- [ ] SSE stream works through Vite dev proxy (no buffering)
- [ ] SSE stream works in production (same-origin via FastAPI static mount)
- [ ] Initial bundle < 300KB gzipped (before lazy chunks)
- [ ] Total bundle (all chunks) < 500KB gzipped
- [ ] Docker multi-stage build works
- [ ] Environment variables inject correctly
- [ ] `npm run analyze` produces bundle visualization report

---

## 📋 PHASE 7 COMPLETION CHECKLIST

Before declaring the Investor Cockpit complete, verify:

### Foundation
- [ ] All 32 tasks completed
- [ ] Design system renders correctly (colors, fonts, glass-panels)
- [ ] Light and dark mode work
- [ ] All 5 accent themes work
- [ ] API client connects to all backend endpoints
- [ ] SSE event stream connects and receives real-time updates
- [ ] SSE reconnects automatically with backoff on disconnect

### Core Pages
- [ ] Cockpit page shows all 6 PRD §6.2.2 widgets with real data
- [ ] Portfolio page shows equity curve, heatmap, histogram (PRD §6.3)
- [ ] Strategy list page shows all strategies with filters
- [ ] Strategy detail page has all 7 PRD §6.4 sections
- [ ] Risk page shows gauges, circuit breakers, kill switch, and kill switch audit history
- [ ] Accounts page shows accounts with risk profiles
- [ ] Orders page shows order history with filters
- [ ] Alerts page shows alert history with acknowledgment
- [ ] Settings page controls theme and preferences
- [ ] Backtest page runs and displays backtest results

### Operational Features
- [ ] Kill switch activation/deactivation works from sidebar
- [ ] Kill switch deactivation requires typing "DEACTIVATE"
- [ ] Kill switch state updates instantly via SSE (no polling delay)
- [ ] Kill switch button uses `aria-live="assertive"` when active
- [ ] Market regime selector in header works
- [ ] Position close from dashboard works
- [ ] Notification bell with unread count works
- [ ] Keyboard shortcuts functional
- [ ] Toast notifications for all user actions

### Quality
- [ ] Loading skeletons on all pages
- [ ] Error states for failed API calls
- [ ] SSE disconnection banner with reconnect status
- [ ] Offline banner escalates when REST health check also fails
- [ ] Stale data indicators on SSE-driven and polled components
- [ ] Tier 2 REST polling stops when browser tab is hidden
- [ ] Responsive at 1920px, 1366px, 768px
- [ ] No console errors in normal operation
- [ ] Initial bundle < 300KB gzipped, total < 500KB gzipped
- [ ] Modal focus trapping works (Tab cycles within modal only)

### PRD Compliance
- [ ] §6.2.2: All dashboard widgets present
- [ ] §6.3.1: Equity curve with benchmark overlay
- [ ] §6.3.2: Monthly returns heatmap
- [ ] §6.3.3: Trade distribution histogram
- [ ] §6.4: Strategy detail with all 7 sections
- [ ] §7: Account management visible
- [ ] Feature B: Regime dropdown in dashboard header
- [ ] Kill switch accessible at all times

### Cost Optimization
- [ ] SSE replaces all high-frequency polling (kill switch, positions, alerts, risk, regime)
- [ ] Backend request volume < 6K requests/day per open dashboard tab (down from ~91K)
- [ ] Tier 2 REST polling uses relaxed intervals (30s-300s, not 3s-15s)
- [ ] Tier 3 on-demand hooks fetch once per page visit (no background polling)

**Sign-off:** _________________ Date: _________________

---

**Previous Phase:** [06_PHASE_6_BACKEND_INTEGRATION.md](./06_PHASE_6_BACKEND_INTEGRATION.md)  
**Return to:** [00_MVP_TASK_INDEX.md](./00_MVP_TASK_INDEX.md)  
**Design Reference:** [DESIGN_GUIDE.md](./design/DESIGN_GUIDE.md)
