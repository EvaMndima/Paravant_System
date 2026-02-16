# PARAVANT INVESTOR COCKPIT — DESIGN GUIDE
## Extracted from AI Studio Prototype (January 2026)

**Purpose:** This document captures the visual design decisions, design tokens, component patterns, and layout architecture from the AI Studio prototype. It serves as the authoritative visual reference when building the production frontend in Phase 6.

**How to Use:** When building dashboard components against FastAPI endpoints, reference this guide for colors, typography, spacing, component styling, and layout structure. Point Claude Code or Antigravity at this file alongside the PRD widget specifications.

**What This Is NOT:** This is not a component library or reusable codebase. The prototype components used mock data and won't work with the real API. Only the *visual decisions* documented here should carry forward.

---

## 1. DESIGN PHILOSOPHY

### Aesthetic Direction: "Quiet Luxury"
The cockpit targets a single sophisticated operator who wants calm confidence, not flashy day-trader energy. The visual language communicates:
- **Precision over excitement** — Muted, considered color choices
- **Trust through restraint** — No unnecessary visual noise
- **Data density with clarity** — Show everything, overwhelm nothing

### Key Principles
- Glass-morphism panels with subtle backdrop blur
- Dark mode as the primary experience (light mode secondary)
- Accent color used sparingly for status and interactive elements
- Monospace font for all numerical/financial data
- Serif display font for branding, sans-serif for everything else
- Smooth, fast page transitions (never blocking)

---

## 2. COLOR SYSTEM

### 2.1 CSS Variable Architecture

Colors are defined as CSS variables using RGB triplets (without `rgb()` wrapper) to enable Tailwind alpha modifiers. This is the core pattern — all theme colors go through variables.

```css
:root {
  /* --- OCEAN (Default Theme) --- */
  --accent-primary: 42 157 143;      /* #2A9D8F — Turquoise */
  --accent-highlight: 61 185 169;    /* #3DB9A9 — Brighter turquoise */
  --accent-dim: 31 122 109;          /* #1F7A6D — Muted turquoise */
  
  --accent-secondary: 15 61 62;      /* #0F3D3E — Deep teal */
  --accent-dark: 10 40 41;           /* #0A2829 — Darkest teal */

  --bg-light: 248 245 242;           /* #F8F5F2 — Warm paper */
  --bg-dark: 16 20 19;              /* #101413 — Near-black green */
  --bg-card-dark: 22 25 24;         /* #161918 — Elevated dark surface */
}
```

### 2.2 Theme Variants

The system supports 5 accent themes. Each overrides `--accent-primary` and `--accent-secondary`. The background variables can also shift per-theme in dark mode.

| Theme | Accent Primary | Dark BG | Personality |
|-------|---------------|---------|-------------|
| **Ocean** (default) | `42 157 143` (#2A9D8F) | `16 20 19` | Calm, professional |
| **Sapphire** | `59 130 246` (#3B82F6) | `2 6 23` | Tech, precision |
| **Emerald** | `16 185 129` (#10B981) | `2 44 34` | Growth, nature |
| **Onyx** | `212 175 55` (#D4AF37) | `0 0 0` | Luxury, authority |
| **Amethyst** | `139 92 246` (#8B5CF6) | `25 5 47` | Creative, bold |

**Dark mode adjustments:** Some themes brighten their accent in dark mode for readability:
- Sapphire: `59 130 246` → `96 165 250` (Blue 400)
- Emerald: `16 185 129` → `52 211 153` (Emerald 400)  
- Onyx: `212 175 55` → `252 211 77` (Amber 300)
- Amethyst: `139 92 246` → `167 139 250` (Violet 400)

### 2.3 Semantic Colors (Fixed, Not Themed)

These never change regardless of theme:

```css
--gain: #2ECC71;       /* Green — Profit, positive change */
--loss: #E74C3C;       /* Red — Loss, negative change */
--warning: #F39C12;    /* Amber — Warnings, caution states */
--info: #3498DB;       /* Blue — Informational */
```

### 2.4 Tailwind Color Mapping

```javascript
// In tailwind.config (or CDN config)
colors: {
  'turquoise': {
    DEFAULT: 'rgb(var(--accent-primary) / <alpha-value>)',
    mist: 'rgb(var(--accent-primary) / <alpha-value>)',
    bright: 'rgb(var(--accent-highlight) / <alpha-value>)',
    dim: 'rgb(var(--accent-dim) / <alpha-value>)',
    glow: 'rgba(var(--accent-primary), 0.4)',
  },
  'deep-teal': {
    DEFAULT: 'rgb(var(--accent-secondary) / <alpha-value>)',
    800: 'rgb(var(--accent-secondary) / <alpha-value>)',
    900: 'rgb(var(--accent-dark) / <alpha-value>)',
  },
  'obsidian': {
    DEFAULT: 'rgb(var(--bg-dark) / <alpha-value>)',
    300: 'rgb(var(--bg-card-dark) / <alpha-value>)',
    400: 'rgb(var(--bg-dark) / <alpha-value>)',
  },
  'paper': {
    DEFAULT: 'rgb(var(--bg-light) / <alpha-value>)',
    100: 'rgb(var(--bg-light) / <alpha-value>)',
    50: '#FDFCFB', 200: '#F0EBE6', 300: '#E5DDD5', 
    400: '#D9CFC4', 500: '#C9BAA8',
  },
  'gain': '#2ECC71',
  'loss': '#E74C3C',
  'warning': '#F39C12',
  'info': '#3498DB',
}
```

---

## 3. TYPOGRAPHY

### 3.1 Font Stack

| Role | Font | Weights | Usage |
|------|------|---------|-------|
| **Display** | Cinzel | 400, 500, 600, 700 | Logo, page titles, branding elements |
| **Body** | Inter | 300, 400, 500, 600 | All UI text, labels, descriptions |
| **Data** | JetBrains Mono | 400, 500, 700 | Prices, P&L, percentages, code, IDs |

### 3.2 Google Fonts Import

```html
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600;700&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
```

### 3.3 Tailwind Font Families

```javascript
fontFamily: {
  'display': ['Cinzel', 'Playfair Display', 'serif'],
  'sans': ['Inter', 'system-ui', 'sans-serif'],
  'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
}
```

### 3.4 Typography Rules (Verified from Source)

- **Page titles (in tables/cards):** `font-display text-lg font-medium` (Cinzel, used in PositionsTable headers)
- **Section headers:** `font-sans text-lg font-semibold`
- **Body text:** `font-sans text-sm font-normal`
- **Data values (prices, P&L):** `font-mono text-sm font-medium`
- **Large metric numbers:** `font-mono text-3xl font-medium tracking-tighter tabular-nums leading-none` (from MetricCard)
- **Metric card labels:** `font-mono text-xs font-bold uppercase tracking-widest` (NOTE: uses font-mono, not font-sans)
- **Badge text:** `font-mono font-medium tracking-wide` (badges use monospace)
- **Change labels (small):** `text-[10px] font-sans` with opacity
- **P&L positive:** `font-mono font-medium text-gain` with `+` prefix
- **P&L negative:** `font-mono font-medium text-loss`
- **Percentage changes:** `font-mono font-bold text-sm` with trend icon
- **Table "View All" links:** `text-xs font-mono uppercase tracking-widest text-turquoise-mist`
- **Sidebar nav labels:** `font-sans font-medium tracking-wide text-sm`
- **Breadcrumbs:** `text-sm font-sans` with opacity for inactive segments

---

## 4. COMPONENT PATTERNS

### 4.1 Glass Panel (Core Surface Component) — Verified

The primary card component uses `framer-motion` for optional hover animation. Four variants:

```typescript
// From GlassCard.tsx — EXACT classes
const variants = {
  default:  "bg-paper-100/80 dark:bg-obsidian-300/60 backdrop-blur-xl border border-deep-teal-800/10 dark:border-white/10 shadow-lg",
  elevated: "bg-paper-50/90 dark:bg-obsidian-300/80 backdrop-blur-2xl border border-deep-teal-800/10 dark:border-white/10 shadow-2xl",
  subtle:   "bg-paper-100/50 dark:bg-obsidian-400/50 backdrop-blur-md border border-deep-teal-800/5 dark:border-white/5",
  dark:     "bg-deep-teal-800/95 dark:bg-obsidian-400/90 text-paper-100 backdrop-blur-xl border border-white/10 shadow-xl",
};

const paddings = {
  none: "p-0",
  sm:   "p-3",
  md:   "p-6",
  lg:   "p-8"
};

// Base classes always applied:
// "rounded-2xl transition-colors duration-300"
```

**Key props:**
- `variant`: default | elevated | subtle | dark
- `padding`: none | sm | md | lg
- `enableHover`: boolean — triggers `hoverCard` animation from animations.ts

**Usage:** `<GlassCard variant="default" padding="md" enableHover>content</GlassCard>`

### 4.2 Metric Card Pattern — Verified

Uses GlassCard internally with `enableHover={true}`. Layout has three zones:

```
┌─────────────────────────────────────┐
│ LABEL (mono,xs,bold,uppercase)  [⊡] │  ← Header: title + optional icon
│                                     │
│ $12,450.00        ▲ 2.45%          │  ← Body: value (left) + trend (right)
│                   vs last period    │
│ ╌╌╌╌╌╌╌╌ sparkline ╌╌╌╌╌╌╌╌╌╌╌╌╌ │  ← Absolute bottom, opacity 30-40%
└─────────────────────────────────────┘
```

**Exact title classes:** `text-xs font-mono font-bold uppercase tracking-widest`
- Light variant: `text-obsidian-400/50 dark:text-paper-100/50`
- Dark variant: `text-turquoise-mist opacity-90`

**Exact value classes:** `font-mono font-medium tracking-tighter tabular-nums leading-none text-3xl`
- Light: `text-deep-teal-800 dark:text-paper-100`
- Dark: `text-paper-50`

**Trend indicator (right-aligned):** `flex items-center gap-1 text-sm font-mono font-bold`
- Uses ArrowUpRight/ArrowDownRight/Minus icons from lucide-react
- Color: `text-gain` (up), `text-loss` (down), `text-obsidian-400/40` (neutral)

**Sparkline zone:** Absolute positioned at bottom, `h-20 opacity-30 dark:opacity-40` with gradient mask overlay that fades sparkline into background

**Icon container:** `p-1.5 rounded-lg backdrop-blur-sm` with `bg-deep-teal-800/5 dark:bg-white/5`

**Min height:** `min-h-[140px]`

**Formatting helpers (from utils.ts):**
```typescript
formatCurrency(value)  // → "$12,450.00" (Intl.NumberFormat USD)
formatNumber(value)    // → "12,450" (with commas, max 2 decimals)
formatPercent(value)   // → "12.45%" (Intl.NumberFormat percent)
```

### 4.3 Status Badges — Verified

From Badge.tsx. Uses **soft translucent backgrounds** (not solid colors) for a premium look.

```typescript
// EXACT variant classes from Badge.tsx
const variants = {
  success: "bg-gain/10 text-gain border-transparent",
  warning: "bg-warning/10 text-warning border-transparent",
  danger:  "bg-loss/10 text-loss border-transparent",
  info:    "bg-info/10 text-info border-transparent",
  neutral: "bg-obsidian-400/5 text-obsidian-400 dark:bg-paper-100/10 dark:text-paper-100 border-transparent",
  outline: "bg-transparent text-obsidian-400 dark:text-paper-100 border border-obsidian-400/20 dark:border-paper-100/20"
};

const sizes = {
  sm: "h-5 px-2 text-[10px] gap-1.5",
  md: "h-6 px-2.5 text-xs gap-2"
};

// Base classes: "inline-flex items-center justify-center rounded-full font-mono font-medium tracking-wide border whitespace-nowrap"
```

**Dot indicator:** Optional `dot` prop adds a 1.5x1.5 circle in current color. `pulsing` prop adds `animate-ping` overlay.

**Status mapping for PARAVANT:**
| Status | Badge variant | Dot | Pulsing |
|--------|-------------|-----|---------|
| LIVE / Active | `success` | yes | yes |
| PAUSED / Warning | `warning` | yes | no |
| STOPPED / Critical | `danger` | yes | yes |
| PAPER / Draft | `info` | yes | no |
| RETIRED / Inactive | `neutral` | no | no |

### 4.4 Button Variants — Verified

From Button.tsx. Uses `framer-motion` for hover/tap micro-animations. **Note: rounded-xl, not rounded-lg.**

```typescript
// EXACT base styles
const baseStyles = "relative inline-flex items-center justify-center rounded-xl font-sans font-medium tracking-wide transition-colors focus:outline-none focus:ring-2 focus:ring-turquoise-mist/50 focus:ring-offset-2 dark:focus:ring-offset-obsidian-400 disabled:opacity-50 disabled:pointer-events-none select-none";

// EXACT variant classes
const variants = {
  primary:   "bg-turquoise-mist text-white hover:shadow-[0_0_20px_rgba(42,157,143,0.4)] border border-transparent shadow-md shadow-turquoise-mist/20",
  secondary: "bg-transparent border border-turquoise-mist/50 text-deep-teal-800 dark:text-turquoise-mist hover:bg-turquoise-mist/10 hover:border-turquoise-mist",
  ghost:     "bg-transparent border border-transparent text-obsidian-400 dark:text-paper-100 hover:bg-deep-teal-800/5 dark:hover:bg-white/5",
  danger:    "bg-loss text-white border border-transparent hover:shadow-[0_0_20px_rgba(231,76,60,0.4)]"
};

const sizes = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-10 px-5 text-sm gap-2",
  lg: "h-12 px-8 text-base gap-2.5"
};
```

**Hover animation:** `whileHover={{ scale: 1.02, y: -1 }}` with smoothSpring
**Tap animation:** `whileTap={{ scale: 0.98 }}`
**Loading state:** Spinner overlay with `Loader2` icon from lucide, content becomes `invisible` but maintains width
**Emergency button (kill switch):** Not a Button variant — it's a custom `<button>` in Header with: `bg-orange-500/10 hover:bg-red-500/20 text-orange-500 hover:text-red-500 border border-orange-500/20 hover:border-red-500/50` using AlertTriangle icon

### 4.5 Data Table Pattern — Verified

From PositionsTable.tsx. Wraps a reusable `DataTable` component inside a `GlassCard padding="none"`.

**Card structure:**
```
┌────────────────────────────────────────────────┐
│ Title (font-display text-lg)    [View All →]   │  ← px-6 py-4 border-b
├────────────────────────────────────────────────┤
│  DataTable (scrollable)                        │  ← flex-1 overflow-auto
│  ┌────┬────┬────┬────┬────┬────┬────┐         │
│  │Inst│Qty │Avg │Mark│P&L$│P&L%│Wt% │         │
│  ├────┼────┼────┼────┼────┼────┼────┤         │
│  │row │... │... │... │... │... │... │         │
│  └────┴────┴────┴────┴────┴────┴────┘         │
└────────────────────────────────────────────────┘
```

**Instrument column pattern (first column with logo):**
```html
<div class="flex items-center gap-3">
  <div class="w-8 h-8 rounded-full bg-deep-teal-800/5 dark:bg-white/5 border border-deep-teal-800/10 dark:border-white/10 flex items-center justify-center text-[10px] font-bold">
    {symbol[0]}  <!-- First letter as logo placeholder -->
  </div>
  <div>
    <div class="font-bold font-sans">NVDA</div>
    <div class="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-sans">NVIDIA Corp.</div>
  </div>
</div>
```

**P&L column pattern:**
- Dollar: `font-mono font-medium text-gain` or `text-loss` with `+` prefix for positive
- Percent: `font-mono` with ArrowUpRight/ArrowDownRight icon, `w-3 h-3 strokeWidth={2}`

**Weight column:** Number + inline progress bar (`w-16 h-1.5 bg-obsidian-400/5 dark:bg-white/10 rounded-full`)

**Responsive visibility:** Columns hide at breakpoints using `hidden md:table-cell`, `hidden lg:table-cell`, `hidden xl:table-cell`

**Loading state:** Uses Skeleton components (circle for avatar, text for data cells)

**Empty state:** `<EmptyState>` component with icon and message

**Row click:** `onRowClick` prop on DataTable opens position detail

### 4.6 Modal / Drawer Pattern

- Overlay: `bg-black/50 backdrop-blur-sm`
- Panel: `glass-panel rounded-2xl max-w-lg p-8`
- Title: `font-display text-xl font-semibold`
- Close button: X icon, top-right, `text-paper-400/50 hover:text-paper-100`
- Entry animation: Fade in + slide up (200ms)

### 4.7 Chart Color Palette

For Recharts / chart components:

```javascript
const chartColors = {
  primary: 'rgb(var(--accent-primary))',        // Main line/area
  secondary: 'rgb(var(--accent-dim))',           // Comparison/benchmark
  positive: '#2ECC71',                           // Gain areas
  negative: '#E74C3C',                           // Loss areas
  grid: 'rgba(255, 255, 255, 0.06)',            // Dark mode grid
  gridLight: 'rgba(0, 0, 0, 0.06)',             // Light mode grid
  tooltip: {
    bg: 'rgba(22, 25, 24, 0.95)',               // Tooltip background
    border: 'rgba(255, 255, 255, 0.1)',
    text: '#F8F5F2',
  }
};
```

### 4.9 Utility Functions — Verified (lib/utils.ts)

```typescript
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Core class merging utility — used everywhere
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Formatting helpers
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD',
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
}

export function formatPercent(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).format(value / 100); // NOTE: divides by 100 internally
}
```

**Dependencies:** `clsx` + `tailwind-merge` (both in package.json)

---

## 5. LAYOUT ARCHITECTURE

### 5.0 Market Regime Panel — Verified

From MarketRegimePanel.tsx. Uses `GlassCard variant="dark"` for a distinctive dark-on-dark look. This is a key reference for the production Regime page.

**Structure:**
```
┌─────────────────────────────────────────┐ (GlassCard dark)
│ CURRENT ASSESSMENT (mono,xs,uppercase)  │
│ ┌─────────┐                             │
│ │ Bullish │  85% Conf.                  │
│ └─────────┘  Active for 12d 8h          │
│                                         │
│ ┌──────────┐ ┌──────────┐              │
│ │ VIX  ●🟢 │ │ BREADTH  │  ← 2-col grid
│ │ 14.2     │ │ 68%      │     of indicators
│ │ Low Vol  │ │ Healthy  │
│ └──────────┘ └──────────┘              │
│ ─────────────────────────               │
│ CURATOR COMMENTARY                      │
│ ▎ "Markets showing sustained..."        │
└─────────────────────────────────────────┘
```

**Indicator cell:** `p-2.5 rounded-lg bg-white/5 border border-white/10`
- Label: `text-[10px] opacity-60 uppercase tracking-wide` with lucide icon
- Status dot: `w-1.5 h-1.5 rounded-full shadow-[0_0_5px_currentColor]` — green/amber/red
- Value: `font-mono font-bold text-sm text-paper-100`
- Sub-label: `text-[10px] text-turquoise-mist`

**Commentary:** `border-t border-white/10 pt-4`, left border quote `border-l-2 border-white/20 pl-3`, italic text

**NOTE for production:** Replace prototype indicators (vix, breadth, putCall, correlation) with PRD indicators: trend (Price vs SMA50), volatility (ATR/ATR_SMA ratio), momentum (RSI 14), composite regime. Keep the same visual grid pattern.

### 5.1 Application Shell

```
┌──────────────────────────────────────────────────────────┐
│ ┌──────┐ ┌──────────────────────────────────────────────┐│
│ │      │ │  Header (title, breadcrumb, actions)         ││
│ │      │ ├──────────────────────────────────────────────┤│
│ │ Side │ │                                              ││
│ │ bar  │ │  Content Area (scrollable)                   ││
│ │      │ │  ┌──────────────────────────────────────┐    ││
│ │ Nav  │ │  │  max-w-7xl mx-auto                   │    ││
│ │      │ │  │  Page content here                   │    ││
│ │      │ │  └──────────────────────────────────────┘    ││
│ │      │ │                                              ││
│ └──────┘ └──────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

### 5.2 Sidebar — Verified

From Sidebar.tsx. Uses SidebarProvider context for collapse state.

- **Width:** Animated with framer-motion — `280px` expanded, `80px` collapsed (spring animation: stiffness 300, damping 30)
- **Background:** `bg-paper-100/80 dark:bg-obsidian-400/80 backdrop-blur-xl`
- **Border:** `border-r border-deep-teal-800/5 dark:border-white/5`
- **Position:** `h-screen sticky top-0 left-0 z-30 flex-shrink-0`
- **Logo:** Top section, `h-20 px-6`, uses `<Logo>` component with Cinzel font
- **Collapse state:** Persisted to localStorage (`sidebar-collapsed`)

**Navigation items (prototype — need renaming for production):**
```typescript
const navItems = [
  { icon: LayoutDashboard, label: 'Cockpit' },
  { icon: Cpu,             label: 'System' },
  { icon: Bot,             label: 'Agents' },    // → rename: 'Strategies'
  { icon: Wallet,          label: 'Portfolio' },
  { icon: LineChart,       label: 'Markets' },    // → rename: 'Regime'
  { icon: ShieldCheck,     label: 'Risk' },
  { icon: Bell,            label: 'Alerts' },
  { icon: History,         label: 'Trade History' },
];
// Production adds: Accounts, Settings, Backtest
```

**Active state:** Uses `motion.div` with `layoutId="activeNavIndicator"` for animated sliding background:
```typescript
// Active indicator classes:
"absolute inset-0 bg-deep-teal-800/5 dark:bg-white/10 rounded-xl"
// Active icon: "text-deep-teal-800 dark:text-turquoise-mist" strokeWidth={2}
// Active label: "text-deep-teal-800 dark:text-turquoise-mist"
// Inactive: "text-obsidian-400/60 dark:text-paper-100/60" with hover brightening
```

**Nav item button:** `rounded-xl` (not rounded-lg). Collapsed = `h-12 w-12 mx-auto justify-center`. Expanded = `px-4 py-3 space-x-3`.

**Mobile:** Slide-in drawer (`x: -100%` → `x: 0`) with backdrop `bg-obsidian-400/60 backdrop-blur-sm`. Width `w-72`. Always renders expanded regardless of desktop collapse state.

**Footer:** Theme toggle (Sun/Moon icon swap), collapse chevron, user profile with avatar and logout

### 5.3 Header — Verified

From Header.tsx. Scroll-reactive glass effect.

- **Height:** `h-16`
- **Padding:** `px-4 md:px-8`
- **Position:** `sticky top-0 z-40`
- **Background (default):** `bg-transparent`
- **Background (scrolled):** `bg-paper-100/80 dark:bg-obsidian-400/80 border-b border-deep-teal-800/5 dark:border-white/5` with `backdrop-blur(12px)` — animated via framer-motion on scroll > 10px
- **Left side:** Mobile hamburger trigger + breadcrumb (`Platform / {title}` using font-sans text-sm)
- **Right side actions (in order):**
  1. Search input (hidden on mobile): `w-64 lg:w-80` with `bg-deep-teal-800/5 dark:bg-white/5`
  2. "New Alert" button: `bg-deep-teal-800/5 dark:bg-white/5 text-xs font-medium` (hidden on mobile)
  3. Emergency button: `bg-orange-500/10 hover:bg-red-500/20 text-orange-500 hover:text-red-500` with AlertTriangle icon + red count badge
  4. Notifications bell: with unread dot indicator (`w-2 h-2 bg-loss rounded-full`)
  5. User avatar dropdown with divider line `border-l border-deep-teal-800/10 dark:border-white/10`

### 5.4 Content Area

- **Padding:** `p-4 md:p-8 lg:p-10` (responsive)
- **Max width:** `max-w-7xl mx-auto`
- **Scrolling:** `overflow-y-auto overflow-x-hidden custom-scrollbar`

### 5.5 Page Transitions

```javascript
// Framer Motion page transition
initial={{ opacity: 0, x: 20 }}
animate={{ opacity: 1, x: 0 }}
exit={{ opacity: 0, x: -20 }}
transition={{ duration: 0.2 }}
```

**Important:** Keep duration at 0.2s or less. Never let animations block data visibility during volatile markets.

### 5.6 Responsive Breakpoints

| Breakpoint | Behavior |
|------------|----------|
| `< md` (768px) | Sidebar hidden (hamburger), reduced padding, stack columns |
| `md-lg` | Sidebar collapsed (icons), 2-column grid |
| `>= lg` (1024px) | Sidebar expanded, full layout |
| `>= xl` (1280px) | Max width content, comfortable spacing |

---

## 6. SCROLLBAR STYLING

```css
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  @apply bg-deep-teal-800/20 rounded-full;
}
html.dark ::-webkit-scrollbar-thumb {
  @apply bg-white/10;
}
```

---

## 7. SELECTION & FOCUS STATES

- **Text selection:** `selection:bg-turquoise-mist/30`
- **Focus ring:** `focus:ring-2 focus:ring-turquoise/50 focus:outline-none`
- **Active/pressed:** Scale down slightly `active:scale-[0.98]`

---

## 8. COMPACT MODE

The prototype includes a compact mode toggle for information-dense viewing:

```css
body.compact {
  font-size: 0.95em;
}
body.compact .p-6 {
  padding: 1rem !important;
}
body.compact .gap-6 {
  gap: 1rem !important;
}
```

---

## 9. DARK MODE & THEME IMPLEMENTATION — Verified

From ThemeContext.tsx. The theme system manages **4 independent settings:**

1. **Mode** (light / dark / system) — class-based on `<html>`
2. **App Theme** (ocean / sapphire / emerald / onyx / amethyst) — `data-theme` attribute on `<html>`
3. **Compact Mode** — `compact` class on `<body>`
4. **Reduced Motion** — `MotionGlobalConfig.skipAnimations` from framer-motion

All 4 are persisted to localStorage under keys: `themeMode`, `appTheme`, `compactMode`, `reducedMotion`.

```typescript
// ThemeContext state shape
interface ThemeContextType {
  mode: 'light' | 'dark' | 'system';
  setMode: (mode: ThemeMode) => void;
  appTheme: 'ocean' | 'sapphire' | 'emerald' | 'onyx' | 'amethyst';
  setAppTheme: (theme: AppTheme) => void;
  compactMode: boolean;
  setCompactMode: (v: boolean) => void;
  reducedMotion: boolean;
  setReducedMotion: (v: boolean) => void;
}
```

**Mode application:**
- `system` mode listens to `prefers-color-scheme: dark` media query with event listener
- Applies `light` or `dark` class to `<html>` element
- Tailwind's `dark:` modifier handles all styling

**Theme application:**
- Sets `data-theme="ocean"` (etc.) on `<html>`
- CSS rules like `[data-theme="sapphire"]` override the `--accent-primary` variables

**Body base:**
```css
body {
  @apply bg-paper-100 text-obsidian-400 antialiased font-sans transition-colors duration-300;
}
html.dark body {
  @apply bg-obsidian-400 text-paper-100;
}
```

---

## 10. ANIMATION SYSTEM — Verified

### 10.1 Animation Library (animations.ts)

Referenced by Button.tsx, GlassCard.tsx, and page transitions. Production needs these constants:

```typescript
// Required exports from lib/animations.ts
export const smoothSpring = { type: "spring", stiffness: 300, damping: 30 };

export const hoverCard = {
  scale: 1.01,
  y: -2,
  transition: smoothSpring
};

// Page transition stagger helper
export function getStaggerDelay(index: number, baseDelay: number = 0.1): number {
  return index * baseDelay;
}
```

### 10.2 Keyframe Animations (Tailwind config)

```javascript
animation: {
  'fade-in': 'fadeIn 0.5s ease-out forwards',
  'slide-up': 'slideUp 0.5s ease-out forwards',
  'ping': 'ping 1s cubic-bezier(0, 0, 0.2, 1) infinite', // used by Badge pulsing dot
},
keyframes: {
  fadeIn: {
    '0%': { opacity: '0' },
    '100%': { opacity: '1' },
  },
  slideUp: {
    '0%': { opacity: '0', transform: 'translateY(20px)' },
    '100%': { opacity: '1', transform: 'translateY(0)' },
  }
}
```

### 10.3 Framer Motion Patterns Used

| Component | Animation | Config |
|-----------|-----------|--------|
| Button | `whileHover={{ scale: 1.02, y: -1 }}` + `whileTap={{ scale: 0.98 }}` | smoothSpring |
| GlassCard | `whileHover={hoverCard}` (when enableHover) | smoothSpring |
| MetricCard value | `initial={{ opacity: 0, y: 5 }}` → `animate={{ opacity: 1, y: 0 }}` | 0.3s delay |
| Sidebar active indicator | `layoutId="activeNavIndicator"` | spring stiffness:300 damping:30 |
| Sidebar mobile | `initial={{ x: "-100%" }}` → `animate={{ x: 0 }}` | spring damping:25 stiffness:200 |
| Header glass effect | `animate={{ backdropFilter, backgroundColor }}` on scroll | 0.2s duration |
| Page transitions | `initial={{ opacity: 0, x: 20 }}` → `animate={{ opacity: 1, x: 0 }}` | 0.2s |

---

## 11. DEPENDENCIES

Production frontend should use these exact versions (matching prototype):

```json
{
  "react": "18.3.1",
  "react-dom": "18.3.1",
  "lucide-react": "0.368.0",
  "clsx": "2.1.0",
  "framer-motion": "11.0.24",
  "tailwind-merge": "2.2.2",
  "recharts": "2.12.7"
}
```

**Icon library:** Lucide React (consistent, clean line icons matching the quiet luxury aesthetic)

---

## 12. CORRECTED NAVIGATION MAP

The prototype used "Agents" terminology. The production build must use PRD-correct terms:

| Prototype Name | Production Name | PRD Section |
|---------------|-----------------|-------------|
| Cockpit | **Cockpit** (keep) | §6.2 Default portfolio view |
| Agents | **Strategies** (rename) | §3.4 Strategy lifecycle |
| Agent Detail | **Strategy Detail** (rename) | §6.4 Strategy detail view |
| Portfolio | **Portfolio** (keep) | §6.2 Equity curve, performance |
| Markets | **Regime** (rename) | §6.2.2 Regime indicators |
| Risk | **Risk** (keep) | §4 Risk management |
| Alerts | **Alerts** (keep) | §8 Alerting system |
| Trade History | **Trade History** (keep) | §6.3.3 Trade distribution |
| System | **System** (keep) | §14 Health, uptime, status |
| Settings | **Settings** (keep) | §2.2 Configuration hierarchy |
| — | **Accounts** (add new) | §7 Account management |
| — | **Backtest** (add new) | §3.6 Backtest engine |
| Journal | *Remove or defer* | Not in MVP PRD |
| Notifications | *Merge into Alerts* | §8.5 Summaries |

---

## 13. ADDITIONAL REFERENCE FILES

All Priority 1 files have been received and their patterns extracted into this guide (Sections 4 and 5 marked "Verified"). The following Priority 2 files would add further detail if needed:

### Still Useful (extract page layouts):
1. **`components/pages/RiskPage.tsx`** (22KB) — Risk gauge/meter visual patterns ✅ Received
2. **`components/pages/CockpitPage.tsx`** (26KB) — Main dashboard widget arrangement ✅ Received
3. **`components/dashboard/EmergencyPanel.tsx`** (26KB) — Kill switch UI ✅ Received
4. **`components/dashboard/charts/AreaChart.tsx`** — Chart configuration
5. **`components/dashboard/charts/SparklineChart.tsx`** — Inline chart pattern
6. **`lib/animations.ts`** — Full animation constants (smoothSpring, hoverCard already documented above)

All Priority 1 core files received and documented:
- ✅ GlassCard.tsx → Section 4.1
- ✅ MetricCard.tsx → Section 4.2
- ✅ Badge.tsx → Section 4.3
- ✅ Button.tsx → Section 4.4
- ✅ PositionsTable.tsx → Section 4.5
- ✅ MarketRegimePanel.tsx → Section 5.0
- ✅ Sidebar.tsx → Section 5.2
- ✅ Header.tsx → Section 5.3
- ✅ ThemeContext.tsx → Section 9
- ✅ utils.ts → Section 4.2 (formatCurrency, formatNumber, cn helper)

---

## 14. REFERENCE FILE INVENTORY

The complete AI Studio prototype is stored in `docs/design/reference/` for visual lookup. Here is the full file tree:

```
docs/design/reference/
├── components/
│   ├── dashboard/
│   │   ├── charts/
│   │   │   ├── AreaChart.tsx          (8KB)
│   │   │   ├── BenchmarkChart.tsx     (6KB)
│   │   │   ├── DonutChart.tsx         (7KB)
│   │   │   ├── SparklineChart.tsx     (4KB)
│   │   │   └── SVGAreaChart.tsx       (9KB)
│   │   ├── ActivityFeed.tsx           (9KB)
│   │   ├── AgentCard.tsx              (8KB)  → rename: StrategyCard
│   │   ├── AgentGrid.tsx              (3KB)  → rename: StrategyGrid
│   │   ├── AlertModal.tsx             (15KB)
│   │   ├── DataTable.tsx              (8KB)
│   │   ├── EmergencyPanel.tsx         (26KB) ★ Key reference
│   │   ├── ExportModal.tsx            (6KB)
│   │   ├── InviteUserModal.tsx        (8KB)  → Remove (multi-user not in MVP)
│   │   ├── MarketRegimePanel.tsx      (5KB)  ★ Key reference
│   │   ├── MarketTicker.tsx           (4KB)
│   │   ├── OrderEntryModal.tsx        (1KB)
│   │   ├── PositionDrawer.tsx         (15KB) ★ Key reference
│   │   ├── PositionsTable.tsx         (8KB)  ★ Key reference
│   │   └── Watchlist.tsx              (8KB)
│   ├── layout/
│   │   ├── Breadcrumbs.tsx            (2KB)
│   │   ├── Header.tsx                 (10KB) ★ Key reference
│   │   ├── NotificationsPanel.tsx     (16KB)
│   │   ├── PageHeader.tsx             (2KB)
│   │   ├── Section.tsx                (4KB)
│   │   └── Sidebar.tsx                (12KB) ★ Key reference
│   ├── pages/
│   │   ├── AgentDetailPage.tsx        (23KB) → rename: StrategyDetailPage
│   │   ├── AgentsPage.tsx             (31KB) → rename: StrategiesPage
│   │   ├── AlertsPage.tsx             (22KB) ★ Key reference
│   │   ├── CockpitPage.tsx            (26KB) ★ Key reference
│   │   ├── JournalPage.tsx            (1KB)  → Remove (not in MVP)
│   │   ├── MarketsPage.tsx            (18KB) → rename: RegimePage
│   │   ├── NotificationsPage.tsx      (19KB)
│   │   ├── PortfolioPage.tsx          (16KB) ★ Key reference
│   │   ├── RiskPage.tsx               (22KB) ★ Key reference
│   │   ├── SettingsPage.tsx           (43KB) ★ Key reference
│   │   ├── SystemPage.tsx             (25KB) ★ Key reference
│   │   └── TradeHistoryPage.tsx       (24KB) ★ Key reference
│   └── ui/
│       ├── Avatar.tsx                 (3KB)
│       ├── Badge.tsx                  (2KB)  ★ Key reference
│       ├── Button.tsx                 (4KB)  ★ Key reference
│       ├── Dropdown.tsx               (8KB)
│       ├── EmptyState.tsx             (2KB)
│       ├── ErrorBoundary.tsx          (3KB)
│       ├── GlassCard.tsx              (2KB)  ★ Key reference
│       ├── Input.tsx                  (5KB)
│       ├── KeyboardShortcuts.tsx      (4KB)
│       ├── LoadingState.tsx           (3KB)
│       ├── Logo.tsx                   (2KB)
│       ├── MetricCard.tsx             (6KB)  ★ Key reference
│       ├── Modal.tsx                  (5KB)
│       ├── Progress.tsx               (3KB)
│       ├── SearchInput.tsx            (2KB)
│       ├── Skeleton.tsx               (1KB)
│       ├── Tabs.tsx                   (7KB)
│       ├── Toast.tsx                  (5KB)
│       ├── Toggle.tsx                 (2KB)
│       └── Tooltip.tsx                (6KB)
├── contexts/
│   ├── DashboardContext.tsx            (4KB)
│   ├── ThemeContext.tsx                (3KB)  ★ Key reference
│   └── ToastContext.tsx                (2KB)
├── hooks/
│   ├── useGlobalShortcuts.ts
│   └── useRealtimeSimulation.ts
├── lib/
│   ├── animations.ts
│   └── utils.ts                       ★ Key reference
├── types/
│   └── index.ts
├── App.tsx                            (5KB)
├── index.html                         (8KB)  ★★ MOST IMPORTANT — full design tokens
├── index.tsx                          (1KB)
├── metadata.json                      (1KB)
├── package.json                       (1KB)
├── tsconfig.json                      (1KB)
└── vite.config.ts                     (1KB)
```

**★ = Key reference files** — consult these first when building production components
**★★ = Critical** — contains the complete Tailwind config and CSS variable system

---

*Last updated: February 2026*
*Source: AI Studio prototype, Paravant_WebApp project*
