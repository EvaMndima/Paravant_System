# Session-by-Session Execution Guide

## How to Use This Guide

Each session below is a self-contained unit of work. Copy the session prompt into a new Claude Code conversation. Each session should result in visually validated, committed code.

**Golden rule:** After each session, visually compare your result with the target PDF/screenshot. Do not proceed to the next session until the current one looks correct.

---

## Session 1: Clean Slate + Design Tokens
**Time:** ~1.5 hours
**Phase:** 0 + 1

**Prompt to use:**
```
I need to rebuild the PARAVANT frontend from scratch.

STEP 1: Delete the entire `frontend/` folder.

STEP 2: Create a new Vite + React + TypeScript project at `frontend/`.

STEP 3: Follow the EXACT setup instructions in `docs/design/phases/PHASE_0_CLEAN_SLATE.md`:
- Install dependencies (use Tailwind v3, not v4)
- Configure tailwind.config.js with the EXACT color system from `docs/design/references/index.html` lines 19-77
- Configure CSS variables in index.css from `docs/design/references/index.html` lines 82-188
- Configure fonts in index.html (Cinzel, Inter, JetBrains Mono)
- Set up path aliases (@/ -> src/)
- Create the verification App.tsx

STEP 4: Follow `docs/design/phases/PHASE_1_DESIGN_TOKENS.md`:
- Port `docs/design/references/lib/utils.ts` to `frontend/src/lib/utils.ts` (change imports to @/)
- Port `docs/design/references/lib/animations.ts` to `frontend/src/lib/animations.ts`
- Port `docs/design/references/contexts/ThemeContext.tsx` (change imports to @/)
- Port `docs/design/references/contexts/ToastContext.tsx` (change imports to @/)

STEP 5: Create a DevPage at `frontend/src/pages/DevPage.tsx` showing theme colors, font samples, and the dark mode toggle.

Verify everything works: fonts load, dark mode toggles, glass-panel renders correctly.
```

---

## Session 2: UI Primitives (Components 2.1-2.10)
**Time:** ~2 hours
**Phase:** 2 (first half)

**Prompt to use:**
```
Continue the PARAVANT frontend rebuild. The project is set up at `frontend/`.

PORT the following components from `docs/design/references/components/ui/` to `frontend/src/components/ui/`:

1. GlassCard.tsx — Port exactly, change imports from relative to @/
2. Badge.tsx — Port exactly
3. Skeleton.tsx — Port exactly
4. Logo.tsx — Port exactly (SVG wings + PARAVANT wordmark)
5. Avatar.tsx — Port exactly (image, fallback, status dot)
6. Button.tsx — CREATE based on patterns in the prototype (primary/secondary/danger/ghost/emergency variants, sm/md/lg sizes, rounded-xl)
7. Input.tsx — Port exactly
8. Toggle.tsx — Port exactly
9. Progress.tsx — Port exactly
10. Tooltip.tsx — Port exactly

Follow the specs in `docs/design/phases/PHASE_2_UI_PRIMITIVES.md`.

Create a barrel export at `frontend/src/components/ui/index.ts`.

Update DevPage to show all 10 components in a gallery layout. Each component should be shown in both light and dark mode variants.

CRITICAL: Do NOT "improve" or simplify the prototype styling. Port it as-is, only changing import paths.
```

---

## Session 3: UI Primitives (Components 2.11-2.20)
**Time:** ~2 hours
**Phase:** 2 (second half)

**Prompt to use:**
```
Continue the PARAVANT frontend rebuild.

PORT the remaining UI components from `docs/design/references/components/ui/` to `frontend/src/components/ui/`:

11. Tabs.tsx — Port exactly (animated indicator with layoutId)
12. Modal.tsx — Port exactly (backdrop blur, focus trap, escape close)
13. SearchInput.tsx — Port exactly (Cmd+K hint)
14. Dropdown.tsx — Port exactly (glass panel, divider support)
15. Toast.tsx — Port exactly (connect to ToastContext)
16. EmptyState.tsx — Port exactly
17. LoadingState.tsx — Port exactly
18. MetricCard.tsx — Port exactly (this is the signature component — title, value, trend, sparkline)
19. DataTable.tsx — Port from `docs/design/references/components/dashboard/DataTable.tsx`
20. ErrorBoundary.tsx — Port exactly

Update barrel export and DevPage to include all 20 components.

The MetricCard MUST match the cockpit.pdf design exactly:
- Label: text-xs font-mono font-bold uppercase tracking-widest
- Value: font-mono font-medium tracking-tighter tabular-nums text-3xl
- Trend arrow + percentage
- Sparkline zone at bottom

Compare with `docs/design/pdf/cockpit.pdf` metric cards.
```

---

## Session 4: Charts
**Time:** ~2 hours
**Phase:** 3

**Prompt to use:**
```
Continue the PARAVANT frontend rebuild.

PORT chart components from `docs/design/references/components/dashboard/charts/`:

1. SparklineChart — from SVGAreaChart.tsx or SparklineChart.tsx (lightweight SVG, NOT Recharts)
2. AreaChart — from AreaChart.tsx (Recharts, gradient fill, custom tooltip)
3. DonutChart — from DonutChart.tsx (Recharts PieChart, center text, legend)
4. BenchmarkChart — from BenchmarkChart.tsx (dual line, area fill)

Put them in `frontend/src/components/charts/` with barrel export.

Follow `docs/design/phases/PHASE_3_4_CHARTS_AND_LAYOUT.md` Phase 3 section.

Test: Place a SparklineChart inside a MetricCard to verify the sparkline zone works.
Test: Render an AreaChart with mock data matching the cockpit.pdf "PERFORMANCE" chart.
Test: Render DonutCharts matching system.pdf "CAPITAL ALLOCATION" section.
```

---

## Session 5: Layout Shell (Sidebar + Header)
**Time:** ~2.5 hours
**Phase:** 4
### Use Opus

**Prompt to use:**
```
Continue the PARAVANT frontend rebuild. This is the most important visual session.

PORT layout components:

1. Sidebar — from `docs/design/references/components/layout/Sidebar.tsx` to `frontend/src/components/layout/Sidebar.tsx`
   - Includes SidebarProvider, SidebarTrigger, ThemeToggle
   - Port EXACTLY as-is, changing imports to @/

2. Header — from `docs/design/references/components/layout/Header.tsx` to `frontend/src/components/layout/Header.tsx`
   - Port EXACTLY, temporarily mock the DashboardContext functions

3. Breadcrumbs — from `docs/design/references/components/layout/Breadcrumbs.tsx`
4. PageHeader — from `docs/design/references/components/layout/PageHeader.tsx`
5. Section — from `docs/design/references/components/layout/Section.tsx`
6. NotificationsPanel — from `docs/design/references/components/layout/NotificationsPanel.tsx`

7. MainLayout — CREATE at `frontend/src/components/layout/MainLayout.tsx`:
   - Compose Sidebar + Header + content area
   - Content: scrollable, max-w-[1440px], px-6

8. Set up React Router in App.tsx with routes to empty page placeholders.

VALIDATION: The shell must match these target screenshots:
- Expanded sidebar: `docs/design/screenshots/target/sidebar/expanded-sidebar.png`
- Collapsed sidebar: `docs/design/screenshots/target/sidebar/collaped-full-sidebar.png`
- Header: `docs/design/screenshots/target/header/header-cockpit.png`

Follow `docs/design/phases/PHASE_3_4_CHARTS_AND_LAYOUT.md` Phase 4 section.
```

---

## Session 6: Dashboard Components
**Time:** ~3 hours
**Phase:** 5

**Prompt to use:**
```
Continue the PARAVANT frontend rebuild.

PORT dashboard components from `docs/design/references/components/dashboard/`:

1. MarketTicker.tsx — horizontal scrolling price ticker
2. ActivityFeed.tsx — tabbed event feed
3. Watchlist.tsx — asset watchlist panel
4. PositionsTable.tsx — holdings table
5. MarketRegimePanel.tsx — regime assessment panel
6. StrategyCard.tsx — individual strategy card
7. StrategyGrid.tsx — grid of strategy cards with filters
8. EmergencyPanel.tsx — kill switch and emergency controls
9. AlertModal.tsx — create alert modal
10. PositionDrawer.tsx — position detail slide-out
11. ExportModal.tsx — export data modal

Put them in `frontend/src/components/dashboard/`.

Create a DashboardContext at `frontend/src/contexts/DashboardContext.tsx` (port from prototype) to manage modal/panel state.

Follow `docs/design/phases/PHASE_5_6_DASHBOARD_AND_PAGES.md` Phase 5 section.
```

---

## Session 7: CockpitPage
**Time:** ~1.5 hours
**Phase:** 6.1
### Use Opus

**Prompt to use:**
```
Continue the PARAVANT frontend rebuild.

BUILD the CockpitPage at `frontend/src/pages/CockpitPage.tsx`.

PORT from `docs/design/references/components/pages/CockpitPage.tsx`, adapting imports.

The page MUST match `docs/design/pdf/cockpit.pdf` EXACTLY. Use mock data:
- Net Liquidity: $994,272.52
- Day P&L: +$14,203.12 (+1.24%)
- Signals Today: 156 (+12%)
- Trades Today: 23 Executed
- 52 agents, 12 open positions, $4.8M deployed

Layout (top to bottom):
1. Alert banner (amber)
2. System Status header with LIVE badge
3. Market ticker
4. 4 MetricCards row
5. Status bar
6. Two-column: Performance chart + Agent Fleet Status
7. Curator Intelligence panel
8. Live Data tabs (System Activity / Positions / Allocation)
9. Watchlist (right column)

COMPARE with cockpit.pdf after building. Fix any visual differences.
```

---

## Sessions 8-13: Remaining Pages
**Time:** ~1-1.5 hours each

Follow the same pattern for each page:
- **Session 8:** SystemPage (match system.pdf)
- **Session 9:** PortfolioPage (match portfolio.pdf)
- **Session 10:** StrategiesPage (match agents PDF)
- **Session 11:** RiskPage (match risk management.pdf)
- **Session 12:** AlertsPage + TradeHistoryPage (match alerts.pdf + trade history.pdf)
- **Session 13:** SettingsPage + RegimePage (match settings/themes PDF + markets PDF)

For each session, use the prompt pattern:
```
Continue the PARAVANT frontend rebuild.

BUILD the [PageName] at `frontend/src/pages/[PageName].tsx`.
PORT from `docs/design/references/components/pages/[PageName].tsx`.
The page MUST match `docs/design/pdf/[target].pdf` EXACTLY.

Use mock data matching the PDF values.
Follow `docs/design/phases/PHASE_5_6_DASHBOARD_AND_PAGES.md` section 6.X.
```

---

## Session 14: Theme Validation
**Time:** ~1 hour
**Phase:** 7

```
Validate all 4 color themes (Ocean, Sapphire, Emerald, Onyx) work correctly.

Check the CockpitPage in:
- Ocean dark, Ocean light
- Sapphire dark, Sapphire light
- Emerald dark, Emerald light
- Onyx dark, Onyx light

Fix any theme-specific visual issues.
Reference: `docs/design/pdf/themes.pdf`
```

---

## Session 15: API Integration
**Time:** ~4-6 hours
**Phase:** 8
### Use Opus

```
Wire up the PARAVANT frontend to the real backend API.

Follow `docs/design/phases/PHASE_7_8_9_THEMES_API_POLISH.md` Phase 8.
Reference the API spec in `docs/07_PHASE_7_FRONTEND.md` Tasks 7.1.5 and 7.1.6.

1. Create API client at `frontend/src/lib/api.ts`
2. Create types at `frontend/src/types/api.ts`
3. Create React Query hooks per the tiered polling strategy
4. Create SSE hook `useEventStream`
5. Replace mock data in pages with real hooks
6. Add loading skeletons (Skeleton component already exists)
7. Add error states (ErrorBoundary already exists)
```

---

## Session 16: Polish & Deploy
**Time:** ~2 hours
**Phase:** 9

```
Final polish for the PARAVANT frontend:

1. Port keyboard shortcuts from `docs/design/references/hooks/useGlobalShortcuts.ts`
2. Validate responsive design at 1920/1366/768/375px
3. Configure production build (code splitting, chunk optimization)
4. Set up FastAPI to serve the built frontend
5. Verify SSE works through Vite proxy
6. Remove /dev route
7. Final visual sweep — compare every page with its PDF
```

---

## Tips for Success

1. **Always start dark mode** — The dark design is the primary design (it's what the PDFs mostly show)
2. **Use the prototype code as-is** — Don't "improve" it. If the prototype uses `bg-obsidian-300/60`, use exactly that
3. **One component at a time** — Build, validate, commit. Never batch
4. **Screenshots are your tests** — Take a screenshot after every component/page and compare with the PDF
5. **Mock data first** — Get visuals right before touching APIs
6. **Don't fight Tailwind** — If the prototype uses inline styles for something, keep them
