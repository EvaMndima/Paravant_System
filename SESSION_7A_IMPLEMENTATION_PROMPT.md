# SESSION 7A: FRONTEND FOUNDATION — PROJECT SETUP
## Weeks 13-14 | 6 Tasks | ~17 Hours | React Infrastructure
**Objective:** Build production-ready frontend infrastructure: React project, UI component library, design system, API client, and data hooks with SSE integration for real-time updates.

**Duration:** ~17 hours
**Delivery:** All infrastructure complete, foundation ready for page development in Session 7B
**Tool Strategy:** Claude Code for all infrastructure tasks (Vite config, API client, data hooks)

---

## ⚡ QUICK START

```bash
# No pre-work needed — start with Task 7.1.1
# All tasks in this session build sequentially
# Recommended execution: 7.1.1 → 7.1.2 → 7.1.3 → 7.1.4 → 7.1.5 → 7.1.6

# Parallel opportunities:
#   - Tasks 7.1.2 (UI components) can start while 7.1.1 completes
#   - Task 7.1.4 (Theme) can start after 7.1.1
#   - Task 7.1.5 (API client) independent after 7.1.1
```

---

## TASK 7.1.1: Initialize Frontend Project

**Effort:** 2 hours
**Status:** Not Started
**Dependencies:** None (can run parallel with Phase 6)
**Tool:** Claude Code

### Deliverables

Create a complete Vite + React + TypeScript + Tailwind project with design system configuration:

```bash
# 1. Create Vite React project at project root
npm create vite@latest frontend -- --template react-ts

# 2. Install core dependencies (exact versions from DESIGN_GUIDE.md)
cd frontend
npm install react-router-dom@6 lucide-react@0.263.1 clsx tailwind-merge \
  framer-motion@11 recharts@2 @tanstack/react-query@5

# 3. Install dev dependencies
npm install -D tailwindcss postcss autoprefixer @types/react @types/react-dom \
  typescript@latest @typescript-eslint/parser @typescript-eslint/eslint-plugin

# 4. Initialize Tailwind
npx tailwindcss init -p
```

### Configuration Files (5 required)

#### 1. `frontend/tailwind.config.js` — Complete color system

```javascript
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Base colors from DESIGN_GUIDE §2.4
        'deep-teal': {
          50: '#f7fdfc',
          100: '#ebf8f7',
          200: '#cceeed',
          300: '#a8dfe4',
          400: '#6fc4d0',
          500: '#45a3ba',  // Primary accent
          600: '#348297',
          700: '#2a6577',
          800: '#24515f',
          900: '#1e404a',
        },
        'obsidian': {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d0d0d0',
          400: '#a3a3a3',
          500: '#707070',  // Dark text
          600: '#404040',
          700: '#262626',
          800: '#171717',
          900: '#0a0a0a',
        },
        'paper': {
          50: '#fefdfb',
          100: '#fdfbf8',
          200: '#faf5ef',
          300: '#f5ebe2',
          400: '#e8dace',
          500: '#d9c5ad',  // Light background
          600: '#c4a88c',
          700: '#a88a6b',
          800: '#8a6f54',
          900: '#6b5642',
        },
        'turquoise-mist': {
          50: '#f0fdfb',
          100: '#d9f5f0',
          200: '#a8e7e1',
          300: '#6dd5ca',  // Accent highlight
          400: '#45bfb0',
          500: '#2fa699',
          600: '#2a8a80',
          700: '#246f67',
          800: '#1f5954',
          900: '#19443f',
        },
        // Price colors (universal, same in light/dark)
        'gain': '#10b981',   // Green for positive P&L
        'loss': '#ef4444',   // Red for negative P&L
        'neutral': '#f59e0b', // Amber for neutral/pending
      },
      fontFamily: {
        'serif': ['Cinzel', 'serif'],  // Display headings
        'sans': ['Inter', 'sans-serif'],  // Body text
        'mono': ['JetBrains Mono', 'monospace'],  // Numbers/data
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
      },
      backdropBlur: {
        'xl': '20px',
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
      },
    },
  },
  plugins: [],
};
```

#### 2. `frontend/src/index.css` — CSS variables and utilities

```css
/* ========== GOOGLE FONTS IMPORTS ========== */
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ========== LIGHT MODE (DEFAULT) ========== */
:root {
  --color-background: #fdfbf8;      /* paper-100 */
  --color-surface: #f5ebe2;         /* paper-200 */
  --color-surface-alt: #ebf8f7;     /* deep-teal-100 */
  --color-text-primary: #1e404a;    /* deep-teal-900 */
  --color-text-secondary: #707070;  /* obsidian-500 */
  --color-text-tertiary: #a3a3a3;   /* obsidian-400 */
  --color-border: #a8dfe4;          /* deep-teal-300 */
  --color-border-subtle: #cceeed;   /* deep-teal-200 */
  --color-accent: #45a3ba;          /* deep-teal-500 */
  --color-accent-light: #6dd5ca;    /* turquoise-mist-300 */
  --color-gain: #10b981;            /* Green (universal) */
  --color-loss: #ef4444;            /* Red (universal) */
  --color-neutral: #f59e0b;         /* Amber (universal) */
}

/* ========== DARK MODE ========== */
@media (prefers-color-scheme: dark),
       [data-theme-mode="dark"] .dark {
  --color-background: #0a0a0a;      /* obsidian-900 */
  --color-surface: #1e404a;         /* deep-teal-900 */
  --color-surface-alt: #24515f;     /* deep-teal-800 */
  --color-text-primary: #fdfbf8;    /* paper-100 */
  --color-text-secondary: #d0d0d0;  /* obsidian-300 */
  --color-text-tertiary: #a3a3a3;   /* obsidian-400 */
  --color-border: #246f67;          /* turquoise-mist-700 */
  --color-border-subtle: #1f5954;   /* turquoise-mist-800 */
  --color-accent: #6dd5ca;          /* turquoise-mist-300 */
  --color-accent-light: #45bfb0;    /* turquoise-mist-400 */
  --color-gain: #10b981;            /* Green (universal) */
  --color-loss: #ef4444;            /* Red (universal) */
  --color-neutral: #f59e0b;         /* Amber (universal) */
}

/* ========== THEME VARIANTS (5 accent themes) ========== */

/* Ocean (default turquoise) */
html {
  --accent-primary: #45a3ba;
  --accent-secondary: #6dd5ca;
}

/* Sapphire (blue) */
[data-theme="sapphire"] {
  --accent-primary: #0ea5e9;
  --accent-secondary: #38bdf8;
}

/* Emerald (deeper green) */
[data-theme="emerald"] {
  --accent-primary: #059669;
  --accent-secondary: #10b981;
}

/* Amber (warm golden) */
[data-theme="amber"] {
  --accent-primary: #d97706;
  --accent-secondary: #f59e0b;
}

/* Slate (cool gray) */
[data-theme="slate"] {
  --accent-primary: #64748b;
  --accent-secondary: #94a3b8;
}

/* ========== GLASS-MORPHISM UTILITIES ========== */

.glass-panel {
  background: rgba(255, 251, 248, 0.8);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(69, 163, 186, 0.1);
}

.dark .glass-panel {
  background: rgba(30, 64, 74, 0.6);
  border-color: rgba(109, 213, 202, 0.1);
}

.glass-panel-elevated {
  @apply glass-panel shadow-lg shadow-deep-teal-800/5;
}

.dark .glass-panel-elevated {
  @apply glass-panel shadow-lg shadow-deep-teal-800/20;
}

.glass-panel-subtle {
  background: rgba(255, 251, 248, 0.4);
  backdrop-filter: blur(10px);
  border: 1px solid transparent;
}

.dark .glass-panel-subtle {
  background: rgba(30, 64, 74, 0.3);
}

.glass-panel-dark {
  background: rgba(30, 64, 74, 0.8);
  border-color: rgba(109, 213, 202, 0.15);
}

/* ========== CUSTOM SCROLLBARS ========== */

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(69, 163, 186, 0.4);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(69, 163, 186, 0.6);
}

.dark ::-webkit-scrollbar-thumb {
  background: rgba(109, 213, 202, 0.3);
}

.dark ::-webkit-scrollbar-thumb:hover {
  background: rgba(109, 213, 202, 0.5);
}

/* ========== TAILWIND DIRECTIVES ========== */

@tailwind base;
@tailwind components;
@tailwind utilities;

/* Global styles */
html {
  scroll-behavior: smooth;
}

body {
  @apply bg-paper-100 text-obsidian-900 dark:bg-obsidian-900 dark:text-paper-100 transition-colors duration-200;
}

/* Reduce motion if requested */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

#### 3. `frontend/vite.config.ts` — Build and dev config

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // SSE endpoint — disable response buffering
      '/api/v1/events/stream': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            proxyRes.headers['X-Accel-Buffering'] = 'no';
            proxyRes.headers['Cache-Control'] = 'no-cache';
          });
        },
      },
    },
  },
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
})
```

#### 4. `frontend/src/lib/utils.ts` — Shared utility functions

```typescript
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatNumber(value: number, decimals: number = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatPercent(value: number, decimals: number = 2): string {
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100)  // Convert to decimal
}

export function formatDuration(hours: number): string {
  const h = Math.floor(hours)
  const m = Math.round((hours - h) * 60)
  return `${h}h ${m}m`
}

// Color utility for gain/loss values
export function getPnLColor(value: number): string {
  if (value > 0) return 'text-gain'
  if (value < 0) return 'text-loss'
  return 'text-neutral'
}

// Abbreviate large numbers
export function formatCompact(value: number): string {
  if (Math.abs(value) >= 1e9) {
    return (value / 1e9).toFixed(1) + 'B'
  }
  if (Math.abs(value) >= 1e6) {
    return (value / 1e6).toFixed(1) + 'M'
  }
  if (Math.abs(value) >= 1e3) {
    return (value / 1e3).toFixed(1) + 'K'
  }
  return value.toFixed(0)
}
```

#### 5. `frontend/src/lib/animations.ts` — Shared animation configs

```typescript
export const smoothSpring = {
  type: 'spring' as const,
  stiffness: 300,
  damping: 30,
}

export const gentleFade = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: 0.3 },
}

export const slideUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { type: 'spring', stiffness: 300, damping: 30 },
}

export const slideDown = {
  initial: { opacity: 0, y: -20 },
  animate: { opacity: 1, y: 0 },
  transition: { type: 'spring', stiffness: 300, damping: 30 },
}

export const modalBackdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
}

export const modalPanelVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: { opacity: 1, scale: 1, y: 0 },
  exit: { opacity: 0, scale: 0.95, y: 20 },
}
```

### Acceptance Criteria

- [ ] `npm run dev` starts on `http://localhost:3000`
- [ ] Vite dev proxy forwards `/api/*` to backend without errors
- [ ] SSE dev proxy handles `/api/v1/events/stream` without buffering
- [ ] Tailwind classes render correctly (test with a `glass-panel` div)
- [ ] CSS variables resolve in both light and dark mode (inspect element shows colors)
- [ ] All 3 fonts load without warnings (Cinzel, Inter, JetBrains Mono)
- [ ] All 5 accent theme variables apply correctly
- [ ] `cn()` helper merges classes correctly (test: `cn('px-2', 'px-4')` → `px-4`)
- [ ] Format functions produce correct output for edge cases (0, negatives, large numbers)
- [ ] No TypeScript errors in `src/` directory

---

## TASK 7.1.2: Create UI Component Library — Foundation

**Effort:** 3.5 hours
**Status:** Not Started
**Dependencies:** [7.1.1]
**Tool:** Claude Code (Antigravity can supplement visual scaffolding, but precise component definitions required)

### 10 Core Components

All components in `src/components/ui/`:

#### 1. GlassCard.tsx

```typescript
import React from 'react'
import { cn } from '@/lib/utils'

interface GlassCardProps {
  variant?: 'default' | 'elevated' | 'subtle' | 'dark'
  padding?: 'sm' | 'md' | 'lg'
  className?: string
  children: React.ReactNode
}

export const GlassCard: React.FC<GlassCardProps> = ({
  variant = 'default',
  padding = 'md',
  className,
  children,
}) => {
  const paddingClass = {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  }[padding]

  const variantClass = {
    default: 'glass-panel',
    elevated: 'glass-panel-elevated',
    subtle: 'glass-panel-subtle',
    dark: 'glass-panel-dark',
  }[variant]

  return (
    <div className={cn('rounded-xl', paddingClass, variantClass, className)}>
      {children}
    </div>
  )
}
```

#### 2. Button.tsx

```typescript
import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'emergency'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  children: React.ReactNode
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  className,
  disabled,
  children,
  ...props
}) => {
  const baseClass = 'font-medium rounded-xl font-sans transition-all'

  const sizeClass = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  }[size]

  const variantClass = {
    primary: 'bg-deep-teal-500 text-white hover:bg-deep-teal-600 disabled:bg-obsidian-300',
    secondary: 'bg-deep-teal-100 text-deep-teal-900 hover:bg-deep-teal-200 dark:bg-deep-teal-800 dark:text-paper-100',
    danger: 'bg-loss text-white hover:bg-red-600',
    ghost: 'bg-transparent text-deep-teal-500 hover:bg-deep-teal-50 dark:hover:bg-deep-teal-900/30',
    emergency: 'bg-loss text-white hover:bg-red-600 animate-pulse',
  }[variant]

  return (
    <motion.button
      whileHover={!disabled && !isLoading ? { scale: 1.02, y: -1 } : {}}
      className={cn(baseClass, sizeClass, variantClass, className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <div className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" />
      ) : (
        children
      )}
    </motion.button>
  )
}
```

#### 3. Badge.tsx

```typescript
import React from 'react'
import { cn } from '@/lib/utils'

interface BadgeProps {
  variant?: 'success' | 'danger' | 'warning' | 'info' | 'neutral'
  withDot?: boolean
  className?: string
  children: React.ReactNode
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'neutral',
  withDot = false,
  className,
  children,
}) => {
  const variantClass = {
    success: 'bg-gain/10 text-gain',
    danger: 'bg-loss/10 text-loss',
    warning: 'bg-neutral/10 text-neutral',
    info: 'bg-deep-teal-100 text-deep-teal-700 dark:bg-deep-teal-900 dark:text-deep-teal-300',
    neutral: 'bg-obsidian-100 text-obsidian-700 dark:bg-obsidian-800 dark:text-obsidian-300',
  }[variant]

  const dotColor = {
    success: 'bg-gain',
    danger: 'bg-loss',
    warning: 'bg-neutral',
    info: 'bg-deep-teal-500',
    neutral: 'bg-obsidian-500',
  }[variant]

  return (
    <span className={cn('inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium', variantClass, className)}>
      {withDot && <span className={cn('w-1.5 h-1.5 rounded-full', dotColor)} />}
      {children}
    </span>
  )
}
```

#### 4. MetricCard.tsx

```typescript
import React from 'react'
import { GlassCard } from './GlassCard'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  label: string
  value: string | number
  icon?: React.ReactNode
  sparkline?: number[]
  sparklineColor?: string
  change?: {
    value: number
    isPositive: boolean
  }
  className?: string
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  icon,
  sparkline,
  sparklineColor,
  change,
  className,
}) => {
  return (
    <GlassCard variant="elevated" padding="md" className={cn('min-h-[140px] relative', className)}>
      <div className="flex items-start justify-between mb-3">
        <label className="text-xs font-mono font-bold uppercase tracking-widest text-obsidian-600 dark:text-obsidian-300">
          {label}
        </label>
        {icon && (
          <div className="p-1.5 rounded-lg backdrop-blur-sm bg-deep-teal-100/50 dark:bg-deep-teal-900/30">
            {icon}
          </div>
        )}
      </div>

      <div className="mb-4">
        <div className="font-mono font-medium tracking-tighter tabular-nums text-3xl text-obsidian-900 dark:text-paper-100 mb-1">
          {value}
        </div>
        {change && (
          <div className={cn('text-xs font-mono', change.isPositive ? 'text-gain' : 'text-loss')}>
            {change.isPositive ? '+' : ''}{change.value.toFixed(2)}%
          </div>
        )}
      </div>

      {sparkline && (
        <div className="absolute bottom-0 left-0 right-0 h-20 opacity-30 pointer-events-none">
          <svg className="w-full h-full" preserveAspectRatio="none" viewBox={`0 0 ${sparkline.length} ${Math.max(...sparkline) || 1}`}>
            <defs>
              <linearGradient id={`sparkline-${label}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={sparklineColor || 'currentColor'} stopOpacity="0.4" />
                <stop offset="100%" stopColor={sparklineColor || 'currentColor'} stopOpacity="0" />
              </linearGradient>
            </defs>
            <polyline
              points={sparkline.map((v, i) => `${i},${v}`).join(' ')}
              fill={`url(#sparkline-${label})`}
              stroke={sparklineColor || 'currentColor'}
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
        </div>
      )}
    </GlassCard>
  )
}
```

#### 5. Input.tsx

```typescript
import React from 'react'
import { cn } from '@/lib/utils'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  isLoading?: boolean
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  className,
  disabled,
  ...props
}) => {
  return (
    <div>
      {label && <label className="block text-sm font-medium mb-2">{label}</label>}
      <input
        className={cn(
          'w-full px-4 py-2 rounded-lg glass-panel',
          'focus:outline-none focus:ring-2 focus:ring-deep-teal-500',
          error ? 'ring-2 ring-loss' : '',
          disabled ? 'opacity-50 cursor-not-allowed' : '',
          className
        )}
        disabled={disabled}
        {...props}
      />
      {error && <p className="text-sm text-loss mt-1">{error}</p>}
      {helperText && <p className="text-sm text-obsidian-500 dark:text-obsidian-400 mt-1">{helperText}</p>}
    </div>
  )
}
```

#### 6. Select.tsx

```typescript
import React from 'react'
import { cn } from '@/lib/utils'

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  options: Array<{ value: string; label: string }>
  error?: string
}

export const Select: React.FC<SelectProps> = ({
  label,
  options,
  error,
  className,
  ...props
}) => {
  return (
    <div>
      {label && <label className="block text-sm font-medium mb-2">{label}</label>}
      <select
        className={cn(
          'w-full px-4 py-2 rounded-lg glass-panel',
          'focus:outline-none focus:ring-2 focus:ring-deep-teal-500',
          error ? 'ring-2 ring-loss' : '',
          className
        )}
        {...props}
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      {error && <p className="text-sm text-loss mt-1">{error}</p>}
    </div>
  )
}
```

#### 7. Toggle.tsx

```typescript
import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
}

export const Toggle: React.FC<ToggleProps> = ({
  checked,
  onChange,
  label,
  disabled,
}) => {
  return (
    <label className="flex items-center gap-3 cursor-pointer">
      <div
        className={cn(
          'relative w-12 h-6 rounded-full transition-colors',
          checked ? 'bg-gain' : 'bg-obsidian-300 dark:bg-obsidian-700',
          disabled ? 'opacity-50 cursor-not-allowed' : ''
        )}
        onClick={() => !disabled && onChange(!checked)}
      >
        <motion.div
          className="absolute top-1 left-1 w-4 h-4 bg-white rounded-full"
          animate={{ x: checked ? 24 : 0 }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        />
      </div>
      {label && <span className="text-sm font-medium">{label}</span>}
    </label>
  )
}
```

#### 8. Modal.tsx

```typescript
import React, { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl'
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  maxWidth = 'md',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'auto'
    }
  }, [isOpen, onClose])

  const maxWidthClass = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  }[maxWidth]

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className={cn('fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50', maxWidthClass)}
          >
            <div className="glass-panel-elevated rounded-xl p-6 max-h-[90vh] overflow-y-auto">
              {title && <h2 className="text-xl font-serif mb-4">{title}</h2>}
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
```

#### 9. Skeleton.tsx

```typescript
import React from 'react'
import { cn } from '@/lib/utils'

interface SkeletonProps {
  className?: string
  variant?: 'default' | 'text' | 'circle'
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = 'default',
}) => {
  const baseClass = 'bg-deep-teal-800/5 dark:bg-white/5 animate-pulse rounded'
  const variantClass = {
    default: 'h-6',
    text: 'h-4',
    circle: 'w-10 h-10 rounded-full',
  }[variant]

  return <div className={cn(baseClass, variantClass, className)} />
}
```

#### 10. DataTable.tsx

```typescript
import React from 'react'
import { GlassCard } from './GlassCard'
import { cn } from '@/lib/utils'

interface Column<T> {
  key: keyof T
  label: string
  sortable?: boolean
  render?: (value: any, row: T) => React.ReactNode
}

interface DataTableProps<T extends { id: string }> {
  columns: Column<T>[]
  data: T[]
  onRowClick?: (row: T) => void
  loading?: boolean
}

export function DataTable<T extends { id: string }>({
  columns,
  data,
  onRowClick,
  loading,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = React.useState<keyof T | null>(null)
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('asc')

  const handleSort = (key: keyof T) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sortedData = React.useMemo(() => {
    if (!sortKey) return data
    return [...data].sort((a, b) => {
      const aVal = a[sortKey]
      const bVal = b[sortKey]
      const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [data, sortKey, sortDir])

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-deep-teal-200 dark:border-deep-teal-800">
            {columns.map(col => (
              <th
                key={String(col.key)}
                className="px-4 py-3 text-left font-medium text-obsidian-600 dark:text-obsidian-300 cursor-pointer hover:bg-deep-teal-50 dark:hover:bg-deep-teal-900/30"
                onClick={() => col.sortable && handleSort(col.key)}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map(row => (
            <tr
              key={row.id}
              className="border-b border-deep-teal-100 dark:border-deep-teal-900 hover:bg-deep-teal-50 dark:hover:bg-deep-teal-900/20 cursor-pointer"
              onClick={() => onRowClick?.(row)}
            >
              {columns.map(col => (
                <td key={String(col.key)} className="px-4 py-3 font-mono">
                  {col.render ? col.render(row[col.key], row) : String(row[col.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

### Acceptance Criteria

- [ ] All 10 components build without errors
- [ ] Components support light and dark mode via CSS variables
- [ ] Button hover animation works (scale 1.02, y: -1)
- [ ] MetricCard renders with sparkline zone properly positioned
- [ ] GlassCard 4 variants visually distinct in browser
- [ ] Badge uses translucent backgrounds (not solid fills)
- [ ] All components accept `className` prop for composition
- [ ] Modal implements focus trapping (Tab/Shift+Tab cycles within modal)
- [ ] Modal returns focus to trigger element on close
- [ ] No information conveyed by color alone (badges use icons + text + color together)

---

## TASK 7.1.3: Create Layout Shell

**Effort:** 3 hours
**Status:** Not Started
**Dependencies:** [7.1.2]
**Tool:** Antigravity (visual) → Claude Code (routing)

### Components to build

1. **Sidebar.tsx** — Navigation with collapse/expand, kill switch at bottom
2. **Header.tsx** — Regime selector, notifications, theme toggle
3. **MainLayout.tsx** — Wrapper for sidebar + header + content area
4. **React Router setup** in App.tsx with routes for all pages

```typescript
// App.tsx — Router configuration
const routes = [
  { path: '/', element: <CockpitPage /> },
  { path: '/portfolio', element: <PortfolioPage /> },
  { path: '/strategies', element: <StrategiesListPage /> },
  { path: '/strategies/:id', element: <StrategyDetailPage /> },
  { path: '/risk', element: <RiskPage /> },
  { path: '/orders', element: <OrdersPage /> },
  { path: '/alerts', element: <AlertsPage /> },
  { path: '/accounts', element: <AccountsPage /> },
  { path: '/settings', element: <SettingsPage /> },
  { path: '/backtest', element: <BacktestPage /> },
]
```

### Acceptance Criteria

- [ ] Sidebar animates collapse/expand smoothly
- [ ] Active route highlighted in sidebar
- [ ] Kill switch button always visible at sidebar bottom
- [ ] Header displays regime badge, mode badge, notification bell
- [ ] Dark mode toggle in header works
- [ ] Content area max-width constrained (max-w-7xl)
- [ ] React Router navigates to all 10 pages without errors
- [ ] Responsive: sidebar collapses on tablet, hidden on mobile

---

## TASK 7.1.4: Implement Theme System

**Effort:** 1.5 hours
**Status:** Not Started
**Dependencies:** [7.1.1, 7.1.3]
**Tool:** Claude Code

### ThemeContext.tsx

```typescript
interface ThemeState {
  mode: 'light' | 'dark' | 'system'
  accent: 'ocean' | 'sapphire' | 'emerald' | 'amber' | 'slate'
  compactMode: boolean
  reducedMotion: boolean
}

const ThemeProvider: React.FC = ({ children }) => {
  // 1. Load from localStorage (persist across reloads)
  // 2. Apply 'dark' class to <html> element
  // 3. Apply 'data-theme={accent}' to <html>
  // 4. Respect prefers-reduced-motion
  // 5. Respect prefers-color-scheme for 'system' mode
}
```

### Acceptance Criteria

- [ ] Light/dark/system mode toggles correctly
- [ ] System mode follows OS preference in real-time
- [ ] 5 accent themes change accent colors
- [ ] Compact mode reduces padding (condensed layout)
- [ ] Reduced motion disables framer-motion animations
- [ ] All preferences persist across page reloads
- [ ] No flash of wrong theme on initial load (check page refresh)

---

## TASK 7.1.5: Build API Client Layer

**Effort:** 2.5 hours
**Status:** Not Started
**Dependencies:** [7.1.1]
**Tool:** Claude Code

### `src/lib/api.ts` — Typed API client for all Phase 6 endpoints

```typescript
class ApiClient {
  private baseUrl = '/api/v1'

  async get<T>(path: string, params?: Record<string, string>): Promise<T>
  async post<T>(path: string, body?: unknown): Promise<T>
  async put<T>(path: string, body?: unknown): Promise<T>
  async delete<T>(path: string): Promise<T>
}

export const api = {
  system: { getStatus, start, stop, getRegime, setRegime },
  dashboard: { getSummary, getEquity, getPerformance, getRecentTrades, getAlerts, getPositions },
  strategies: { list, get, create, update, pause, resume },
  accounts: { list, get, getBalance, getPnl },
  risk: { getStatus, getKillSwitch, activateKillSwitch, deactivateKillSwitch },
  pnl: { daily, monthly, byStrategy, heatmap },
  health: { quick, detailed },
}
```

### `src/types/api.ts` — All TypeScript types matching Phase 6 Pydantic models

Every Phase 6 response has a corresponding TypeScript type:
- `SystemStatus`, `RegimeInfo`, `DashboardSummary`, `Position`, `Strategy`, `Alert`, etc.

### Acceptance Criteria

- [ ] All Phase 6 endpoints have typed API methods
- [ ] Error handling produces clear `ApiError` objects
- [ ] TypeScript types match backend Pydantic models exactly
- [ ] Base URL configurable via environment variable
- [ ] Works with Vite proxy in development
- [ ] Works with relative URLs in production (same-origin)

---

## TASK 7.1.6: Build Data Hooks (SSE + Tiered Polling)

**Effort:** 4 hours
**Status:** Not Started
**Dependencies:** [7.1.5, Phase 6 Task 6.2.8]
**Tool:** Claude Code

### Architecture: Two-tier data strategy

**Tier 1 (SSE): Real-time state changes**
- Single persistent HTTP connection for: kill switch, positions, alerts, risk status, regime
- Cost: ~1 connection per tab, near-zero request overhead
- Update pattern: `setQueryData` (full state) or `invalidateQueries` (partial, needs fetch)

**Tier 2 (REST polling): Slow-changing aggregates**
- Dashboard summary: 30s (expensive computation)
- Equity curve: 120s (historical data, slowly-changing)
- Strategies: 60s (rarely changes)
- P&L heatmap: 300s (daily granularity)
- **Visibility-aware: stops when browser tab hidden, resumes when visible**

**Tier 3 (On-demand): No background polling**
- Strategy detail, account detail, backtest results
- Fetch once on page visit, cache until navigation

### `src/hooks/useEventStream.ts` — SSE connection

```typescript
export function useEventStream(apiKey: string) {
  // 1. Establish EventSource connection at app mount
  // 2. Route SSE events to react-query cache
  // 3. Exponential backoff on disconnect: 1s → 2s → 4s → max 30s
  // 4. Expose connection status for health banner
  // 5. Close EventSource on unmount
}
```

**SSE event handlers:**
- `kill_switch_changed` → `setQueryData(['risk', 'kill-switch'], data)`
- `system_status_changed` → `setQueryData(['system', 'status'], data)`
- `position_updated` → `invalidateQueries(['dashboard', 'positions'])`
- `alert_created` → `invalidateQueries(['dashboard', 'alerts'])`
- `risk_status_changed` → `setQueryData(['risk', 'status'], data)`
- `regime_changed` → `setQueryData(['system', 'regime'], data)` + invalidate dashboard

### Data hooks (by polling tier)

**Tier 1 (SSE-driven, initial fetch only):**
- `useKillSwitch()` — `staleTime: Infinity`, `refetchOnWindowFocus: true`
- `useSystemStatus()` — same pattern
- `useRiskStatus()` — same pattern
- `usePositions()` — invalidated on SSE event
- `useAlerts()` — invalidated on SSE event
- `useRegime()` — includes `setRegime` mutation

**Tier 2 (REST polls, visibility-aware):**
- `useDashboardSummary()` — refetch 30s (hidden → false)
- `useEquityCurve()` — refetch 120s (hidden → false)
- `useStrategies()` — refetch 60s (hidden → false)
- `usePnlHeatmap()` — refetch 300s (hidden → false)
- `usePnlByStrategy()` — refetch 300s (hidden → false)

**Tier 3 (On-demand, no polling):**
- `useStrategy(id)` — no `refetchInterval`
- `useAccount(id)` — no `refetchInterval`
- `useBacktestResult(id)` — `staleTime: Infinity` (immutable)

### QueryClient provider in App.tsx

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
      refetchOnWindowFocus: false,  // Default off
    },
  },
})
```

### Acceptance Criteria

- [ ] SSE connection established on app mount
- [ ] Kill switch, system status, risk status update instantly via SSE (< 100ms)
- [ ] Positions and alerts queries invalidated and re-fetched on SSE events
- [ ] Tier 2 polls stop when browser tab is hidden (`document.hidden` check)
- [ ] Tier 2 polls resume when tab becomes visible
- [ ] Tier 3 hooks fetch once on mount, no background polling
- [ ] SSE reconnects with exponential backoff (1s → 2s → 4s → max 30s)
- [ ] SSE connection status exposed for health banner (from `useEventStream`)
- [ ] No memory leaks — EventSource closed on unmount
- [ ] All hooks return `{ data, isLoading, error }` consistently
- [ ] Mutations invalidate relevant queries (e.g., `setRegime` invalidates regime + dashboard)

---

## ✅ COMPLETION CHECKLIST

**Session 7A is complete when:**

- [ ] **Project Setup:** Vite + React + TypeScript running on port 3000
- [ ] **Design System:** All Tailwind colors, fonts, glass-panel utilities configured
- [ ] **Components:** All 10 UI components built and tested (GlassCard, Button, Badge, MetricCard, Input, Select, Toggle, Modal, Skeleton, DataTable)
- [ ] **Layout:** Sidebar, Header, MainLayout functional with React Router
- [ ] **Theme:** Light/dark mode + 5 accent themes working with persistence
- [ ] **API Client:** All Phase 6 endpoints typed and callable
- [ ] **Data Layer:** SSE + Tier 2 polling + Tier 3 on-demand hooks fully implemented
- [ ] **Testing:** `npm run dev` starts without errors, Tailwind classes render, API client connects to backend

**Output:** Ready for Session 7B (Core Pages development)

---

## 📊 SESSION 7A SUMMARY

| Task | Hours | Deliverable |
|------|-------|-------------|
| 7.1.1 | 2h | Vite project, Tailwind, design system config |
| 7.1.2 | 3.5h | 10 UI components (GlassCard, Button, Badge, MetricCard, etc.) |
| 7.1.3 | 3h | Sidebar, Header, MainLayout, React Router setup |
| 7.1.4 | 1.5h | ThemeContext (light/dark/system + 5 accent themes) |
| 7.1.5 | 2.5h | API client layer with all Phase 6 endpoints typed |
| 7.1.6 | 4h | useEventStream + data hooks (Tier 1 SSE, Tier 2 polling, Tier 3 on-demand) |
| **TOTAL** | **~17h** | **Production-ready frontend foundation** |

---

**Next Phase:** SESSION_7B_IMPLEMENTATION_PROMPT.md (Core Pages: Cockpit, Portfolio, Strategies, Risk, etc.)
**Related Files:** 07_PHASE_7_FRONTEND.md | DESIGN_GUIDE.md
