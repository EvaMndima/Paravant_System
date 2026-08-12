# PARAVANT Dashboard — Frontend Project Context

**Version:** 2.0 (supersedes v1.0 of the same date — v1 was incomplete and wrong in
three places; see Section 13)
**Compiled:** 2026-08-08
**Source:** `frontend/` in the Paravant_System repository
**Purpose:** Complete self-contained briefing on the frontend, written so it can be
extracted into a standalone portfolio project. A reader with no access to the
original repository should finish this able to reason about the whole codebase and
present it honestly.

Every claim below was verified against the code. Commands are in Appendix C.

---

## 0. READ FIRST — two urgent items

### 0.1 3,086 lines are uncommitted

**26 modified files and 3 untracked files exist only on the local disk.** Not
committed, not pushed, not backed up.

```
26 files changed, 3,086 insertions(+), 144 deletions(-)
```

Untracked (a `git clean` deletes these permanently):

- `frontend/src/hooks/usePaperSessions.ts`
- `frontend/src/hooks/useRegimeState.ts`
- `frontend/src/pages/BacktestResultsPage.tsx`

Uncommitted page work by size:

| Page | Added | What was built |
|---|---|---|
| `SettingsPage.tsx` | +555 | Six tabs: Profile, Appearance, Notifications, Connections, Security, Help |
| `StrategiesPage.tsx` | +379 | Strategy grid, filters, status pipeline |
| `RegimePage.tsx` | +351 | Regime state, fear/greed, sector rotation, movers |
| `CockpitPage.tsx` | +341 | Ticker, watchlist, positions, activity, allocation |
| `SystemPage.tsx` | +328 | Strategy/decision/risk panels |
| `AlertsPage.tsx` | +325 | Price/risk/system alerts, history |
| `TradeHistoryPage.tsx` | +298 | Filterable trade table |
| `RiskPage.tsx` | +246 | Metrics, correlation matrix, concentration |
| `PortfolioPage.tsx` | +221 | Positions, allocation donut, 6-range equity curves |

Plus `App.tsx` (+77, routing/lazy loading), `DashboardContext.tsx` (+31),
`index.css` (+19), `Sidebar.tsx` (+16), and eight component files.

Frontend git history is only **7 commits** for 17,334 lines. Roughly a fifth of the
work has never been committed at all.

### 0.2 Provenance — the honesty issue that must be settled before publishing

**This frontend was ported from a Google AI Studio prototype, not designed from
scratch.** This is documented in the repository itself:

- `docs/design/DESIGN_GUIDE.md` is subtitled *"Extracted from AI Studio Prototype
  (January 2026)"*
- `docs/design/FRONTEND_REBUILD_PLAN.md` states plainly: *"The prototype in
  `docs/design/references/` IS the design"* and *"Port, Don't Recreate"*
- **73 prototype files are tracked in git** at `docs/design/references/`

The prototype already contained: all three contexts (Theme, Toast, Dashboard), the
CSS-variable four-palette theming system, `lib/animations.ts`, `lib/utils.ts`,
`types/index.ts`, 20 UI components, 6 layout components, 14 dashboard components,
5 charts, 11 pages, and 2 hooks.

Normalised diffs of ported components show 20-40% modification — genuinely adapted,
not copy-pasted, but unambiguously derivative.

**Why this matters:** if you present this as original design work and a reviewer
opens `docs/design/references/`, your credibility is gone — and the references
folder is committed, so it travels with the repo unless deliberately removed.

**The honest frame, which is still strong:** *"Ported and productionised an
AI-generated design prototype into a typed, routed, code-split React application —
then extended it with 18 new components, 4 new pages, and a real API layer."*
Hardening AI-generated scaffolding into production code is a current, in-demand
skill. Claiming you invented the palette is not.

Section 5 quantifies exactly what is yours.

---

## 1. Can this stand alone as a portfolio project?

**Yes, with the framing in 0.2.**

**What it genuinely is:** a production-quality frontend architecture for a complex
financial dashboard — 61 components, 13 pages, four palettes across light and dark,
code-split routing, coherent animation language. Builds clean in 41s.

**What it is not:** a working application. Three network calls total; every other
view renders hardcoded data. `PortfolioPage` generates equity curves with
`Math.sin() + Math.random()`.

**Two paths:**

1. **Design-system showcase** (~3-5 days). Keep mock data but label it. Add
   Storybook, component API docs, deployed static demo.
2. **Full standalone product** (~2-3 weeks). Add a mock API layer (MSW) so data flow
   is real end-to-end with synthetic data. Add tests. Fix the lint failures.

Path 2 is materially stronger for a frontend role, mainly because of the tests.

---

## 2. Technology stack

| Concern | Choice | Version | Notes |
|---|---|---|---|
| Framework | React | 19.2 | StrictMode enabled |
| Build | Vite | 7.3 | dev port 3000, `/api` proxy to :8000 |
| Language | TypeScript | 5.9 | `verbatimModuleSyntax: true` |
| Styling | Tailwind CSS | 3.4 | v3 deliberately — see 8.2 |
| Animation | framer-motion | 12.35 | incl. `MotionGlobalConfig` |
| Charts | Recharts | 3.8 | 303 KB chunk |
| Routing | react-router-dom | 6.30 | v7 future flags on |
| Server state | TanStack Query | 5.90 | **installed but never wired — see 7.5** |
| Icons | lucide-react | 0.577 | |
| Class utils | clsx + tailwind-merge | 2.1 / 3.5 | |
| Lint | ESLint 9 flat config | | **fails: 85 problems — see 9** |

**Scripts:** `dev` (vite), `build` (`tsc -b && vite build`), `lint` (`eslint .`),
`preview`.

**Scale:** 91 source files (80 `.tsx`, 11 `.ts`) plus `index.css`. 17,334 lines.

**External runtime dependency:** `index.html` loads Cinzel, Inter, and JetBrains Mono
from the Google Fonts CDN. Offline or CSP-restricted environments fall back to system
fonts and the design degrades noticeably. Worth self-hosting before deploying.

**`index.html` hardcodes `class="dark"` on `<html>`** so the app paints dark before
`ThemeContext` hydrates. Prevents a light flash for dark users; causes one for light
users.

---

## 3. Architecture

### 3.1 Provider composition (`App.tsx`)

```
ThemeProvider
  └── ToastProvider
        └── BrowserRouter (v7_startTransition, v7_relativeSplatPath)
              └── DashboardProvider
                    └── SidebarProvider
                          └── Suspense (LoadingState fallback)
                                └── Routes
```

**`main.tsx` is minimal** — `StrictMode` + `createRoot` only. No QueryClientProvider,
no error boundary at the root.

### 3.2 Routing

Every page is `lazy()`-loaded — genuine per-route code splitting, visible as separate
chunks in the build output.

| Path | Page | Layout |
|---|---|---|
| `/` | Cockpit | MainLayout |
| `/system` | System | MainLayout |
| `/strategies` | Strategies | MainLayout |
| `/portfolio` | Portfolio | MainLayout |
| `/regime` | Regime | MainLayout |
| `/risk` | Risk | MainLayout |
| `/alerts` | Alerts | MainLayout |
| `/trade-history` | Trade history | MainLayout |
| `/settings` | Settings | MainLayout |
| `/backtests` | Backtest results | MainLayout |
| `/dev`, `/dev2`, `/dev3` | Component galleries | none |
| `*` | redirect to `/` | — |

`MainLayout` is a nested layout route rendering sidebar + header + `<Outlet />`.

**Note:** `PlaceholderPage.tsx` exists in `src/pages/` but is not routed. Dead file.

### 3.3 Vite config

```ts
resolve.alias: { '@': resolve(import.meta.dirname, 'src') }
server: { port: 3000, proxy: { '/api': { target: 'http://localhost:8000' } } }
```

The dev proxy matters: `useBacktestResults` uses a **relative** `/api/v1/...` path
(works via proxy in dev, breaks in production without a reverse proxy), while the
other two hooks use an **absolute** `VITE_API_URL` base. This inconsistency will
cause a production bug. Unify on one approach.

### 3.4 Path aliasing

`@/` -> `src/`, configured in **both** `tsconfig.app.json` and `vite.config.ts`. The
Vite scaffold splits TS config — aliases go in `tsconfig.app.json`, not
`tsconfig.json`. Getting it wrong gives working editor resolution with a failing build.

---

## 4. Design system

### 4.1 Aesthetic direction

`docs/design/DESIGN_GUIDE.md` names it **"Quiet Luxury"** — restrained palette,
generous whitespace, serif display against clean sans, glass-morphism surfaces,
motion felt rather than noticed. Stated principles: precision over excitement, trust
through restraint, data density with clarity.

**Origin: the AI Studio prototype.** See 0.2.

### 4.2 Theming architecture

Four palettes, each light and dark, driven by CSS custom properties.

**Layer 1 — CSS variables as raw RGB triplets** (`src/index.css`):

```css
:root {                        /* OCEAN, default */
  --accent-primary:   42 157 143;
  --accent-highlight: 61 185 169;
  --accent-dim:       31 122 109;
  --accent-secondary: 15 61 62;
  --accent-dark:      10 40 41;
  --bg-light:         248 245 242;
  --bg-dark:          16 20 19;
  --bg-card-dark:     236 232 228;
  --bg-border:        15 61 62;
}

html.dark { --bg-card-dark: 22 25 24; --bg-border: 255 255 255; }

[data-theme="sapphire"]          { --accent-primary: 59 130 246; ... }
html.dark[data-theme="sapphire"] { --accent-primary: 96 165 250; --bg-dark: 2 6 23; ... }
```

Palettes: **ocean** (teal, default), **sapphire** (blue), **emerald** (green),
**onyx** (gold on black).

**Layer 2 — Tailwind consumes them with alpha support** (`tailwind.config.js`):

```js
'turquoise': {
  DEFAULT: 'rgb(var(--accent-primary) / <alpha-value>)',
  bright:  'rgb(var(--accent-highlight) / <alpha-value>)',
  dim:     'rgb(var(--accent-dim) / <alpha-value>)',
  glow:    'rgba(var(--accent-primary), 0.4)',
}
```

The `<alpha-value>` placeholder is what makes `bg-turquoise/20` resolve correctly
across all eight theme combinations. Without it you would need eight colour scales.

**Layer 3 — semantic colours are fixed, deliberately not themed:**
`gain` `#2ECC71`, `loss` `#E74C3C`, `warning` `#F39C12`, `info` `#3498DB`.
A themeable "loss" colour is a usability bug in a financial interface.

**Switching:** `ThemeContext` writes `data-theme` to `<html>` for palette and toggles
the `dark` class for mode. Modes: light / dark / **system**.

### 4.3 `glass-panel` utility

```css
.glass-panel {
  @apply bg-paper-100/80 dark:bg-obsidian-300/60 backdrop-blur-xl
         border border-deep-teal-800/10 dark:border-white/10
         shadow-lg dark:shadow-2xl;
}
```

### 4.4 The light-mode remapping trick

```css
html:not(.dark) .text-paper-100 { color: rgb(16 20 19); }
html:not(.dark) .bg-obsidian-300 { background-color: rgb(236 232 228); }
```

The library was built dark-first, so components use `text-paper-100` (near-white) for
primary text. Rather than adding `dark:` variants across 61 components, light mode
remaps semantic tokens at the utility layer. Trade-off: far fewer changes, at the cost
of indirection that makes a component look wrong when read in isolation.

### 4.5 Typography

Display: Cinzel / Playfair Display / serif. Body: Inter / system-ui / sans-serif.
Numeric: JetBrains Mono / Fira Code / monospace. Monospace for figures keeps columns
aligned as values change — the correct call for financial data.

### 4.6 Animation system (`src/lib/animations.ts`)

```ts
smoothSpring:      spring, stiffness 100, damping 15, mass 1
fadeInUp:          opacity 0->1, y 20->0
staggerContainer:  staggerChildren 0.08, delayChildren 0.1
scaleIn:           opacity 0 + scale 0.95 -> 1
hoverCard:         scale 1.02, y -4, 0.2s
```

Pages compose `staggerContainer` with `fadeInUp` children. One spring config
everywhere is what makes it feel like one product.

### 4.7 Other system touches

Custom scrollbars (8px, themed), `body.compact` density mode at 0.95em, Tailwind
keyframes (`fade-in`, `slide-up`).

---

## 5. What is ported versus original

This is the section to consult before writing any portfolio copy.

### 5.1 Ported from the prototype (~70%)

All three contexts, `lib/animations.ts`, `lib/utils.ts`, `types/index.ts`, the CSS
variable theming architecture including all four palettes, `compactMode`,
`reducedMotion` with `MotionGlobalConfig`, 20 UI components, 6 layout components,
14 dashboard components, all 5 chart components including `SVGAreaChart`, and 11 pages.

### 5.2 Genuinely added — 18 new components

**Dashboard (13):** `AlertRuleCard`, `BacktestResultsModal`, `DrawdownChart`,
`EquityChart`, `PnLSummaryStrip`, `RegimeTagSelector`, `RiskGauge`, `SettingsForm`,
`StrategyConfigModal`, `StrategyDetailDrawer`, `SystemStatusBar`, `TradeDetailModal`,
`TradeHistoryTable`

**UI (3):** `DateRangePicker`, `Pagination`, `Select`

**Layout (1):** `MainLayout`

**Charts (1):** `SizedResponsiveContainer`

### 5.3 Genuinely added — architecture

- **React Router with `lazy()` code splitting.** The prototype switched views with
  `useState('Cockpit')` and no routing at all. This is a real architectural upgrade:
  URLs, deep linking, browser history, per-route chunks.
- **`MainLayout` as a nested layout route.**
- **Tailwind v3 build pipeline.** The prototype used CDN Tailwind with a JS config.
- **TypeScript strictness** — `verbatimModuleSyntax`, path aliases, typed barrels.
- **The light-mode utility remap** (4.4).
- **The 300ms drawer-close delay** in `DashboardContext` so exit animations complete
  before content clears. Verified absent from the prototype.

### 5.4 Genuinely added — pages and data

**4 new pages:** `BacktestResultsPage`, `DevPage`, `Dev2Page`, `Dev3Page`.

**3 new API hooks** — all the real ones: `useRegimeState`, `usePaperSessions`,
`useBacktestResults`.

**Dropped from the prototype:** `JournalPage`, `NotificationsPage`,
`StrategyDetailPage`, `InviteUserModal`, `OrderEntryModal`, `useGlobalShortcuts`.

---

## 6. Component inventory — 61 components

### 6.1 `components/ui/` — 24 primitives

`Avatar`, `Badge`, `Button`, `DataTable`, `DateRangePicker`, `Dropdown`,
`EmptyState`, `ErrorBoundary`, `GlassCard`, `Input`, `KeyboardShortcuts`,
`LoadingState`, `Logo`, `MetricCard`, `Modal`, `Pagination`, `Progress`,
`SearchInput`, `Select`, `Skeleton`, `Tabs`, `Toast`, `Toggle`, `Tooltip`

Core prop APIs (needed to write any code against this library):

```ts
GlassCardProps extends HTMLMotionProps<"div"> {
  variant?: 'default' | 'elevated' | 'subtle' | 'dark';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  enableHover?: boolean;
}

ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'outline';
  size?: 'sm' | 'md';
  dot?: boolean;
  pulsing?: boolean;
}

MetricCardProps extends Omit<GlassCardProps, 'children' | 'padding'> {
  title: string; value: number; change?: number; changeLabel?: string;
  prefix?: string; suffix?: string; icon?: LucideIcon;
  format?: 'currency' | 'number' | 'percent' | 'raw';
  sparkline?: React.ReactNode; delay?: number;
}

DataTableProps<T> {
  columns: Column<T>[]; data: T[]; isLoading?: boolean;
  emptyMessage?: string; onRowClick?: (row: T) => void;
  stickyHeader?: boolean; className?: string;
}
// internal: SortConfig { key, direction: 'asc'|'desc'|null }

ModalProps {
  isOpen: boolean; onClose: () => void; title?: string; description?: string;
  size?: 'sm' | 'md' | 'lg' | 'full'; closeOnBackdropClick?: boolean;
}
```

`GlassCard`, `Button`, `Badge`, and `MetricCard` use `React.forwardRef` — correct for
a component library.

### 6.2 `components/dashboard/` — 24 domain components

`ActivityFeed`, `AlertModal`, `AlertRuleCard`, `BacktestResultsModal`,
`DrawdownChart`, `EmergencyPanel`, `EquityChart`, `ExportModal`,
`MarketRegimePanel`, `MarketTicker`, `PnLSummaryStrip`, `PositionDrawer`,
`PositionsTable`, `RegimeTagSelector`, `RiskGauge`, `SettingsForm`, `StrategyCard`,
`StrategyConfigModal`, `StrategyDetailDrawer`, `StrategyGrid`, `SystemStatusBar`,
`TradeDetailModal`, `TradeHistoryTable`, `Watchlist`

Largest: `BacktestResultsModal` (795), `EmergencyPanel` (483), `PositionDrawer` (366).

### 6.3 `components/charts/` — 6 components

`AreaChart` (Recharts), `SVGAreaChart` (hand-rolled SVG — **from the prototype**, but
substantially rewritten: 174 changed lines of ~250), `BenchmarkChart`, `DonutChart`,
`SparklineChart`, `SizedResponsiveContainer`.

### 6.4 `components/layout/` — 7 components

`MainLayout`, `Header`, `Sidebar` (with `SidebarProvider`), `NotificationsPanel`,
`Breadcrumbs`, `PageHeader`, `Section`.

Every category has a barrel `index.ts`. **No unused components** — verified: every
component is imported somewhere outside its own file and the barrels.

---

## 7. State, data, and types

### 7.1 `ThemeContext`

Palette, mode, `compactMode`, `reducedMotion`. Persists all four to localStorage.
`reducedMotion` sets `MotionGlobalConfig.skipAnimations` globally — a genuine
accessibility feature, wired to a `Toggle` in Settings > Appearance. **Ported from
the prototype**, but real and working.

### 7.2 `DashboardContext`

Coordinates every overlay from one place: emergency panel, alert modal, position
drawer, export modal, strategy viewer, settings tab navigation. All callbacks
`useCallback`-memoised. `closePositionDrawer` delays clearing state by 300ms for the
exit animation (original addition). Hook throws if used outside its provider — applied
consistently across all three contexts.

### 7.3 `ToastContext`

Typed notification queue.

### 7.4 Persistence — 6 localStorage keys

`themeMode`, `appTheme`, `compactMode`, `reducedMotion`, `sidebar-collapsed`,
`paravant_notif_sound`. No namespacing convention — five bare keys plus one
`paravant_`-prefixed. Worth unifying.

### 7.5 Hooks — and the TanStack Query problem

| Hook | Purpose | Real API? |
|---|---|---|
| `useRegimeState` | Polls `/api/v1/regime/current`, 60s | Yes |
| `usePaperSessions` | Polls `/api/v1/regime/paper-sessions`, 60s | Yes |
| `useBacktestResults` | Fetches `/api/v1/strategies/{id}/backtest/results` | Yes |
| `useRealtimeSimulation` | Client-side price drift | No — synthetic |

**`@tanstack/react-query` is installed but there is no `QueryClientProvider` anywhere
and no `useQuery` call anywhere in the codebase.** It is a dead dependency. Any
attempt to use it today throws "No QueryClient set". All three real hooks use raw
`fetch` with `useState`/`useEffect` and manual `AbortSignal` cancellation.

The polling hooks do map snake_case API responses to camelCase view models at the
boundary — a good pattern worth keeping when migrating to Query.

### 7.6 Type system — thin and drifting

`src/types/index.ts` is only 5 exports: `ThemeMode`, `AppTheme`, `ThemeContextType`,
`MetricCardProps`, `UserProfile`, `PortfolioPosition`.

**Three overlapping position types exist:**

- `PortfolioPosition` in `types/index.ts` (symbol, quantity, avgPrice, currentPrice,
  pnl, pnlPercent)
- `Position` in `components/dashboard/PositionsTable.tsx` (adds name, weight,
  assetType)
- `DashboardPosition` in `contexts/DashboardContext.tsx` (adds sector, avgCost,
  price, value)

None is canonical; pages import whichever is nearest. Also `MetricCardProps` is
declared in `types/index.ts` **and** redeclared more fully in `MetricCard.tsx`.
Consolidating these is a quick, visible quality win.

`DashboardPosition.assetType` includes `'Stock' | 'ETF' | 'Option' | 'Cash' | 'Crypto'`
— leftover from a generic investing prototype. The backend is crypto-only.

### 7.7 `lib/utils.ts` — complete contents

```ts
cn(...inputs)            // twMerge(clsx(inputs))
formatCurrency(value)    // Intl, USD, 2dp
formatPercent(value)     // Intl percent — DIVIDES BY 100 internally
formatNumber(value)      // Intl, max 2dp
getStaggerDelay(i, base) // i * base
```

**Footgun:** `formatPercent` divides by 100, so it expects `5.5` for "5.50%", not
`0.055`. Nothing enforces this and nothing documents it at call sites.

---

## 8. Constraints and gotchas

### 8.1 `verbatimModuleSyntax: true`

Every type-only import must use `import type` or it crashes at runtime with a
`SyntaxError` — the import is not erased and resolves to nothing.

```ts
// CORRECT
import type { Variants, Transition } from 'framer-motion';
import { type ToastData, useToast } from '@/contexts/ToastContext';

// WRONG — compiles, crashes in the browser
import { AppTheme } from '@/types';
```

### 8.2 Tailwind must stay on v3

Running **3.4** deliberately. An earlier build on v4 failed because
`darkMode: 'class'` is **ignored** in v4 — it defaults to
`@media (prefers-color-scheme: dark)`, handing dark mode to the OS instead of the
toggle. The v4 fix requires a CSS directive before `@tailwind base`:

```css
@custom-variant dark (&:is(.dark, .dark *));
```

The frontend was rebuilt on v3 rather than migrated. If you upgrade, this breaks
first and it breaks **silently** — the toggle just stops working.

### 8.3 Path aliases live in `tsconfig.app.json`

Not `tsconfig.json`. See 3.4.

### 8.4 Light mode depends on the utility remap

See 4.4. A component using `text-paper-100` looks wrong in isolation, correct in app.

### 8.5 Mixed API base-path strategy

See 3.3. One hook relies on the Vite dev proxy; two use `VITE_API_URL`. Production
will break one of them.

---

## 9. Code health — measured

### 9.1 Build: passes

`npm run build` succeeds in ~41s, no errors or warnings.
Main chunk 418 KB (gzip 133 KB); Recharts chunk 303 KB (gzip 93 KB).

### 9.2 Lint: fails — 85 problems in `src/` (82 errors, 3 warnings)

| Count | Rule |
|---|---|
| 46 | `react-hooks/static-components` |
| 14 | `react-hooks/set-state-in-effect` |
| 10 | `@typescript-eslint/no-explicit-any` |
| 6 | `react-refresh/only-export-components` |
| 4 | `react-hooks/exhaustive-deps` |
| 4 | `@typescript-eslint/no-unused-vars` |
| 1 | `react-hooks/refs` |
| 1 | `react-hooks/purity` |

**Two are genuine correctness bugs, not style:**

- `components/charts/DonutChart.tsx:191` — accessing a ref during render
- `components/dashboard/ExportModal.tsx:38` — calling an impure function during render

`react-hooks/static-components` (46) is components defined inside other components'
render bodies — they remount on every parent render, losing state and thrashing the
DOM. Concentrated in the Dev gallery pages but present in real pages too.

`react-hooks/set-state-in-effect` (14) is the classic `useEffect` -> `setState`
cascade causing double renders.

**ESLint config gap:** `eslint.config.js` only ignores `dist`, so `eslint .` also
lints `.vite/deps/` (the Vite dependency cache), inflating the count to 88 and
producing spurious "rule not found" errors. Add `.vite` to `globalIgnores`.

### 9.3 Tests: none

No Vitest, no React Testing Library, no Playwright, no test file of any kind.

### 9.4 Accessibility: partial, not absent

Measured across all `.tsx`: 17 `aria-label`, 2 `aria-selected`, 2 `aria-hidden`,
2 `aria-current`, 1 each of `aria-modal`, `aria-live`, `aria-haspopup`,
`aria-expanded`, `aria-checked`. 5 files use `role=`.

That is ~28 ARIA attributes across 61 components — thin but not zero. `aria-live` and
`aria-modal` in particular show intent. Not audited: focus traps, focus restoration on
close, tab order, contrast across all eight theme combinations.

**Genuine a11y wins already present:** `reducedMotion` honoured globally via
`MotionGlobalConfig.skipAnimations`, and `compactMode` for density.

### 9.5 Responsive: real coverage

Breakpoint usage: `sm` 34, `md` 33, `lg` 38, `xl` 2, `2xl` 0. Every page except the
unrouted `PlaceholderPage` uses responsive classes. Not verified on real devices, and
`xl`/`2xl` are essentially unused so very wide screens are untuned.

---

## 10. Honest gaps

| Gap | Severity for a frontend portfolio piece |
|---|---|
| Zero tests | **Critical.** Fastest possible rejection for a frontend role |
| Lint fails with 85 problems incl. 2 correctness bugs | **Critical.** Reviewers run `npm run lint` |
| Provenance not disclosed (Section 0.2) | **Critical.** Credibility risk if discovered |
| 3 real API calls; rest hardcoded | **High.** Fine if labelled, fatal if not |
| TanStack Query installed but never wired | High. Reads as cargo-culted dependency |
| Three overlapping position types | Medium |
| No accessibility audit | Medium-high for financial UI |
| `formatPercent` /100 footgun undocumented | Medium |
| Mixed API base-path strategy | Medium — will break in production |
| No CI | Medium |
| No frontend README | Medium |
| Google Fonts CDN dependency | Low-medium |
| `Dev`/`Dev2`/`Dev3` page names | Low, but reads unfinished |
| `PlaceholderPage` dead file | Low |

---

## 11. Extraction plan

**Step 0 — commit first.** Do not extract uncommitted work.

**Step 1 — decide the provenance story** before writing a line of README. Either
(a) include `docs/design/references/` and state plainly that you ported and
productionised an AI Studio prototype, or (b) exclude it and still say so. Option (a)
is stronger — it lets you show before/after and quantify the 18 new components and
the routing rewrite. Do **not** silently drop the folder and claim original design.

**Step 2 — copy `frontend/` to a new directory,** `git init` fresh. Bring
`docs/design/DESIGN_GUIDE.md` and this document. Leave behind
`docs/design/references/node_modules/`.

**Step 3 — fix lint to zero.** Add `.vite` to ignores, fix the two correctness bugs
first, hoist the 46 nested component definitions, resolve the 14 setState-in-effect
cascades. This is the highest-value cleanup and it is mostly mechanical.

**Step 4 — add tests.** Vitest + RTL. Priority: the three data hooks, `cn()` and the
formatters, `DataTable` sorting/pagination, `ThemeContext` palette+mode switching,
`Modal` focus behaviour. Moves the project further than anything else here.

**Step 5 — decide the data story.** MSW mock API (strong) or centralise all hardcoded
data into `src/mocks/` so it is visibly deliberate (acceptable). Wire
`QueryClientProvider` and migrate the three hooks to `useQuery` — this both removes
the dead dependency and makes the data layer real.

**Step 6 — consolidate types.** One canonical `Position`. Remove the
`Stock | ETF | Option` asset types. Document `formatPercent`.

**Step 7 — accessibility pass.** Focus traps in `Modal` and drawers, focus restoration
on close, ARIA on `DataTable` and `Tabs`, contrast across all eight theme
combinations. Then say in the README that you did it.

**Step 8 — rename Dev pages to `/showcase`.** 2,097 lines of apparent scratch work
becomes a hand-built component gallery — a feature, not debt.

**Step 9 — self-host fonts, unify the API base path, add CI, deploy to Vercel.**

**Step 10 — write the README** around the architecture work, not the visual design.
Rename the project so it reads as independent.

---

## 12. What to say about it

Accurate talking points, strongest first. Note these are **different** from a naive
list — several obvious-looking ones belong to the prototype, not to you.

1. **Porting an AI-generated prototype into production architecture.** The prototype
   switched views with `useState('Cockpit')`. You replaced that with React Router,
   nested layout routes, and `lazy()` code splitting — real URLs, deep linking,
   browser history, per-route chunks verifiable in the build output. This is the
   single most defensible piece of work and it is very current.
2. **Migrating CDN Tailwind to a real v3 build pipeline**, including diagnosing the
   v4 dark-mode breakage (`darkMode: 'class'` silently ignored, falls back to OS
   preference) and deciding to rebuild on v3 rather than migrate. Good failure story:
   root-cause diagnosis, deliberate trade-off.
3. **18 new components and 4 new pages** built into an existing design language
   without breaking it — including `DataTable` with generics, `Pagination`,
   `DateRangePicker`, and the whole backtest-results surface.
4. **Explaining the theming architecture you inherited and extended.** You can still
   discuss `<alpha-value>`, the fixed-semantic-colour decision, and the light-mode
   utility remap (which *is* yours) — as long as you attribute the base architecture.
5. **The 300ms drawer-close delay** so exit animations complete before state clears.
   Yours, verified absent from the prototype. Small, and interviewers remember it.
6. **Knowing what you did not build.** Naming the ported 70% before being asked is a
   strong signal. So is naming the gaps: no tests yet, lint failing, mock data,
   a11y unaudited.

**Do not claim:** original design of the palette system, the glass-morphism language,
`SVGAreaChart`, or the `EmptyState`/`LoadingState`/`Skeleton`/`ErrorBoundary`
primitives. All came from the prototype.

---

## 13. Corrections to v1.0 of this document

Recorded so nothing propagates:

1. **v1 omitted provenance entirely.** It implied the design system was original work
   and listed "the theming architecture" as the top talking point. Both wrong.
   See 0.2 and 5.
2. **v1 credited `SVGAreaChart` and the `EmptyState`/`LoadingState`/`Skeleton`/
   `ErrorBoundary` primitives as original.** All are from the prototype.
3. **v1 said accessibility was absent.** `reducedMotion` (via
   `MotionGlobalConfig.skipAnimations`) and `compactMode` are implemented and wired
   to Settings; ~28 ARIA attributes exist. It is thin, not absent.
4. **v1 did not report that lint fails** (85 problems, 2 correctness bugs) or that
   TanStack Query is a dead dependency with no provider.

---

## Appendix A — How to run it

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000, proxies /api -> http://localhost:8000
npm run build        # tsc -b && vite build
npm run lint         # currently fails
```

Environment: `VITE_API_URL` (optional; defaults to `http://localhost:8000`).
Without a backend, the three API-backed views show error/empty states; every other
page renders fine on hardcoded data.

## Appendix B — File map

```
frontend/
├── index.html                 Google Fonts CDN, hardcoded class="dark"
├── vite.config.ts             port 3000, /api proxy, @ alias
├── tsconfig.app.json          verbatimModuleSyntax, @ paths
├── tailwind.config.js         CSS-var colours, fonts, keyframes
├── eslint.config.js           flat config; only ignores dist
└── src/
    ├── main.tsx               StrictMode only — no QueryClientProvider
    ├── App.tsx                providers + lazy routes
    ├── index.css              4 palettes, glass-panel, light-mode remap
    ├── types/index.ts         5 exports; thin, drifting
    ├── lib/{utils,animations}.ts
    ├── contexts/{Theme,Toast,Dashboard}Context.tsx
    ├── hooks/                 3 real API + 1 synthetic
    ├── components/{ui,dashboard,charts,layout}/   61 components + barrels
    └── pages/                 13 pages + unrouted PlaceholderPage
```

## Appendix C — Reproducing this audit

```bash
git status --short frontend/
git diff --stat HEAD -- frontend/
git log --oneline -- frontend/ | wc -l
find frontend/src -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.css" \) -exec cat {} + | wc -l

cd frontend
npm run build
npx eslint src 2>&1 | tail -3
npx eslint . -f json | grep -o '"ruleId":"[^"]*"' | sort | uniq -c | sort -rn

grep -rn "QueryClient\|useQuery" src            # empty = dead dependency
grep -rno "aria-[a-z]*" src --include=*.tsx | sed 's/.*://' | sort | uniq -c
grep -rn "localStorage" src --include=*.tsx --include=*.ts

# Provenance
ls docs/design/references/components/ui/
git ls-files docs/design/references | grep -v node_modules | wc -l
diff <(sed 's/[[:space:]]//g' docs/design/references/components/dashboard/Watchlist.tsx) \
     <(sed 's/[[:space:]]//g' frontend/src/components/dashboard/Watchlist.tsx) | grep -c "^[<>]"
```
