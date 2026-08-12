# Phase 7: Themes + Phase 8: API Integration + Phase 9: Polish

## Phase 7: Theme Variants (1-2 hours)

### Goal
Validate all 4 color themes work correctly across all pages.

### Pre-requisite
Phase 6 complete (all pages rendering with mock data)

---

### 7.1 Theme Verification

The CSS variables are already set up from Phase 0. Now validate:

| Theme | Accent Color | Dark BG | Card BG |
|-------|-------------|---------|---------|
| Ocean (default) | Teal #2A9D8F | #101413 | #161918 |
| Sapphire | Blue #3B82F6 | #020617 | #0F172A |
| Emerald | Green #10B981 | #022C22 | #064E3B |
| Onyx | Gold #D4AF37 | #000000 | #0A0A0A |

### 7.2 Validation

For each theme, check:
1. Cockpit page in dark mode — accent colors update
2. Cockpit page in light mode — accent colors update
3. Sidebar active item uses accent color
4. MetricCard trend arrows use gain/loss (NOT accent)
5. Glass-panel borders use accent-derived opacity
6. Charts use accent colors
7. Settings page theme cards show current selection

### 7.3 Theme Screenshots

Reference: `docs/design/pdf/themes.pdf` pages 8-20 show all theme variants on multiple pages.

---

## Phase 8: API Integration (4-6 hours)

### Goal
Replace mock data with real API calls. This phase uses the backend API defined in Phase 6/7 of the backend.

### Pre-requisite
Phase 7 complete (all themes validated), Backend running on port 8000

---

### 8.1 API Client
**File:** `frontend/src/lib/api.ts`

Create typed API client matching `docs/07_PHASE_7_FRONTEND.md` Task 7.1.5:
- Base client with error handling
- Typed methods for each endpoint group (system, dashboard, strategies, accounts, risk, pnl, health)
- ApiError class

### 8.2 TypeScript Types
**File:** `frontend/src/types/api.ts`

Define types matching backend Pydantic models.

### 8.3 React Query Setup
**File:** `frontend/src/lib/queryClient.ts`

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
      refetchOnWindowFocus: false,
    },
  },
});
```

### 8.4 Data Hooks

Create hooks per `docs/07_PHASE_7_FRONTEND.md` Task 7.1.6:

**Tier 1 (SSE-driven, no polling):**
- `useKillSwitch()` — from SSE push
- `useSystemStatus()` — from SSE push
- `useRiskStatus()` — from SSE push
- `usePositions()` — invalidated by SSE
- `useAlerts()` — invalidated by SSE
- `useRegime()` — from SSE push

**Tier 2 (Slow REST polling):**
- `useDashboardSummary()` — 30s
- `useEquityCurve(range)` — 120s
- `useStrategies()` — 60s
- `usePnlHeatmap()` — 300s

**Tier 3 (On-demand, no polling):**
- `useStrategy(id)` — fetch on visit
- `useAccount(id)` — fetch on visit

### 8.5 SSE Event Stream
**File:** `frontend/src/hooks/useEventStream.ts`

Per Task 7.1.6 spec:
- Single EventSource connection
- Routes events into react-query cache
- Exponential backoff reconnect
- Connection status exposed for health banner

### 8.6 Wire Up Pages

Replace mock data in each page:
1. CockpitPage: `useDashboardSummary()`, `usePositions()`, `useStrategies()`, `useAlerts()`
2. PortfolioPage: `useEquityCurve()`, `usePnlHeatmap()`, `usePositions()`
3. StrategiesPage: `useStrategies()`
4. RiskPage: `useRiskStatus()`, `useKillSwitch()`
5. AlertsPage: `useAlerts()`
6. SystemPage: `useSystemStatus()`, `useRegime()`

### 8.7 Loading & Error States

- Each page shows Skeleton layout during initial load (components already built)
- ErrorBoundary wraps each page section
- API errors show user-friendly messages via ApiErrorDisplay component
- SSE disconnection shows amber banner

---

## Phase 9: Polish & Deployment (2-3 hours)

### 9.1 Responsive Design

Validate at:
- 1920px (desktop) — full layout
- 1366px (laptop) — slightly condensed
- 768px (tablet) — sidebar collapsed to icons
- 375px (mobile) — sidebar hidden, single column

### 9.2 Keyboard Shortcuts
**Source:** `docs/design/references/hooks/useGlobalShortcuts.ts` + `docs/design/references/components/ui/KeyboardShortcuts.tsx`

Port from prototype:
- G+H: Go to Cockpit
- G+S: Go to System
- G+P: Go to Portfolio
- Ctrl+K: Open search / kill switch
- Ctrl+/: Show shortcuts help
- Escape: Close modals
- D: Toggle dark mode

### 9.3 Production Build

**Vite config additions:**
```typescript
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
}
```

### 9.4 FastAPI Integration

Serve built frontend from FastAPI:
```python
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

### 9.5 SSE Proxy Config

Vite dev proxy for SSE:
```typescript
'/api/v1/events/stream': {
  target: 'http://localhost:8000',
  changeOrigin: true,
  configure: (proxy) => {
    proxy.on('proxyRes', (proxyRes) => {
      proxyRes.headers['X-Accel-Buffering'] = 'no';
      proxyRes.headers['Cache-Control'] = 'no-cache';
    });
  },
}
```

---

## Final Validation Checklist

### Visual
- [ ] All pages match PDF designs in dark mode
- [ ] All pages match PDF designs in light mode
- [ ] All 4 themes work correctly
- [ ] Glass-morphism effects visible on all cards
- [ ] Typography hierarchy correct (Cinzel / Inter / JetBrains Mono)
- [ ] Animations smooth (hover, transition, collapse)

### Functional
- [ ] All API endpoints connected
- [ ] SSE updates in real-time
- [ ] Kill switch works from sidebar/emergency panel
- [ ] Regime selector works
- [ ] Keyboard shortcuts work
- [ ] Search works
- [ ] Notifications panel works

### Responsive
- [ ] 1920px — no issues
- [ ] 1366px — no issues
- [ ] 768px — sidebar collapsed, content fills
- [ ] 375px — mobile layout, sidebar drawer

### Performance
- [ ] Initial bundle < 300KB gzipped
- [ ] No console errors in normal operation
- [ ] SSE reconnects on disconnect
- [ ] Polling stops when tab hidden
