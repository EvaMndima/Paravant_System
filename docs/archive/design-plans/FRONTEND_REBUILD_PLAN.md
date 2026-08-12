# FRONTEND REBUILD PLAN — From Scratch

## Why the Previous Build Failed

After 2 weeks of iteration, the frontend looks nothing like the target design. Here's why:

### Root Causes
1. **Built from description, not from code** — The AI Studio prototype in `docs/design/references/` contains a COMPLETE working design system (22 UI components, 6 layout components, 12 full pages, 5 chart types, 3 contexts, 2 hooks). Previous attempts tried to recreate the design from scratch by interpreting markdown specs, instead of directly porting the working prototype code.

2. **Built pages before components** — Pages were attempted before individual components were visually validated. This created a cascade of broken styling.

3. **Too much at once** — Entire pages were built in single sessions. When something looked wrong, it was unclear which component caused the issue.

4. **Wrong Tailwind version handling** — Tailwind v4 config works differently than v3. The prototype uses CDN Tailwind v3 with a JS config. The production build needs to map this correctly.

5. **Data wiring mixed with styling** — API hooks, error states, and loading skeletons were built simultaneously with visual components. This made it impossible to validate visuals in isolation.

---

## The Solution: Port, Don't Recreate

The prototype in `docs/design/references/` IS the design. The plan:

1. **Delete `frontend/` entirely** and start fresh
2. **Create new Vite + React + TypeScript project**
3. **Port prototype CSS variables and Tailwind config** as the theme foundation
4. **Port each UI component from the prototype** — one at a time, adapting imports
5. **Port layout components** (Sidebar, Header) from the prototype
6. **Build pages** using the ported components, matching the PDF screenshots
7. **Wire up API data LAST** — only after pages look correct with mock data

---

## Implementation Phases

### Phase 0: Clean Slate (30 min)
- Delete `frontend/` folder completely
- Create fresh `npm create vite@latest frontend -- --template react-ts`
- Install exact dependencies
- Configure Tailwind, PostCSS, fonts
- Port CSS variables from prototype `index.html` lines 82-188
- Port Tailwind config (colors, fonts, animations)
- Verify: dark mode toggle works, fonts load, glass-panel utility works

### Phase 1: Design Tokens & Utilities (1 hour)
**Files to create (ported from prototype):**
- `src/lib/utils.ts` — from `docs/design/references/lib/utils.ts`
- `src/lib/animations.ts` — from `docs/design/references/lib/animations.ts`
- `src/contexts/ThemeContext.tsx` — from `docs/design/references/contexts/ThemeContext.tsx`

**Validation:** Create a test page showing all theme colors, font samples, and animation demos.

### Phase 2: UI Primitives — One Component at a Time (4-5 hours)
Each component is ported from `docs/design/references/components/ui/`.
Build order chosen by dependency chain (simplest first):

| # | Component | Source File | Depends On | Validation |
|---|-----------|-------------|------------|------------|
| 2.1 | GlassCard | `ui/GlassCard.tsx` | None | 4 variants render correctly |
| 2.2 | Badge | `ui/Badge.tsx` | None | All color variants |
| 2.3 | Skeleton | `ui/Skeleton.tsx` | None | Pulse animation works |
| 2.4 | Logo | `ui/Logo.tsx` | None | SVG wings + PARAVANT text |
| 2.5 | Avatar | `ui/Avatar.tsx` | None | Image, fallback, status dot |
| 2.6 | Button | (create new) | None | Primary, secondary, danger, ghost, emergency |
| 2.7 | Input | `ui/Input.tsx` | None | Glass styling, focus ring |
| 2.8 | Toggle | `ui/Toggle.tsx` | None | Smooth switch animation |
| 2.9 | Progress | `ui/Progress.tsx` | None | Animated fill |
| 2.10 | Tooltip | `ui/Tooltip.tsx` | None | Hover reveal |
| 2.11 | Tabs | `ui/Tabs.tsx` | None | Animated indicator |
| 2.12 | Modal | `ui/Modal.tsx` | GlassCard | Backdrop blur, enter/exit |
| 2.13 | SearchInput | `ui/SearchInput.tsx` | Input | Cmd+K hint |
| 2.14 | Dropdown | `ui/Dropdown.tsx` | None | Glass panel, hover effects |
| 2.15 | Toast | `ui/Toast.tsx` | None | Stack, auto-dismiss |
| 2.16 | EmptyState | `ui/EmptyState.tsx` | None | Icon + message |
| 2.17 | LoadingState | `ui/LoadingState.tsx` | Skeleton | Full-page skeleton |
| 2.18 | MetricCard | `ui/MetricCard.tsx` | GlassCard | Title, value, trend, sparkline |
| 2.19 | DataTable | `dashboard/DataTable.tsx` | GlassCard | Sortable, glass-panel |
| 2.20 | ErrorBoundary | `ui/ErrorBoundary.tsx` | GlassCard | Error recovery UI |

**Critical rule:** Do NOT proceed to Phase 3 until every component above renders correctly in BOTH light and dark mode. Create a `/dev` route that shows all components side by side for validation.

### Phase 3: Chart Components (2-3 hours)
Ported from `docs/design/references/components/dashboard/charts/`:

| # | Component | Source File | Validation |
|---|-----------|-------------|------------|
| 3.1 | SparklineChart | `charts/SparklineChart.tsx` or `SVGAreaChart.tsx` | Inline mini chart |
| 3.2 | AreaChart | `charts/AreaChart.tsx` | Gradient fill, tooltip |
| 3.3 | DonutChart | `charts/DonutChart.tsx` | Center text, legends |
| 3.4 | BenchmarkChart | `charts/BenchmarkChart.tsx` | Dual line overlay |

### Phase 4: Layout Shell (2-3 hours)
**This is where the "look" of the app comes together.**

| # | Component | Source File | Validation Screenshot |
|---|-----------|-------------|----------------------|
| 4.1 | Sidebar | `layout/Sidebar.tsx` | Match `screenshots/target/sidebar/expanded-sidebar.png` |
| 4.2 | Sidebar (collapsed) | Same file | Match `screenshots/target/sidebar/collaped-full-sidebar.png` |
| 4.3 | Header | `layout/Header.tsx` | Match `screenshots/target/header/header-cockpit.png` |
| 4.4 | Breadcrumbs | `layout/Breadcrumbs.tsx` | "Platform / Cockpit" format |
| 4.5 | PageHeader | `layout/PageHeader.tsx` | Cinzel title + subtitle + actions |
| 4.6 | Section | `layout/Section.tsx` | Content wrapper |
| 4.7 | MainLayout | Compose all | Full page with sidebar + header |

**Validation:** Navigate between empty pages. The shell should look exactly like the PDF sidebar/header. Take screenshots and compare with `docs/design/screenshots/target/`.

### Phase 5: Dashboard Components (3-4 hours)
Complex components used within pages:

| # | Component | Source File |
|---|-----------|-------------|
| 5.1 | MarketTicker | `dashboard/MarketTicker.tsx` |
| 5.2 | ActivityFeed | `dashboard/ActivityFeed.tsx` |
| 5.3 | Watchlist | `dashboard/Watchlist.tsx` |
| 5.4 | PositionsTable | `dashboard/PositionsTable.tsx` |
| 5.5 | MarketRegimePanel | `dashboard/MarketRegimePanel.tsx` |
| 5.6 | StrategyCard | `dashboard/StrategyCard.tsx` |
| 5.7 | StrategyGrid | `dashboard/StrategyGrid.tsx` |
| 5.8 | EmergencyPanel | `dashboard/EmergencyPanel.tsx` |
| 5.9 | NotificationsPanel | `layout/NotificationsPanel.tsx` |
| 5.10 | AlertModal | `dashboard/AlertModal.tsx` |
| 5.11 | PositionDrawer | `dashboard/PositionDrawer.tsx` |

### Phase 6: Pages — One at a Time (6-8 hours)
Each page is ported from `docs/design/references/components/pages/`.
**Every page uses MOCK DATA first** — no API calls.

| # | Page | Source File | Target PDF |
|---|------|-------------|------------|
| 6.1 | CockpitPage | `pages/CockpitPage.tsx` | `pdf/cockpit.pdf` |
| 6.2 | SystemPage | `pages/SystemPage.tsx` | `pdf/system.pdf` |
| 6.3 | PortfolioPage | `pages/PortfolioPage.tsx` | `pdf/portfolio.pdf` |
| 6.4 | StrategiesPage | `pages/StrategiesPage.tsx` | `pdf/agent page - renamed to strategies pages.pdf` |
| 6.5 | RiskPage | `pages/RiskPage.tsx` | `pdf/risk management.pdf` |
| 6.6 | AlertsPage | `pages/AlertsPage.tsx` | `pdf/alerts.pdf` |
| 6.7 | TradeHistoryPage | `pages/TradeHistoryPage.tsx` | `pdf/trade history.pdf` |
| 6.8 | SettingsPage | `pages/SettingsPage.tsx` | `pdf/system settings and menu to access and avatar.pdf` |
| 6.9 | RegimePage | `pages/RegimePage.tsx` | `pdf/markets - renames to regime in the real build.pdf` |

**Validation method:** After each page, take a screenshot and compare side-by-side with the PDF. Fix any visual discrepancies BEFORE moving to the next page.

### Phase 7: Theme Variants (1-2 hours)
Port from prototype's CSS variables:
- Ocean (default) — teal/green
- Sapphire — blue
- Emerald — green
- Onyx — gold/black
- Amethyst — purple (if in prototype)

Validate each theme on the Cockpit page in both light and dark mode.

### Phase 8: API Integration (4-6 hours)
**ONLY after all pages look correct with mock data:**
- Port/create API client (`src/lib/api.ts`)
- Create React Query hooks per Phase 7 spec
- Replace mock data with real hooks
- Add loading skeletons (components already built in Phase 2)
- Add error states (ErrorBoundary already built in Phase 2)
- SSE integration for real-time updates

### Phase 9: Polish & Deployment (2-3 hours)
- Responsive design validation at 1920px, 1366px, 768px
- Keyboard shortcuts
- Production build optimization
- Docker integration

---

## Execution Rules

### Rule 1: One Component Per Commit
Every component gets its own commit. Never batch multiple components.

### Rule 2: Visual Validation Before Moving On
- Each component must render correctly in BOTH light and dark mode
- Take screenshot, compare with PDF/prototype
- Fix discrepancies immediately, not later

### Rule 3: Mock Data First, Real Data Last
- Pages use hardcoded mock data matching the PDFs
- API integration is Phase 8 — after all visuals are validated
- This prevents data-fetching issues from blocking visual development

### Rule 4: Port, Don't Rewrite
- Copy prototype code, adapt imports, fix TypeScript types
- Do NOT "improve" or "simplify" the prototype styling
- The prototype styling IS the spec — match it exactly

### Rule 5: Dev Route for Component Gallery
- Create `/dev` route showing all components
- Use this for rapid visual validation
- Remove before production

---

## File Structure (Target)

```
frontend/
  src/
    components/
      ui/           # Phase 2: 20 UI primitives
      charts/        # Phase 3: 4 chart types
      layout/        # Phase 4: Sidebar, Header, MainLayout, etc.
      dashboard/     # Phase 5: Complex dashboard components
    pages/           # Phase 6: Full pages
    contexts/        # ThemeContext, ToastContext, DashboardContext
    hooks/           # useGlobalShortcuts, data hooks
    lib/             # utils.ts, animations.ts, api.ts
    types/           # TypeScript types for API responses
    App.tsx
    main.tsx
    index.css        # CSS variables, fonts, utilities
```

---

## Time Estimate

| Phase | Estimated Time | Description |
|-------|---------------|-------------|
| Phase 0 | 30 min | Clean slate, project setup |
| Phase 1 | 1 hour | Design tokens, utilities |
| Phase 2 | 4-5 hours | 20 UI components |
| Phase 3 | 2-3 hours | 4 chart components |
| Phase 4 | 2-3 hours | Layout shell (sidebar, header) |
| Phase 5 | 3-4 hours | 11 dashboard components |
| Phase 6 | 6-8 hours | 9 pages |
| Phase 7 | 1-2 hours | Theme variants |
| Phase 8 | 4-6 hours | API integration |
| Phase 9 | 2-3 hours | Polish & deployment |
| **Total** | **~26-35 hours** | |

---

## Key Design Specifications (From PDF Analysis)

### Typography
- **Page titles:** Cinzel, small-caps, 600 weight (e.g., "SYSTEM STATUS", "RISK MANAGEMENT")
- **Section headers:** Cinzel, small-caps, 500 weight (e.g., "CAPITAL ALLOCATION")
- **Body text:** Inter 400/500
- **Numbers/data:** JetBrains Mono 400/500, tabular-nums, tracking-tighter
- **Labels:** JetBrains Mono, uppercase, tracking-widest, 10-12px

### Color System (Ocean Theme)
- **Dark bg:** `#101413` (obsidian-400)
- **Dark card bg:** `#161918` (obsidian-300)
- **Light bg:** `#F8F5F2` (paper-100)
- **Accent:** `#2A9D8F` (turquoise/deep-teal)
- **Accent bright:** `#3DB9A9`
- **Gain:** `#2ECC71`
- **Loss:** `#E74C3C`
- **Warning:** `#F39C12`

### Glass-Morphism
- **Light cards:** `bg-paper-100/80 backdrop-blur-xl border border-deep-teal-800/10 shadow-lg`
- **Dark cards:** `bg-obsidian-300/60 backdrop-blur-xl border border-white/10 shadow-2xl`
- **Rounded corners:** `rounded-2xl`
- **Hover:** subtle scale(1.01) + translateY(-1px)

### Layout
- **Sidebar expanded:** 280px
- **Sidebar collapsed:** 80px
- **Header height:** 64px (h-16)
- **Content padding:** p-6 to p-8
- **Max content width:** ~1440px centered
- **Grid gaps:** gap-6

---

## Reference File Index

| What | Where |
|------|-------|
| Target PDFs (visual spec) | `docs/design/pdf/*.pdf` |
| Target screenshots | `docs/design/screenshots/target/` |
| AI Studio prototype code | `docs/design/references/` |
| Prototype UI components | `docs/design/references/components/ui/` |
| Prototype layout components | `docs/design/references/components/layout/` |
| Prototype dashboard components | `docs/design/references/components/dashboard/` |
| Prototype pages | `docs/design/references/components/pages/` |
| Prototype charts | `docs/design/references/components/dashboard/charts/` |
| Prototype CSS/theme | `docs/design/references/index.html` (lines 82-188) |
| Prototype contexts | `docs/design/references/contexts/` |
| Backend API spec (for Phase 8) | `docs/07_PHASE_7_FRONTEND.md` |
