# PARAVANT UI REFACTOR — COMPREHENSIVE TASK BREAKDOWN

**Created:** 2026-02-26
**Last Updated:** 2026-03-05
**Total Phases:** 5 (+ Phase 0 baseline)
**Total Tasks:** 37 main + 23 subtasks + 2 checkpoints + 3 baseline steps = 65 total
**Estimated Total Time:** 22–30 hours (Claude Code sessions)  
**Strategy:** Sand and polish the existing build to match the AI Studio prototype.  
**Rule:** Visual changes ONLY — no business logic modifications.  
**Validation:** See companion file `UI_REFACTOR_VALIDATION.md` for visual QA checklist.

**Reference Prototype Location:**  
`D:\Eva\Projects\Paravant_System\docs\design\references`

**Key Principle:** The current PARAVANT build has solid architecture (React Router, React Query hooks, SSE + tiered polling, Tailwind v4 themes). The AI Studio prototype has superior visual design. This plan bridges the gap by adopting the prototype's visual patterns while preserving the production system's data layer.

---

## 📊 PROGRESS TRACKER

> **Instructions:** After completing each task, update the status below AND run the corresponding validation checks from `UI_REFACTOR_VALIDATION.md`. Mark ✅ when done, 🔄 when in progress, ❌ if blocked, ⏭️ if skipped.

> **Validation companion:** [`08_UI_REFACTOR_VALIDATION.md`](./08_UI_REFACTOR_VALIDATION.md) — run after every phase completes before moving on. Contains per-phase visual QA checklists, before/after screenshot comparisons, and browser compatibility checks.

### Phase 0 — Baseline (3 steps)
| Step | Description | Status | Date | Blocker |
|------|-------------|--------|------|---------|
| 0.1 | Take baseline screenshots (dark + light + mobile, all 10 pages) | ⬜ | | |
| 0.2 | Open prototype reference files for side-by-side comparison | ⬜ | | |
| 0.3 | Verify dev environment: npm run dev, no console errors, theme toggle works | ⬜ | | |

### Phase 1 — Global Foundation (5 main + 1 subtask)
| Task | Description | Status | Date | Notes |
|------|-------------|--------|------|-------|
| 1.1 | Expand animations.ts | ✅ | 2026-03-05 | Added fadeInUp, staggerContainer, scaleIn, tapButton, snappySpring; smoothSpring softened to 100/15/1; hoverCard scale 1.02 y:-4 |
| 1.2 | Add missing utils | ✅ | 2026-03-05 | formatNumber already existed with a more capable signature (decimals param) — no change needed |
| 1.3 | Fix MainLayout spacing/scroll | ✅ | 2026-03-05 | overflow-y-auto + custom-scrollbar on main; p-4 md:p-8 lg:p-10 + w-full on inner; AnimatePresence page transitions added |
| 1.3a | Add global root styles (selection, font-sans) | ✅ | 2026-03-05 | text-obsidian-400 dark:text-paper-100, transition-colors duration-300, font-sans added to layout root div; ::selection was already in index.css |
| 1.4 | Create PageHeader component | ✅ | 2026-03-05 | Created PageHeader.tsx; exported from barrel index.ts |
| 1.5 | Align GlassCard variants | ✅ | 2026-03-05 | default dark:bg-obsidian-300/60 (was /80); subtle dark:bg-obsidian-400/50 (was obsidian-300/30) |

### Phase 2 — Component-Level Alignment (8 main + 10 subtasks)
| Task | Description | Status | Date | Notes |
|------|-------------|--------|------|-------|
| 2.1 | Upgrade Badge | ✅ | 2026-03-05 | Already matched spec from prior session — forwardRef, 6 translucent variants, dot/pulsing, rounded-full, font-mono |
| 2.1a | Create Avatar component | ✅ | 2026-03-05 | Created Avatar.tsx — forwardRef, 4 sizes, image+initials fallback, imageError state, status dot with glow, hover ring |
| 2.1b | Create Logo component | ✅ | 2026-03-05 | Created Logo.tsx — React.FC, 3-layer SVG wing paths, turquoise-bright, tracking-[0.15em] wordmark, showText prop |
| 2.1c | Create Progress component | ✅ | 2026-03-05 | Created Progress.tsx — forwardRef, motion.div width animation, smoothSpring, 4 glow variants, showLabel, animated prop |
| 2.2 | Upgrade Button | ✅ | 2026-03-05 | Already at proto spec; enhanced: aria-busy, cursor-wait on loading, useReducedMotion |
| 2.3 | Upgrade Input | ✅ | 2026-03-05 | Full rewrite: motion.div focus scale, glass bg-white/5, focus/error/success glows, password toggle, helperText, auto-linked label (useId+htmlFor), useReducedMotion |
| 2.3a | Upgrade Select with glass styling | ✅ | 2026-03-05 | dark:bg-white/5 glass bg; animated ChevronDown 180deg rotation on focus via motion.div |
| 2.3b | Upgrade Toggle to match proto | ✅ | 2026-03-05 | size sm/md with pixel dims, motion.button, animate-x thumb, Check/X icons in thumb via AnimatePresence, useReducedMotion |
| 2.4 | Create EmptyState | ✅ | 2026-03-05 | Created EmptyState.tsx — React.FC, 3 variants (default/search/error), auto-icons (Inbox/Search/AlertCircle), fadeInUp animation, action slot, min-h-[250px] |
| 2.4a | Upgrade Skeleton with variants | ✅ | 2026-03-05 | Added variant prop (text/circle/card/chart) with default dims; backward compatible (default='text' matches old behavior); className still overrides |
| 2.5 | Create LoadingState | ✅ | 2026-03-05 | Created LoadingState.tsx — 3 variants: inline (flex row + Loader2), section (min-h-200px centered), page (fixed inset-0 z-50, branded P badge, backdrop blur) |
| 2.6 | Upgrade Modal | ✅ | 2026-03-05 | createPortal, header/content glass zones, description prop, full size alias, aria-modal+role+labelledby, p-2.5 touch target, closeOnBackdropClick prop |
| 2.6a | Glass-style specialty Modals | ✅ | 2026-03-05 | KillSwitch: emoji→ShieldOff icon, warning banner, light-mode text tokens, textarea glass styling. PositionClose: full theme-aware compat, Button components, decel animation (was spring). Regime: cursor-pointer, focus-visible rings, textarea Input tokens, all dark-only tokens fixed |
| 2.7 | Upgrade MetricCard | ✅ | 2026-03-05 | Layout pivot 3-row→2-row; icon moved to header container (p-1.5 rounded-lg); trend column in value row (text-sm, w-4 h-4); min-h-[140px]; sparkline h-20 opacity-30/40; compact unchanged |
| 2.8 | Create Tooltip | ✅ | 2026-03-06 | Portal + createPortal, smoothSpring variants per side, backdrop-blur-xl, layered shadow with turquoise glow, inner glass sheen div, arrow w-2.5 rotate-45 |
| 2.8a | Create DonutChart component | ✅ | 2026-03-06 | Recharts PieChart, renderActiveShape hover +6px expand + inner ring, theme palette (all 5 AccentTheme incl. amethyst), motion fade-in on mount, synced legend hover, glass tooltip |
| 2.8b | Create BenchmarkChart component | ✅ | 2026-03-06 | Dual Area (solid portfolio + dashed benchmark), ReferenceLine at 0%, glass tooltip with tabular-nums + diff row, theme-aware accent, 1500ms animation |
| 2.8c | Create general AreaChart component | ✅ | 2026-03-06 | ChartErrorBoundary + SVG polyline fallback, 0.5 gradient opacity, visible YAxis, glow drop-shadow on stroke, all 5 AccentTheme mapped, empty data handled |
| 2.✓ | Barrel export verification checkpoint | ✅ | 2026-03-06 | ui/index.ts: Tooltip added. charts/index.ts: CREATED — exports all 8 chart components with types |

### Phase 3 — Page-by-Page Assembly (10 main + 7 subtasks)
| Task | Description | Status | Date | Notes |
|------|-------------|--------|------|-------|
| 3.1 | Cockpit hero metrics + status bar | ✅ | 2026-03-06 | CockpitHeader: plain typographic section (no GlassCard) matching reference — always renders (no isError collapse); "System Status" font-display text-4xl + turquoise span + LIVE pulse badge; agent/position/regime status line; 4 MetricCards in lg:grid-cols-4 (Net Liquidity + Day P&L variant="dark"); Export CSV + Emergency Ctrl buttons |
| 3.1a | Style ApiErrorDisplay glass | ✅ | 2026-03-06 | Glass container bg-paper-100/80 dark:bg-obsidian-300/60; w-16 h-16 rounded-2xl icon; iconColorClass per error type; Button component retry; fadeInUp animation; compact text tokens fixed |
| 3.2 | Cockpit positions + trades feed | ✅ | 2026-03-06 | Full Cockpit rewrite to match reference prototype: main grid xl:grid-cols-3 gap-6 items-start (was lg:); left col xl:col-span-2 space-y-6: PerformanceChartSection h-[420px] with BarChart3 glass header + LiveDataTabs (System Activity | Positions | Allocation with DonutChart); right col xl:col-span-1: FleetStatusPanel with Agent Fleet + RecentTradesFeed + CuratorIntelligence (decisions feed with timeline dots); root space-y-6 pt-2 pb-10 |
| 3.2a | Style DataTable with glass aesthetic | ✅ | 2026-03-06 | backdrop-blur-sm + border-b on thead; px-4 py-3 text-[10px] font-bold header cells; px-4 py-3 body cells; EmptyState component replaces custom Inbox div |
| 3.2b | Polish EquityCurveChart tooltip + tabs | ✅ | 2026-03-06 | isAnimationActive=true + 1500ms ease-in-out on both Area; gradient stopOpacity 0.25→0.40 equity / 0.4→0.30 drawdown; tabular-nums on tooltip values; inactive tabs now have light-mode tokens |
| 3.3 | Portfolio page layout | ⬜ | | |
| 3.3a | Style MonthlyHeatmap theme-aware | ⬜ | | |
| 3.3b | Style TradeDistributionHistogram | ⬜ | | |
| 3.4 | Risk page layout | ⬜ | | |
| 3.4a | Style GaugeChart glass + motion | ⬜ | | |
| 3.5 | Strategies page layout | ⬜ | | |
| 3.5a | Style StrategyStatusGrid | ⬜ | | |
| 3.6 | Strategy Detail page layout | ⬜ | | |
| 3.7 | Backtest page form styling | ⬜ | | |
| 3.8 | Orders page layout | ⬜ | | |
| 3.9 | Alerts page layout | ⬜ | | |
| 3.10 | Settings + Accounts pages | ⬜ | | |

### Phase 4 — Interaction Polish (6 main + 3 subtasks)
| Task | Description | Status | Date | Notes |
|------|-------------|--------|------|-------|
| 4.1 | Create Dropdown | ⬜ | | |
| 4.1a | Style Header glass alignment | ⬜ | | |
| 4.1b | Style Sidebar alignment + Logo | ⬜ | | |
| 4.2 | Create PositionDrawer | ⬜ | | |
| 4.3 | Upgrade MarketTicker | ⬜ | | |
| 4.3a | Style NotificationDropdown glass | ⬜ | | |
| 4.4 | Create ActivityFeed | ⬜ | | |
| 4.4a | Style ConnectionBanner + StaleDataIndicator | ⬜ | | |
| 4.5 | Upgrade Tabs | ⬜ | | |
| 4.6 | Create SearchInput | ⬜ | | |

### Phase 5 — Animation & Micro-Interaction Polish (8 main + 2 subtasks)
| Task | Description | Status | Date | Notes |
|------|-------------|--------|------|-------|
| 5.1 | Staggered MetricCard entry | ⬜ | | |
| 5.1a | Upgrade PageSkeletons + DashboardSkeleton | ⬜ | | |
| 5.2 | Chart draw animations | ⬜ | | |
| 5.3 | List item stagger | ⬜ | | |
| 5.4 | Toast slide animations | ⬜ | | |
| 5.5 | Hover/press micro-interactions | ⬜ | | |
| 5.6 | Page transition choreography | ⬜ | | |
| 5.7 | Reduced-motion support | ⬜ | | |
| 5.7a | Upgrade ErrorBoundary visual state | ⬜ | | |
| 5.8 | Final animation audit | ⬜ | | |

### Overall Progress
| Phase | Total | Done | % |
|-------|-------|------|---|
| Phase 0 | 3 | 0 | 0% |
| Phase 1 | 6 | 6 | 100% |
| Phase 2 | 19 | 19 | 100% |
| Phase 3 | 17 | 5 | 29% |
| Phase 4 | 10 | 0 | 0% |
| Phase 5 | 10 | 0 | 0% |
| **TOTAL** | **65** | **30** | **46%** |

### Blockers Log
> Add an entry here whenever a task is marked ❌ blocked. Resolve or escalate before moving to the next phase.

| ID | Phase | Task | Blocker Description | Resolution | Resolved Date |
|----|-------|------|---------------------|------------|---------------|
| — | — | — | No blockers yet | — | — |

---

## DEFINITION OF DONE

The refactor is **complete** when ALL of the following conditions are met:

- [ ] All 65 tasks marked ✅ (Phase 0 baseline + Phases 1–5)
- [ ] All 10 dashboard pages visually match the prototype reference (verified by screenshot comparison)
- [ ] Dark mode and light mode render correctly on every page
- [ ] Mobile responsive: 375px, 768px, and 1280px breakpoints pass visual checks
- [ ] Chrome DevTools Performance tab: no dropped frames on page transitions
- [ ] Framer Motion: no console warnings or errors in any browser
- [ ] React Query data hooks: zero new network requests introduced by visual changes
- [ ] All animations respect `prefers-reduced-motion` (Task 5.7 complete)
- [ ] Color contrast ratios maintained: body text >= 4.5:1, large text >= 3:1
- [ ] Keyboard navigation: all interactive elements remain focusable and operable
- [ ] `UI_REFACTOR_VALIDATION.md` checklist fully complete with after-screenshots attached

---

## SAFETY & ROLLBACK CHECKLIST

Run this checklist **before merging** any phase branch. If any item fails, do not merge — fix first.

### Before Starting Each Phase
- [ ] `git stash` or commit current work so you have a clean rollback point
- [ ] `npm run dev` launches without errors
- [ ] All pages load with data (or graceful mock fallback)
- [ ] Theme toggle (dark/light) works correctly
- [ ] No TypeScript compilation errors (`npm run build` passes)

### After Completing Each Phase
- [ ] All pages still load without console errors
- [ ] React Query hooks: open Network tab — confirm no new API calls were introduced
- [ ] Theme toggle still works (check both directions: dark→light, light→dark)
- [ ] Mobile view at 375px: no horizontal overflow, no broken layouts
- [ ] Screenshots match the `before/` baseline for unchanged pages

### Rollback Procedure (if something breaks)
```bash
# Option 1: Undo last commit (keeps changes staged)
git reset HEAD~1

# Option 2: Discard all changes since last commit
git checkout .

# Option 3: Stash current work and return to safe state
git stash
```

> If a task causes a regression that cannot be quickly fixed, mark it ❌ in the Blockers Log above, note the rollback commit hash, and skip to the next task. Revisit at the end of the phase.

---

## TWO-CODEBASE COMPARISON LEGEND

Throughout this document:  
- **[SYSTEM]** = Current PARAVANT system files (in project, uses `@/` imports, React Router, React Query)  
- **[PROTO]** = AI Studio prototype files (uploaded reference, uses local state + mock data, `../../lib/` imports)  
- **[GAP]** = What the system is missing vs the prototype  
- **[PROMPT]** = Exact Claude Code prompt to use for this task  

---

# PHASE 0 — BASELINE (Do this BEFORE any code changes)

**Time:** 15 min  
**No files to modify.**

Before touching any code, capture the current state of every page. This is your "before" reference for the entire refactor. Without this, you can't prove the refactor improved anything.

### Step 0.1 — Take baseline screenshots
1. Create folder: `docs/validation/screenshots/before/`
2. Run `npm run dev` and open the app
3. For each page (Cockpit, Portfolio, Risk, Strategies, StrategyDetail, Backtest, Orders, Alerts, Settings, Accounts):
   - Screenshot in **dark mode** at 1280px width
   - Screenshot in **light mode** at 1280px width
   - Screenshot in **dark mode** at 375px width (mobile)
4. Name files: `{page}-{theme}-{breakpoint}.png` (e.g., `cockpit-dark-desktop.png`)

### Step 0.2 — Print the prototype PDFs
Open each PDF in the project (`cockpit.pdf`, `portfolio.pdf`, `risk_management.pdf`, etc.) and keep them accessible for side-by-side comparison throughout the refactor.

### Step 0.3 — Verify dev environment
- `npm run dev` works without errors
- All pages load with data (or mock data)
- Theme toggle works (light ↔ dark)
- No console errors visible

> 📋 **After completing Phase 0:** You now have a baseline. Every phase validation will compare against these screenshots.

---

# PHASE 1 — GLOBAL FOUNDATION

**Goal:** Fix the shell, layout, and design token layer so every page inherits correct spacing, typography, and surface treatment before touching individual pages.  
**Tasks:** 5  
**Estimated Time:** 3–4 hours  
**Dependencies:** Phase 0 baseline screenshots taken.

---

### Task 1.1 — Expand animations.ts to match prototype library

**Time:** 15 min  
**Files to modify:** `src/lib/animations.ts`

**[SYSTEM] Current state:**
```ts
// 6 exports: smoothSpring, gentleFade, slideUp, slideDown, hoverCard, 
//            modalBackdropVariants, modalPanelVariants, getStaggerDelay
// smoothSpring: stiffness 300, damping 30 (snappier than proto)
// Missing: fadeInUp (Variants type), staggerContainer, scaleIn, tapButton
```

**[PROTO] Target state:**
```ts
// animations.ts exports:
// smoothSpring: { type: "spring", stiffness: 100, damping: 15, mass: 1 } — slower, more elegant
// fadeInUp: Variants — { initial: {opacity:0, y:20}, animate: {opacity:1, y:0}, exit: {opacity:0, y:-20} }
// staggerContainer: Variants — { animate: { transition: { staggerChildren: 0.08, delayChildren: 0.1 }}}
// scaleIn: Variants — { initial: {opacity:0, scale:0.95}, animate: {opacity:1, scale:1} }
// hoverCard: { scale: 1.02, y: -4, transition: { duration: 0.2 } }
// tapButton: { scale: 0.98 }
```

**[GAP]:**
- `smoothSpring` is too snappy (300/30) — prototype uses softer (100/15/1) for premium feel
- Missing `fadeInUp`, `staggerContainer`, `scaleIn` (Framer Motion `Variants` type) — needed by ActivityFeed, EmptyState, MetricCard stagger
- Missing `tapButton` — used by Button whileTap
- `hoverCard` scale too subtle (1.01) — prototype uses 1.02 with y:-4

**[PROMPT]:**
```
Refactor src/lib/animations.ts to expand the animation library. 

KEEP all existing exports (smoothSpring, gentleFade, slideUp, slideDown, 
hoverCard, modalBackdropVariants, modalPanelVariants, getStaggerDelay) 
but modify values and add new ones:

1. Change smoothSpring to: { type: "spring", stiffness: 100, damping: 15, mass: 1 }
   - Add a NEW export `snappySpring` with old values { type: "spring", stiffness: 300, damping: 30 }
     for cases where snap-back is desired (keep backward compat)

2. Add import: import { Variants, Transition } from 'framer-motion';

3. Add fadeInUp as Variants:
   initial: { opacity: 0, y: 20 }
   animate: { opacity: 1, y: 0, transition: smoothSpring }
   exit: { opacity: 0, y: -20, transition: { duration: 0.2 } }

4. Add staggerContainer as Variants:
   initial: {}
   animate: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } }

5. Add scaleIn as Variants:
   initial: { opacity: 0, scale: 0.95 }
   animate: { opacity: 1, scale: 1, transition: smoothSpring }

6. Change hoverCard to: { scale: 1.02, y: -4, transition: { duration: 0.2 } }

7. Add tapButton: { scale: 0.98 }

Do NOT change any other files. Only modify animations.ts.
Ensure all existing imports from other files still work.
```

**Acceptance Criteria:**
- [ ] `smoothSpring` is softer (100/15/1)
- [ ] `snappySpring` preserves old values for backward compat
- [ ] `fadeInUp`, `staggerContainer`, `scaleIn` are typed as `Variants`
- [ ] `tapButton` exported
- [ ] `hoverCard` uses scale 1.02, y -4
- [ ] No other files modified

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 1.2 — Add missing utility functions to utils.ts

**Time:** 10 min  
**Files to modify:** `src/lib/utils.ts`

**[SYSTEM] Current state:**
```ts
// Exports: cn, formatCurrency, formatPercent
```

**[PROTO] Target state:**
```ts
// Exports: cn, formatCurrency, formatPercent, formatNumber, getStaggerDelay
```

**[GAP]:**
- Missing `formatNumber` — formats numbers with commas, max 2 decimal places. Used in MarketTicker, MetricCard, PositionDrawer
- `getStaggerDelay` exists in animations.ts but prototype has it in utils.ts — keep in animations.ts (it's already there), just ensure it's re-exported or accessible

**[PROMPT]:**
```
Add the missing formatNumber function to src/lib/utils.ts:

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2,
  }).format(value);
}

Place it after the existing formatPercent function.
Do NOT modify any existing functions. Only add this new one.
```

**Acceptance Criteria:**
- [ ] `formatNumber` is exported
- [ ] Existing `cn`, `formatCurrency`, `formatPercent` unchanged

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 1.3 — Fix MainLayout content area spacing and scroll behavior

**Time:** 20 min  
**Files to modify:** `src/layouts/MainLayout.tsx`

**[SYSTEM] Current state:**
```tsx
<main className="flex-1 overflow-x-hidden">
  <div className="max-w-7xl mx-auto px-4 md:px-8 py-8">
    <ErrorBoundary>{children}</ErrorBoundary>
  </div>
</main>
```

**[PROTO] Target state (from App.tsx):**
```tsx
<div className="flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-8 lg:p-10 custom-scrollbar">
  <div className="max-w-7xl mx-auto w-full">
    <AnimatePresence mode="wait">
      <motion.div key={currentView}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        transition={{ duration: 0.2 }}
      >
        {renderView()}
      </motion.div>
    </AnimatePresence>
  </div>
</div>
```

**[GAP]:**
- Missing `overflow-y-auto` on main → scroll isn't contained, full-page scrollbar appears outside content area
- Missing responsive padding progression: `p-4 md:p-8 lg:p-10` (current has `px-4 md:px-8 py-8` — inconsistent x/y)
- Missing `custom-scrollbar` class
- Missing `w-full` on inner container
- Missing page transition animation (AnimatePresence + motion.div on route change)
- Current system uses React Router, not `useState` for routing, so page transitions need to wrap `<Outlet />` or `{children}`

**[PROMPT]:**
```
Refactor src/layouts/MainLayout.tsx to improve the content area layout and add page transitions.

Changes to the <main> element and its contents:

1. Change the main element to:
   <main className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">

2. Change the inner container to:
   <div className="max-w-7xl mx-auto w-full p-4 md:p-8 lg:p-10">

3. Wrap the ErrorBoundary children in page transition animation:
   - Import { motion, AnimatePresence } from 'framer-motion'
   - Import { useLocation } from 'react-router-dom'
   - Get location with: const location = useLocation();
   - Wrap children:
     <AnimatePresence mode="wait">
       <motion.div
         key={location.pathname}
         initial={{ opacity: 0, x: 20 }}
         animate={{ opacity: 1, x: 0 }}
         exit={{ opacity: 0, x: -20 }}
         transition={{ duration: 0.2 }}
       >
         <ErrorBoundary>{children}</ErrorBoundary>
       </motion.div>
     </AnimatePresence>

4. Add a CSS class for custom-scrollbar to the global CSS (or confirm it exists).
   The class should style scrollbar-width, webkit-scrollbar to be thin and themed:
   .custom-scrollbar { scrollbar-width: thin; scrollbar-color: rgba(42,157,143,0.3) transparent; }
   .custom-scrollbar::-webkit-scrollbar { width: 6px; }
   .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
   .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(42,157,143,0.3); border-radius: 3px; }

Keep everything else the same — do NOT change Sidebar, Header, 
ConnectionBanner, KeyboardShortcutsHelp, or ErrorBoundary logic.
```

**Acceptance Criteria:**
- [ ] Scrollbar is contained within main content area (not full page)
- [ ] Responsive padding: p-4 → md:p-8 → lg:p-10
- [ ] Page transitions animate on route change
- [ ] Custom scrollbar is thin and themed
- [ ] Sidebar and header remain fixed/sticky

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark Task 1.3 status and date.

---

### Task 1.3a — Add global root styles from prototype

**Time:** 5 min  
**Files to modify:** Root App component (e.g. `src/App.tsx` or `src/main.tsx`), global CSS

**[GAP]** The prototype's App.tsx wraps the entire app in a div with specific global styles that the system is missing:
- `selection:bg-turquoise-mist/30` — branded text selection highlight
- `font-sans` — ensures the custom font stack applies everywhere
- `text-obsidian-400 dark:text-paper-100` — base text color on root
- `transition-colors duration-300` — smooth theme transitions on root

**[PROMPT]:**
```
Add global root-level styles to match the prototype App.tsx.

1. Find the root wrapping div (in App.tsx or the layout root) and ensure it has:
   className="... bg-paper-100 dark:bg-obsidian-400 text-obsidian-400 dark:text-paper-100 transition-colors duration-300 font-sans selection:bg-turquoise-mist/30"

2. In the global CSS file (index.css or global.css), add if not present:
   ::selection { background: theme('colors.turquoise-mist / 0.3'); }

3. Verify the <html> element gets the dark class toggle 
   (this should already be handled by ThemeContext).

Do NOT change routing, providers, or any business logic.
```

**Acceptance Criteria:**
- [ ] Text selection everywhere uses turquoise-mist/30 tint
- [ ] Font-sans cascades to all elements by default
- [ ] Dark/light base text colors applied at root level
- [ ] Theme transition is smooth on toggle (300ms)

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark Task 1.3a status and date.

---

### Task 1.4 — Standardize page header pattern

**Time:** 20 min  
**Files to create:** `src/components/ui/PageHeader.tsx`

**[SYSTEM] Current state:** Each page implements its own header pattern inconsistently. Some use `<h1>`, some use `<div>`, spacing varies.

**[PROTO] Pattern (observed across all pages):**
```tsx
// Consistent pattern: title left, optional subtitle, actions right
<div className="flex items-center justify-between mb-8">
  <div>
    <h1 className="text-2xl font-display font-bold text-obsidian-400 dark:text-paper-100 tracking-tight">
      {title}
    </h1>
    {subtitle && (
      <p className="text-sm text-obsidian-400/60 dark:text-paper-100/60 mt-1">
        {subtitle}
      </p>
    )}
  </div>
  {actions && <div className="flex items-center gap-3">{actions}</div>}
</div>
```

**[PROMPT]:**
```
Create a new reusable PageHeader component at src/components/ui/PageHeader.tsx:

import React from 'react';
import { cn } from '@/lib/utils';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ 
  title, 
  subtitle, 
  actions, 
  className 
}) => {
  return (
    <div className={cn("flex items-center justify-between mb-8", className)}>
      <div>
        <h1 className="text-2xl font-display font-bold text-obsidian-400 dark:text-paper-100 tracking-tight">
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm text-obsidian-400/60 dark:text-paper-100/60 mt-1 font-sans">
            {subtitle}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-3">
          {actions}
        </div>
      )}
    </div>
  );
};

Then add it to the barrel export in src/components/ui/index.ts:
export { PageHeader } from './PageHeader';

Do NOT modify any existing page files yet — just create the component.
```

**Acceptance Criteria:**
- [ ] PageHeader component created with title, subtitle, actions props
- [ ] Uses font-display for title, font-sans for subtitle
- [ ] Exported from barrel file
- [ ] No existing files modified

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 1.5 — Align GlassCard variants with prototype

**Time:** 15 min  
**Files to modify:** `src/components/ui/GlassCard.tsx`

**[SYSTEM] Current state:** Has 8 variants (default, elevated, subtle, dark, kpi, chart, status, flat). The base 4 have slightly different opacity values than prototype.

**[PROTO] Target state:** Has 4 variants (default, elevated, subtle, dark) with these exact values:
```ts
default: "bg-paper-100/80 dark:bg-obsidian-300/60 backdrop-blur-xl border border-deep-teal-800/10 dark:border-white/10 shadow-lg"
elevated: "bg-paper-50/90 dark:bg-obsidian-300/80 backdrop-blur-2xl border border-deep-teal-800/10 dark:border-white/10 shadow-2xl"
subtle: "bg-paper-100/50 dark:bg-obsidian-400/50 backdrop-blur-md border border-deep-teal-800/5 dark:border-white/5"
dark: "bg-deep-teal-800/95 dark:bg-obsidian-400/90 text-paper-100 backdrop-blur-xl border border-white/10 shadow-xl"
```

**[GAP]:**
- `default` dark bg: system uses `obsidian-300/80`, proto uses `obsidian-300/60` (more transparent = more glass effect)
- `subtle` dark bg: system uses `obsidian-300/30`, proto uses `obsidian-400/50` (different base + opacity)
- Keep the extra system variants (kpi, chart, status, flat) since they serve production use cases

**[PROMPT]:**
```
Update src/components/ui/GlassCard.tsx to align the base 4 variant 
styles with the design prototype while keeping the extended variants.

Only change these two lines in the variants object:

1. default: change dark:bg-obsidian-300/80 to dark:bg-obsidian-300/60
   Full line: "bg-paper-100/80 dark:bg-obsidian-300/60 backdrop-blur-xl border border-deep-teal-800/10 dark:border-white/10 shadow-lg"

2. subtle: change dark:bg-obsidian-300/30 to dark:bg-obsidian-400/50
   Full line: "bg-paper-100/50 dark:bg-obsidian-400/50 backdrop-blur-md border border-deep-teal-800/5 dark:border-white/5"

Do NOT change elevated, dark, kpi, chart, status, or flat variants.
Do NOT change any other logic, props, or structure.
```

**Acceptance Criteria:**
- [ ] `default` variant dark bg is `obsidian-300/60`
- [ ] `subtle` variant dark bg is `obsidian-400/50`
- [ ] All 8 variants still exist
- [ ] No structural changes

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

# PHASE 2 — COMPONENT-LEVEL ALIGNMENT

**Goal:** Bring each shared UI primitive (Badge, Button, Input, Modal, MetricCard, etc.) to visual parity with the prototype. These are the building blocks every page uses.  
**Tasks:** 8  
**Estimated Time:** 4–5 hours  
**Dependencies:** Phase 1 complete

---

### Task 2.1 — Upgrade Badge component

**Time:** 15 min  
**Files to modify:** `src/components/ui/Badge.tsx`

**[SYSTEM] Current state:** Basic badge with variant colors. No `dot` or `pulsing` props. Uses `rounded-md` or similar. Limited size options.

**[PROTO] Target:**
- Pill shape: `rounded-full`
- Sizes: sm (`h-5 px-2 text-[10px] gap-1.5`), md (`h-6 px-2.5 text-xs gap-2`)
- Variants: success, warning, danger, info, neutral, outline — all with soft translucent backgrounds (`bg-gain/10 text-gain border-transparent`)
- Dot indicator: optional pulsing dot using `animate-ping`
- Font: `font-mono font-medium tracking-wide`

**[PROMPT]:**
```
Rewrite src/components/ui/Badge.tsx to match this exact specification.
Keep the existing import path and export name.

The component should:
- Accept props: variant ('success'|'warning'|'danger'|'info'|'neutral'|'outline'), 
  size ('sm'|'md'), dot (boolean), pulsing (boolean), className, children
- Use forwardRef<HTMLDivElement>
- Base classes: "inline-flex items-center justify-center rounded-full font-mono 
  font-medium tracking-wide border whitespace-nowrap transition-colors"
- Variant styles (all use translucent backgrounds):
  success: "bg-gain/10 text-gain border-transparent"
  warning: "bg-warning/10 text-warning border-transparent"
  danger: "bg-loss/10 text-loss border-transparent"
  info: "bg-info/10 text-info border-transparent"
  neutral: "bg-obsidian-400/5 text-obsidian-400 dark:bg-paper-100/10 dark:text-paper-100 border-transparent"
  outline: "bg-transparent text-obsidian-400 dark:text-paper-100 border border-obsidian-400/20 dark:border-paper-100/20"
- Size styles:
  sm: "h-5 px-2 text-[10px] gap-1.5"
  md: "h-6 px-2.5 text-xs gap-2"
- When dot=true, render a 1.5x1.5 dot before children
- When pulsing=true AND dot=true, add animate-ping overlay on the dot

Reference implementation is in the uploaded Badge.tsx prototype file.
Do NOT change the export name or file path.
```

**Acceptance Criteria:**
- [ ] Pills are `rounded-full`
- [ ] All 6 variants render with translucent backgrounds
- [ ] Dot with optional pulsing animation works
- [ ] Font is mono, medium weight, tracking-wide

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark Task 2.1 status and date.

---

### Task 2.1a — Create Avatar component

**Time:** 15 min  
**Files to create:** `src/components/ui/Avatar.tsx`

**[GAP]** The prototype has an Avatar component used in the Header (user profile), PositionDrawer, and Settings page. The system has no Avatar — it likely uses inline styles or nothing.

**[PROTO] Reference:** `Avatar.tsx` — initials fallback, image with error handling, status indicator (online/offline), 4 sizes (sm/md/lg/xl).

**[PROMPT]:**
```
Create src/components/ui/Avatar.tsx matching the prototype Avatar component.

Props interface:
  src?: string          // Image URL
  alt?: string          // Alt text
  name?: string         // For initials fallback ("John Doe" → "JD")
  size?: 'sm' | 'md' | 'lg' | 'xl'
  status?: 'online' | 'offline'
  className?: string

Implementation:
1. Size styles:
   sm: "h-8 w-8 text-[10px]"
   md: "h-10 w-10 text-xs"
   lg: "h-12 w-12 text-sm"
   xl: "h-16 w-16 text-base"

2. If src provided and no error → show <img> with rounded-full, object-cover
3. If no src OR image error → show initials div:
   - bg-turquoise-mist/20 dark:bg-turquoise-mist/30
   - text-turquoise-mist font-mono font-bold
   - Extract initials: name.split(' ').map(n => n[0]).slice(0,2).join('').toUpperCase()

4. Status indicator (if status prop):
   - Absolute positioned dot at bottom-right
   - online: "bg-gain" with ring-2 ring-paper-100 dark:ring-obsidian-400
   - offline: "bg-obsidian-400/30 dark:bg-white/30"

5. Use forwardRef pattern. Export from barrel index.

Do NOT modify any other files. Just create the component.
```

**Acceptance Criteria:**
- [ ] Shows image when src provided, initials when not
- [ ] Handles image load errors gracefully (falls back to initials)
- [ ] Status dot positioned correctly at all 4 sizes
- [ ] All sizes render at correct dimensions

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.1a status and date.

---

### Task 2.1b — Create Logo component

**Time:** 10 min  
**Files to create:** `src/components/ui/Logo.tsx`

**[GAP]** The prototype has a branded Logo component with an SVG wing symbol + "PARAVANT" wordmark. The system Sidebar likely uses plain text or no logo. This component is used in the Sidebar header.

**[PROTO] Reference:** `Logo.tsx` — SVG viewBox="0 0 100 100" with 3 layered wing paths at different opacities.

**[PROMPT]:**
```
Create src/components/ui/Logo.tsx matching the prototype Logo component.

Props:
  className?: string
  showText?: boolean (default: true)
  iconClassName?: string
  textClassName?: string

Implementation:
1. Flex container: "flex items-center gap-3 select-none"
2. SVG icon: viewBox="0 0 100 100", className "w-8 h-8 text-turquoise-bright"
   Three paths (wing shapes):
   Path 1: d="M20 85C20 85 35 80 45 65C55 50 85 20 85 20C85 20 60 35 45 55C30 75 20 85 20 85Z" opacity-90
   Path 2: d="M15 70C15 70 30 65 40 50C50 35 75 10 75 10C75 10 55 25 40 40C25 55 15 70 15 70Z" opacity-75
   Path 3: d="M10 55C10 55 25 50 35 35C45 20 65 0 65 0C65 0 45 15 30 30C15 45 10 55 10 55Z" opacity-60
   All paths: fill="currentColor"

3. Wordmark (when showText=true):
   <span className="font-sans font-bold text-xl tracking-[0.15em] text-obsidian-400 dark:text-paper-100">
     PARAVANT
   </span>

Export as named export. Do NOT modify other files.
```

**Acceptance Criteria:**
- [ ] SVG wing renders in turquoise-bright
- [ ] Wordmark shows/hides based on showText prop
- [ ] Visually matches prototype's Sidebar header

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.1b status and date.

---

### Task 2.1c — Create Progress component

**Time:** 15 min  
**Files to create:** `src/components/ui/Progress.tsx`

**[GAP]** The prototype has an animated Progress bar component used heavily in the Risk page (drawdown bars, limit usage). The system has no Progress component — Task 3.4 (Risk page) references it but it doesn't exist.

**[PROTO] Reference:** `Progress.tsx` — motion.div animated width, 4 color variants with glow shadows, sm/md sizes, optional percentage label.

**[PROMPT]:**
```
Create src/components/ui/Progress.tsx matching the prototype Progress component.

Props:
  value: number
  max?: number (default: 100)
  size?: 'sm' | 'md'
  variant?: 'default' | 'success' | 'warning' | 'danger'
  showLabel?: boolean (default: false)
  animated?: boolean (default: true)
  className?: string

Implementation:
1. Calculate percentage: Math.min(Math.max((value / max) * 100, 0), 100)

2. Track container:
   "flex-1 bg-obsidian-400/5 dark:bg-white/10 rounded-full overflow-hidden backdrop-blur-sm"
   Heights: sm="h-1.5", md="h-2.5"

3. Fill bar (motion.div):
   - initial={{ width: 0 }} animate={{ width: `${percentage}%` }}
   - transition: smoothSpring with duration 1.5
   - Variants with glow:
     default: "bg-turquoise-mist shadow-[0_0_12px_rgba(42,157,143,0.4)]"
     success: "bg-gain shadow-[0_0_12px_rgba(46,204,113,0.4)]"
     warning: "bg-warning shadow-[0_0_12px_rgba(243,156,18,0.4)]"
     danger: "bg-loss shadow-[0_0_12px_rgba(231,76,60,0.4)]"

4. Label (when showLabel=true):
   "font-mono text-xs font-medium text-obsidian-400/60 dark:text-paper-100/60 tabular-nums"
   Shows: Math.round(percentage) + "%"

5. Wrapper: "w-full flex items-center gap-3"

Use forwardRef. Import smoothSpring from animations.ts. Export from barrel index.
```

**Acceptance Criteria:**
- [ ] Bar animates from 0 to value on mount
- [ ] All 4 color variants render with glow shadows
- [ ] Label shows correct percentage when enabled
- [ ] Respects animated=false for instant render

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.1c status and date.

---

### Task 2.2 — Upgrade Button component with Framer Motion

**Time:** 20 min  
**Files to modify:** `src/components/ui/Button.tsx`

**[SYSTEM] Current state:** Standard HTML button with Tailwind classes. No Framer Motion animation. No loading state.

**[PROTO] Target:**
- Uses `motion.button` for hover scale/lift and tap press
- whileHover: `{ scale: 1.02, y: -1, transition: smoothSpring }` (when not disabled/loading)
- whileTap: `{ scale: 0.98 }` (when not disabled/loading)
- Loading state: spinner overlay with `Loader2` icon, content becomes invisible but maintains width
- Variants: primary (turquoise-mist bg, glow shadow), secondary (transparent + border), ghost (transparent), danger (loss bg)
- Sizes: sm (`h-8 px-3 text-xs`), md (`h-10 px-5 text-sm`), lg (`h-12 px-8 text-base`)
- leftIcon / rightIcon support
- `rounded-xl`, focus ring with `ring-turquoise-mist/50`

**[PROMPT]:**
```
Rewrite src/components/ui/Button.tsx to add Framer Motion micro-interactions 
and a loading state. Match the prototype specification exactly.

Key requirements:
1. Import motion from 'framer-motion' and Loader2 from 'lucide-react'
2. Import smoothSpring from '@/lib/animations'
3. Use motion.button as the root element
4. Add whileHover (scale 1.02, y -1) and whileTap (scale 0.98) — disabled when loading/disabled
5. Add isLoading prop — shows Loader2 spinner overlay, hides content but maintains width
6. Add leftIcon and rightIcon props (React.ReactNode)
7. Variant styles:
   primary: "bg-turquoise-mist text-white hover:shadow-[0_0_20px_rgba(42,157,143,0.4)] border border-transparent shadow-md shadow-turquoise-mist/20"
   secondary: "bg-transparent border border-turquoise-mist/50 text-deep-teal-800 dark:text-turquoise-mist hover:bg-turquoise-mist/10 hover:border-turquoise-mist"
   ghost: "bg-transparent border border-transparent text-obsidian-400 dark:text-paper-100 hover:bg-deep-teal-800/5 dark:hover:bg-white/5"
   danger: "bg-loss text-white border border-transparent hover:shadow-[0_0_20px_rgba(231,76,60,0.4)]"
8. Size styles:
   sm: "h-8 px-3 text-xs gap-1.5"
   md: "h-10 px-5 text-sm gap-2"
   lg: "h-12 px-8 text-base gap-2.5"
9. Base: "relative inline-flex items-center justify-center rounded-xl font-sans 
   font-medium tracking-wide transition-colors focus:outline-none 
   focus:ring-2 focus:ring-turquoise-mist/50 focus:ring-offset-2 
   dark:focus:ring-offset-obsidian-400 disabled:opacity-50 
   disabled:pointer-events-none select-none"

Keep the existing export name and forwardRef pattern.
Reference the uploaded Button.tsx prototype for the exact implementation.
```

**Acceptance Criteria:**
- [ ] Hover lift animation works
- [ ] Tap press animation works
- [ ] Loading spinner replaces content
- [ ] All 4 variants render correctly
- [ ] Icons render in correct positions

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 2.3 — Upgrade Input component with focus animations

**Time:** 20 min  
**Files to modify:** `src/components/ui/Input.tsx`

**[SYSTEM] Current state:** Basic input with label support. Dark mode styling may use stark white backgrounds that break theme.

**[PROTO] Target:**
- Wrapper uses `motion.div` with `animate={{ scale: 1.005 }}` on focus (subtle zoom)
- Background: `bg-paper-50 dark:bg-white/5` (glass-morphism compatible)
- Focus: `border-turquoise-mist ring-2 ring-turquoise-mist/20 shadow-[0_0_15px_rgba(42,157,143,0.15)]`
- Error: `border-loss ring-1 ring-loss/20 shadow-[0_0_15px_rgba(231,76,60,0.1)]`
- Password toggle with eye icon
- leftIcon / rightIcon support
- Validation/helper text with animated appearance
- Label: `text-xs font-sans font-medium text-obsidian-400/70 dark:text-paper-100/70`

**[PROMPT]:**
```
Rewrite src/components/ui/Input.tsx to match the prototype design with 
focus animations and glass-morphism dark mode styling.

Key changes:
1. Import motion from 'framer-motion' and smoothSpring from '@/lib/animations'
2. Import Eye, EyeOff, AlertCircle from 'lucide-react'
3. Track focus state with useState
4. Wrap the input container in motion.div that scales to 1.005 on focus
5. Background: "bg-paper-50 dark:bg-white/5" (NOT white/100 or paper-100)
6. Border states:
   - Normal: "border-deep-teal-800/10 dark:border-white/10"
   - Hover: "hover:border-deep-teal-800/20 dark:hover:border-white/20"
   - Focus: "border-turquoise-mist ring-2 ring-turquoise-mist/20"
   - Error: "border-loss ring-1 ring-loss/20"
7. Password type: toggle visibility with Eye/EyeOff icons
8. Support leftIcon and rightIcon props
9. Error/helper text animates in with motion.div

Reference the uploaded Input.tsx prototype for exact implementation.
Keep the existing export name, prop types, and forwardRef pattern.
```

**Acceptance Criteria:**
- [ ] Dark mode inputs use `bg-white/5` (not white backgrounds)
- [ ] Focus state shows turquoise ring + subtle glow
- [ ] Error state shows loss color ring
- [ ] Password toggle works
- [ ] Focus scale animation is subtle

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.3 status and date.

---

### Task 2.3a — Upgrade Select component with glass styling

**Time:** 10 min  
**Files to modify:** `src/components/ui/Select.tsx`

**[GAP]** The system's Select component uses basic Tailwind styling but doesn't match the glass aesthetic of the upgraded Input. It needs the same backdrop-blur, dark mode bg-white/5, focus glow, and label styling treatment.

**[PROMPT]:**
```
Upgrade src/components/ui/Select.tsx to match the glass styling of the Input component.

Current: Basic select with bg-paper-100/50 dark:bg-obsidian-400/50
Target: Match the Input glass pattern exactly.

1. Select element should have:
   - "bg-paper-100/50 dark:bg-white/5 backdrop-blur-md"
   - "border border-deep-teal-800/10 dark:border-white/10"
   - "rounded-xl px-4 py-2.5 font-sans text-sm"
   - "focus:outline-none focus:ring-2 focus:ring-turquoise-mist/50 focus:border-turquoise-mist"
   - "transition-colors duration-200"
   - "appearance-none" (remove native dropdown arrow)

2. Custom chevron icon: Use ChevronDown from lucide-react positioned absolute right-3
   - "text-obsidian-400/40 dark:text-paper-100/40 pointer-events-none"

3. Label: same as Input — "text-xs font-mono font-medium uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-2"

4. Error state: same as Input — "border-loss focus:ring-loss/50"

Keep all existing props and functionality. Only change visual styling.
```

**Acceptance Criteria:**
- [ ] Select visually matches Input glass aesthetic
- [ ] Custom chevron replaces native dropdown arrow
- [ ] Dark mode uses bg-white/5 (not opaque backgrounds)
- [ ] Error and focus states consistent with Input

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.3a status and date.

---

### Task 2.3b — Upgrade Toggle component to match prototype

**Time:** 10 min  
**Files to modify:** `src/components/ui/Toggle.tsx`

**[GAP]** The system Toggle works but differs from prototype in several ways:
- Proto uses `motion.button` wrapper (system uses plain `<button>`)
- Proto has `size` prop (sm/md) with pixel-level dimensions
- Proto uses `onCheckedChange` prop name (system uses `onChange`)
- Proto uses exact pixel widths via `style={{width, height}}`

**[PROMPT]:**
```
Upgrade src/components/ui/Toggle.tsx to align with prototype patterns.

1. Add size prop: 'sm' | 'md' (default: 'md')
   Dimensions object:
   sm: { w: 36, h: 20, p: 2 }
   md: { w: 44, h: 24, p: 2 }
   thumbSize = height - (padding * 2)

2. Change outer element to motion.button with pixel-level sizing:
   style={{ width: currentDim.w, height: currentDim.h }}

3. Keep the existing onChange prop name (do NOT rename to onCheckedChange — 
   the system already uses onChange and changing the API would break consumers).

4. Keep all existing styling: turquoise-mist when checked, focus ring, disabled state.
5. Keep the existing label/description layout.
6. The inner thumb stays as motion.span with layout animation.

Only add the size prop and motion.button wrapper. 
Do NOT change the prop API names (onChange stays onChange).
```

**Acceptance Criteria:**
- [ ] Toggle supports sm and md sizes
- [ ] Outer element is motion.button with precise pixel dimensions
- [ ] Existing onChange/label/description API unchanged
- [ ] Thumb animation still uses layout + smoothSpring

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.3b status and date.

---

### Task 2.4 — Create EmptyState component

**Time:** 15 min  
**Files to create:** `src/components/ui/EmptyState.tsx`

**[SYSTEM] Current state:** No EmptyState component. Pages show plain "No data" text.

**[PROTO] Target:** Centered empty state with icon circle, title, description, optional action button. Three variants (default, search, error) with different icon defaults and colors.

**[PROMPT]:**
```
Create a new EmptyState component at src/components/ui/EmptyState.tsx 
matching the prototype exactly.

Props: title (string), description (string), icon (optional LucideIcon),
action (optional ReactNode), variant ('default'|'search'|'error'), className

Behavior:
- Default icons: Inbox for default, Search for search, AlertCircle for error
- Icon sits in a colored circle:
  default: "text-obsidian-400/30 dark:text-paper-100/30 bg-obsidian-400/5 dark:bg-white/5"
  search: "text-turquoise-mist/50 bg-turquoise-mist/10"
  error: "text-loss/50 bg-loss/10"
- Title: "text-lg font-display font-medium text-obsidian-400 dark:text-paper-100"
- Description: "text-sm text-obsidian-400/50 dark:text-paper-100/50 max-w-sm leading-relaxed"
- Container: centered flex column, min-h-[250px], uses fadeInUp animation
- Import fadeInUp from '@/lib/animations'

Add to barrel export: export { EmptyState } from './EmptyState';
```

**Acceptance Criteria:**
- [ ] Three variants render with correct colors
- [ ] Animate in with fadeInUp
- [ ] Action button renders when provided
- [ ] Centered with minimum height

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.4 status and date.

---

### Task 2.4a — Upgrade Skeleton component with variant shapes

**Time:** 5 min  
**Files to modify:** `src/components/ui/Skeleton.tsx`

**[GAP]** System Skeleton has no variant prop — it's always a generic rounded rectangle. The prototype has `variant?: 'text' | 'circle' | 'card' | 'chart'` with appropriate default dimensions for each.

**[PROMPT]:**
```
Upgrade src/components/ui/Skeleton.tsx to add a variant prop.

Current: Generic rounded-md pulse div.
Target: Add variant prop for common skeleton shapes.

1. Add prop: variant?: 'text' | 'circle' | 'card' | 'chart' (default: 'text')

2. Variant default dimensions:
   text: "h-4 w-full rounded-md"
   circle: "h-10 w-10 rounded-full"
   card: "h-24 w-full rounded-xl"
   chart: "h-40 w-full rounded-lg"

3. Base classes: "animate-pulse bg-obsidian-400/5 dark:bg-white/5"
4. className prop still overrides everything (for custom sizes)

Keep forwardRef pattern. Keep existing export.
```

**Acceptance Criteria:**
- [ ] All 4 variants render with correct default shapes
- [ ] className override still works for custom dimensions
- [ ] Backwards compatible (no variant = text = current behavior)

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.4a status and date.

---

### Task 2.5 — Create LoadingState component

**Time:** 15 min  
**Files to create:** `src/components/ui/LoadingState.tsx`

**[SYSTEM] Current state:** Uses Skeleton components for loading. No dedicated full-section or full-page loading indicator.

**[PROTO] Target:** Three loading variants: `page` (full-screen with PARAVANT logo pulse), `section` (centered spinner with message), `inline` (small inline spinner + text).

**[PROMPT]:**
```
Create src/components/ui/LoadingState.tsx matching the prototype.

Props: variant ('page'|'section'|'inline'), message (string, default 'Loading...'), className

Variants:
1. inline: flex row, Loader2 w-4 h-4 animate-spin + message text
2. section (default): centered column, Loader2 w-8 h-8 turquoise-mist animate-spin, 
   message in font-mono uppercase tracking-wide, min-h-[200px]
3. page: fixed inset-0 z-50, backdrop blur, centered branded loading:
   - 16x16 rounded-2xl gradient square with "P" letter
   - Pulsing outer border ring
   - Message in font-mono uppercase tracking-widest with animate-pulse

Import Loader2 from 'lucide-react', motion from 'framer-motion'.
Add to barrel export.
```

**Acceptance Criteria:**
- [ ] All 3 variants render correctly
- [ ] Page variant has branded PARAVANT logo
- [ ] Section variant is minimal and clean
- [ ] Inline variant works within text flow

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 2.6 — Upgrade Modal with glass styling and improved animations

**Time:** 20 min  
**Files to modify:** `src/components/ui/Modal.tsx`

**[SYSTEM] Current state:** Has modal with backdrop and panel. Uses modalBackdropVariants and modalPanelVariants from animations.ts.

**[PROTO] Target:**
- Portal-based with createPortal
- Backdrop: `bg-obsidian-400/60 backdrop-blur-sm`
- Panel: `bg-paper-100 dark:bg-obsidian-300` with `border border-deep-teal-800/10 dark:border-white/10`
- Header zone: `bg-white/50 dark:bg-black/20 backdrop-blur-xl` with bottom border
- Content zone: `bg-paper-100/50 dark:bg-obsidian-300/50 backdrop-blur-xl` with `overflow-y-auto custom-scrollbar`
- Close button: round pill `p-2 rounded-full`
- Sizes: sm (max-w-sm), md (max-w-lg), lg (max-w-2xl), full (max-w-4xl)
- Body scroll lock on open
- Escape key closes

**[PROMPT]:**
```
Refactor src/components/ui/Modal.tsx to improve the glass styling and 
match the prototype's visual treatment.

Key changes:
1. Ensure portal-based rendering (createPortal to document.body)
2. Backdrop: "bg-obsidian-400/60 backdrop-blur-sm" 
3. Panel sizes: sm="max-w-sm", md="max-w-lg", lg="max-w-2xl", full="max-w-4xl"
4. Panel styling: "bg-paper-100 dark:bg-obsidian-300 border border-deep-teal-800/10 dark:border-white/10 rounded-2xl shadow-2xl"
5. Header section (when title exists): 
   "px-6 py-5 border-b border-deep-teal-800/5 dark:border-white/5 bg-white/50 dark:bg-black/20 backdrop-blur-xl"
6. Title: "text-xl font-display font-semibold text-deep-teal-800 dark:text-paper-100"
7. Description: "text-sm font-sans text-obsidian-400/60 dark:text-paper-100/60"
8. Close button: "rounded-full p-2" with hover bg transition
9. Content area: "p-6 overflow-y-auto custom-scrollbar bg-paper-100/50 dark:bg-obsidian-300/50 backdrop-blur-xl"
10. Max height: max-h-[90vh] with flex-col layout
11. Body scroll lock: document.body.style.overflow = 'hidden' when open
12. Escape key handler

Reference the uploaded Modal.tsx prototype for exact implementation.
Keep existing prop interface but add size='full' option.
```

**Acceptance Criteria:**
- [ ] Glass header with backdrop blur
- [ ] Glass content area
- [ ] Body scroll locked when open
- [ ] Escape closes modal
- [ ] 4 size options

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.6 status and date.

---

### Task 2.6a — Apply glass styling to specialty Modals

**Time:** 15 min  
**Files to modify:** `src/components/dashboard/KillSwitchModal.tsx`, `src/components/dashboard/PositionCloseModal.tsx`, `src/components/dashboard/RegimeChangeModal.tsx`

**[GAP]** The three specialty modals use the base Modal component but their inner content (form fields, buttons, status indicators) may not follow the glass aesthetic. After Task 2.6 upgrades the Modal shell, these inner layouts need alignment.

**[PROMPT]:**
```
Align the inner content styling of the three specialty modals with the glass design system.

For each modal (KillSwitchModal, PositionCloseModal, RegimeChangeModal):

1. Ensure all Input components use the upgraded glass variant (from Task 2.3)
2. Ensure all Button components use the upgraded motion variant (from Task 2.2)
3. Status/warning sections should use GlassCard variant="status" or "flat":
   - Warning banners: bg-loss/5 border border-loss/20 rounded-xl p-4
   - Info banners: bg-info/5 border border-info/20 rounded-xl p-4
4. Icon containers: rounded-xl bg-loss/10 p-3 (for danger icons)
5. Section spacing: space-y-4 between form groups
6. Text hierarchy: 
   - Section titles: text-sm font-mono font-medium uppercase tracking-widest
   - Body text: text-sm text-obsidian-400/70 dark:text-paper-100/70
   - Warning text: text-xs font-mono text-loss

Do NOT change any business logic, API calls, validation, or state management.
Visual styling only.
```

**Acceptance Criteria:**
- [ ] KillSwitchModal inner content uses glass Inputs and Buttons
- [ ] PositionCloseModal warning section has glass treatment
- [ ] RegimeChangeModal regime options use glass card styling
- [ ] All three modals visually consistent with upgraded Modal shell

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.6a status and date.

---

### Task 2.7 — Upgrade MetricCard with trend indicator and sparkline zone

**Time:** 25 min  
**Files to modify:** `src/components/ui/MetricCard.tsx`

**[SYSTEM] Current state:** Has MetricCard with GlassCard base, value display, change indicator, sparkline. Uses existing hook data.

**[PROTO] Target:**
- Layout: Header row (title left, optional icon right), Value row (number left, trend right), Sparkline absolute bottom
- Title: `text-xs font-mono font-bold uppercase tracking-widest`
- Value: `font-mono font-medium tracking-tighter tabular-nums text-3xl`
- Trend badge with `ArrowUpRight`/`ArrowDownRight`/`Minus` icons, colored gain/loss
- Change label: `text-[10px] text-obsidian-400/40` hidden on small screens
- Sparkline zone: `absolute bottom-0 left-0 right-0 h-20 z-0 pointer-events-none opacity-30` with gradient mask overlay
- Min height: `min-h-[140px]`
- Uses GlassCard as base container with `enableHover={true}`

**[PROMPT]:**
```
Refactor src/components/ui/MetricCard.tsx to match the prototype's 
visual design while preserving its existing prop interface and data hooks.

Visual specification:
1. Use GlassCard as container with enableHover={true}, padding="md", min-h-[140px]
2. Layout: flex-col, justify-between, relative overflow-hidden
3. Header row: flex justify-between items-start
   - Title: "text-xs font-mono font-bold uppercase tracking-widest" 
     (dark variant: text-turquoise-mist, light variant: text-obsidian-400/50)
   - Optional Icon in rounded-lg container with subtle bg
4. Value section: flex items-end justify-between, mt-4
   - Value: "font-mono font-medium tracking-tighter tabular-nums text-3xl"
   - Trend: ArrowUpRight (gain) / ArrowDownRight (loss) / Minus (neutral)
     with percentage, colored text-gain / text-loss
   - Change label: "text-[10px]" hidden sm:inline-block
5. Sparkline zone: absolute bottom-0, h-20, opacity-30 dark:opacity-40
   - Gradient mask: "bg-gradient-to-b from-paper-100/90 via-transparent to-transparent 
     dark:from-obsidian-300/90"
6. Entry animations: value fades in with delay, trend slides in

IMPORTANT: Keep all existing props (title, value, change, changeLabel, 
prefix, suffix, icon, variant, format, sparkline, className, delay).
Keep all existing data formatting logic (formatCurrency, formatNumber, formatPercent).
Only change the visual rendering.

Reference the uploaded MetricCard.tsx prototype for exact layout.
```

**Acceptance Criteria:**
- [ ] Title is mono uppercase tracking-widest
- [ ] Value is large mono tabular-nums
- [ ] Trend arrows are colored
- [ ] Sparkline has gradient mask
- [ ] Hover lift animation works
- [ ] Existing data hooks still work

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 2.8 — Create Tooltip component

**Time:** 15 min  
**Files to create:** `src/components/ui/Tooltip.tsx`

**[SYSTEM] Current state:** No Tooltip component.

**[PROTO] Target:** Portal-based tooltip with arrow, 4 sides (top/bottom/left/right), configurable delay, dark glassmorphic appearance.

**[PROMPT]:**
```
Create src/components/ui/Tooltip.tsx matching the prototype.

Props: content (ReactNode), children (ReactNode), side ('top'|'bottom'|'left'|'right'), 
delay (number, default 200), disabled (boolean), className, triggerClassName

Key implementation:
1. Portal-based (createPortal to document.body)
2. Position calculation based on trigger element getBoundingClientRect
3. AnimatePresence for enter/exit animations
4. Dark appearance: "bg-obsidian-400/90 dark:bg-obsidian-300/95 backdrop-blur-md 
   border border-white/10 shadow-xl text-paper-100 text-xs font-sans"
5. Arrow indicator: rotated 2.5x2.5 square matching background
6. Delay before showing (setTimeout)
7. Update position on scroll/resize
8. Motion variants based on side (y offset for top/bottom, x offset for left/right)

Reference the uploaded Tooltip.tsx prototype for exact implementation.
Add to barrel export.
```

**Acceptance Criteria:**
- [ ] Tooltip appears on hover with delay
- [ ] Arrow points toward trigger
- [ ] All 4 sides work
- [ ] Dark glass appearance

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.8 status and date.

---

### Task 2.8a — Create DonutChart component

**Time:** 20 min  
**Files to create:** `src/components/charts/DonutChart.tsx`

**[GAP]** The prototype has a DonutChart (Recharts PieChart) used in Portfolio for sector/asset allocation. The system has no donut/pie chart. Task 3.3 currently says "or placeholder if no chart component yet" — this ensures the chart exists.

**[PROTO] Reference:** `DonutChart.tsx` — Recharts PieChart with hover-expand active sector, glass tooltip, interactive legend.

**[PROMPT]:**
```
Create src/components/charts/DonutChart.tsx based on the prototype DonutChart.

Props:
  data: Array<{ name: string; value: number; color: string }>
  height?: number (default: 250)
  innerRadius?: string | number (default: "55%")
  outerRadius?: string | number (default: "80%")
  showLegend?: boolean (default: true)
  className?: string

Implementation:
1. Use Recharts: PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Sector
2. Active sector on hover — expand with Sector component:
   - outerRadius += 8 on active
   - Use onMouseEnter/onMouseLeave on Pie to track activeIndex
3. Glass tooltip:
   - "bg-obsidian-400/90 dark:bg-obsidian-300/90 backdrop-blur-xl border border-white/10 rounded-xl px-3 py-2 shadow-xl"
   - Show name + value + percentage
4. Legend (when showLegend):
   - Horizontal flex-wrap below chart
   - Each item: colored dot (w-2.5 h-2.5 rounded-full) + name text-xs font-mono
   - Interactive: click to toggle segment visibility (optional)
5. Import useTheme for theme-aware colors if needed
6. Handle empty data: show EmptyState or message

Wire up all Cell fills from data[i].color.
```

**Acceptance Criteria:**
- [ ] Donut renders with correct colors from data
- [ ] Active sector expands on hover
- [ ] Glass tooltip shows name, value, percentage
- [ ] Legend displays below chart
- [ ] Empty data handled gracefully

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.8a status and date.

---

### Task 2.8b — Create BenchmarkChart component

**Time:** 20 min  
**Files to create:** `src/components/charts/BenchmarkChart.tsx`

**[GAP]** The prototype has a BenchmarkChart for portfolio vs benchmark overlay. The system has EquityCurveChart (which shows equity + drawdown) but no dual-line benchmark comparison chart. Task 3.3 (Portfolio) references it.

**[PROTO] Reference:** `BenchmarkChart.tsx` — Recharts AreaChart with two Areas (portfolio + benchmark), legend toggle, glass tooltip.

**[PROMPT]:**
```
Create src/components/charts/BenchmarkChart.tsx based on the prototype.

Props:
  data: Array<{ date: string; portfolio: number; benchmark: number }>
  height?: number (default: 300)
  className?: string

Implementation:
1. Use Recharts: AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
2. Two areas:
   - Portfolio: stroke turquoise-mist, gradient fill turquoise-mist/20 → transparent
   - Benchmark: stroke "#94a3b8" (slate-400), dashed strokeDasharray="5 5", no fill
3. Grid: strokeDasharray="3 3", opacity 0.1
4. Axes: 
   - XAxis: tick font-mono text-[10px], stroke none
   - YAxis: tick font-mono text-[10px], stroke none, formatter: formatPercent
5. Glass tooltip:
   - "bg-obsidian-400/90 backdrop-blur-xl border border-white/10 rounded-xl shadow-xl"
   - Show date, portfolio value, benchmark value, difference
6. Legend: simple colored line + label text-xs font-mono

Import useTheme for dynamic grid/tick colors.
```

**Acceptance Criteria:**
- [ ] Two overlapping areas render correctly
- [ ] Benchmark line is dashed
- [ ] Glass tooltip shows both values + diff
- [ ] Responsive container fills parent width

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.8b status and date.

---

### Task 2.8c — Create general-purpose AreaChart component

**Time:** 15 min  
**Files to create:** `src/components/charts/AreaChart.tsx`

**[GAP]** The prototype has a reusable AreaChart (Recharts) with error boundary, theme-aware colors, and glass tooltip. The system uses EquityCurveChart for equity-specific rendering but has no general-purpose area chart for pages like Backtest and Strategy Detail.

**[PROTO] Reference:** `AreaChart.tsx` — Recharts AreaChart wrapper with gradient fill, error boundary, empty state fallback.

**[PROMPT]:**
```
Create src/components/charts/AreaChart.tsx as a general-purpose Recharts area chart.

Props:
  data: Array<{ date: string; value: number }>
  height?: number (default: 300)
  showGrid?: boolean (default: true)
  gradientId?: string (default: "area-gradient")
  curveType?: 'linear' | 'monotone' | 'step' (default: 'monotone')
  showTooltip?: boolean (default: true)
  color?: string (default: turquoise-mist hex)
  className?: string

Implementation:
1. ResponsiveContainer wrapping AreaChart
2. Single Area: 
   - type={curveType}, stroke={color}, strokeWidth=2
   - Gradient fill: linearGradient from color/40 at top to color/0 at bottom
3. Grid (when showGrid): strokeDasharray="3 3" opacity 0.1
4. Axes: same pattern as BenchmarkChart — minimal, font-mono
5. Glass tooltip (when showTooltip)
6. Error boundary: wrap in try-catch or ErrorBoundary
7. Empty data: render SVG with flat line and "No data" text

This replaces placeholder divs in pages that say "Chart component — wire in Phase 4".
```

**Acceptance Criteria:**
- [ ] Single area renders with gradient fill
- [ ] Theme-aware axis colors
- [ ] Glass tooltip
- [ ] Handles empty data gracefully

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 2.8c status and date.

---

### PHASE 2 CHECKPOINT — Barrel Export Verification

**Time:** 5 min  
**Files to modify:** `src/components/ui/index.ts` (or equivalent barrel file)

Before proceeding to Phase 3, verify that ALL new components are exported from the barrel file. This is critical — if Claude Code creates components but forgets the barrel export, every page that imports them will fail.

**[PROMPT]:**
```
Verify the barrel export file (likely src/components/ui/index.ts or 
src/components/index.ts) exports ALL of these components:

NEW components created in Phase 2:
- EmptyState
- LoadingState  
- Tooltip
- Avatar
- Logo
- Progress
- DonutChart
- BenchmarkChart
- AreaChart (general purpose)

UPGRADED components (should already be exported):
- Badge, Button, Input, Select, Toggle, Modal, MetricCard, 
  GlassCard, Skeleton, Toast

If any are missing, add the export. Example:
export { EmptyState } from './EmptyState';

Also verify there are no circular import issues by checking that 
the app still compiles without errors after all exports are added.
```

**Acceptance Criteria:**
- [ ] All 9 new components are in the barrel export
- [ ] `npm run build` or `npm run dev` compiles without import errors
- [ ] No circular dependency warnings

> 📋 **After completing this checkpoint:** Update the Progress Tracker. Confirm Phase 2 is 100% complete before starting Phase 3.

---

# PHASE 3 — PAGE-BY-PAGE ASSEMBLY

**Goal:** Refactor each page to use the upgraded components with proper layout zones, card containment, spacing, and mock data displays matching the mockup PDFs.  
**Tasks:** 10  
**Estimated Time:** 6–8 hours  
**Dependencies:** Phase 1 and 2 complete

---

### Task 3.1 — Cockpit page: hero metrics row and status bar

**Time:** 30 min  
**Files to modify:** `src/pages/Cockpit.tsx`

**[SYSTEM] Current state:** Has all widgets (metrics, status bar, equity chart, positions table, strategies grid, alerts). Layout may lack clear visual zones and spacing.

**[PROTO] Cockpit layout zones (from mockup PDF):**
1. Alert banner (conditional — existing, keep)
2. Hero metrics row: 4-6 MetricCards in responsive grid
3. Status bar: system health, regime, risk level badges
4. Market ticker: scrolling price feed
5. Equity curve chart in GlassCard
6. Strategy fleet grid
7. Positions table in GlassCard
8. Recent activity feed

**[PROMPT]:**
```
Refactor the Cockpit page (src/pages/Cockpit.tsx) layout to create clear 
visual zones matching the design mockup.

Changes — layout and spacing ONLY, do NOT modify data hooks or business logic:

1. Add PageHeader at top: title="Cockpit", subtitle="System overview and active monitoring"
   with action buttons (export, settings)

2. Hero Metrics Row: 
   <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
   Render MetricCards for: Portfolio Value, Daily P&L, Open Positions, 
   Win Rate, Active Strategies, Max Drawdown
   
3. Status Bar section:
   <div className="mb-6"> (keep existing StatusBar component)

4. Market Ticker:
   <div className="mb-6"> (keep existing MarketTicker)

5. Main content: two-column layout on large screens
   <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
     <div className="lg:col-span-2"> — Equity Curve in GlassCard
     <div className="lg:col-span-1"> — Strategy Status Grid in GlassCard
   
6. Bottom section: 
   <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
     Positions Table in GlassCard (with header "Open Positions")
     Recent Trades / Activity Feed in GlassCard

7. Each GlassCard section should have a consistent header pattern:
   <div className="flex items-center justify-between mb-4">
     <h3 className="font-display text-lg font-medium text-obsidian-400 dark:text-paper-100">
       Section Title
     </h3>
     {optional action link}
   </div>

Keep ALL existing data fetching hooks (useDashboardSummary, useEquityCurve, etc.)
Keep ALL existing state management and event handlers.
Only restructure the JSX layout and add spacing/containment.
```

**Acceptance Criteria:**
- [ ] Clear visual zones with consistent gaps
- [ ] Metrics row is responsive 2→3→6 columns
- [ ] Chart and strategy grid in two-column layout
- [ ] Each widget section wrapped in GlassCard
- [ ] All data hooks still work

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 3.1a — Style ApiErrorDisplay with glass aesthetic

**Time:** 10 min  
**Files to modify:** `src/components/ui/ApiErrorDisplay.tsx`

**[SYSTEM] Current state:** ApiErrorDisplay handles 3 error categories (network, 401, 500) with compact and full variants. Uses basic styling with Lucide icons (WifiOff, ServerCrash, ShieldAlert, RefreshCw).

**[GAP]:** Likely uses flat background colors instead of glass-morphism. No Framer Motion entry animation. Retry button may not match upgraded Button component.

**[PROMPT]:**
```
Refactor src/components/ui/ApiErrorDisplay.tsx to match the glass design system.

1. Full variant (compact=false):
   - Wrap in glass container: "bg-paper-100/80 dark:bg-obsidian-300/60 backdrop-blur-md 
     rounded-2xl border border-deep-teal-800/10 dark:border-white/10 p-8"
   - Center content: "flex flex-col items-center justify-center text-center gap-4 min-h-[200px]"
   - Icon container: "w-16 h-16 rounded-2xl flex items-center justify-center mb-2"
     Network error: "bg-loss/10 text-loss"
     Auth error: "bg-warning/10 text-warning"  
     Server error: "bg-loss/10 text-loss"
   - Heading: "text-lg font-semibold text-obsidian-400 dark:text-paper-100"
   - Message: "text-sm text-obsidian-400/60 dark:text-paper-100/60 max-w-sm"
   - Retry button: use Button component, variant="secondary", with RefreshCw icon
   - Add fadeInUp animation: wrap in motion.div with fadeInUp variants

2. Compact variant (compact=true):
   - "inline-flex items-center gap-2 text-sm text-obsidian-400/60 dark:text-paper-100/60"
   - Small icon (w-4 h-4) + message text + optional retry link
   - No glass card, just inline

Keep all existing error classification logic and props interface.
```

**Acceptance Criteria:**
- [ ] Full variant uses glass container with backdrop-blur
- [ ] Icon container is color-coded by error type
- [ ] Retry button uses upgraded Button component
- [ ] Compact variant remains minimal and inline
- [ ] fadeInUp animation on mount (full variant)
- [ ] Works in both light and dark mode

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 3.2 — Cockpit page: positions table and trades feed polish

**Time:** 20 min  
**Files to modify:** `src/pages/Cockpit.tsx` (continued)

**[PROMPT]:**
```
Continue refactoring Cockpit.tsx — focus on the positions table and 
trades feed sections.

Positions Table:
1. Wrap in GlassCard with padding="none"
2. Add section header inside: "Open Positions" with "View All" link
3. DataTable should have sticky header with subtle bg
4. P&L column: text-gain for positive, text-loss for negative
5. All number columns: font-mono tabular-nums
6. Empty state: use EmptyState component with title="No open positions"
7. Row click opens PositionDetailDrawer (keep existing handler)

Recent Trades Feed:
1. Wrap in GlassCard with padding="none"  
2. Header: "Recent Activity" with filter dropdown
3. Each trade item: icon bubble (colored by type), title, timestamp
4. Timestamp: relative time format ("2m ago", "1h ago")
5. Empty state: EmptyState with "No recent trades"
6. Footer: "View All" link to orders page

Keep all existing data hooks and handlers.
```

**Acceptance Criteria:**
- [ ] Positions table has glass containment
- [ ] Numbers are monospace
- [ ] P&L is color-coded
- [ ] Empty states use EmptyState component
- [ ] Trades feed shows relative timestamps

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 3.2 status and date.

---

### Task 3.2a — Style DataTable component with glass aesthetic

**Time:** 15 min  
**Files to modify:** `src/components/ui/DataTable.tsx`

**[GAP]** DataTable is used in Cockpit, Portfolio, Orders, Strategy Detail, and Backtest pages but has no explicit styling task. Without this, every page will style its own table inconsistently. The DataTable needs a single glass aesthetic treatment.

**[PROMPT]:**
```
Upgrade src/components/ui/DataTable.tsx with glass aesthetic styling.

1. Table wrapper: "overflow-x-auto" (already likely exists)

2. Table header row:
   - "bg-paper-100/50 dark:bg-white/5 backdrop-blur-sm"
   - "border-b border-deep-teal-800/10 dark:border-white/10"
   - Sticky header: "sticky top-0 z-10"
   - Header cells: "text-[10px] font-mono font-bold uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 px-4 py-3 text-left"

3. Table body rows:
   - "border-b border-deep-teal-800/5 dark:border-white/5 last:border-b-0"
   - Hover: "hover:bg-deep-teal-800/3 dark:hover:bg-white/3 transition-colors"
   - Body cells: "px-4 py-3 text-sm"
   - Clickable rows (if onClick): "cursor-pointer"

4. Numeric columns helper class:
   - "font-mono tabular-nums text-right"
   - Apply when column type hints at numbers (optional — can be per-page)

5. Empty state: When no rows, show EmptyState component centered

6. Pagination area (if exists):
   - "border-t border-deep-teal-800/10 dark:border-white/10 px-4 py-3"
   - Buttons use Button variant="ghost" size="sm"

Do NOT change the DataTable's props API, column definitions, or rendering logic.
Only change CSS classes and add glass treatment.
```

**Acceptance Criteria:**
- [ ] Header row has glass background with sticky positioning
- [ ] Body rows have subtle hover state
- [ ] Consistent padding and typography across all table usage
- [ ] Empty state renders EmptyState component
- [ ] No breaking changes to existing DataTable consumers

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 3.2a status and date.

---

### Task 3.2b — Polish EquityCurveChart tooltip and time-range tabs

**Time:** 10 min  
**Files to modify:** `src/components/charts/EquityCurveChart.tsx`

**[SYSTEM] Current state:** EquityCurveChart is already well-built — has custom tooltip with glass styling (inline styles), time-range tabs (1W/1M/3M/6M/1Y/ALL), Recharts Area with gradient fills, drawdown subplot. Uses hardcoded semantic colors per DESIGN_GUIDE §4.3 (correct — Recharts doesn't reliably resolve CSS variables in SVG attributes).

**[GAP]:** Tooltip uses inline `style={}` objects instead of Tailwind classes where possible. Time-range tab buttons may not use the layoutId sliding indicator from the Tabs component. Gradient opacity values may need tuning to match prototype. Missing draw animation on mount.

**[PROMPT]:**
```
Polish src/components/charts/EquityCurveChart.tsx visual details.

NOTE: This chart already has good structure. Only adjust visual details:

1. Time-range tabs: migrate to the Tabs component (Task 4.5) if available,
   OR ensure tab buttons use the consistent styling:
   Active: "bg-deep-teal-800 text-white dark:bg-turquoise-mist dark:text-deep-teal-900 
   rounded-lg px-3 py-1 text-xs font-mono font-bold"
   Inactive: "text-obsidian-400/50 dark:text-paper-100/50 hover:opacity-80 px-3 py-1 
   text-xs font-mono"

2. Tooltip: keep the glass styling (already good), but ensure:
   - rounded-xl (not rounded-lg)
   - Values use tabular-nums for alignment
   - P&L values color-coded: positive=COLOR_GAIN, negative=COLOR_LOSS

3. Area gradient: ensure fill gradient goes from 40% opacity at top to 0% 
   at bottom (check current <stop> values match this)

4. Animation: add isAnimationActive={true} animationDuration={1500} 
   animationEasing="ease-in-out" to the Area component

5. Drawdown subplot: ensure it uses COLOR_LOSS for the fill with 30% opacity

Do NOT change the semantic color constants (COLOR_GAIN, COLOR_LOSS, etc.)
— these are correct per DESIGN_GUIDE §4.3.
Do NOT change the data hooks or props interface.
```

**Acceptance Criteria:**
- [ ] Time-range tabs styled consistently with design system (active/inactive states)
- [ ] Tooltip values use `tabular-nums` and P&L is color-coded
- [ ] Area gradient: 40% opacity at top, 0% at bottom
- [ ] `isAnimationActive={true}` with 1500ms duration on Area
- [ ] Drawdown subplot uses loss color at 30% opacity
- [ ] Semantic color constants unchanged

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 3.3 — Portfolio page layout

**Time:** 30 min  
**Files to modify:** `src/pages/Portfolio.tsx`

**[PROTO] Portfolio layout (from mockup PDF):**
1. KPI cards row: Active Positions, Total Net Liquidity, Unrealized P&L, Cash Available
2. Two-column allocation charts: Sector Allocation (donut), Asset Class Allocation (donut)  
3. Holdings table: full DataTable with symbol, sector, qty, avg cost, price, market value, P&L, weight
4. Performance attribution: line chart vs benchmark with time range selector

**[PROMPT]:**
```
Refactor src/pages/Portfolio.tsx to match the mockup layout.

1. Add PageHeader: title="Portfolio", subtitle="Holdings and performance attribution"

2. KPI Metrics Row:
   <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
   4 MetricCards: Active Positions, Net Liquidity, Unrealized P&L, Cash Available

3. Allocation Charts Row:
   <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
   Each in GlassCard:
   - "Sector Allocation" with DonutChart (or placeholder if no chart component yet)
   - "Asset Class Allocation" with DonutChart
   
4. Holdings Table:
   Full-width GlassCard with padding="none"
   Header: "Current Holdings" with search input and export button
   DataTable with columns: Instrument, Sector, Qty, Avg Cost, Price, Mkt Value, P&L ($), P&L (%), Weight
   All currency columns: font-mono, P&L color-coded
   Row click opens position drawer

5. Performance Chart:
   GlassCard with header "Performance Attribution"
   Time range selector: 1M, 3M, 6M, YTD, 1Y, ALL (use Tabs component with pill variant)
   AreaChart or BenchmarkChart component

Wire to existing data hooks. Use EmptyState for empty data.
If chart components don't exist yet in the system, create placeholder 
divs with className "h-64 flex items-center justify-center" and text 
"Chart component — wire in Phase 4".
```

**Acceptance Criteria:**
- [ ] 4 KPI cards responsive
- [ ] Two allocation charts side by side
- [ ] Holdings table with all required columns
- [ ] Performance chart with time range tabs
- [ ] All data hooks connected

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 3.3a — Style MonthlyHeatmap with glass aesthetic and theme-aware colors

**Time:** 15 min  
**Files to modify:** `src/components/charts/MonthlyHeatmap.tsx`

**[SYSTEM] Current state:** MonthlyHeatmap uses inline RGB color interpolation (`rgb(r,g,b)`) for cell colors. Uses hardcoded white→green (gain) and white→red (loss) gradients. Wrapped in GlassCard. Uses basic grid layout with month labels.

**[GAP]:** Color interpolation doesn't respect dark mode (white base works for light, not dark). No hover interaction on cells. No transition animation. Missing theme-aware color tokens.

**[PROMPT]:**
```
Refactor src/components/charts/MonthlyHeatmap.tsx to use theme-aware colors 
and match the glass design system.

1. Color system — fix the heatColor function:
   - Light mode base: paper-100 (white-ish) → gain green or loss red
   - Dark mode base: obsidian-300 (dark) → gain green or loss red
   - Use CSS custom properties or check dark mode class to pick base color
   - Gain color target: hsl from --color-gain
   - Loss color target: hsl from --color-loss

2. Cell styling:
   - Each cell: "rounded-lg transition-all duration-200 cursor-pointer"
   - Hover: "ring-2 ring-deep-teal-800/20 dark:ring-white/20 scale-105"
   - Show tooltip on hover with: month name, return %, absolute value
   - Use title attribute or the Tooltip component if available

3. Grid layout:
   - Year labels: "text-xs font-mono text-obsidian-400/50 dark:text-paper-100/50"
   - Month labels: "text-xs font-mono uppercase text-obsidian-400/40 dark:text-paper-100/40"
   - Cell gap: "gap-1"
   - Cell size: "w-10 h-10 md:w-12 md:h-12"

4. Return value overlay on each cell:
   - "text-[10px] font-mono" centered in cell
   - Use contrasting text color (dark text on light cells, light text on dark cells)

5. Skeleton loading: use Skeleton grid matching cell layout

Keep usePnlHeatmap hook and HeatmapCell type unchanged.
```

**Acceptance Criteria:**
- [ ] Colors adapt correctly in dark mode (dark base instead of white base)
- [ ] Cells have rounded corners, hover ring effect, and scale transition
- [ ] Return percentages visible inside cells with appropriate contrast
- [ ] Labels use mono font with muted opacity
- [ ] Tooltip or title shows details on hover
- [ ] Skeleton matches cell grid layout during loading
- [ ] Works in both light and dark mode

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 3.3b — Style TradeDistributionHistogram with theme-aware colors

**Time:** 10 min  
**Files to modify:** `src/components/charts/TradeDistributionHistogram.tsx`

**[SYSTEM] Current state:** Uses Recharts BarChart with Cell-level coloring, ReferenceLine at zero, CartesianGrid, Tooltip. Wrapped in GlassCard with Skeleton loading.

**[GAP]:** Chart likely uses hardcoded colors instead of CSS variable-aware theme colors. CartesianGrid and axis text may not match glass aesthetic. No entry animation.

**[PROMPT]:**
```
Refactor src/components/charts/TradeDistributionHistogram.tsx to match 
the glass design system.

1. Theme-aware colors:
   - Positive return bars: "var(--color-gain)" or hsl(142, 71%, 45%)
   - Negative return bars: "var(--color-loss)" or hsl(0, 84%, 60%)
   - CartesianGrid: stroke="currentColor" with className="text-deep-teal-800/5 dark:text-white/5"
   - Axis text: fill="currentColor" with className="text-obsidian-400/40 dark:text-paper-100/40"
   - ReferenceLine at zero: stroke with subtle color, strokeDasharray="3 3"

2. Tooltip styling:
   - Custom tooltip with glass background: "bg-paper-100/95 dark:bg-obsidian-300/95 
     backdrop-blur-md border border-deep-teal-800/10 dark:border-white/10 
     rounded-xl shadow-lg p-3"
   - Label: font-mono text-sm
   - Value: font-mono font-semibold

3. Bar styling:
   - radius={[4, 4, 0, 0]} for rounded top corners
   - Subtle hover opacity change on bar hover

4. Animation:
   - isAnimationActive={true} animationDuration={1000} animationEasing="ease-out"

5. Responsive: <ResponsiveContainer width="100%" height={250}>

Keep useDailyPnL hook and histogram bucket logic unchanged.
```

**Acceptance Criteria:**
- [ ] Bar colors use theme-aware gain/loss colors
- [ ] CartesianGrid is subtle (5-10% opacity)
- [ ] Custom glass tooltip with proper dark mode support
- [ ] Bars have rounded top corners
- [ ] Entry animation on chart load
- [ ] Reference line at zero is subtle with dashed style
- [ ] Works in both light and dark mode

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 3.4 — Risk page layout

**Time:** 25 min  
**Files to modify:** `src/pages/Risk.tsx`

**[PROTO] Risk layout (from mockup PDF):**
1. Risk status hero: overall risk level badge (LOW/MEDIUM/HIGH/CRITICAL)
2. Progress bars: drawdown used, daily loss used, position count used (vs limits)
3. Circuit breaker states: grid of status indicators
4. Kill switch panel: prominent emergency control

**[PROMPT]:**
```
Refactor src/pages/Risk.tsx to match the mockup layout.

1. PageHeader: title="Risk Management", subtitle="Real-time risk monitoring and controls"

2. Risk Overview Row:
   <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
   Three MetricCards: Current Drawdown, Daily P&L, Position Count
   Each should show value with progress bar underneath showing % of limit used

3. Circuit Breakers Section:
   GlassCard with header "Circuit Breakers"
   Grid of 2-3 columns showing each breaker:
   - Name, Status badge (ARMED/TRIPPED/DISABLED), Threshold, Current value
   - TRIPPED breakers highlighted with bg-loss/5 border-loss/20

4. Risk Limits Section:
   GlassCard with header "Risk Limits"
   Use Progress component for each limit:
   - Max Drawdown: show % used of limit
   - Daily Loss Limit: show % used
   - Max Positions: show count/limit
   - Max Position Size: show %
   Color: default when <60%, warning when 60-80%, danger when >80%

5. Kill Switch Panel:
   GlassCard variant="dark" with prominent kill switch button
   Status indicator (active/inactive), last triggered time
   Confirmation modal on click (use existing KillSwitchModal)

Keep all existing data hooks (useRiskStatus, useActivateKillSwitch, etc.)
```

**Acceptance Criteria:**
- [ ] Risk metrics show progress toward limits
- [ ] Circuit breakers display clearly
- [ ] Kill switch is prominently placed
- [ ] Color escalation at thresholds

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 3.4a — Style GaugeChart with glass aesthetic and motion

**Time:** 10 min  
**Files to modify:** `src/components/charts/GaugeChart.tsx`

**[SYSTEM] Current state:** SVG semicircle gauge with motion.path for animated arc fill. Uses gaugeColor() function mapping 0-50% green, 50-80% amber, 80-100% red. Has stroke classes for gain/warning/loss.

**[GAP]:** Background arc may not match glass aesthetic. No glow effect on the filled arc. Label styling may not match design system typography. Missing hover interaction.

**[PROMPT]:**
```
Refactor src/components/charts/GaugeChart.tsx to enhance visual quality.

1. Background arc:
   - Stroke: "stroke-deep-teal-800/10 dark:stroke-white/10" (very subtle)
   - strokeWidth: 12 (thicker for more presence)

2. Filled arc:
   - Keep existing gaugeColor logic (green/amber/red zones)
   - Add glow: use SVG filter with feGaussianBlur for subtle glow effect
     matching the arc color at critical levels (>80%)
   - strokeLinecap="round" for smooth endpoints

3. Center text:
   - Percentage: "text-2xl font-mono font-bold tabular-nums" 
     color matching the arc color
   - Label below: "text-xs text-obsidian-400/50 dark:text-paper-100/50 uppercase tracking-wider"

4. Animation:
   - Keep existing motion.path with pathLength animation
   - Ensure spring transition matches smoothSpring (100/15/1)

5. Container:
   - Center the gauge: "flex flex-col items-center justify-center"
   - Responsive sizing: viewBox="0 0 200 120" (semicircle)

Keep all existing gauge math constants and color logic.
```

**Acceptance Criteria:**
- [ ] Background arc is subtle (10% opacity)
- [ ] Filled arc has rounded endpoints (strokeLinecap="round")
- [ ] Glow effect appears at critical levels (>80%)
- [ ] Center percentage uses font-mono, color matches arc
- [ ] Label below uses muted uppercase styling
- [ ] Spring animation on mount
- [ ] Works in both light and dark mode

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 3.5 — Strategies page layout

**Time:** 25 min  
**Files to modify:** `src/pages/Strategies.tsx`

**[PROMPT]:**
```
Refactor src/pages/Strategies.tsx to match the mockup layout.

1. PageHeader: title="Strategies", subtitle="Strategy fleet management"
   Actions: "Create Strategy" button (primary), filter dropdown

2. Summary Metrics Row:
   <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
   MetricCards: Total Strategies, Active, Paused, Best Performer (today)

3. Strategy Cards Grid:
   <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
   Each strategy as GlassCard with:
   - Header: strategy name + status badge (active=success, paused=warning, stopped=danger)
   - Key metrics: Today P&L, Total P&L, Win Rate, Trades Today
   - Mini sparkline chart at bottom
   - Click navigates to strategy detail
   - Template type badge (EMA Trend, Donchian, Bollinger, etc.)

4. Each card should use enableHover={true} on GlassCard
5. Empty state when no strategies: "No strategies configured yet" with create button

Keep all existing hooks (useStrategies) and navigation logic.
```

**Acceptance Criteria:**
- [ ] Summary metrics row shows 4 MetricCards
- [ ] Strategy cards grid responsive (1/2/3 columns)
- [ ] Each card shows status badge, metrics, sparkline
- [ ] Hover effects on cards
- [ ] Empty state when no strategies

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 3.5 status and date.

---

### Task 3.5a — Style StrategyStatusGrid component

**Time:** 10 min  
**Files to modify:** `src/components/dashboard/StrategyStatusGrid.tsx`

**[GAP]** StrategyStatusGrid (98 lines) is used in the Cockpit and Strategies pages to show a compact grid of strategy statuses. It has no explicit styling task and could end up inconsistent with the glass aesthetic.

**[PROMPT]:**
```
Upgrade src/components/dashboard/StrategyStatusGrid.tsx with glass aesthetic.

1. Grid container: "grid grid-cols-2 md:grid-cols-3 gap-3"

2. Each strategy cell:
   - GlassCard variant="flat" padding="sm" (or inline glass classes)
   - "rounded-xl bg-paper-100/30 dark:bg-white/3 p-3"
   - Hover: "hover:bg-paper-100/50 dark:hover:bg-white/5 transition-colors cursor-pointer"

3. Strategy name: "text-xs font-mono font-medium truncate"
4. Status indicator: Use Badge component with dot + appropriate variant:
   - active → success + pulsing
   - paused → warning
   - stopped → danger
   - idle → neutral
5. P&L value: "font-mono tabular-nums text-sm" with getPnLColor()

Keep all existing data bindings and click handlers.
```

**Acceptance Criteria:**
- [ ] Each cell has glass card treatment
- [ ] Status badges use consistent Badge component
- [ ] P&L values are color-coded
- [ ] Grid is responsive

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 3.5a status and date.

---

### Task 3.6 — Strategy Detail page layout

**Time:** 25 min  
**Files to modify:** `src/pages/StrategyDetail.tsx`

**[SYSTEM] Current state:** StrategyDetail.tsx uses route params to load individual strategy data. Has sections for metrics, equity curve (EquityCurveChart), parameters, and trades. Uses React Query hooks for data fetching.

**[GAP]:** Missing PageHeader pattern, no breadcrumb navigation back to Strategies list. Metrics likely not in a uniform 6-column grid. Parameters section may lack glass card containment. Action buttons (Pause/Resume, Edit, Backtest) may not be in PageHeader actions slot.

**[PROMPT]:**
```
Refactor src/pages/StrategyDetail.tsx to match the prototype's detail view.

1. Back navigation: breadcrumb or back arrow linking to Strategies list
2. PageHeader with strategy name, status badge, and action buttons 
   (Pause/Resume, Edit Parameters, Run Backtest)

3. Key Metrics Row:
   <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
   MetricCards: Total Return, Sharpe Ratio, Max Drawdown, Win Rate, 
   Profit Factor, Trades (Total)

4. Performance Chart:
   GlassCard with equity curve chart, time range selector tabs

5. Parameters Section:
   GlassCard with header "Strategy Parameters"
   Two-column grid showing each parameter: name, current value, allowed range
   Read-only display (edit happens in modal)

6. Recent Trades Table:
   GlassCard with DataTable: Date, Side, Symbol, Qty, Price, P&L, Duration

7. Risk Metrics Section:
   GlassCard with risk-specific metrics for this strategy

Keep all existing data hooks and route params logic.
```

**Acceptance Criteria:**
- [ ] Back navigation (breadcrumb or back arrow) links to Strategies list
- [ ] PageHeader shows strategy name, status Badge, action buttons
- [ ] 6 MetricCards in responsive grid: Total Return, Sharpe, Max DD, Win Rate, Profit Factor, Total Trades
- [ ] Equity curve chart inside GlassCard with time-range selector tabs
- [ ] Parameters section: two-column grid, read-only, inside GlassCard
- [ ] Recent trades DataTable: Date, Side, Symbol, Qty, Price, P&L, Duration
- [ ] All numbers use `font-mono tabular-nums`
- [ ] Works in both light and dark mode

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 3.7 — Backtest page form styling

**Time:** 20 min  
**Files to modify:** `src/pages/Backtest.tsx`

**[GAP]:** Backtest page likely has stark white form backgrounds that break the dark theme.

**[PROMPT]:**
```
Refactor src/pages/Backtest.tsx to fix form styling and match the 
glass-morphism design system.

1. PageHeader: title="Backtest", subtitle="Validate strategies against historical data"

2. Configuration Form:
   Wrap in GlassCard
   All Input components should use the upgraded Input (Task 2.3) 
   which handles dark mode properly
   Form sections separated by subtle borders:
   "border-b border-deep-teal-800/5 dark:border-white/5 pb-6 mb-6"
   
   Sections: Strategy Selection, Date Range, Parameters, Execution Settings
   Each section has a label: "text-xs font-mono uppercase tracking-widest 
   text-obsidian-400/50 dark:text-paper-100/50 mb-4"
   
3. Run Backtest Button: primary variant, full width at bottom of form

4. Results Section (shown after backtest runs):
   GlassCard with tabs: Summary, Equity Curve, Trade Log, Statistics
   Use Tabs component with underline variant
   Summary: grid of MetricCards (Sharpe, Max DD, Win Rate, etc.)
   Equity Curve: AreaChart
   Trade Log: DataTable
   Statistics: key-value pairs in two columns

5. Loading state: use LoadingState variant="section" while backtest runs

Keep all existing backtest data hooks and submission logic.
```

**Acceptance Criteria:**
- [ ] PageHeader with title and subtitle present
- [ ] Configuration form wrapped in GlassCard with section dividers (`border-b border-deep-teal-800/5 dark:border-white/5 pb-6 mb-6`)
- [ ] Section labels use `text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50`
- [ ] All inputs use upgraded glass-styled Input component
- [ ] Run Backtest button: primary variant, full-width
- [ ] Results section uses Tabs (underline variant) with Summary, Equity Curve, Trade Log, Statistics
- [ ] LoadingState shown during backtest execution
- [ ] EmptyState shown before first backtest run
- [ ] Works in both light and dark mode

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 3.8 — Orders page layout

**Time:** 15 min  
**Files to modify:** `src/pages/Orders.tsx`

**[SYSTEM] Current state:** Orders.tsx displays trade history using DataTable. Has filtering capability and date handling. Uses React Query hooks for order data.

**[GAP]:** Missing PageHeader pattern. Filter controls may not use glass-styled Select components. Side column likely not color-coded (BUY/SELL). P&L column may not be color-coded. Pagination controls may need styling upgrade. No EmptyState for zero results.

**[PROMPT]:**
```
Refactor src/pages/Orders.tsx for visual consistency.

1. PageHeader: title="Trade History", subtitle="Order execution log"
   Actions: date range picker, export button

2. Filters Row:
   Flex row with filter dropdowns: Status (All/Filled/Cancelled/Pending), 
   Side (All/Buy/Sell), Strategy (dropdown of strategies)
   Use the upgraded Input/Select components

3. Orders Table:
   GlassCard padding="none"
   DataTable with columns: Date, Symbol, Side, Type, Qty, Price, 
   Status, Strategy, P&L
   Side column: "BUY" in text-gain, "SELL" in text-loss
   Status badges using Badge component
   All numbers: font-mono tabular-nums

4. Pagination at bottom if >20 rows

5. Empty state: EmptyState with "No orders found"

Keep all existing data hooks.
```

**Acceptance Criteria:**
- [ ] PageHeader with title "Trade History" and export action button
- [ ] Filter row with Status, Side, Strategy dropdowns using glass-styled Select
- [ ] DataTable inside GlassCard (padding="none") with all specified columns
- [ ] Side column: BUY in `text-gain`, SELL in `text-loss`
- [ ] Status uses Badge component with appropriate variant
- [ ] All numeric columns: `font-mono tabular-nums`
- [ ] P&L column color-coded: positive=`text-gain`, negative=`text-loss`
- [ ] Pagination controls when >20 rows
- [ ] EmptyState when no orders match filters
- [ ] Works in both light and dark mode

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 3.9 — Alerts page layout

**Time:** 15 min  
**Files to modify:** `src/pages/Alerts.tsx`

**[SYSTEM] Current state:** Alerts.tsx displays system alerts using useDashboardAlerts hook. Has acknowledge functionality. Alert severity levels are defined in the API types.

**[GAP]:** Missing PageHeader pattern. Alert rows may not have color-coded severity icons. No stagger animation on list. Unacknowledged alerts may not have visual distinction. No EmptyState for zero alerts. Missing "Clear All" bulk action.

**[PROMPT]:**
```
Refactor src/pages/Alerts.tsx for visual consistency.

1. PageHeader: title="Alerts", subtitle="System notifications and warnings"
   Actions: "Clear All" button (ghost), filter by severity

2. Alert List:
   Each alert in a GlassCard-like row with:
   - Severity icon (color-coded): info (blue), warning (amber), 
     critical (red), success (green)
   - Alert message and timestamp
   - Acknowledge button
   - Unacknowledged alerts: slightly highlighted bg

3. Use staggerContainer + fadeInUp for list animation

4. Empty state: EmptyState with "No active alerts — all clear"

Keep existing data hooks (useDashboardAlerts).
```

**Acceptance Criteria:**
- [ ] PageHeader with title, subtitle, Clear All ghost button, severity filter
- [ ] Alert rows have color-coded severity icons (info=blue, warning=amber, critical=red, success=green)
- [ ] Unacknowledged alerts have highlighted background (`bg-deep-teal-800/5 dark:bg-white/5`)
- [ ] Acknowledge button on each alert
- [ ] List uses staggerContainer + fadeInUp animation
- [ ] EmptyState with "No active alerts — all clear" when list is empty
- [ ] Timestamps display relative time (e.g., "5 min ago")
- [ ] Works in both light and dark mode

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 3.10 — Settings and Accounts pages styling

**Time:** 20 min  
**Files to modify:** `src/pages/Settings.tsx`, `src/pages/Accounts.tsx`

**[PROMPT]:**
```
Refactor Settings and Accounts pages for visual consistency.

SETTINGS PAGE:
1. PageHeader: title="Settings"
2. Use Tabs component (underline variant) for sections:
   Profile, Appearance, Notifications, API Keys, System
3. Each tab content in GlassCard
4. Form groups with section labels:
   "text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50"
5. Toggle components for boolean settings
6. Input components for text/number settings
7. All forms use glass-styled inputs (bg-paper-50 dark:bg-white/5)

ACCOUNTS PAGE:
1. PageHeader: title="Accounts", subtitle="Broker connections and balances"
2. Account cards in grid:
   <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
   Each GlassCard with:
   - Broker name and logo
   - Connection status badge (connected=success, disconnected=danger)
   - Balance display: font-mono text-2xl
   - Last sync timestamp
   - Connect/Disconnect button

Keep all existing data hooks and form handlers.
```

**Acceptance Criteria:**
- [ ] Settings: PageHeader, Tabs (underline variant) for sections
- [ ] Settings: Each tab content inside GlassCard
- [ ] Settings: Section labels use mono uppercase tracking-widest styling
- [ ] Settings: Toggle components for boolean settings, Input for text/number
- [ ] Settings: Appearance tab includes theme toggle, reduced motion, compact mode
- [ ] Accounts: PageHeader with title and subtitle
- [ ] Accounts: Cards in responsive 2-column grid
- [ ] Accounts: Each card shows broker name, status Badge, balance (font-mono text-2xl), last sync
- [ ] Accounts: Connect/Disconnect button with appropriate variant
- [ ] Both pages work in light and dark mode

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

# PHASE 4 — INTERACTION POLISH

**Goal:** Refine interactive elements — drawers, dropdowns, notification panels, keyboard shortcuts, market ticker — to match prototype polish.
**Tasks:** 6
**Estimated Time:** 3–4 hours
**Dependencies:** Phase 2 and 3 complete

> **Accessibility note (Phase 4):** All interactive components created or upgraded in this phase must maintain baseline accessibility. Verify: (1) keyboard navigation works without a mouse, (2) focus is visible on all interactive elements, (3) ARIA roles and attributes match the element's semantic purpose, (4) color contrast ratios are maintained (body text >= 4.5:1). These are **not** optional polish — they are correctness requirements.

---

### Task 4.1 — Create Dropdown component

**Time:** 20 min  
**Files to create:** `src/components/ui/Dropdown.tsx`

**[SYSTEM] Current state:** No dropdown component. Uses native selects or custom implementations per page.

**[PROTO] Target:** Portal-based dropdown menu with Framer Motion animations, keyboard navigation (Arrow keys, Enter, Escape), divider support, danger items.

**[PROMPT]:**
```
Create src/components/ui/Dropdown.tsx matching the prototype exactly.

Props: trigger (ReactNode), items (DropdownItemType[]), 
align ('start'|'end'), side ('bottom'|'top'), className

DropdownItemType: { label: ReactNode, icon?: LucideIcon, onClick?: fn, 
disabled?: boolean, danger?: boolean, type?: 'item' } | { type: 'divider' }

Implementation:
1. Portal to document.body
2. Position calculation from trigger getBoundingClientRect
3. AnimatePresence with scale/opacity/y animation
4. Menu: "min-w-[200px] p-1.5 rounded-xl shadow-xl border 
   border-deep-teal-800/10 dark:border-white/10 
   bg-paper-100/90 dark:bg-obsidian-300/90 backdrop-blur-xl"
5. Items: "px-3 py-2 rounded-lg text-sm hover:bg-deep-teal-800/5 dark:hover:bg-white/5"
6. Dividers: "h-px bg-deep-teal-800/5 dark:bg-white/5 mx-2"
7. Keyboard: ArrowDown/Up cycle, Enter activates, Escape closes
8. Click outside closes
9. Scroll/resize repositions

Reference uploaded Dropdown.tsx. Add to barrel export.
```

**Acceptance Criteria:**
- [ ] Portal renders outside component tree
- [ ] Keyboard navigation (arrows, enter, escape) works
- [ ] Click outside closes dropdown
- [ ] Glass background with backdrop blur
- [ ] Danger items styled in loss color
- [ ] ARIA: trigger has `aria-haspopup="menu"` and `aria-expanded` state
- [ ] Menu has `role="menu"`, items have `role="menuitem"`
- [ ] Focus is trapped within menu when open; returns to trigger on close

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 4.1 status and date.

---

### Task 4.1a — Align Header component with glass design system

**Time:** 15 min  
**Files to modify:** `src/components/layout/Header.tsx`

**[GAP]** The system Header (183 lines) already has scroll-based glass effect and notification badge, but hasn't been explicitly checked against the prototype design. Needs integration of Avatar component and verification of glass treatment.

**[PROMPT]:**
```
Refine src/components/layout/Header.tsx to align with prototype polish.

1. Verify scrolled state glass treatment:
   - Scrolled: "bg-paper-100/80 dark:bg-obsidian-300/90 backdrop-blur-[12px] border-b border-deep-teal-800/5 dark:border-white/5"
   - Not scrolled: "bg-transparent" (no border, no blur)
   - Transition: "transition-all duration-300"

2. Replace any raw user icon/image with the Avatar component:
   <Avatar name="Operator" size="sm" status="online" />

3. Notification bell area:
   - Badge count: "min-w-[18px] h-[18px] bg-loss text-white text-[10px] font-bold rounded-full"
   - Ring around badge: "ring-2 ring-paper-100 dark:ring-obsidian-400"

4. Kill switch indicator in header (if present):
   - When active: pulsing loss badge with "animate-pulse"
   - When armed: subtle secondary badge

5. All interactive elements (buttons, icons):
   - "p-2 rounded-lg hover:bg-deep-teal-800/5 dark:hover:bg-white/10 transition-colors"

Do NOT change routing logic, notification dropdown behavior, or kill switch state management.
```

**Acceptance Criteria:**
- [ ] Glass effect transitions smoothly on scroll
- [ ] Avatar component renders in place of raw icon
- [ ] Notification badge styled consistently
- [ ] Interactive elements have consistent hover states

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 4.1a status and date.

---

### Task 4.1b — Align Sidebar with glass design system + Logo integration

**Time:** 15 min  
**Files to modify:** `src/components/layout/Sidebar.tsx`

**[GAP]** The system Sidebar (315 lines) has good structure but needs Logo component integration and final glass polish verification. The prototype uses Logo (wing + wordmark) in the sidebar header area.

**[PROMPT]:**
```
Refine src/components/layout/Sidebar.tsx to integrate Logo and verify glass polish.

1. Sidebar header: Replace any text/icon branding with Logo component:
   - Expanded: <Logo showText={true} />
   - Collapsed: <Logo showText={false} />
   - Container: "px-4 py-6 mb-2"

2. Desktop sidebar surface:
   - "bg-paper-100/80 dark:bg-obsidian-300 backdrop-blur-xl"
   - "border-r border-deep-teal-800/10 dark:border-white/10"
   - Verify sticky: "h-screen sticky top-0"

3. Nav item active state:
   - Active indicator: "bg-deep-teal-800/5 dark:bg-white/10 rounded-xl" (layout animated)
   - Active text: "text-turquoise-mist font-medium"
   - Inactive: "text-obsidian-400/60 dark:text-paper-100/60 hover:text-obsidian-400 dark:hover:text-paper-100"

4. Mobile overlay:
   - Backdrop: "bg-obsidian-400/60 backdrop-blur-sm"
   - Panel: "bg-paper-100 dark:bg-obsidian-300 border-r"

5. Kill switch button in sidebar:
   - Verify it uses the upgraded Button danger variant
   - When active: "bg-loss text-white animate-pulse shadow-lg shadow-loss/30"

6. Collapse button: "hover:bg-deep-teal-800/5 dark:hover:bg-white/5"

Do NOT change navigation items, routing, kill switch logic, or collapse behavior.
```

**Acceptance Criteria:**
- [ ] Logo component renders with correct expand/collapse behavior
- [ ] Active nav item has glass highlight
- [ ] Mobile overlay has backdrop blur
- [ ] Kill switch button uses upgraded Button styling
- [ ] Desktop sidebar has backdrop-blur-xl

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 4.1b status and date.

---

### Task 4.2 — Create PositionDrawer (slide-out detail panel)

**Time:** 25 min  
**Files to modify:** `src/components/ui/PositionDetailDrawer.tsx`

**[SYSTEM] Current state:** Has a PositionDetailDrawer. May lack glass styling and animation.

**[PROTO] Target:** Full slide-out drawer from right with spring animation, glass backdrop, detailed position view with chart, transactions, fundamentals, notes.

**[PROMPT]:**
```
Refactor src/components/ui/PositionDetailDrawer.tsx to match the 
prototype's PositionDrawer design.

Key changes:
1. Portal-based with backdrop: "bg-obsidian-400/40 backdrop-blur-sm"
2. Drawer panel: slides from right with spring animation
   initial={{ x: "100%" }} animate={{ x: 0 }} 
   transition={{ type: "spring", damping: 25, stiffness: 200 }}
3. Panel: "w-full md:w-[480px] bg-paper-100/95 dark:bg-obsidian-300/95 
   backdrop-blur-xl border-l border-deep-teal-800/10 dark:border-white/10"
4. Header: symbol name large, asset type badge, current price + day change
5. Quick actions bar: Set Alert, Watchlist star, More menu (Dropdown)
6. Summary grid: 2-col grid with detail rows (qty, value, avg cost, P&L, weight)
7. Chart section: 30-day performance mini chart
8. Transaction history: list of recent buys/sells
9. Body scroll lock when open

Keep existing props and data structure.
Adapt to use PositionResponse type from the system's API types.
```

**Acceptance Criteria:**
- [ ] Portal-based rendering (outside main DOM tree)
- [ ] Backdrop: `bg-obsidian-400/40 backdrop-blur-sm`, click to close
- [ ] Panel slides from right with spring animation (damping: 25, stiffness: 200)
- [ ] Panel width: `w-full md:w-[480px]` with glass background
- [ ] Header shows symbol, asset type badge, current price + day change
- [ ] Summary grid: 2-column layout with position details
- [ ] Chart section present (30-day performance)
- [ ] Transaction history list
- [ ] Body scroll locks when drawer is open
- [ ] Escape key closes drawer
- [ ] Works in both light and dark mode

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 4.3 — Upgrade MarketTicker with flash animation

**Time:** 15 min  
**Files to modify:** `src/components/ui/MarketTicker.tsx`

**[SYSTEM] Current state:** Has MarketTicker component. May lack price flash animation and smooth marquee.

**[PROTO] Target:**
- CSS marquee with configurable speed (slow/normal/fast)
- Price flash: green/red briefly when value changes
- Pause on hover
- Edge fade gradients
- Duplicated content for seamless loop

**[PROMPT]:**
```
Refactor src/components/ui/MarketTicker.tsx to add price flash 
animations and smooth marquee scrolling.

Key features:
1. Marquee: CSS @keyframes animation with two copies of content
   Speed: slow=60s, normal=40s, fast=20s
2. Pause on hover: "hover:pause-animation" parent class
3. Price flash: when item.value changes, briefly flash green (up) or red (down)
   Use useRef to track previous value, useState for flash state
   Flash duration: 1000ms, then returns to normal
4. Edge fade gradients: left and right 16px gradients fading to background
   "bg-gradient-to-r from-paper-100 dark:from-obsidian-400 to-transparent"
5. Each item: symbol (font-sans bold), price (font-mono), change % with arrow icon
6. Container: "bg-paper-100/50 dark:bg-obsidian-400/50 backdrop-blur-sm 
   border-y border-deep-teal-800/5 dark:border-white/5"

Reference the uploaded MarketTicker.tsx prototype.
Keep existing data structure and hooks.
```

**Acceptance Criteria:**
- [ ] Marquee scrolls continuously
- [ ] Price flash on value change
- [ ] Pause on hover
- [ ] Gradient fade edges

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 4.3 status and date.

---

### Task 4.3a — Style NotificationDropdown with glass aesthetic

**Time:** 10 min  
**Files to modify:** `src/components/layout/NotificationDropdown.tsx`

**[GAP]** NotificationDropdown (184 lines) is triggered from the Header bell icon but has no explicit styling task. Needs glass container, consistent typography, and styled notification items.

**[PROMPT]:**
```
Upgrade src/components/layout/NotificationDropdown.tsx with glass styling.

1. Dropdown container (portal or absolute):
   - "bg-paper-100/90 dark:bg-obsidian-300/90 backdrop-blur-xl"
   - "border border-deep-teal-800/10 dark:border-white/10"
   - "rounded-xl shadow-2xl"
   - "w-80 max-h-96 overflow-y-auto custom-scrollbar"

2. Header section:
   - "px-4 py-3 border-b border-deep-teal-800/10 dark:border-white/10"
   - Title: "text-sm font-sans font-semibold"
   - Clear all / Mark read button: text-xs text-turquoise-mist

3. Notification items:
   - "px-4 py-3 hover:bg-deep-teal-800/3 dark:hover:bg-white/3 transition-colors cursor-pointer"
   - "border-b border-deep-teal-800/5 dark:border-white/5 last:border-b-0"
   - Unread indicator: small turquoise-mist dot
   - Title: text-sm font-medium
   - Body: text-xs text-obsidian-400/60 dark:text-paper-100/60
   - Time: text-[10px] font-mono text-obsidian-400/40

4. Empty state: "No notifications" centered with muted icon

Do NOT change notification data structure, read/unread logic, or click handlers.
```

**Acceptance Criteria:**
- [ ] Glass container with backdrop blur
- [ ] Notification items have subtle hover
- [ ] Unread indicator visible
- [ ] Custom scrollbar on overflow

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 4.3a status and date.

---

### Task 4.4 — Create ActivityFeed component

**Time:** 20 min  
**Files to create or modify:** `src/components/ui/RecentTradesFeed.tsx` or create `ActivityFeed.tsx`

**[PROTO] Target:** Timeline-style activity feed with icon bubbles, filter dropdown, staggered entry animation, relative timestamps.

**[PROMPT]:**
```
Create or refactor the activity feed component to match the prototype's 
ActivityFeed design.

Key features:
1. GlassCard container with header "Recent Activity" and filter Dropdown
2. Timeline vertical line: "absolute w-px bg-deep-teal-800/10 dark:bg-white/10"
3. Each item: icon bubble (colored by type) + content column
   Types: trade (TrendingUp, turquoise), alert (Bell, red), 
   agent (Bot, teal), deposit (ArrowDownLeft, blue)
4. Icon bubble: 8x8 rounded-full with border, solid bg to hide timeline
5. Content: title, description, optional metadata tags, relative timestamp
6. Filter: All, Trades, Alerts, Transfers
7. Animation: staggerContainer + fadeInUp for items
8. Footer: "View All Activity" link
9. Empty state: EmptyState component

Reference uploaded ActivityFeed.tsx. Adapt to use system's trade data types.
```

**Acceptance Criteria:**
- [ ] Timeline renders with icon bubbles
- [ ] Stagger animation on items
- [ ] Filter toggles work
- [ ] Relative timestamps display correctly

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 4.4 status and date.

---

### Task 4.4a — Style ConnectionBanner, StaleDataIndicator, and StatusBar

**Time:** 15 min  
**Files to modify:** `src/components/ui/ConnectionBanner.tsx`, `src/components/ui/StaleDataIndicator.tsx`, `src/components/dashboard/StatusBar.tsx`

**[GAP]** These three system-only components (ConnectionBanner 79 lines, StaleDataIndicator 75 lines, StatusBar 94 lines) provide critical operational status information but have no explicit styling task. They need glass aesthetic alignment.

**[PROMPT]:**
```
Align ConnectionBanner, StaleDataIndicator, and StatusBar with the glass design system.

1. ConnectionBanner (top-of-page warning when SSE disconnected):
   - "bg-warning/10 dark:bg-warning/5 backdrop-blur-sm border-b border-warning/20"
   - Icon + text: "text-sm font-sans text-warning"
   - Reconnect button: Button variant="ghost" size="sm"
   - AnimatePresence: slide down from top (initial y: -40)

2. StaleDataIndicator (inline badge when data is old):
   - Use Badge component variant="warning" with dot + pulsing
   - Text: "text-[10px] font-mono" showing age (e.g. "Data 5m old")
   - Tooltip on hover explaining staleness

3. StatusBar (system status row on Cockpit):
   - Container: "flex items-center gap-4 px-4 py-2 rounded-xl bg-paper-100/30 dark:bg-white/3 border border-deep-teal-800/5 dark:border-white/5"
   - Status items: Badge component for each (SSE Connected, Regime, Last Trade, etc.)
   - Use dot + pulsing for live indicators
   - Separator: "w-px h-4 bg-deep-teal-800/10 dark:bg-white/10"

Keep all existing data bindings and logic for each component.
```

**Acceptance Criteria:**
- [ ] ConnectionBanner animates in/out with glass treatment
- [ ] StaleDataIndicator uses Badge component
- [ ] StatusBar items use consistent Badge styling
- [ ] All three visually cohesive with glass system

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 4.4a status and date.

---

### Task 4.5 — Upgrade Tabs component

**Time:** 15 min  
**Files to modify:** Check if system has Tabs or create

**[PROTO] Target:** Compound component (Tabs, TabsList, TabsTrigger, TabsContent) with two variants: underline (border-bottom indicator) and pill (background indicator). Both use `motion.div` with `layoutId` for smooth sliding animation.

**[PROMPT]:**
```
Create or upgrade the Tabs component to match the prototype's compound 
component pattern with animated indicators.

File: src/components/ui/Tabs.tsx

Exports: Tabs, TabsList, TabsTrigger, TabsContent

Key features:
1. Controlled or uncontrolled (defaultValue or value+onValueChange)
2. TabsList variants:
   underline: "border-b border-deep-teal-800/10 dark:border-white/10 gap-6"
   pill: "gap-2 p-1 bg-deep-teal-800/5 dark:bg-white/5 rounded-xl inline-flex"
3. TabsTrigger active indicators:
   underline: motion.div layoutId="activeTabUnderline" — sliding bottom border
   pill: motion.div layoutId="activeTabPill" — sliding background
4. TabsContent: AnimatePresence with fade-up animation, mt-6
5. Keyboard: ArrowLeft/Right to navigate tabs
6. ARIA: role="tablist", role="tab", aria-selected

Reference uploaded Tabs.tsx. Add all to barrel export.
```

**Acceptance Criteria:**
- [ ] Exports: Tabs, TabsList, TabsTrigger, TabsContent
- [ ] Controlled (value+onValueChange) and uncontrolled (defaultValue) modes work
- [ ] Underline variant: border-bottom indicator slides with layoutId animation
- [ ] Pill variant: background indicator slides with layoutId animation
- [ ] TabsContent uses AnimatePresence with fade-up animation
- [ ] Keyboard: ArrowLeft/Right navigates between tabs
- [ ] ARIA: role="tablist", role="tab", aria-selected on active
- [ ] Added to barrel export (index.ts)
- [ ] Used in at least one page (Backtest results or Settings) to verify integration

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 4.6 — Create SearchInput component

**Time:** 10 min  
**Files to create:** `src/components/ui/SearchInput.tsx`

**[PROMPT]:**
```
Create src/components/ui/SearchInput.tsx matching the prototype.

Wraps Input component with:
- Left icon: Search (lucide-react)
- Right slot: Clear button (X icon, shown when value exists) + keyboard shortcut badge ("⌘K", shown when empty)
- Clear button: p-1 rounded-full hover:bg
- Shortcut badge: "hidden md:inline-flex text-[10px] font-mono border rounded px-1.5 py-0.5"

Props: extends InputProps (minus leftIcon/rightIcon), onClear, shortcut

Reference uploaded SearchInput.tsx. Add to barrel export.
```

**Acceptance Criteria:**
- [ ] Search icon (lucide) on left
- [ ] Clear button (X) appears when value is non-empty
- [ ] Keyboard shortcut badge ("⌘K") shown when empty, hidden when focused or has value
- [ ] Extends InputProps, works with all Input features (focus animation, glass styling)
- [ ] Clear button: `p-1 rounded-full hover:bg` subtle hover
- [ ] Added to barrel export
- [ ] Renders correctly in both light and dark mode

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

# PHASE 5 — ANIMATION & MICRO-INTERACTION POLISH

**Goal:** Ensure every component has the prototype's Framer Motion choreography — entry animations, staggered lists, hover states, transition curves, and reduced-motion support.  
**Tasks:** 8  
**Estimated Time:** 3–4 hours  
**Dependencies:** Phase 1-4 complete

---

### Task 5.1 — Add staggered entry animation to MetricCard rows

**Time:** 15 min  
**Files to modify:** All pages that render MetricCard rows (Cockpit, Portfolio, Risk, StrategyDetail)

**[PROMPT]:**
```
Add staggered entry animations to all MetricCard grid rows across pages.

Pattern to apply everywhere MetricCards appear in a grid:

import { motion } from 'framer-motion';
import { staggerContainer, fadeInUp } from '@/lib/animations';

<motion.div 
  className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4"
  variants={staggerContainer}
  initial="initial"
  animate="animate"
>
  {metrics.map((metric, i) => (
    <motion.div key={metric.title} variants={fadeInUp}>
      <MetricCard {...metric} />
    </motion.div>
  ))}
</motion.div>

Apply this to:
- Cockpit.tsx: hero metrics row
- Portfolio.tsx: KPI cards row
- Risk.tsx: risk metrics row
- StrategyDetail.tsx: metrics row

Each card should fade in and slide up with 0.08s stagger between them.
```

**Acceptance Criteria:**
- [ ] MetricCards stagger on mount across all pages
- [ ] 0.08s delay between cards
- [ ] Uses fadeInUp from animations.ts

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 5.1 status and date.

---

### Task 5.1a — Upgrade PageSkeletons and DashboardSkeleton

**Time:** 10 min  
**Files to modify:** `src/components/ui/PageSkeletons.tsx`, `src/components/ui/DashboardSkeleton.tsx`

**[GAP]** PageSkeletons (141 lines) and DashboardSkeleton (52 lines) are shown during data loading but haven't been upgraded to use the new Skeleton variants (text/circle/card/chart from Task 2.4a). They should produce loading states that mirror the actual page layouts.

**[PROMPT]:**
```
Upgrade PageSkeletons and DashboardSkeleton to use the Skeleton variant system.

1. PageSkeletons.tsx — Each page skeleton should mirror its page layout:
   - CockpitSkeleton: 
     Row of 4-6 Skeleton variant="card" for MetricCards
     Skeleton variant="chart" for equity curve area
     Two columns of Skeleton variant="card" for tables
   
   - PortfolioSkeleton:
     Row of 4 Skeleton variant="card" for KPI cards
     Two Skeleton variant="chart" side by side for donuts
     Skeleton variant="card" h-64 for holdings table

   - StrategiesSkeleton:
     Row of 4 Skeleton variant="card"
     Grid of 3-6 Skeleton variant="card" for strategy cards

   - Generic skeleton for other pages:
     Skeleton variant="text" w-48 for title
     Row of Skeleton variant="card" for metrics
     Skeleton variant="chart" for content area

2. DashboardSkeleton.tsx:
   - Full-page loading with Logo component pulsing (import from Task 2.1b)
   - Or: centered LoadingState variant="page"

3. All skeletons should use GlassCard containment for sections
4. Spacing should match actual page layouts (gap-4, gap-6, mb-8)

Do NOT change the skeleton selection logic (which skeleton renders for which route).
```

**Acceptance Criteria:**
- [ ] Page skeletons mirror actual page layouts
- [ ] Uses Skeleton variants (card, chart, text)
- [ ] GlassCard containment matches real pages
- [ ] DashboardSkeleton uses branded loading state

> 📋 **After completing this task:** Update the Progress Tracker. Mark Task 5.1a status and date.

---

### Task 5.2 — Add chart draw animations

**Time:** 20 min  
**Files to modify:** Chart components (EquityCurveChart, SparklineChart, etc.)

**[PROTO] Animations:**
- SVGAreaChart: `pathLength` animation from 0→1 (1.5s ease-in-out) for line draw, opacity 0→1 (1s) for fill
- AreaChart (Recharts): `isAnimationActive={true}` with 1500ms duration
- DonutChart: hover expand active segment by 4px, dim inactive to opacity 0.6
- SparklineChart: No animation (lightweight, `isAnimationActive={false}`)

**[PROMPT]:**
```
Add draw animations to chart components.

1. EquityCurveChart (or main area chart):
   - Ensure Recharts Area has: isAnimationActive={true} animationDuration={1500} animationEasing="ease-in-out"
   - If using SVG path directly: add motion.path with 
     initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
     transition={{ duration: 1.5, ease: "easeInOut" }}

2. Donut charts (if they exist):
   - Active segment expands outerRadius by 4px on hover
   - Inactive segments dim to opacity 0.6
   - Legend items: opacity transitions on hover matching chart

3. SparklineChart:
   - Keep isAnimationActive={false} for performance
   - These are small and should be instant

4. Gradient definitions:
   Ensure all charts have proper linearGradient defs:
   <linearGradient id="gradientId" x1="0" y1="0" x2="0" y2="1">
     <stop offset="5%" stopColor={accent} stopOpacity={0.4} />
     <stop offset="95%" stopColor={accent} stopOpacity={0} />
   </linearGradient>
```

**Acceptance Criteria:**
- [ ] EquityCurveChart: Recharts Area has `isAnimationActive={true} animationDuration={1500}`
- [ ] Any SVG path charts: motion.path with pathLength 0→1 transition (1.5s)
- [ ] Donut charts: active segment expands +4px outerRadius on hover
- [ ] Donut charts: inactive segments dim to opacity 0.6
- [ ] SparklineChart: `isAnimationActive={false}` (stays instant)
- [ ] All area charts have proper linearGradient defs (5% opacity at top, 0% at bottom)
- [ ] GaugeChart: animated arc fill with motion.path
- [ ] MonthlyHeatmap: subtle fade-in on cells
- [ ] No animation jank or layout shift on chart load

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 5.3 — Add list item stagger animations

**Time:** 15 min  
**Files to modify:** ActivityFeed, AlertsList, TradeHistory, StrategyCards

**[PROMPT]:**
```
Add staggered fadeInUp animations to all list/grid views.

Pattern:
<motion.div variants={staggerContainer} initial="initial" animate="animate">
  {items.map(item => (
    <motion.div key={item.id} variants={fadeInUp}>
      {/* item content */}
    </motion.div>
  ))}
</motion.div>

Apply to:
- Activity/trades feed items
- Alert list items  
- Strategy cards grid
- Orders table rows (wrap each <tr> or use AnimatePresence)
- Position drawer transaction list

Use AnimatePresence mode="wait" when filter changes cause list re-render
so items exit before new items enter.
```

**Acceptance Criteria:**
- [ ] Activity/trades feed items animate in with staggered fadeInUp
- [ ] Alert list items animate in with staggered fadeInUp
- [ ] Strategy cards grid animates in with stagger
- [ ] Order table rows animate in on load
- [ ] Position drawer transaction list animates in
- [ ] AnimatePresence mode="wait" used when filters change (exit before enter)
- [ ] staggerContainer uses 0.08s staggerChildren, 0.1s delayChildren
- [ ] No layout shift during stagger animation

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 5.4 — Add Toast slide animations

**Time:** 10 min  
**Files to modify:** `src/components/ui/Toast.tsx`

**[PROTO] Target:**
- Toast enters: slide from right (`x: 100` → `x: 0`), scale 0.95→1, opacity 0→1
- Toast exits: slide to right + scale down
- Progress bar: width animates from 100%→0% over duration
- Left accent bar colored by type
- `mode="popLayout"` on AnimatePresence for smooth reflow

**[PROMPT]:**
```
Upgrade src/components/ui/Toast.tsx animations.

1. Toast item motion:
   initial={{ opacity: 0, x: 100, scale: 0.95 }}
   animate={{ opacity: 1, x: 0, scale: 1 }}
   exit={{ opacity: 0, x: 100, scale: 0.95 }}

2. Add layout prop to motion.div for smooth reflow

3. Container AnimatePresence: mode="popLayout"

4. Progress bar (bottom of toast):
   <motion.div 
     initial={{ width: "100%" }}
     animate={{ width: "0%" }}
     transition={{ duration: duration/1000, ease: "linear" }}
   />

5. Left accent bar: absolute left, 3px width, colored by type
   success=bg-gain, error=bg-loss, warning=bg-warning, info=bg-info

Keep existing toast data interface and context.
```

**Acceptance Criteria:**
- [ ] Toast enters: slide from right (x: 100→0), scale 0.95→1, opacity 0→1
- [ ] Toast exits: reverse of enter animation
- [ ] AnimatePresence mode="popLayout" for smooth reflow when toasts dismiss
- [ ] Progress bar animates width from 100%→0% over toast duration
- [ ] Left accent bar: 3px wide, colored by type (success=gain, error=loss, warning, info)
- [ ] layout prop on motion.div for smooth reflow
- [ ] Existing toast data interface and context preserved

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 5.5 — Add hover/press micro-interactions to interactive elements

**Time:** 15 min  
**Files to modify:** Multiple components

**[PROMPT]:**
```
Add consistent hover and press micro-interactions across the UI.

1. GlassCard enableHover effect:
   Already exists: whileHover={{ scale: 1.02, y: -4 }}
   Ensure all interactive cards use enableHover={true}

2. Buttons (already handled in Task 2.2):
   whileHover={{ scale: 1.02, y: -1 }}
   whileTap={{ scale: 0.98 }}

3. Table rows:
   Add "hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors cursor-pointer"
   to all clickable DataTable rows

4. Sidebar nav items:
   Add smooth color transition: "transition-colors duration-200"
   Active state should have subtle left border indicator

5. Avatar hover:
   "hover:ring-turquoise-mist/30" ring effect
   Image: "group-hover:scale-110 transition-transform duration-500"

6. Badge hover:
   "transition-colors" on all badges (already in base classes)

7. Links and text buttons:
   "hover:text-deep-teal-800 dark:hover:text-turquoise-mist transition-colors"

Audit all interactive elements and ensure they have appropriate 
hover/press feedback. No element should feel "dead" on interaction.
```

**Acceptance Criteria:**
- [ ] Interactive GlassCards use enableHover with scale 1.02, y -4
- [ ] Table rows have `hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors`
- [ ] Sidebar nav items have `transition-colors duration-200` and active left border
- [ ] Avatar has ring hover effect and image scale on group-hover
- [ ] All links/text buttons have `hover:text-deep-teal-800 dark:hover:text-turquoise-mist transition-colors`
- [ ] No interactive element feels "dead" on hover/click
- [ ] Hover states work in both light and dark mode

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 5.6 — Add page transition choreography

**Time:** 15 min  
**Files to modify:** `src/layouts/MainLayout.tsx`, individual pages

**[PROTO] Pattern:**
```tsx
<AnimatePresence mode="wait">
  <motion.div
    key={currentView}
    initial={{ opacity: 0, x: 20 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: -20 }}
    transition={{ duration: 0.2 }}
  >
    {content}
  </motion.div>
</AnimatePresence>
```

**[PROMPT]:**
```
Verify and refine page transition animation (partially done in Task 1.3).

1. Confirm AnimatePresence mode="wait" wraps the route outlet
2. Enter: slide from right (x: 20 → 0) with fade
3. Exit: slide to left (x: 0 → -20) with fade  
4. Duration: 0.2s (fast, not sluggish)
5. Key: use location.pathname as key to trigger on route change

Additionally, add section-level choreography within pages:
- Each major section (metrics row, chart, table) should fade in 
  sequentially using stagger, not all at once
- Use staggerContainer on the page's root div with delayChildren: 0.1

Test: navigate between Cockpit → Portfolio → Risk and verify 
smooth transitions without layout jumps.
```

**Acceptance Criteria:**
- [ ] AnimatePresence mode="wait" wraps route outlet
- [ ] Page enter: slide from right (x: 20→0) with fade, 0.2s duration
- [ ] Page exit: slide to left (x: 0→-20) with fade, 0.2s duration
- [ ] Key uses location.pathname for route change triggers
- [ ] Within pages: major sections (metrics row, chart, table) stagger in sequentially
- [ ] staggerContainer on page root with delayChildren: 0.1
- [ ] Navigate Cockpit→Portfolio→Risk: smooth transitions, no layout jumps
- [ ] No flash of unstyled content between routes

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 5.7 — Implement reduced-motion support

**Time:** 15 min  
**Files to modify:** `src/contexts/ThemeContext.tsx` (or equivalent), `src/lib/animations.ts`

**[PROTO] Pattern:** ThemeContext has `reducedMotion` state that sets `MotionGlobalConfig.skipAnimations = true`

**[SYSTEM] Current state:** ThemeContext exists but may not have reducedMotion toggle.

**[PROMPT]:**
```
Add reduced-motion support to the animation system.

1. In ThemeContext (or equivalent), add:
   - reducedMotion state (boolean, persisted to localStorage)
   - setReducedMotion setter
   - useEffect that sets: MotionGlobalConfig.skipAnimations = reducedMotion
   - Import MotionGlobalConfig from 'framer-motion'

2. In Settings page Appearance tab:
   Add Toggle for "Reduce Motion" with description 
   "Disable animations for accessibility or performance"

3. In animations.ts:
   Add a check for prefers-reduced-motion media query as initial default:
   const prefersReducedMotion = typeof window !== 'undefined' 
     && window.matchMedia('(prefers-color-scheme: reduced-motion)').matches;

4. All CSS transitions should respect:
   @media (prefers-reduced-motion: reduce) {
     *, *::before, *::after {
       animation-duration: 0.01ms !important;
       transition-duration: 0.01ms !important;
     }
   }
   Add this to the global CSS.

This ensures the system is accessible for users with motion sensitivity.
```

**Acceptance Criteria:**
- [ ] ThemeContext has `reducedMotion` boolean state, persisted to localStorage
- [ ] `setReducedMotion` setter available in context
- [ ] useEffect sets `MotionGlobalConfig.skipAnimations = reducedMotion`
- [ ] Settings → Appearance tab has "Reduce Motion" Toggle
- [ ] Initial default respects `prefers-reduced-motion` media query
- [ ] Global CSS includes `@media (prefers-reduced-motion: reduce)` override
- [ ] When enabled: all Framer Motion and CSS animations are suppressed
- [ ] UI remains functional with reduced motion (no broken layouts)

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

### Task 5.8 — Final animation audit and performance check

**Time:** 20 min  
**No files to modify** — this is a review task

**[PROMPT]:**
```
Perform a final animation audit across the entire frontend.

Checklist:
1. Page transitions: smooth enter/exit on all routes
2. MetricCard rows: staggered fadeInUp on every page
3. Chart draw: line draws on mount, gradient fades in
4. Lists: staggered entry on filter change
5. Modals: backdrop fade + panel scale-in
6. Drawers: spring slide from edge
7. Toasts: slide from right + progress bar
8. Tooltips: fade with directional offset
9. Dropdowns: scale from anchor point
10. Market ticker: smooth marquee, price flash
11. Buttons: hover lift, tap press
12. Cards: hover lift on interactive cards
13. Inputs: focus ring + subtle scale
14. Tabs: sliding indicator (underline or pill)
15. Badges: color transitions
16. Reduced motion: all above suppressed when enabled

For each, verify:
- Animation is smooth (no jank)
- Duration feels right (not too slow, not too fast)
- No layout shifts during animation
- Works in both light and dark mode
- No console errors from Framer Motion

Report any issues found for remediation.
```

**Acceptance Criteria:**
- [ ] All 16 animation categories audited (page transitions, MetricCard stagger, chart draw, list stagger, modals, drawers, toasts, tooltips, dropdowns, ticker, buttons, cards, inputs, tabs, badges, reduced motion)
- [ ] Each animation: smooth (no jank), appropriate duration, no layout shifts
- [ ] All animations work in both light and dark mode
- [ ] No Framer Motion console errors
- [ ] Reduced motion toggle suppresses all animations
- [ ] Performance: no dropped frames on page transitions (check with Chrome DevTools Performance tab)
- [ ] Any issues documented and remediation plan noted
- [ ] **Accessibility audit:** all interactive elements keyboard-navigable (Tab, Enter, Escape)
- [ ] **Accessibility audit:** all interactive elements have visible focus rings (not just outline: none)
- [ ] **Accessibility audit:** color contrast >= 4.5:1 for body text, >= 3:1 for large text (use browser DevTools accessibility panel)
- [ ] **Accessibility audit:** no ARIA violations in browser DevTools (Accessibility tree shows no errors)

> 📋 **After completing this task:** Update the Progress Tracker at the top of this document. Mark this task ✅, add the date, and note any deviations or issues encountered.

---

# APPENDIX A — COMPONENT CROSS-REFERENCE

| Component | System File | Proto Reference | Gap Level |
|-----------|------------|-----------------|-----------|
| GlassCard | `GlassCard.tsx` | `GlassCard.tsx` | Minor (opacity) |
| MetricCard | `MetricCard.tsx` | `MetricCard.tsx` | Moderate (layout) |
| Badge | `Badge.tsx` | `Badge.tsx` | Major (rewrite) |
| Button | `Button.tsx` | `Button.tsx` | Major (add motion) |
| Input | `Input.tsx` | `Input.tsx` | Major (add motion) |
| Modal | `Modal.tsx` | `Modal.tsx` | Moderate (glass) |
| Toast | `Toast.tsx` | `Toast.tsx` | Moderate (animation) |
| Toggle | `Toggle.tsx` | `Toggle.tsx` | Minor |
| Skeleton | `Skeleton.tsx` | `Skeleton.tsx` | Minor |
| DataTable | `DataTable.tsx` | N/A | Moderate (styling) |
| EmptyState | **CREATE** | `EmptyState.tsx` | New |
| LoadingState | **CREATE** | `LoadingState.tsx` | New |
| Tooltip | **CREATE** | `Tooltip.tsx` | New |
| Dropdown | **CREATE** | `Dropdown.tsx` | New |
| SearchInput | **CREATE** | `SearchInput.tsx` | New |
| Tabs | `LiveDataTabs.tsx`? | `Tabs.tsx` | Major (compound) |
| Avatar | N/A | `Avatar.tsx` | New (optional) |
| Progress | N/A | `Progress.tsx` | New |
| ActivityFeed | `RecentTradesFeed.tsx` | `ActivityFeed.tsx` | Major |
| MarketTicker | `MarketTicker.tsx` | `MarketTicker.tsx` | Moderate |
| PositionDrawer | `PositionDetailDrawer.tsx` | `PositionDrawer.tsx` | Moderate |
| Logo | N/A | `Logo.tsx` | New (optional) |
| PageHeader | **CREATE** | (observed pattern) | New |
| ErrorBoundary | `ErrorBoundary.tsx` | `ErrorBoundary.tsx` | Minor |
| animations.ts | `animations.ts` | `animations.ts` | Moderate |
| utils.ts | `utils.ts` | `utils.ts` | Minor |

---

# APPENDIX B — EXECUTION ORDER RECOMMENDATION

```
Week 1 (Foundation + Components):
  Day 1: Tasks 1.1, 1.2, 1.3, 1.4, 1.5  (Phase 1 complete)
  Day 2: Tasks 2.1, 2.2, 2.3, 2.4, 2.5   
  Day 3: Tasks 2.6, 2.7, 2.8              (Phase 2 complete)

Week 2 (Pages):
  Day 4: Tasks 3.1, 3.2                   (Cockpit complete)
  Day 5: Tasks 3.3, 3.4                   (Portfolio + Risk)
  Day 6: Tasks 3.5, 3.6, 3.7             (Strategies + Backtest)
  Day 7: Tasks 3.8, 3.9, 3.10            (Phase 3 complete)

Week 3 (Interactions + Animation):
  Day 8: Tasks 4.1, 4.2, 4.3             
  Day 9: Tasks 4.4, 4.5, 4.6             (Phase 4 complete)
  Day 10: Tasks 5.1, 5.2, 5.3, 5.4       
  Day 11: Tasks 5.5, 5.6, 5.7, 5.8       (Phase 5 complete)
```

---

# APPENDIX C — CLAUDE CODE SESSION TEMPLATE

Use this pattern for every task:

```
Context:
- I am refactoring the PARAVANT trading dashboard frontend
- The AI Studio prototype is in: D:\Eva\Projects\Paravant_System\docs\design\references
- The production system uses: React Router, React Query, Tailwind v4 CSS variables, 
  TypeScript, @/ path aliases, Framer Motion
- Only change visual/styling code — preserve ALL business logic and data hooks

Task: [TASK NUMBER] — [TASK TITLE]
[PASTE THE [PROMPT] SECTION FROM THE TASK]

Important constraints:
- Do NOT change any React Query hooks, API calls, or data fetching logic
- Do NOT change route definitions or navigation logic  
- Do NOT change TypeScript types/interfaces for API data
- Do NOT remove any existing functionality
- ONLY modify visual rendering, Tailwind classes, component structure, and animations
- Test that the component still renders without errors after changes
```

---

# APPENDIX D — PHASE DEPENDENCY GRAPH

Understanding which phases depend on others prevents starting work that will be immediately broken by a prerequisite.

```
Phase 0 — Baseline (screenshots, env verification)
    |
    v
Phase 1 — Global Foundation
    animations.ts  -->  used by ALL components in Phases 2–5
    utils.ts       -->  used by ALL pages in Phase 3
    MainLayout     -->  wraps ALL pages
    PageHeader     -->  used by ALL pages in Phase 3
    GlassCard      -->  used by MetricCard, Modal, Drawer
    |
    v
Phase 2 — Component Library
    Badge, Button, Input, Modal, Toggle  -->  used by Phase 3 pages
    EmptyState, LoadingState, Skeleton   -->  used by Phase 3 pages
    MetricCard                           -->  used by Cockpit, Portfolio, Risk
    Tooltip                              -->  used by charts, MetricCard
    DonutChart, AreaChart, BenchmarkChart  -->  used by Portfolio, Risk, StrategyDetail
    |
    v
Phase 3 — Pages (can run in parallel per page once Phase 2 is done)
    Cockpit        -->  needs MetricCard, DataTable, AreaChart
    Portfolio      -->  needs DonutChart, BenchmarkChart, heatmaps
    Risk           -->  needs GaugeChart, MetricCard, Progress
    Strategies     -->  needs StrategyCard, StrategyGrid, Badge
    StrategyDetail -->  needs AreaChart, Tabs, Badge, MetricCard
    Backtest       -->  needs Input, Select, Toggle, Button
    Orders         -->  needs DataTable, Badge, EmptyState
    Alerts         -->  needs DataTable, Badge, Modal
    Settings       -->  needs Toggle, Input, Select, Button
    Accounts       -->  needs MetricCard, Badge, Avatar
    |
    v
Phase 4 — Interaction Polish
    Dropdown       -->  used by Header, SearchInput, Backtest filters
    PositionDrawer -->  overlay on Cockpit positions
    MarketTicker   -->  Header sub-component
    ActivityFeed   -->  Cockpit sidebar
    Tabs           -->  StrategyDetail, Backtest results
    SearchInput    -->  Orders, Alerts, Strategies filter bars
    |
    v
Phase 5 — Animation & Micro-interactions
    (depends on ALL prior phases — runs last)
    Stagger, page transitions, chart draw, reduced-motion  -->  applied across all
```

**Key constraint:** Phase 1 `animations.ts` exports (`fadeInUp`, `staggerContainer`, `scaleIn`) are imported directly by Phase 2 components. Complete Task 1.1 before ANY Phase 2 work.
