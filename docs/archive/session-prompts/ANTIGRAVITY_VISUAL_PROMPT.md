# PARAVANT — Antigravity Visual Alignment Prompt
## Version 1.0 | February 2026
## Use with: Gemini Pro (high compute), model = gemini-2.5-pro

---

## WHO YOU ARE

You are a precision UI engineer. Your ONLY job in this task is to align the PARAVANT production frontend
visual layer to match the AI Studio reference prototype. You must not touch logic, data, APIs, or types.

---

## PROJECT CONTEXT

PARAVANT is a crypto trading dashboard built with:
- React 18 + TypeScript
- Tailwind CSS 4 (dark mode via `class` strategy)
- Framer Motion for animations
- Recharts for charts
- Lucide React for icons

The frontend lives at: `frontend/`
The visual reference lives at: `docs/design/references/`
The authoritative design guide is: `docs/design/DESIGN_GUIDE.md`

---

## THE VISUAL TARGET

The AI Studio prototype implements a "Quiet Luxury" aesthetic:
- Dark mode first, light mode secondary
- Near-black dark background (#101413) with subtle green tint — NOT pure black
- Warm paper light background (#F8F5F2) — NOT pure white
- Cinzel serif font for logos and headings — elegant and authoritative
- Inter sans-serif for all UI text — clean and readable
- JetBrains Mono for all numbers, prices, percentages — precise and data-focused
- Glass-morphism panels with backdrop blur, subtle borders, layered transparency
- Turquoise (#2A9D8F) as the primary accent — calm, professional
- Semantic colors: gain #2ECC71 (green), loss #E74C3C (red), warning #F39C12 (amber)
- Animations via Framer Motion: spring-based, fast (0.2s max), never blocking

---

## WHAT IS ALREADY FIXED (DO NOT REDO)

The following changes have already been applied:

1. `frontend/index.html` — Google Fonts loaded via `<link>` tags with preconnect
2. `frontend/src/index.css` — CSS variables switched to RGB triplet system
3. `frontend/tailwind.config.js` — Colors mapped to CSS variable system
4. `frontend/src/contexts/ThemeContext.tsx` — Theme names: amber→onyx, slate→amethyst
5. `frontend/src/pages/dashboard/Settings.tsx` — Theme option labels updated
6. `frontend/src/components/layout/MainLayout.tsx` — Dark bg fixed: obsidian-900→obsidian-400

---

## YOUR TASK

Audit every frontend component for visual drift from the reference design. The specific areas to check:

### AREA 1: Typography Consistency

Reference typography rules from `docs/design/DESIGN_GUIDE.md` Section 3.4:

| Element | Classes Required |
|---------|-----------------|
| Page titles | `font-display text-lg font-medium` (Cinzel) |
| Section headers | `font-sans text-lg font-semibold` |
| Body text | `font-sans text-sm font-normal` |
| Data values (prices, P&L) | `font-mono text-sm font-medium` |
| Large metrics | `font-mono text-3xl font-medium tracking-tighter tabular-nums leading-none` |
| Metric labels | `font-mono text-xs font-bold uppercase tracking-widest` |
| Badge text | `font-mono font-medium tracking-wide` |
| P&L positive | `font-mono font-medium text-gain` with `+` prefix |
| P&L negative | `font-mono font-medium text-loss` |

Check files: MetricCard.tsx, all pages under pages/dashboard/

### AREA 2: GlassCard Variants

File: `frontend/src/components/ui/GlassCard.tsx`

The 4 variants should exactly match these classes:
```typescript
const variants = {
  default:  "bg-paper-100/80 dark:bg-obsidian-300/60 backdrop-blur-xl border border-deep-teal-800/10 dark:border-white/10 shadow-lg",
  elevated: "bg-paper-50/90 dark:bg-obsidian-300/80 backdrop-blur-2xl border border-deep-teal-800/10 dark:border-white/10 shadow-2xl",
  subtle:   "bg-paper-100/50 dark:bg-obsidian-400/50 backdrop-blur-md border border-deep-teal-800/5 dark:border-white/5",
  dark:     "bg-deep-teal-800/95 dark:bg-obsidian-400/90 text-paper-100 backdrop-blur-xl border border-white/10 shadow-xl",
};
// Base classes: "rounded-2xl transition-colors duration-300"
```

Note: `obsidian-300` maps to `--bg-card-dark` (#161918) and `obsidian-400` maps to `--bg-dark` (#101413).

### AREA 3: Button Variants

File: `frontend/src/components/ui/Button.tsx`

Verify:
- Base: `rounded-xl` (not `rounded-lg`)
- Primary: `bg-turquoise-mist text-white hover:shadow-[0_0_20px_rgba(42,157,143,0.4)]`
- Secondary: border-based, no background fill
- Focus ring: `focus:ring-2 focus:ring-turquoise-mist/50`
- Hover animation: `whileHover={{ scale: 1.02, y: -1 }}`
- Tap animation: `whileTap={{ scale: 0.98 }}`

### AREA 4: Badge Variants

File: `frontend/src/components/ui/Badge.tsx`

Verify soft translucent backgrounds:
```typescript
success: "bg-gain/10 text-gain border-transparent"
warning: "bg-warning/10 text-warning border-transparent"
danger:  "bg-loss/10 text-loss border-transparent"
info:    "bg-info/10 text-info border-transparent"
```
Base: `rounded-full font-mono font-medium tracking-wide`

### AREA 5: Sidebar

File: `frontend/src/components/layout/Sidebar.tsx`

Verify:
- Background: `bg-paper-100/80 dark:bg-obsidian-400/80 backdrop-blur-xl`
- Border: `border-r border-deep-teal-800/5 dark:border-white/5`
- Width: 280px expanded, 80px collapsed (Framer Motion spring stiffness:300 damping:30)
- Logo uses: `font-display font-bold text-2xl`
- Active nav item: `text-deep-teal-800 dark:text-turquoise-mist`
- Active indicator: `layoutId="activeNavIndicator"` animated div
- Inactive: `text-obsidian-400/60 dark:text-paper-100/60`
- Nav items: `rounded-xl` (not `rounded-lg`)

### AREA 6: Header

File: `frontend/src/components/layout/Header.tsx`

Verify:
- Height: `h-16`
- Default: `bg-transparent`
- Scrolled (>10px): `bg-paper-100/80 dark:bg-obsidian-400/80 backdrop-blur-[12px]`
- Scroll detection via Framer Motion `useScroll` or addEventListener
- Border appears on scroll: `border-b border-deep-teal-800/5 dark:border-white/5`
- Title: `font-sans font-semibold`

### AREA 7: MetricCard

File: `frontend/src/components/ui/MetricCard.tsx`

Verify:
- Min height: `min-h-[140px]`
- Title: `text-xs font-mono font-bold uppercase tracking-widest`
- Value: `font-mono font-medium tracking-tighter tabular-nums leading-none text-3xl`
- Sparkline: absolute positioned at bottom, opacity 30-40%
- Change indicator: ArrowUpRight/ArrowDownRight from lucide-react
- `text-gain` for positive, `text-loss` for negative

### AREA 8: Chart Colors

Files: all files in `frontend/src/components/charts/`

Chart color constants should use:
```typescript
const PRIMARY = 'rgb(42, 157, 143)';   // --accent-primary
const GAIN = '#2ECC71';
const LOSS = '#E74C3C';
const GRID = 'rgba(255, 255, 255, 0.06)';     // dark mode
const GRID_LIGHT = 'rgba(0, 0, 0, 0.06)';     // light mode
```

### AREA 9: Page Transitions

File: `frontend/src/App.tsx` or page components

Each page should have entry animation:
```typescript
initial={{ opacity: 0, x: 20 }}
animate={{ opacity: 1, x: 0 }}
exit={{ opacity: 0, x: -20 }}
transition={{ duration: 0.2 }}
```

### AREA 10: Cockpit Page Layout

File: `frontend/src/pages/dashboard/Cockpit.tsx`

Verify the Market Regime panel uses `GlassCard variant="dark"` (dark glass-on-dark for distinctive contrast).

Indicator cells inside regime panel:
`p-2.5 rounded-lg bg-white/5 border border-white/10`

---

## APPROACH

1. Use Playwright MCP to take screenshots BEFORE making any changes
   - Navigate to http://localhost:3000 (ensure dev server is running)
   - Screenshot each page with fullPage: true
   - Save to docs/design/screenshots/before/

2. Audit each AREA above by reading the relevant files

3. Apply only the minimum changes needed to match the reference

4. Use Playwright MCP to take screenshots AFTER changes

5. Visually compare and iterate if needed

---

## ABSOLUTE RULES

DO NOT CHANGE:
- Any import statements for data hooks
- Any `useQuery`, `useMutation`, `useEventStream` calls
- Any TypeScript interface or type definitions
- Any API endpoint paths or HTTP methods
- Any routing logic in App.tsx
- Any test files (*.test.tsx, *.spec.ts)
- Any backend Python files
- The `lib/animations.ts` file (already correct)
- The `lib/api.ts` file
- Any files in `src/hooks/` or `src/types/`

DO CHANGE (visual layer only):
- Tailwind class names on JSX elements
- CSS variable values
- Framer Motion animation props (scale, y, opacity values)
- Color constants in chart files
- Font class names (font-display, font-mono, font-sans)
- Border radius (rounded-xl vs rounded-lg on UI components)
- Spacing that affects visual feel (not layout)

---

## VERIFICATION CHECKLIST

After completing changes, verify each item:

- [ ] Cinzel font (font-display) renders in PARAVANT logo and page titles
- [ ] Inter font (font-sans) renders in body text, navigation
- [ ] JetBrains Mono (font-mono) renders in all numbers, prices, percentages
- [ ] Dark mode background is #101413 (warm near-black), not #0a0a0a (pure black)
- [ ] Light mode background is #F8F5F2 (warm paper), not pure white
- [ ] Glass panels have visible backdrop blur effect
- [ ] Turquoise accent (#2A9D8F) visible in active states, buttons, links
- [ ] Gain values show in green (#2ECC71)
- [ ] Loss values show in red (#E74C3C)
- [ ] Theme switcher shows: Ocean, Sapphire, Emerald, Onyx, Amethyst
- [ ] Each theme changes the accent color throughout the UI
- [ ] Sidebar has animated active indicator (layoutId animation)
- [ ] Header glass effect appears on scroll
- [ ] Buttons have hover lift (scale 1.02, y -1px) and tap press (scale 0.98)
- [ ] GlassCard hover animates (scale 1.01, y -2px) when enableHover=true
- [ ] No layout shifts or broken component structures

---

## REFERENCE FILES (ranked by importance)

1. `docs/design/references/index.html` — Complete CSS token system (MOST IMPORTANT)
2. `docs/design/DESIGN_GUIDE.md` — Authoritative visual specification
3. `docs/design/references/components/ui/GlassCard.tsx` — Exact variant classes
4. `docs/design/references/components/ui/Button.tsx` — Button patterns
5. `docs/design/references/components/ui/MetricCard.tsx` — Metric display
6. `docs/design/references/components/ui/Badge.tsx` — Status badge system
7. `docs/design/references/components/layout/Sidebar.tsx` — Navigation layout
8. `docs/design/references/components/layout/Header.tsx` — Header scroll behavior
9. `docs/design/references/components/pages/CockpitPage.tsx` — Main dashboard layout
10. `docs/design/references/lib/animations.ts` — Animation constants

---

## EXAMPLE DIFF (what good output looks like)

```diff
// GlassCard.tsx
- default: "bg-white/80 dark:bg-gray-900/60 backdrop-blur-lg border border-gray-200/10"
+ default: "bg-paper-100/80 dark:bg-obsidian-300/60 backdrop-blur-xl border border-deep-teal-800/10 dark:border-white/10 shadow-lg"

// Button.tsx
- primary: "bg-teal-500 text-white rounded-lg"
+ primary: "bg-turquoise-mist text-white hover:shadow-[0_0_20px_rgba(42,157,143,0.4)] border border-transparent shadow-md shadow-turquoise-mist/20 rounded-xl"
```

---

*Last Updated: February 2026*
*Reference: docs/design/DESIGN_GUIDE.md*
*Applies To: frontend/ directory only*
