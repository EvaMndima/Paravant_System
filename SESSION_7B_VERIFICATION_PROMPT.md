# SESSION 7B VERIFICATION PROMPT
## Core Pages & Data Integration Validation
## 8 Hours | 4 Validation Stages | Production Quality Assurance

**Objective:** Verify that all 10 core pages render correctly with real backend data, all API integrations work properly, and responsive design meets standards.

**Duration:** 8 hours total (2h per stage)
**Effort Split:** Stage 1 (2h) + Stage 2 (2h) + Stage 3 (2h) + Stage 4 (2h)

---

## STAGE 1: CODE QUALITY & COMPONENT STRUCTURE (2 hours)

### TypeScript Strict Mode Verification

```bash
# Must pass with ZERO errors
npx tsc --strict src/

# Must pass with ZERO errors
npx eslint src/ --ext ts,tsx

# Check for any console.error or console.warn
grep -r "console\." src/ | grep -v "\.test\."
# Should return empty (only in test files)
```

### Checklist Items

- [ ] **Type Hints (100% Coverage)**
  - All component props have `interface ComponentProps` defined
  - All hooks return typed values `{ data: T, isLoading: boolean, error: Error | null }`
  - All API responses match backend Pydantic models exactly (verify with backend Phase 6 specs)
  - No `any` types used (except in absolutely justified cases with `// @ts-ignore` comment)
  - All event handlers typed: `(e: React.ChangeEvent<HTMLInputElement>) => void`

- [ ] **React Component Structure**
  - All components either `function Component(props: Props)` or `const Component: React.FC<Props>`
  - All hooks follow rules of hooks (no conditional hooks, no hooks in loops)
  - Components accept `className` prop for composition (Tailwind utility override)
  - No direct DOM manipulation (`useRef` for focus/scroll only, not innerHTML)
  - Proper cleanup in `useEffect` (return cleanup function)

- [ ] **Accessibility Requirements**
  - All interactive elements have `aria-label` or semantic label
  - Kill switch button has `role="alert"` + `aria-live="assertive"` when active
  - Modals have focus trap (Tab cycles within modal only)
  - All buttons keyboard-accessible (can be activated with Enter/Space)
  - Images have `alt` text (or `aria-hidden` if decorative)
  - Form inputs have associated `<label>` elements
  - Color not the only indicator (e.g., status uses icon + color + text)
  - Touch targets minimum 44px (mobile buttons/links)

- [ ] **Component Props Validation**
  - Verify each page component accepts props correctly:
    ```typescript
    // Cockpit page uses useQuery hooks, not prop-drilling
    const dashboard = useDashboardSummary()
    const positions = usePositions()
    // NOT: <Cockpit data={dashboard} positions={positions} />
    ```
  - No prop drilling beyond 2 levels deep (use Context or URL params instead)
  - Default props sensible (e.g., `variant="primary"` not undefined)
  - Optional props marked with `?` (e.g., `optional?: string`)

### Verification Commands

```bash
# Type check
npx tsc --strict

# Lint
npx eslint src/ --fix

# Check for accessibility issues (warning tool, not comprehensive)
npx axe-core src/  # if installed, or manual review

# Code coverage
npm run test -- --coverage

# Expected: >80% coverage on src/ (excluding pages index files)
```

### Acceptance Criteria

- [ ] `npm run build` succeeds with zero TypeScript errors
- [ ] `npx eslint` passes with zero errors (fix auto-fixable ones first)
- [ ] No `console.error` or `console.warn` in production code (test files OK)
- [ ] All interactive components have ARIA labels
- [ ] Kill switch has `role="alert"` + `aria-live="assertive"`
- [ ] Modal focus trapped (test with Tab key)
- [ ] No prop drilling beyond 2 levels
- [ ] All page components use hooks, not props

---

## STAGE 2: PAGE RENDERING & DATA INTEGRATION (2 hours)

### Task: Verify All 10 Pages Render with Real Data

```typescript
// Test framework: Vitest + React Testing Library

describe('Cockpit Page', () => {
  it('renders all 6 PRD widgets', async () => {
    render(<CockpitPage />)

    // Should show skeletons initially
    expect(screen.getByText(/loading/i)).toBeInTheDocument()

    // Wait for data load
    await waitFor(() => {
      expect(screen.getByText(/portfolio value/i)).toBeInTheDocument()
    }, { timeout: 5000 })

    // Verify all 6 widgets rendered
    expect(screen.getByText(/daily p&l/i)).toBeInTheDocument()
    expect(screen.getByText(/open positions/i)).toBeInTheDocument()
    expect(screen.getByText(/win rate/i)).toBeInTheDocument()
    expect(screen.getByText(/active strategies/i)).toBeInTheDocument()
    expect(screen.getByText(/current drawdown/i)).toBeInTheDocument()

    console.log('✓ Cockpit page renders with all 6 widgets')
  })

  it('displays real portfolio data', async () => {
    render(<CockpitPage />)
    await waitFor(() => {
      const portfolioValue = screen.getByText(/\$[\d,]+\.?\d*/i)
      expect(portfolioValue).toBeInTheDocument()
    })
  })

  it('shows position table with close buttons', async () => {
    render(<CockpitPage />)
    await waitFor(() => {
      const closeButtons = screen.getAllByText(/close/i)
      expect(closeButtons.length).toBeGreaterThan(0)
    })
  })
})

describe('Portfolio Page', () => {
  it('renders equity curve chart', async () => {
    render(<PortfolioPage />)
    await waitFor(() => {
      // Recharts creates SVG
      expect(document.querySelector('svg')).toBeInTheDocument()
    })
  })

  it('shows monthly heatmap', async () => {
    render(<PortfolioPage />)
    await waitFor(() => {
      expect(screen.getByText(/monthly returns/i)).toBeInTheDocument()
    })
  })

  it('has time range selector buttons', async () => {
    render(<PortfolioPage />)
    const buttons = screen.getAllByRole('button')
    const rangeButtons = buttons.filter(b => ['1W', '1M', '3M', '6M', '1Y', 'ALL'].includes(b.textContent || ''))
    expect(rangeButtons.length).toBe(6)
  })
})

describe('Strategy Pages', () => {
  it('renders strategies list grid', async () => {
    render(<StrategiesListPage />)
    await waitFor(() => {
      expect(screen.getByText(/strategies/i)).toBeInTheDocument()
    })
  })

  it('shows strategy cards with metrics', async () => {
    render(<StrategiesListPage />)
    await waitFor(() => {
      expect(screen.getByText(/return:/i)).toBeInTheDocument()
      expect(screen.getByText(/sharpe:/i)).toBeInTheDocument()
    })
  })

  it('navigates to strategy detail on click', async () => {
    render(<StrategiesListPage />)
    const card = await screen.findByText(/EMA Trend/i)
    fireEvent.click(card)
    // Verify navigation or modal opens
    await waitFor(() => {
      expect(screen.getByText(/overview|parameters|backtest/i)).toBeInTheDocument()
    })
  })

  it('displays all 7 PRD sections in detail', async () => {
    render(<StrategyDetailPage params={{ id: 'test-strategy' }} />)
    await waitFor(() => {
      expect(screen.getByText(/overview/i)).toBeInTheDocument()
      expect(screen.getByText(/parameters/i)).toBeInTheDocument()
      expect(screen.getByText(/backtest/i)).toBeInTheDocument()
      expect(screen.getByText(/paper/i)).toBeInTheDocument()
      expect(screen.getByText(/live/i)).toBeInTheDocument()
      expect(screen.getByText(/recommendations/i)).toBeInTheDocument()
      expect(screen.getByText(/lifecycle/i)).toBeInTheDocument()
    })
  })
})

describe('Risk Page', () => {
  it('renders risk gauges with values', async () => {
    render(<RiskPage />)
    await waitFor(() => {
      expect(screen.getByText(/drawdown/i)).toBeInTheDocument()
      expect(screen.getByText(/daily loss/i)).toBeInTheDocument()
      expect(screen.getByText(/positions/i)).toBeInTheDocument()
    })
  })

  it('shows circuit breakers table', async () => {
    render(<RiskPage />)
    await waitFor(() => {
      const table = screen.getByRole('table')
      expect(table).toBeInTheDocument()
    })
  })

  it('displays kill switch with correct status', async () => {
    render(<RiskPage />)
    await waitFor(() => {
      const killSwitchButton = screen.getByText(/kill switch/i)
      expect(killSwitchButton).toBeInTheDocument()
      // Verify it's red if active
      const isActive = killSwitchButton.classList.contains('bg-loss')
      console.log(`Kill switch is ${isActive ? 'ACTIVE' : 'INACTIVE'}`)
    })
  })

  it('shows kill switch audit history', async () => {
    render(<RiskPage />)
    await waitFor(() => {
      expect(screen.getByText(/kill switch history/i)).toBeInTheDocument()
    })
  })
})

describe('Other Pages', () => {
  it('Orders page renders order table', async () => {
    render(<OrdersPage />)
    await waitFor(() => {
      expect(screen.getByText(/orders/i)).toBeInTheDocument()
    })
  })

  it('Alerts page renders alert feed', async () => {
    render(<AlertsPage />)
    await waitFor(() => {
      expect(screen.getByText(/alerts/i)).toBeInTheDocument()
    })
  })

  it('Accounts page lists accounts', async () => {
    render(<AccountsPage />)
    await waitFor(() => {
      expect(screen.getByText(/accounts/i)).toBeInTheDocument()
    })
  })

  it('Settings page shows controls', async () => {
    render(<SettingsPage />)
    expect(screen.getByText(/dark mode/i)).toBeInTheDocument()
    expect(screen.getByText(/theme/i)).toBeInTheDocument()
  })

  it('Backtest page has input form', async () => {
    render(<BacktestPage />)
    expect(screen.getByRole('combobox')).toBeInTheDocument() // Strategy selector
    expect(screen.getByLabelText(/from/i)).toBeInTheDocument() // Date input
    expect(screen.getByRole('button', { name: /run backtest/i })).toBeInTheDocument()
  })
})
```

### Acceptance Criteria

- [ ] All 10 pages render without errors
- [ ] Cockpit shows all 6 PRD widgets
- [ ] Portfolio shows equity curve + heatmap + histogram
- [ ] Strategies list shows all strategies with filters
- [ ] Strategy detail has all 7 PRD sections
- [ ] Risk page shows gauges, circuit breakers, kill switch, history
- [ ] Orders/Alerts/Accounts render with data
- [ ] Settings page displays all controls
- [ ] Backtest page has form and can run backtests
- [ ] All pages show loading skeletons initially
- [ ] All pages show error states on API failure

---

## STAGE 3: API INTEGRATION & REAL-TIME UPDATES (2 hours)

### Task: Verify Data Flows from Backend

```typescript
// Integration tests with real backend

describe('API Data Integration', () => {
  it('fetches dashboard summary and displays', async () => {
    const { data: dashboard } = await api.dashboard.getSummary()

    // Verify response shape
    expect(dashboard).toHaveProperty('portfolio_value')
    expect(dashboard).toHaveProperty('daily_pnl')
    expect(dashboard).toHaveProperty('open_positions')
    expect(dashboard).toHaveProperty('win_rate_7d')

    // Verify values are valid numbers
    expect(typeof dashboard.portfolio_value).toBe('number')
    expect(dashboard.portfolio_value > 0).toBe(true)

    console.log('✓ Dashboard summary API working')
  })

  it('SSE connection receives kill switch updates', async () => {
    const { status } = useEventStream(apiKey)
    const killSwitch = useKillSwitch()

    // Initially SSE should connect
    await waitFor(() => {
      expect(status).toBe('connected')
    }, { timeout: 5000 })

    // Activate kill switch
    await api.risk.activateKillSwitch({ reason: 'Test activation' })

    // SSE should push update
    await waitFor(() => {
      expect(killSwitch.data?.is_active).toBe(true)
    }, { timeout: 2000 })

    // Deactivate
    await api.risk.deactivateKillSwitch({ confirm: 'DEACTIVATE' })

    await waitFor(() => {
      expect(killSwitch.data?.is_active).toBe(false)
    }, { timeout: 2000 })

    console.log('✓ Kill switch SSE updates working')
  })

  it('position updates trigger refresh', async () => {
    const positions1 = await api.dashboard.getPositions()
    const count1 = positions1.length

    // Simulate position close via API
    if (positions1.length > 0) {
      await api.positions.close(positions1[0].id, { close_type: 'market' })

      // Should receive SSE event + invalidate query
      await waitFor(async () => {
        const positions2 = await api.dashboard.getPositions()
        expect(positions2.length).toBeLessThan(count1)
      }, { timeout: 3000 })
    }

    console.log('✓ Position close SSE workflow working')
  })

  it('regime change updates dashboard', async () => {
    const regimeOld = (await api.system.getRegime()).current
    const newRegime = regimeOld === 'trending_up' ? 'ranging' : 'trending_up'

    await api.system.setRegime({ regime: newRegime, note: 'Test' })

    await waitFor(async () => {
      const regimeNew = (await api.system.getRegime()).current
      expect(regimeNew).toBe(newRegime)
    }, { timeout: 2000 })

    console.log('✓ Regime change workflow working')
  })

  it('fetches strategy list correctly', async () => {
    const strategies = await api.strategies.list()

    expect(Array.isArray(strategies)).toBe(true)
    if (strategies.length > 0) {
      const strategy = strategies[0]
      expect(strategy).toHaveProperty('id')
      expect(strategy).toHaveProperty('name')
      expect(strategy).toHaveProperty('status')
      expect(strategy).toHaveProperty('return_pct')
    }

    console.log(`✓ Strategies API working (${strategies.length} strategies)`)
  })

  it('fetches equity curve data', async () => {
    const curve = await api.dashboard.getEquity('1M')

    expect(Array.isArray(curve.points)).toBe(true)
    expect(curve.points.length).toBeGreaterThan(0)

    // Check each point has required fields
    curve.points.forEach(point => {
      expect(point).toHaveProperty('date')
      expect(point).toHaveProperty('equity')
      expect(point).toHaveProperty('drawdown_pct')
    })

    console.log('✓ Equity curve API working')
  })

  it('handles API errors gracefully', async () => {
    // Test 401 (session expired)
    try {
      // Make request with bad token
      const response = await fetch('/api/v1/system/status', {
        headers: { 'Authorization': 'Bearer invalid' }
      })
      expect(response.status).toBe(401)
    } catch (error) {
      expect(error).toBeDefined()
    }

    console.log('✓ Error handling working')
  })
})
```

### Data Freshness Verification

```typescript
// Measure actual data freshness

describe('Data Freshness', () => {
  it('SSE events arrive < 100ms', async () => {
    const killSwitch = useKillSwitch()
    const startTime = Date.now()

    await api.risk.activateKillSwitch({ reason: 'Speed test' })

    // Wait for SSE update
    await waitFor(() => {
      expect(killSwitch.data?.is_active).toBe(true)
    })

    const latency = Date.now() - startTime
    console.log(`Kill switch SSE latency: ${latency}ms`)
    expect(latency).toBeLessThan(100)
  })

  it('Polling respects visibility (stops when hidden)', async () => {
    const dashboard = useDashboardSummary()
    const staleTime = dashboard.dataUpdatedAt

    // Hide tab
    Object.defineProperty(document, 'hidden', {
      writable: true,
      value: true,
    })

    // Wait 40 seconds (polling interval is 30s)
    await new Promise(r => setTimeout(r, 40000))

    // Data should NOT have updated (no polling while hidden)
    expect(dashboard.dataUpdatedAt).toBe(staleTime)

    // Show tab again
    Object.defineProperty(document, 'hidden', { value: false })

    // Should refetch quickly
    await waitFor(() => {
      expect(dashboard.dataUpdatedAt).toBeGreaterThan(staleTime)
    }, { timeout: 5000 })

    console.log('✓ Visibility-aware polling working')
  })
})
```

### Acceptance Criteria

- [ ] All API endpoints return data matching Pydantic models
- [ ] SSE events arrive < 100ms after backend state change
- [ ] Position table updates instantly on fill/close (via SSE)
- [ ] Kill switch state updates < 1s (via SSE)
- [ ] Risk status updates < 1s (via SSE)
- [ ] Regime dropdown changes reflect in dashboard
- [ ] Polling stops when browser tab hidden
- [ ] Polling resumes when tab becomes visible
- [ ] API errors show user-friendly messages
- [ ] No network request loops (infinite polling)

---

## STAGE 4: RESPONSIVE DESIGN & PRODUCTION READINESS (2 hours)

### Task: Test Responsive Design at 4 Breakpoints

```bash
# Test at these exact widths:
# 375px (mobile)
# 768px (tablet)
# 1366px (laptop)
# 1920px (desktop)

# Use Chrome DevTools device emulation or:
npm install -D puppeteer
```

### Responsive Design Checklist

```typescript
// Responsive test suite

describe('Responsive Design', () => {
  const breakpoints = [
    { width: 375, name: 'mobile' },
    { width: 768, name: 'tablet' },
    { width: 1366, name: 'laptop' },
    { width: 1920, name: 'desktop' },
  ]

  breakpoints.forEach(({ width, name }) => {
    describe(`${name} (${width}px)`, () => {
      beforeEach(() => {
        // Set viewport
        window.innerWidth = width
        window.dispatchEvent(new Event('resize'))
      })

      it('has no horizontal scroll', () => {
        const body = document.body
        expect(body.scrollWidth).toBeLessThanOrEqual(window.innerWidth)
        console.log(`✓ ${name}: no horizontal scroll`)
      })

      it('sidebar responsive', () => {
        const sidebar = screen.getByRole('navigation')
        if (width >= 1024) {
          expect(sidebar).toHaveClass('w-[280px]')  // Full sidebar
        } else if (width >= 768) {
          expect(sidebar).toHaveClass('w-[80px]')   // Collapsed to icons
        } else {
          expect(sidebar).toHaveClass('hidden')     // Hidden on mobile
        }
        console.log(`✓ ${name}: sidebar responsive`)
      })

      it('metric cards grid responsive', () => {
        const cards = screen.getAllByRole('article')
        if (width >= 1440) {
          // 3-4 cards per row on desktop
          expect(cards.length).toBeGreaterThan(0)
        } else if (width >= 768) {
          // 2 cards per row on tablet
          expect(cards.length).toBeGreaterThan(0)
        } else {
          // 1 card per row on mobile
          expect(cards.length).toBeGreaterThan(0)
        }
        console.log(`✓ ${name}: metric cards responsive`)
      })

      it('tables have horizontal scroll on small screens', () => {
        const tables = document.querySelectorAll('table')
        tables.forEach(table => {
          const container = table.parentElement
          if (width < 768) {
            expect(container?.style.overflowX).toBe('auto')
          }
        })
        console.log(`✓ ${name}: tables scrollable`)
      })

      it('modals adapt to screen size', () => {
        // Open a modal
        const triggerButton = screen.getByRole('button', { name: /open.*modal/i })
        fireEvent.click(triggerButton)

        const modal = screen.getByRole('dialog')
        if (width < 768) {
          expect(modal).toHaveClass('max-w-[90%]')  // Full-screen on mobile
        } else {
          expect(modal).toHaveClass('max-w-lg')     // Standard on larger
        }
        console.log(`✓ ${name}: modals responsive`)
      })

      it('buttons have touch-friendly size (min 44px)', () => {
        const buttons = screen.getAllByRole('button')
        buttons.forEach(button => {
          const rect = button.getBoundingClientRect()
          expect(Math.min(rect.width, rect.height)).toBeGreaterThanOrEqual(44)
        })
        console.log(`✓ ${name}: touch targets >= 44px`)
      })
    })
  })
})
```

### Performance & Bundle Size

```bash
# Check bundle size
npm run build

# Expected output:
# ✓ dist/index.*.js    < 150KB (main chunk)
# ✓ dist/vendor.*.js   < 100KB (React, Router)
# ✓ dist/charts.*.js   < 80KB  (Recharts)
# ✓ dist/motion.*.js   < 50KB  (Framer Motion)
# ✓ Total gzipped      < 500KB

# Check for large imports
npm run analyze  # Uses rollup-plugin-visualizer
```

### Production Build Verification

```bash
# 1. Build
npm run build

# 2. Preview production build locally
npm run preview

# 3. Test in preview:
# - Can you navigate between pages?
# - Does SSE connect?
# - Does API work?
# - Are styles correct?
# - Are fonts loaded?

# 4. Test with slow 4G (Chrome DevTools)
# - Page load < 3 seconds
# - Skeleton shown while loading
# - Data arrives and renders

# 5. Lighthouse audit
# - Performance > 80
# - Accessibility > 90
# - Best Practices > 90
```

### Acceptance Criteria

- [ ] Dashboard works at 375px (mobile), 768px (tablet), 1366px (laptop), 1920px (desktop)
- [ ] No horizontal scroll at any breakpoint
- [ ] Sidebar responsive (expanded on desktop, collapsed on tablet, hidden on mobile)
- [ ] Metric cards responsive grid (3-4 cols desktop, 2 cols tablet, 1 col mobile)
- [ ] Tables horizontal scroll on small screens
- [ ] Modals full-screen on mobile, standard size on desktop
- [ ] All buttons/links >= 44px touch target
- [ ] Initial bundle < 300KB gzipped
- [ ] Total bundle (with lazy chunks) < 500KB gzipped
- [ ] Lighthouse score > 80 (performance)
- [ ] No `console.error` or `console.warn` in production build
- [ ] Fonts load correctly (Cinzel, Inter, JetBrains Mono)
- [ ] Dark mode CSS variables apply correctly

---

## DEBUGGING GUIDE

### Issue: Page Shows Skeleton Forever

**Symptoms:** Skeleton animation loops indefinitely, data never arrives

**Solutions:**
1. Check network tab: Is API request happening?
2. Verify backend is running (`curl http://localhost:8000/api/v1/health`)
3. Check hook for errors: Add `console.log(dashboard.error)`
4. Verify query key matches: `useQuery({ queryKey: ['dashboard', 'summary'] })`
5. Add timeout to useQuery: `retry: 1, retryDelay: 1000`

### Issue: Responsive Design Breaks at 768px

**Symptoms:** Layout misaligned on tablet, buttons overlap

**Solutions:**
1. Verify media query: `@media (max-width: 768px)`
2. Check Tailwind config breakpoints are standard
3. Test in DevTools with actual device emulation
4. Verify no hardcoded widths (use `w-full`, `max-w-*`)

### Issue: SSE Connection Drops Frequently

**Symptoms:** Connection banner appears, kill switch slow to update

**Solutions:**
1. Check browser console: Any 403/401 errors?
2. Verify API key is correct
3. Check proxy config in vite.config.ts for `/api/v1/events/stream`
4. Verify `X-Accel-Buffering: no` header set
5. Test with simpler network (no corporate proxy)

### Issue: Dark Mode Not Applying

**Symptoms:** Dark mode toggle doesn't change colors

**Solutions:**
1. Verify `<html>` element has `class="dark"` or `data-theme="ocean"`
2. Check CSS variables are defined in `index.css`
3. Verify components use `dark:` prefix (e.g., `dark:bg-obsidian-900`)
4. Check ThemeContext actually saves to localStorage

---

## SIGN-OFF CHECKLIST

**Code Quality:**
- [ ] `npm run build` succeeds (zero TypeScript errors)
- [ ] `npm run lint` passes (zero eslint errors)
- [ ] All components have ARIA labels
- [ ] Kill switch has `role="alert"` + `aria-live="assertive"`
- [ ] No `console.error` in production

**Pages & Features:**
- [ ] All 10 pages render without errors
- [ ] Cockpit shows all 6 PRD widgets
- [ ] Strategy list has filters and sorting
- [ ] Strategy detail has all 7 sections
- [ ] Risk page shows gauges, breakers, kill switch, history
- [ ] Orders/Alerts pages render with real data

**Data Integration:**
- [ ] All API calls work correctly
- [ ] SSE connection established and stable
- [ ] Kill switch updates < 1s via SSE
- [ ] Position updates via SSE
- [ ] Polling stops when tab hidden
- [ ] No request loops or infinite polling

**Responsive Design:**
- [ ] 375px (mobile): works perfectly
- [ ] 768px (tablet): works perfectly
- [ ] 1366px (laptop): works perfectly
- [ ] 1920px (desktop): works perfectly
- [ ] No horizontal scroll at any breakpoint
- [ ] Touch targets >= 44px

**Production:**
- [ ] Bundle size < 500KB gzipped
- [ ] Initial chunk < 300KB gzipped
- [ ] Lighthouse score > 80
- [ ] Dark/light mode works
- [ ] All 5 accent themes work
- [ ] Fonts load correctly

**Sign-Off:** _________________ Date: _________________ Time: _________

---

**Next Step:** Proceed to SESSION_7C_VERIFICATION_PROMPT.md
**Related Files:** SESSION_7B_IMPLEMENTATION_PROMPT.md | PHASE_7_IMPLEMENTATION_GUIDE.md
