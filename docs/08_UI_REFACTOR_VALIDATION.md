# PARAVANT UI REFACTOR — VALIDATION & VISUAL QA GUIDE

**Created:** 2026-02-26  
**Companion to:** `UI_REFACTOR_TASKS.md`  
**Purpose:** Ensure every refactoring task produces production-grade, visually stunning results — not just "code that compiles."

---

## WHY THIS FILE EXISTS

The #1 failure mode of AI-assisted UI refactoring is: *the code runs, but the result looks generic, inconsistent, or broken.* Claude Code will follow your prompts literally, but it can't see the output. This file gives you a systematic way to catch visual regressions before they compound.

**The approach:** After each phase (not each task), run a structured validation pass. This mirrors professional workflows:
- **Storybook** → We use isolated component checks (Phase 2 validation)
- **Percy/Chromatic** → We use manual screenshot comparison against the prototype PDFs
- **Design token audit** → We verify specific CSS values match the spec
- **Responsive testing** → We check 3 breakpoints per page

---

## HOW TO USE THIS FILE

### After completing each phase in `UI_REFACTOR_TASKS.md`:

1. **Run the dev server** — `npm run dev` or equivalent
2. **Open the app** in both light and dark mode
3. **Walk through the validation checklist** for that phase
4. **Take before/after screenshots** (see Screenshot Protocol below)
5. **Run the Claude Code validation prompt** if you want automated checks
6. **Log results** in the Phase Validation Log at the bottom of this file

### If a check fails:
- Note the failure in the log with a screenshot reference
- Create a remediation task (use format: `R-{phase}.{number}` e.g., `R-2.1`)
- Fix before proceeding to the next phase — visual debt compounds fast

---

## SCREENSHOT PROTOCOL

This is the single most effective validation technique for a solo developer. Professional teams automate this with Percy ($$$), but manual comparison works just as well when done systematically.

### Setup (one time):
1. Create a folder: `docs/validation/screenshots/`
2. Inside, create subfolders: `before/`, `after-phase-1/`, `after-phase-2/`, etc.

### Before starting ANY refactoring:
Take screenshots of every page in the current state. This is your baseline.

**Required screenshots (per page, per theme):**

| # | Page | Dark Mode | Light Mode | Mobile (375px) |
|---|------|-----------|------------|-----------------|
| 1 | Cockpit | ☐ | ☐ | ☐ |
| 2 | Portfolio | ☐ | ☐ | ☐ |
| 3 | Risk | ☐ | ☐ | ☐ |
| 4 | Strategies | ☐ | ☐ | ☐ |
| 5 | Strategy Detail | ☐ | ☐ | ☐ |
| 6 | Backtest | ☐ | ☐ | ☐ |
| 7 | Orders | ☐ | ☐ | ☐ |
| 8 | Alerts | ☐ | ☐ | ☐ |
| 9 | Settings | ☐ | ☐ | ☐ |
| 10 | Accounts | ☐ | ☐ | ☐ |

**Naming convention:** `{page}-{theme}-{breakpoint}.png`  
Example: `cockpit-dark-desktop.png`, `portfolio-light-mobile.png`

### After each phase:
Retake the same screenshots into the `after-phase-N/` folder. Side-by-side compare with the `before/` folder AND the prototype PDFs in the project.

### Compare against three references:
1. **Before screenshots** → Confirm nothing regressed
2. **Prototype PDFs** → Confirm convergence toward target design
3. **Prototype .tsx files** → Confirm specific Tailwind classes match

---

## DESIGN TOKEN SPOT-CHECK

These are the specific values that define the PARAVANT glass aesthetic. If any of these are wrong, the whole UI will feel "off." Check these after every phase.

### Typography Tokens
| Token | Expected Value | Check |
|-------|---------------|-------|
| Metric card titles | `text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50` | ☐ |
| Metric card values | `text-2xl font-mono font-bold tabular-nums` | ☐ |
| Section headers | `text-xs font-mono uppercase tracking-widest` with muted color | ☐ |
| Body text | `text-sm text-obsidian-400/80 dark:text-paper-100/80` | ☐ |
| Page titles | `text-2xl font-bold text-obsidian-400 dark:text-paper-100` | ☐ |

### Surface & Glass Tokens
| Token | Expected Value | Check |
|-------|---------------|-------|
| GlassCard default | `bg-paper-100/80 dark:bg-obsidian-300/60 backdrop-blur-md` | ☐ |
| GlassCard border | `border border-deep-teal-800/10 dark:border-white/10` | ☐ |
| GlassCard radius | `rounded-2xl` | ☐ |
| Page background | `bg-paper-50 dark:bg-obsidian-400` | ☐ |
| Input background | `bg-paper-50 dark:bg-white/5` | ☐ |
| Modal backdrop | `bg-obsidian-400/40 backdrop-blur-sm` | ☐ |

### Color Tokens
| Token | Expected Usage | Check |
|-------|---------------|-------|
| Gain (green) | Positive P&L, BUY badges, success states | ☐ |
| Loss (red) | Negative P&L, SELL badges, error states, critical alerts | ☐ |
| Warning (amber) | Warning alerts, caution states | ☐ |
| Turquoise-mist | Primary accent, active states, focus rings | ☐ |
| Deep-teal | Secondary accent, borders (light mode) | ☐ |

### Animation Tokens
| Token | Expected Value | Check |
|-------|---------------|-------|
| smoothSpring | `stiffness: 100, damping: 15, mass: 1` | ☐ |
| hoverCard | `scale: 1.02, y: -4, duration: 0.2` | ☐ |
| tapButton | `scale: 0.98` | ☐ |
| staggerChildren | `0.08s` | ☐ |
| delayChildren | `0.1s` | ☐ |
| Page transition | `duration: 0.2s`, x: 20→0 enter, 0→-20 exit | ☐ |

---

## PHASE-BY-PHASE VALIDATION CHECKLISTS

---

### PHASE 1 VALIDATION — Global Foundation

**When to run:** After completing Tasks 1.1 through 1.5 (and 1.3a)

**Quick visual check (2 min):**
- [ ] Open Cockpit page — does it have proper padding (not edge-to-edge, not too cramped)?
- [ ] Scroll the page — is there a custom scrollbar (thin, themed)?
- [ ] Switch between dark and light mode — does the page background change smoothly?
- [ ] Check any GlassCard — does it have visible backdrop-blur and translucent background?
- [ ] Check font rendering — is `::selection` styled (turquoise highlight)?

**Specific checks:**
- [ ] `animations.ts`: Import `smoothSpring` in console → confirm `{ stiffness: 100, damping: 15, mass: 1 }`
- [ ] `animations.ts`: Confirm `fadeInUp`, `staggerContainer`, `scaleIn`, `tapButton` all export without error
- [ ] `utils.ts`: `formatNumber(1234567)` returns `"1.23M"` or similar abbreviated format
- [ ] `MainLayout.tsx`: Content area has `overflow-y-auto` and responsive padding
- [ ] PageHeader renders with title on left, actions slot on right, subtitle below title
- [ ] GlassCard "default" variant in dark mode: background is `obsidian-300/60` not solid black

**Claude Code validation prompt:**
```
Run a quick validation of Phase 1 changes.

1. Check animations.ts exports: smoothSpring, snappySpring, fadeInUp, 
   staggerContainer, scaleIn, hoverCard, tapButton — all should be defined
2. Check smoothSpring values: stiffness should be 100 (not 300)
3. Check utils.ts: formatNumber function exists
4. Check MainLayout: content area has overflow-y-auto
5. Check GlassCard: look for backdrop-blur-md in default variant classes
6. Check for PageHeader component exists and exports

Report any issues found.
```

---

### PHASE 2 VALIDATION — Component Alignment

**When to run:** After completing Tasks 2.1 through 2.8c

**Component isolation checks (5 min):**

Test each component in isolation. Either render them on a test page, or temporarily add them to the Cockpit page to verify.

| Component | Light Mode | Dark Mode | Hover/Focus State | Check |
|-----------|-----------|-----------|-------------------|-------|
| Badge (all 6 variants) | ☐ | ☐ | ☐ | ☐ |
| Button (all variants) | ☐ | ☐ | Hover lift + tap press | ☐ |
| Button loading spinner | ☐ | ☐ | N/A | ☐ |
| Input (empty) | ☐ | ☐ | Focus glow + scale | ☐ |
| Input (with value) | ☐ | ☐ | ☐ | ☐ |
| Input (password toggle) | ☐ | ☐ | ☐ | ☐ |
| Select | ☐ | ☐ | ☐ | ☐ |
| Toggle | ☐ | ☐ | ☐ | ☐ |
| Modal (open) | ☐ | ☐ | Escape closes | ☐ |
| MetricCard (with data) | ☐ | ☐ | Trend arrow visible | ☐ |
| MetricCard (loading) | ☐ | ☐ | N/A | ☐ |
| Tooltip | ☐ | ☐ | Appears on hover | ☐ |
| EmptyState (all 3 variants) | ☐ | ☐ | N/A | ☐ |
| LoadingState (page variant) | ☐ | ☐ | Logo pulses | ☐ |
| Avatar | ☐ | ☐ | Ring on hover | ☐ |
| Progress (all colors) | ☐ | ☐ | N/A | ☐ |
| Skeleton (all shapes) | ☐ | ☐ | Shimmer animation | ☐ |

**Specific checks:**
- [ ] Button: Hover should visibly lift (scale 1.02, y -1) — must be perceptible
- [ ] Button: Click/tap should compress (scale 0.98) — must feel responsive
- [ ] MetricCard: Title is `text-xs font-mono uppercase tracking-widest` — NOT regular weight
- [ ] MetricCard: Value is `text-2xl font-mono font-bold tabular-nums`
- [ ] MetricCard: Has min-height (~140px) so cards align in grid
- [ ] MetricCard: Sparkline gradient fades to transparent at bottom
- [ ] Input: Dark mode background is `bg-white/5` NOT solid gray or white
- [ ] Modal: Glass header with blur, body scrolls independently, footer sticky
- [ ] Tooltip: Has directional arrow pointing toward trigger element
- [ ] DonutChart: Active segment expands on hover, inactive dims
- [ ] BenchmarkChart: Two distinct lines (portfolio vs benchmark) are distinguishable

**Common failure modes to watch for:**
- Buttons look flat (no hover lift) → Framer Motion may not be wrapping the element
- Inputs have white background in dark mode → Missing `dark:bg-white/5` class
- MetricCard values misaligned in grid → Missing `tabular-nums` or `min-h` 
- Modals have harsh background → Missing `backdrop-blur-sm` on overlay
- Tooltips clip at page edge → Missing portal-based rendering

**Claude Code validation prompt:**
```
Audit Phase 2 component changes.

For each upgraded component, verify:
1. Badge: check for rounded-full class, 6 variant colors
2. Button: check for motion.button, whileHover and whileTap props
3. Input: check for motion.div wrapper, dark mode bg-white/5
4. MetricCard: check for font-mono, tabular-nums, min-h, sparkline section
5. Modal: check for backdrop-blur on overlay, glass header styling
6. Tooltip: check for portal rendering (createPortal)
7. EmptyState: check exists with 3 variants
8. LoadingState: check exists with page/section/inline variants
9. DonutChart: check exists with hover interaction
10. BenchmarkChart: check exists with dual line support
11. Check all new components are in barrel export (index.ts)

Report missing implementations.
```

---

### PHASE 3 VALIDATION — Page Assembly

**When to run:** After completing Tasks 3.1 through 3.10 (and all subtasks)

This is the most important validation phase. This is where you see if the pages actually look like the prototype.

**Page-by-page comparison (15 min):**

Open each page side-by-side with the corresponding prototype PDF. Score each page on a 1-5 scale:

| Score | Meaning |
|-------|---------|
| 1 | Looks nothing like prototype — major layout/color issues |
| 2 | Same general structure but clearly different styling |
| 3 | Recognizably similar — some details off (spacing, colors, fonts) |
| 4 | Very close — only minor differences noticeable on close inspection |
| 5 | Pixel-close match — professional quality |

| Page | Prototype PDF | Score (Dark) | Score (Light) | Issues |
|------|--------------|-------------|--------------|--------|
| Cockpit | `cockpit.pdf` | /5 | /5 | |
| Portfolio | `portfolio.pdf` | /5 | /5 | |
| Risk | `risk_management.pdf` | /5 | /5 | |
| Strategies | `agent_page__renamed_to_strategies_pages.pdf` | /5 | /5 | |
| Strategy Detail | (see Strategies PDF) | /5 | /5 | |
| Backtest | (no specific PDF — match glass aesthetic) | /5 | /5 | |
| Orders | `trade_history.pdf` | /5 | /5 | |
| Alerts | `alerts.pdf` / `alerts_page_detail.pdf` | /5 | /5 | |
| Settings | `system_settings_and_menu_to_access_and_avatar.pdf` | /5 | /5 | |
| Accounts | (no specific PDF — match glass aesthetic) | /5 | /5 | |

**Target: Every page should score ≥ 4 before proceeding to Phase 4.**

If any page scores ≤ 3, create remediation tasks before moving on.

**Per-page checks:**

**Cockpit:**
- [ ] Hero metrics row: 4-6 MetricCards in responsive grid, evenly sized
- [ ] Status bar visible with system status indicators
- [ ] Positions table: color-coded P&L, font-mono numbers
- [ ] Trades feed: relative timestamps, type badges
- [ ] Overall: clear visual hierarchy — metrics → charts → tables

**Portfolio:**
- [ ] 4 KPI MetricCards at top
- [ ] Allocation charts (DonutChart) visible and interactive
- [ ] Holdings table with proper column formatting
- [ ] MonthlyHeatmap: theme-aware colors, hover interaction
- [ ] TradeDistributionHistogram: themed bars, glass tooltip
- [ ] Performance chart with time range tabs

**Risk:**
- [ ] Risk limit progress bars show usage clearly
- [ ] GaugeChart: animated arc, color-coded by severity
- [ ] Circuit breakers grid with status indicators
- [ ] Kill switch panel with appropriate warning styling
- [ ] All risk metrics use font-mono tabular-nums

**Strategies:**
- [ ] Summary metrics row at top
- [ ] Strategy cards in grid layout with sparklines
- [ ] StrategyStatusGrid styled with glass aesthetic
- [ ] Each card shows: name, status badge, key metric, sparkline

**Orders:**
- [ ] Filters functional and glass-styled
- [ ] BUY/SELL color coding
- [ ] P&L color coding
- [ ] Status badges
- [ ] Pagination
- [ ] EmptyState when filtered to zero

**Alerts:**
- [ ] Severity color-coding (icons + optional background tint)
- [ ] Acknowledge buttons
- [ ] Stagger animation on list load
- [ ] EmptyState for zero alerts

**Responsive check (3 breakpoints):**
- [ ] 1920px (desktop) — full layout, all columns visible
- [ ] 1024px (tablet) — grid collapses gracefully, no horizontal scroll
- [ ] 375px (mobile) — single column, cards stack, tables become scrollable

**Common failure modes:**
- Pages look "flat" despite glass cards → Check page background is `bg-paper-50 dark:bg-obsidian-400` not white/black
- Charts have wrong colors in dark mode → Chart color props not using CSS variables
- Tables feel cramped → Missing proper padding in DataTable cells
- MetricCards different heights in same row → Missing min-h or tabular-nums

---

### PHASE 4 VALIDATION — Interaction Polish

**When to run:** After completing Tasks 4.1 through 4.6 (and subtasks)

**Interaction-specific checks (5 min):**

| Interaction | Works? | Feels Right? | Notes |
|-------------|--------|-------------|-------|
| Dropdown opens on click | ☐ | ☐ | Scale from anchor, not pop |
| Dropdown keyboard nav | ☐ | ☐ | Arrow keys + Enter |
| Dropdown closes on outside click | ☐ | ☐ | |
| PositionDrawer slides open | ☐ | ☐ | Spring animation, not linear |
| PositionDrawer backdrop blur | ☐ | ☐ | |
| PositionDrawer scroll lock | ☐ | ☐ | Body shouldn't scroll behind |
| MarketTicker scrolls | ☐ | ☐ | CSS marquee, smooth |
| MarketTicker price flash | ☐ | ☐ | Brief green/red flash on change |
| MarketTicker pauses on hover | ☐ | ☐ | |
| Tabs indicator slides | ☐ | ☐ | layoutId animation, smooth |
| Tabs keyboard nav | ☐ | ☐ | ArrowLeft/Right |
| SearchInput clear button | ☐ | ☐ | X appears when value exists |
| SearchInput shortcut badge | ☐ | ☐ | ⌘K visible when empty |
| Header glass styling | ☐ | ☐ | Blur, border-bottom |
| Sidebar active indicator | ☐ | ☐ | Left border or background |
| NotificationDropdown glass | ☐ | ☐ | |
| ActivityFeed stagger | ☐ | ☐ | Items fade in sequentially |
| ConnectionBanner styling | ☐ | ☐ | Appropriate urgency level |

**The "feel" test:**
Close your eyes, open the app, and interact with it for 30 seconds. Does it feel:
- [ ] **Responsive** — Every click has immediate visual feedback?
- [ ] **Smooth** — Animations flow naturally, nothing snaps or jumps?
- [ ] **Professional** — Would you trust this dashboard with real money?
- [ ] **Consistent** — Same interaction patterns everywhere?

If any of these feel wrong, note what specifically breaks the impression.

---

### PHASE 5 VALIDATION — Animation & Micro-Interaction Polish

**When to run:** After completing Tasks 5.1 through 5.8

**Animation audit checklist (from Task 5.8):**

| # | Animation Type | Present? | Smooth? | Both Themes? | Reduced Motion? |
|---|---------------|----------|---------|-------------|----------------|
| 1 | Page transitions | ☐ | ☐ | ☐ | ☐ |
| 2 | MetricCard stagger | ☐ | ☐ | ☐ | ☐ |
| 3 | Chart draw on mount | ☐ | ☐ | ☐ | ☐ |
| 4 | List stagger (feeds, alerts) | ☐ | ☐ | ☐ | ☐ |
| 5 | Modal backdrop + panel | ☐ | ☐ | ☐ | ☐ |
| 6 | Drawer slide | ☐ | ☐ | ☐ | ☐ |
| 7 | Toast slide + progress | ☐ | ☐ | ☐ | ☐ |
| 8 | Tooltip fade | ☐ | ☐ | ☐ | ☐ |
| 9 | Dropdown scale | ☐ | ☐ | ☐ | ☐ |
| 10 | Market ticker marquee | ☐ | ☐ | ☐ | ☐ |
| 11 | Button hover lift | ☐ | ☐ | ☐ | ☐ |
| 12 | Button tap press | ☐ | ☐ | ☐ | ☐ |
| 13 | Card hover lift | ☐ | ☐ | ☐ | ☐ |
| 14 | Input focus scale | ☐ | ☐ | ☐ | ☐ |
| 15 | Tab indicator slide | ☐ | ☐ | ☐ | ☐ |
| 16 | Badge color transitions | ☐ | ☐ | ☐ | ☐ |

**Performance check:**
- [ ] Open Chrome DevTools → Performance tab
- [ ] Record a page navigation (Cockpit → Portfolio → Risk)
- [ ] Check for dropped frames (should be <5% of total frames)
- [ ] Check for long tasks (>50ms) during animations
- [ ] If jank detected: identify the component and reduce animation complexity

**Reduced motion check:**
- [ ] Enable "Reduce Motion" in Settings → Appearance
- [ ] Navigate through all pages — NO animations should play
- [ ] All content should still be visible and functional
- [ ] Toggle back off — animations resume

**Final "would I ship this?" test:**
Record a 60-second screen recording navigating through the entire app. Watch it back. Ask yourself:
- Does this look like a product a hedge fund would pay for?
- Are there any moments that look janky, broken, or amateur?
- Is there visual consistency across every page?

---

## RESPONSIVE BREAKPOINT TESTING

Test at these exact widths for each page:

| Breakpoint | Width | What to Check |
|-----------|-------|---------------|
| Mobile | 375px | Single column, stacked cards, scrollable tables, hamburger menu |
| Tablet | 768px | 2-column grid, sidebar collapsible, charts resize |
| Desktop | 1280px | Full layout, all columns, sidebar expanded |
| Wide | 1920px | No wasted space, content doesn't stretch too wide (max-width) |

**How to test:** Chrome DevTools → Toggle device toolbar (Ctrl+Shift+M) → Set specific widths

---

## DARK/LIGHT MODE TESTING

For EVERY validation check, always test both modes. The most common failures:

| Failure | Symptom | Fix |
|---------|---------|-----|
| White text on white bg | Invisible text in light mode | Missing `dark:` prefix on text color |
| Black text on dark bg | Invisible text in dark mode | Missing `dark:` prefix on text color |
| Bright input fields in dark mode | Glaring white input backgrounds | Use `bg-white/5` not `bg-white` in dark mode |
| Charts invisible in dark mode | Chart lines/bars same color as background | Use CSS variable-aware chart colors |
| Borders too harsh in dark | Thick visible borders | Use `dark:border-white/10` not `dark:border-white` |
| Glass cards look solid | No translucency | Missing `backdrop-blur-md` or opacity in bg color |

---

## CLAUDE CODE VALIDATION PROMPTS

Use these prompts for automated checks after each phase.

### Full Audit (after Phase 5 / final):
```
Perform a comprehensive visual audit of the PARAVANT frontend.

For EVERY page (Cockpit, Portfolio, Risk, Strategies, StrategyDetail, 
Backtest, Orders, Alerts, Settings, Accounts):

1. Check PageHeader is present with title and optional subtitle
2. Check all GlassCards use: rounded-2xl, border, backdrop-blur-md
3. Check MetricCards use: font-mono titles, tabular-nums values
4. Check all numbers use font-mono tabular-nums
5. Check gain/loss colors: positive=text-gain, negative=text-loss
6. Check dark mode: no white backgrounds, no invisible text
7. Check responsive: grid collapses at md breakpoint
8. Check EmptyState is used for zero-data scenarios
9. Check all buttons are motion.button with whileHover/whileTap
10. Check all inputs use glass styling (bg-white/5 in dark mode)

For EVERY chart component:
11. Check theme-aware colors (not hardcoded hex)
12. Check animation settings present
13. Check gradient definitions

For app shell:
14. Check MainLayout has overflow-y-auto on content area
15. Check Sidebar has glass styling
16. Check Header has glass styling with border-bottom

Report: list of passing checks and failing checks with specific file and line.
```

### Quick Spot Check (between tasks):
```
Quick visual check: open [PAGE_NAME] in the browser.
Take a screenshot and compare to the prototype.
List the top 3 visual differences you notice.
```

---

## PHASE VALIDATION LOG

Record your results here after each validation pass.

### Phase 1 — Foundation
| Date | Validator | Pass/Fail | Issues Found | Remediation |
|------|-----------|-----------|-------------|-------------|
| | | | | |

### Phase 2 — Components
| Date | Validator | Pass/Fail | Issues Found | Remediation |
|------|-----------|-----------|-------------|-------------|
| | | | | |

### Phase 3 — Pages
| Date | Validator | Score Avg (Dark) | Score Avg (Light) | Issues Found | Remediation |
|------|-----------|-----------------|-------------------|-------------|-------------|
| | | /5 | /5 | | |

### Phase 4 — Interactions
| Date | Validator | Pass/Fail | Issues Found | Remediation |
|------|-----------|-----------|-------------|-------------|
| | | | | |

### Phase 5 — Animations
| Date | Validator | Pass/Fail | Performance OK? | Reduced Motion OK? | Issues Found |
|------|-----------|-----------|----------------|-------------------|-------------|
| | | | | | |

### Final Sign-Off
| Date | Overall Score | Ship-Ready? | Outstanding Issues |
|------|-------------|-------------|-------------------|
| | /5 | Yes / No | |

---

## REMEDIATION TASK FORMAT

When validation finds issues, log them here using this format:

```
### R-{phase}.{number} — {Brief description}
**Found during:** Phase {N} validation
**Severity:** Critical / Major / Minor / Cosmetic
**Page(s) affected:** {list}
**What's wrong:** {description}
**Expected:** {what it should look like}
**Fix:** {suggested approach}
**Status:** ⬜ Open / 🔄 In Progress / ✅ Fixed
```

Example:
```
### R-3.1 — MetricCard values not using tabular-nums on Portfolio page
**Found during:** Phase 3 validation
**Severity:** Minor
**Page(s) affected:** Portfolio
**What's wrong:** MetricCard values use proportional figures, causing misalignment in grid
**Expected:** All numeric values should use font-mono tabular-nums for column alignment
**Fix:** Add tabular-nums to MetricCard value className
**Status:** ⬜ Open
```

---

## APPENDIX — PROTOTYPE PDF TO PAGE MAPPING

Use this to know which PDF to compare each page against:

| Page | Primary PDF | Secondary Reference |
|------|------------|-------------------|
| Cockpit | `cockpit.pdf` | `system.pdf` |
| Portfolio | `portfolio.pdf` | |
| Risk | `risk_management.pdf` | `emergency_panel_slide_out_for_kill_switch_and_emergency_controls.pdf` |
| Strategies | `agent_page__renamed_to_strategies_pages.pdf` | |
| Strategy Detail | `agent_page__renamed_to_strategies_pages.pdf` | |
| Backtest | (no specific PDF) | Match glass aesthetic of other pages |
| Orders | `trade_history.pdf` | |
| Alerts | `alerts.pdf`, `alerts_page_detail.pdf` | |
| Settings | `system_settings_and_menu_to_access_and_avatar.pdf` | `export_buttron_and_settings.pdf` |
| Accounts | (no specific PDF) | Match glass aesthetic |
| Notifications | `notifications_panel_and_page.pdf` | |
| Sidebar | `system.pdf` | |
| Header | `system.pdf` | `avatar_drop_down_menu.pdf` |
| Themes | `themes.pdf` | |
| Markets/Regime | `markets__renames_to_regime_in_the_real_build.pdf` | |
