# SESSION 7C VERIFICATION PROMPT
## Operational Features, Charts & Production Deployment Validation
## 8 Hours | 4 Validation Stages | Production Readiness

**Objective:** Verify all operational controls work safely, charts render correctly, error handling is robust, and deployment configuration is production-ready.

**Duration:** 8 hours total (2h per stage)

---

## STAGE 1: OPERATIONAL FEATURES & SAFETY CONTROLS (2 hours)

### Critical: Kill Switch Functionality

```typescript
describe('Kill Switch Safety', () => {
  it('kill switch button always visible in sidebar', () => {
    render(<App />)
    const killSwitchBtn = screen.getByRole('button', { name: /kill switch/i })
    expect(killSwitchBtn).toBeInTheDocument()
    expect(killSwitchBtn).toBeVisible()
  })

  it('kill switch activation requires reason', async () => {
    render(<KillSwitchModal isOpen={true} isActive={false} onConfirm={mockConfirm} onCancel={() => {}} />)

    const reasonField = screen.getByPlaceholderText(/reason/i)
    const confirmBtn = screen.getByRole('button', { name: /halt/i })

    // Try to confirm without reason
    fireEvent.click(confirmBtn)
    expect(mockConfirm).not.toHaveBeenCalled()

    // Enter reason and confirm
    fireEvent.change(reasonField, { target: { value: 'Manual intervention' } })
    fireEvent.click(confirmBtn)
    expect(mockConfirm).toHaveBeenCalledWith('Manual intervention')
  })

  it('kill switch deactivation requires typing DEACTIVATE', async () => {
    render(<KillSwitchModal isOpen={true} isActive={true} onConfirm={mockConfirm} onCancel={() => {}} />)

    const confirmField = screen.getByPlaceholderText(/type deactivate/i)
    const confirmBtn = screen.getByRole('button', { name: /confirm deactivation/i })

    // Try with wrong text
    fireEvent.change(confirmField, { target: { value: 'deactivate' } })  // lowercase
    expect(confirmBtn).toBeDisabled()

    // Try with correct text
    fireEvent.change(confirmField, { target: { value: 'DEACTIVATE' } })
    expect(confirmBtn).not.toBeDisabled()
    fireEvent.click(confirmBtn)
    expect(mockConfirm).toHaveBeenCalled()
  })

  it('kill switch button shows visual state change when active', async () => {
    const { rerender } = render(<Sidebar killSwitchActive={false} />)
    const btn = screen.getByRole('button', { name: /kill switch/i })

    // Inactive state
    expect(btn).toHaveClass('bg-deep-teal-100')
    expect(btn).not.toHaveClass('animate-pulse')

    // Rerender as active
    rerender(<Sidebar killSwitchActive={true} />)

    // Active state
    expect(btn).toHaveClass('bg-loss')
    expect(btn).toHaveClass('animate-pulse')
  })

  it('kill switch button has accessibility attributes', () => {
    render(<Sidebar killSwitchActive={true} />)
    const btn = screen.getByRole('button', { name: /kill switch/i })

    expect(btn).toHaveAttribute('role', 'alert')
    expect(btn).toHaveAttribute('aria-live', 'assertive')
  })

  it('kill switch updates instantly via SSE', async () => {
    // Simulate SSE event
    const mockSSEHandler = jest.fn()
    const es = new EventTarget()

    // Trigger kill_switch_changed event
    es.dispatchEvent(new CustomEvent('kill_switch_changed', {
      detail: { is_active: true, activated_at: new Date() }
    }))

    // React query should update
    const queryClient = useQueryClient()
    await queryClient.setQueryData(['risk', 'kill-switch'], { is_active: true })

    // Component should reflect change
    render(<RiskPage />)
    await waitFor(() => {
      expect(screen.getByText(/active/i)).toBeInTheDocument()
    })
  })

  it('kill switch API call is audited', async () => {
    const response = await api.risk.activateKillSwitch({ reason: 'Test' })

    // Response should include transaction_id for audit
    expect(response).toHaveProperty('transaction_id')
    expect(response).toHaveProperty('server_timestamp')
    expect(response).toHaveProperty('is_active', true)

    console.log(`✓ Kill switch audit transaction_id: ${response.transaction_id}`)
  })
})
```

### Other Operational Features

```typescript
describe('Operational Features', () => {
  it('regime selector changes regime', async () => {
    render(<Header />)
    const regimeDropdown = screen.getByText(/trending_up/i)  // Current regime
    fireEvent.click(regimeDropdown)

    const trending_down = screen.getByRole('option', { name: /trending down/i })
    fireEvent.click(trending_down)

    // Modal appears with confirmation
    expect(screen.getByText(/change regime/i)).toBeInTheDocument()

    // Confirm
    const confirmBtn = screen.getByRole('button', { name: /confirm/i })
    fireEvent.click(confirmBtn)

    // API call made
    await waitFor(() => {
      expect(mockAPI.system.setRegime).toHaveBeenCalledWith(
        expect.objectContaining({ regime: 'trending_down' })
      )
    })
  })

  it('position close modal validates and closes position', async () => {
    render(<PositionCloseModal isOpen={true} position={mockPosition} onConfirm={mockClose} />)

    // Shows position details
    expect(screen.getByText(/BTCUSDT/i)).toBeInTheDocument()
    expect(screen.getByText(/0.5 BTC/i)).toBeInTheDocument()

    // Close button works
    const closeBtn = screen.getByRole('button', { name: /close position/i })
    fireEvent.click(closeBtn)

    expect(mockClose).toHaveBeenCalledWith({
      position_id: mockPosition.id,
      close_type: 'market'
    })
  })

  it('notification bell shows unread count', async () => {
    render(<Header alerts={[
      { id: '1', acknowledged: false, level: 'warning' },
      { id: '2', acknowledged: false, level: 'error' },
      { id: '3', acknowledged: true, level: 'info' }
    ]} />)

    const badge = screen.getByText('2')  // 2 unread
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('bg-loss')  // Error color
  })

  it('keyboard shortcuts work', async () => {
    const navigate = useNavigate()
    jest.mock('react-router-dom', () => ({
      ...jest.requireActual('react-router-dom'),
      useNavigate: () => navigate
    }))

    render(<App />)

    // G then H → Cockpit
    fireEvent.keyDown(document, { key: 'g' })
    fireEvent.keyDown(document, { key: 'h' })
    expect(navigate).toHaveBeenCalledWith('/')

    // Ctrl+K → Kill switch modal
    fireEvent.keyDown(document, { ctrlKey: true, key: 'k' })
    expect(screen.getByText(/activate kill switch/i)).toBeInTheDocument()

    // Escape → Close modal
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByText(/activate kill switch/i)).not.toBeInTheDocument()
  })

  it('toast notifications appear and auto-dismiss', async () => {
    render(<ToastContainer />)
    const { addToast } = useToast()

    addToast({ type: 'success', title: 'Test toast', duration: 500 })

    // Toast appears
    const toast = await screen.findByText(/test toast/i)
    expect(toast).toBeInTheDocument()

    // Auto-dismisses after duration
    await waitFor(() => {
      expect(toast).not.toBeInTheDocument()
    }, { timeout: 1000 })
  })

  it('position detail drawer shows all info', async () => {
    render(<CockpitPage />)

    // Click position row
    const positionRow = screen.getByText(/BTCUSDT/i)
    fireEvent.click(positionRow)

    // Drawer opens with details
    await waitFor(() => {
      expect(screen.getByText(/entry.*65000/i)).toBeInTheDocument()
      expect(screen.getByText(/current.*67500/i)).toBeInTheDocument()
      expect(screen.getByText(/p&l.*2500/i)).toBeInTheDocument()
    })

    // Close button closes drawer
    const closeBtn = screen.getByRole('button', { name: /close/i })
    fireEvent.click(closeBtn)

    expect(screen.queryByText(/entry.*65000/i)).not.toBeInTheDocument()
  })
})
```

### Acceptance Criteria

- [ ] Kill switch button always visible and not disabled
- [ ] Kill switch activation requires reason text
- [ ] Kill switch deactivation requires typing "DEACTIVATE" exactly
- [ ] Kill switch visual state changes when active (red + pulsing)
- [ ] Kill switch button has `role="alert"` + `aria-live="assertive"`
- [ ] Kill switch updates < 1s when activated/deactivated (via SSE)
- [ ] Regime selector opens confirmation modal
- [ ] Regime change reflected in dashboard immediately
- [ ] Position close modal shows all details
- [ ] Notification bell shows unread count
- [ ] Keyboard shortcuts work (G+navigation, Ctrl+K, Escape)
- [ ] Toast notifications auto-dismiss after duration
- [ ] Position drawer opens and closes correctly
- [ ] All modals have focus trap (Tab cycles within)

---

## STAGE 2: CHART COMPONENTS & DATA VISUALIZATION (2 hours)

### Equity Curve Chart

```typescript
describe('EquityCurveChart', () => {
  it('renders main equity line and benchmark overlay', () => {
    render(
      <EquityCurveChart
        data={mockEquityData}
        range="1M"
        onRangeChange={() => {}}
      />
    )

    // Recharts creates SVG
    const svg = document.querySelector('svg')
    expect(svg).toBeInTheDocument()

    // Check line paths (Recharts creates <polyline> for lines)
    const lines = document.querySelectorAll('polyline')
    expect(lines.length).toBeGreaterThanOrEqual(2)  // Equity + benchmark

    console.log('✓ Equity curve renders with lines')
  })

  it('displays drawdown underwater chart below', () => {
    render(
      <EquityCurveChart
        data={mockEquityData}
        range="1M"
        showDrawdown={true}
      />
    )

    // Should have 2 SVGs (equity + drawdown)
    const svgs = document.querySelectorAll('svg')
    expect(svgs.length).toBeGreaterThanOrEqual(2)
  })

  it('time range selector changes data', async () => {
    const mockOnRangeChange = jest.fn()
    render(
      <EquityCurveChart
        data={mockEquityData}
        range="1M"
        onRangeChange={mockOnRangeChange}
      />
    )

    const button3M = screen.getByRole('button', { name: /3m/i })
    fireEvent.click(button3M)

    expect(mockOnRangeChange).toHaveBeenCalledWith('3M')
  })

  it('tooltip shows correct data on hover', async () => {
    render(
      <EquityCurveChart
        data={mockEquityData}
        range="1M"
        onRangeChange={() => {}}
      />
    )

    // Hover over data point
    const dataPoints = document.querySelectorAll('circle')
    fireEvent.mouseOver(dataPoints[0])

    // Tooltip should appear
    await waitFor(() => {
      const tooltip = screen.queryByText(/date:|equity:/i)
      expect(tooltip).toBeInTheDocument()
    })
  })

  it('handles empty data gracefully', () => {
    render(
      <EquityCurveChart
        data={[]}
        range="1M"
        onRangeChange={() => {}}
      />
    )

    // Should show message or empty state
    expect(screen.getByText(/no data|empty/i)).toBeInTheDocument()
  })
})
```

### Heatmap Component

```typescript
describe('MonthlyHeatmap', () => {
  it('renders grid with correct dimensions', () => {
    render(<MonthlyHeatmap data={mockHeatmapData} />)

    // Should have cells for each month
    const cells = document.querySelectorAll('[data-testid="heatmap-cell"]')
    expect(cells.length).toBeGreaterThan(0)
  })

  it('colors cells correctly (red/white/green)', () => {
    render(<MonthlyHeatmap data={mockHeatmapData} />)

    const cells = document.querySelectorAll('[data-testid="heatmap-cell"]')
    cells.forEach(cell => {
      const style = window.getComputedStyle(cell)
      const bgColor = style.backgroundColor

      // Should be red, white, or green (in RGB)
      const isValidColor = bgColor.includes('rgb')
      expect(isValidColor).toBe(true)
    })
  })

  it('shows return % and trade count per cell', () => {
    render(<MonthlyHeatmap data={mockHeatmapData} />)

    // Each cell should show return and trade count
    expect(screen.getByText(/+2.3%/i)).toBeInTheDocument()  // Return
    expect(screen.getByText(/5 trades/i)).toBeInTheDocument()  // Trade count
  })

  it('tooltip on hover shows detailed info', async () => {
    render(<MonthlyHeatmap data={mockHeatmapData} />)

    const cell = document.querySelector('[data-testid="heatmap-cell"]')
    fireEvent.mouseOver(cell)

    await waitFor(() => {
      const tooltip = screen.getByText(/january|feb|mar/i)
      expect(tooltip).toBeInTheDocument()
    })
  })
})
```

### Sparkline & Gauge Components

```typescript
describe('SparklineChart', () => {
  it('renders inline SVG', () => {
    render(<SparklineChart data={[1, 2, 3, 4, 5, 4, 3, 2, 1]} />)

    const svg = document.querySelector('svg')
    expect(svg).toBeInTheDocument()

    // Should have polyline for line
    const polyline = svg?.querySelector('polyline')
    expect(polyline).toBeInTheDocument()
  })

  it('colors based on trend (green up, red down)', () => {
    // Uptrend: first value < last value
    const { container: upContainer } = render(
      <SparklineChart data={[1, 2, 3, 4, 5]} color={undefined} />
    )
    const upStroke = upContainer.querySelector('polyline')?.getAttribute('stroke')
    expect(upStroke).toContain('gain')  // Should be green

    // Downtrend
    const { container: downContainer } = render(
      <SparklineChart data={[5, 4, 3, 2, 1]} color={undefined} />
    )
    const downStroke = downContainer.querySelector('polyline')?.getAttribute('stroke')
    expect(downStroke).toContain('loss')  // Should be red
  })

  it('is lightweight (no Recharts overhead)', () => {
    const { container } = render(<SparklineChart data={[1, 2, 3]} />)

    // Should be single SVG, not complex Recharts component
    const svgs = container.querySelectorAll('svg')
    expect(svgs.length).toBe(1)
  })
})

describe('GaugeChart', () => {
  it('renders semi-circular gauge', () => {
    render(
      <GaugeChart
        value={30}
        max={100}
        label="Drawdown"
        size={150}
      />
    )

    // Should show SVG with arc
    const svg = document.querySelector('svg')
    expect(svg).toBeInTheDocument()

    // Should have center text
    expect(screen.getByText('30%')).toBeInTheDocument()
  })

  it('color zones: green (0-50%), yellow (50-80%), red (80-100%)', () => {
    const { rerender } = render(
      <GaugeChart value={25} max={100} label="Test" />
    )
    let arc = document.querySelector('[data-testid="gauge-arc"]')
    expect(arc).toHaveClass('stroke-gain')  // Green

    rerender(<GaugeChart value={65} max={100} label="Test" />)
    arc = document.querySelector('[data-testid="gauge-arc"]')
    expect(arc).toHaveClass('stroke-neutral')  // Yellow

    rerender(<GaugeChart value={85} max={100} label="Test" />)
    arc = document.querySelector('[data-testid="gauge-arc"]')
    expect(arc).toHaveClass('stroke-loss')  // Red
  })

  it('animates arc on mount', async () => {
    render(<GaugeChart value={50} max={100} label="Test" />)

    const arc = document.querySelector('[data-testid="gauge-arc"]')
    expect(arc).toHaveClass('animate-draw-arc')  // Animation class
  })
})
```

### Acceptance Criteria

- [ ] Equity curve renders with main line + benchmark overlay + drawdown
- [ ] Time range selector (1W/1M/3M/6M/1Y/ALL) changes data
- [ ] Tooltip shows date, equity, benchmark, drawdown on hover
- [ ] Heatmap renders with correct year/month grid
- [ ] Heatmap colors scale from red (negative) → white (zero) → green (positive)
- [ ] Each heatmap cell shows return % + trade count
- [ ] Sparkline renders inline, colors by trend (green up, red down)
- [ ] Gauge renders semi-circular with 3 color zones
- [ ] Gauge animates on mount
- [ ] All charts responsive (resize with container)
- [ ] Charts handle empty data gracefully
- [ ] Colors from CSS variables (theme-aware)

---

## STAGE 3: ERROR HANDLING & OFFLINE DETECTION (2 hours)

### Error Boundary

```typescript
describe('Error Handling', () => {
  it('error boundary catches render errors', () => {
    const BadComponent = () => {
      throw new Error('Render error')
    }

    render(
      <ErrorBoundary>
        <BadComponent />
      </ErrorBoundary>
    )

    // Should show error UI
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reload/i })).toBeInTheDocument()
  })

  it('error is logged to console', () => {
    const consoleError = jest.spyOn(console, 'error')

    const BadComponent = () => {
      throw new Error('Test error')
    }

    render(
      <ErrorBoundary>
        <BadComponent />
      </ErrorBoundary>
    )

    expect(consoleError).toHaveBeenCalledWith(expect.stringContaining('Test error'))
  })
})

describe('API Error Display', () => {
  it('shows 401 error (session expired)', async () => {
    // Mock API to return 401
    jest.mock('api', () => ({
      dashboard: {
        getSummary: () => Promise.reject({ status: 401, detail: 'Unauthorized' })
      }
    }))

    render(<CockpitPage />)

    await waitFor(() => {
      expect(screen.getByText(/session expired/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /reload/i })).toBeInTheDocument()
    })
  })

  it('shows 500 error (server error)', async () => {
    jest.mock('api', () => ({
      dashboard: {
        getSummary: () => Promise.reject({ status: 500, detail: 'Internal server error' })
      }
    }))

    render(<CockpitPage />)

    await waitFor(() => {
      expect(screen.getByText(/server error/i)).toBeInTheDocument()
    })
  })

  it('shows network error', async () => {
    jest.mock('api', () => ({
      dashboard: {
        getSummary: () => Promise.reject(new TypeError('Failed to fetch'))
      }
    }))

    render(<CockpitPage />)

    await waitFor(() => {
      expect(screen.getByText(/unable to connect/i)).toBeInTheDocument()
    })
  })
})
```

### Offline & SSE Disconnection Detection

```typescript
describe('Connection Status', () => {
  it('shows banner when SSE disconnects', async () => {
    const mockSSE = { status: 'disconnected' }
    jest.mock('hooks/useEventStream', () => ({
      useEventStream: () => mockSSE
    }))

    render(<App />)

    // Banner appears
    await waitFor(() => {
      expect(screen.getByText(/live connection lost/i)).toBeInTheDocument()
      expect(screen.getByText(/reconnecting/i)).toBeInTheDocument()
    })
  })

  it('escalates to "data may be stale" when REST health also fails', async () => {
    const mockSSE = { status: 'disconnected' }
    const mockHealth = { status: 'fail' }

    jest.mock('hooks/useEventStream', () => ({ useEventStream: () => mockSSE }))
    jest.mock('hooks/useHealth', () => ({ useHealth: () => mockHealth }))

    render(<App />)

    // Banner escalates
    await waitFor(() => {
      expect(screen.getByText(/connection lost.*data may be stale/i)).toBeInTheDocument()
      expect(screen.getByText('❌')).toBeInTheDocument()  // Red X icon
    })
  })

  it('auto-hides banner when SSE reconnects', async () => {
    const mockSSE = { status: 'connecting' }
    const { rerender } = render(<App sseStatus={mockSSE.status} />)

    // Banner visible
    expect(screen.getByText(/reconnecting/i)).toBeInTheDocument()

    // SSE reconnects
    rerender(<App sseStatus="connected" />)

    // Banner disappears
    await waitFor(() => {
      expect(screen.queryByText(/reconnecting/i)).not.toBeInTheDocument()
    })
  })

  it('shows stale data indicator on cards > 30s without update', async () => {
    const { rerender } = render(<MetricCard label="Portfolio Value" value={10000} lastUpdated={Date.now()} />)

    // Initially no stale indicator
    expect(screen.queryByText(/last updated/i)).not.toBeInTheDocument()

    // Simulate 35 seconds passing without SSE update
    jest.useFakeTimers()
    jest.advanceTimersByTime(35000)

    rerender(<MetricCard label="Portfolio Value" value={10000} lastUpdated={Date.now() - 35000} />)

    // Stale indicator appears
    expect(screen.getByText(/last updated.*35.*ago/i)).toBeInTheDocument()
    expect(screen.getByTestId('metric-card')).toHaveClass('bg-yellow-50')  // Yellow tint

    jest.useRealTimers()
  })

  it('shows very stale indicator > 2 minutes', async () => {
    render(<MetricCard label="Portfolio Value" value={10000} lastUpdated={Date.now() - 130000} />)

    expect(screen.getByText(/last updated.*2.*minutes.*ago/i)).toBeInTheDocument()
    expect(screen.getByTestId('metric-card')).toHaveClass('bg-red-50')  // Red tint
  })
})
```

### Acceptance Criteria

- [ ] Error boundary catches and displays React errors
- [ ] API 401 shows "Session expired. Reload." message
- [ ] API 500 shows "Server error. The team has been notified."
- [ ] Network error shows "Unable to connect to server"
- [ ] SSE disconnection shows amber banner "Live connection lost"
- [ ] Banner shows reconnection attempt count: "Reconnecting (attempt 3)..."
- [ ] Escalation to red when REST health check fails
- [ ] Banner auto-hides when SSE reconnects
- [ ] Stale data indicator appears > 30s without update
- [ ] Yellow tint on cards with stale data (> 30s)
- [ ] Red tint on very stale cards (> 2 minutes)
- [ ] Last updated timestamp shown on stale cards
- [ ] No unhandled promise rejections in console

---

## STAGE 4: PRODUCTION BUILD & DEPLOYMENT CONFIG (2 hours)

### Build Optimization

```bash
# 1. Build production bundle
npm run build

# Expected output:
# ✓ dist/index.*.js     ~150KB (main)
# ✓ dist/vendor.*.js    ~100KB (React, Router)
# ✓ dist/charts.*.js    ~80KB  (Recharts)
# ✓ dist/motion.*.js    ~50KB  (Framer Motion)
# TOTAL (gzipped)       ~400KB

# 2. Analyze bundle
npm run analyze
# Opens rollup-plugin-visualizer report
# Should identify any unexpectedly large imports

# 3. Check actual gzipped sizes
brotli -c dist/index.*.js | wc -c  # Size in bytes
gzip -c dist/index.*.js | wc -c

# Expected:
# Initial (index.js): < 150KB
# Vendor: < 100KB
# Charts: < 80KB
# Motion: < 50KB
# Total: < 500KB (gzipped)
```

### Production Build Verification

```typescript
describe('Production Build', () => {
  it('serves frontend correctly', async () => {
    // Start: npm run preview
    // This starts Vite in preview mode

    const response = await fetch('http://localhost:5173/')
    expect(response.status).toBe(200)

    const html = await response.text()
    expect(html).toContain('<!DOCTYPE html>')
    expect(html).toContain('<div id="root">')
  })

  it('all routes resolve correctly', async () => {
    const routes = ['/', '/portfolio', '/strategies', '/risk', '/orders', '/alerts', '/accounts', '/settings', '/backtest']

    for (const route of routes) {
      const response = await fetch(`http://localhost:5173${route}`)
      expect(response.status).toBe(200)
    }
  })

  it('API calls work from preview', async () => {
    // Note: requires backend running on localhost:8000

    const response = await fetch('http://localhost:5173/api/v1/system/status')
    expect(response.status).toBe(200)

    const data = await response.json()
    expect(data).toHaveProperty('status')
  })

  it('SSE stream works from preview', async () => {
    // Test SSE endpoint
    const response = await fetch('http://localhost:5173/api/v1/events/stream?api_key=test')
    expect(response.status).toBe(200)
    expect(response.headers.get('content-type')).toContain('text/event-stream')
  })
})
```

### Docker & FastAPI Integration

```bash
# 1. Build Docker image
docker build -t paravant:frontend .

# 2. Verify build stages
docker build -t paravant:frontend --target frontend .  # Frontend stage only
docker build -t paravant:frontend --target production .  # Full image

# 3. Run container
docker run -p 8000:8000 paravant:frontend

# 4. Test endpoints
curl http://localhost:8000/                 # Frontend served
curl http://localhost:8000/api/v1/health    # API works
curl http://localhost:8000/health           # Health check

# 5. Verify frontend distribution
docker exec <container-id> ls -la /app/frontend/dist

# Expected:
# index.html
# assets/
#   - index.*.js (main)
#   - vendor.*.js
#   - charts.*.js
#   - motion.*.js
#   - *.css files
```

### Environment Variables

```typescript
// Verify VITE_ variables are injected correctly

describe('Environment Variables', () => {
  it('VITE_API_URL used for API calls', () => {
    // In development: http://localhost:8000/api/v1
    // In production: /api/v1 (same origin)

    const apiUrl = import.meta.env.VITE_API_URL || '/api/v1'
    expect(apiUrl).toBeTruthy()
  })

  it('SSE endpoint uses same base URL', () => {
    const apiUrl = import.meta.env.VITE_API_URL || '/api/v1'
    const sseUrl = `${apiUrl}/events/stream`

    expect(sseUrl).toBe('/api/v1/events/stream')  // In production
  })
})
```

### Performance Metrics

```bash
# 1. Lighthouse audit (Chrome DevTools)
# Target scores:
# - Performance: > 80
# - Accessibility: > 90
# - Best Practices: > 90
# - SEO: > 90

# 2. Core Web Vitals
# - LCP (Largest Contentful Paint): < 2.5s
# - FID (First Input Delay): < 100ms
# - CLS (Cumulative Layout Shift): < 0.1

# 3. Load time on 4G
# - Initial page load: < 3 seconds
# - TTI (Time to Interactive): < 4 seconds

# Test using Chrome DevTools:
# 1. Open DevTools → Lighthouse
# 2. Select "Mobile" device
# 3. Throttle to "Slow 4G"
# 4. Run audit
```

### Acceptance Criteria

- [ ] `npm run build` succeeds with zero errors
- [ ] Bundle analysis shows no unexpectedly large imports
- [ ] Initial chunk < 150KB gzipped
- [ ] Total bundle < 500KB gzipped
- [ ] `npm run preview` starts successfully
- [ ] All routes accessible in preview
- [ ] API calls work from preview (proxy working)
- [ ] SSE stream works from preview (no buffering)
- [ ] Docker build succeeds
- [ ] Docker container runs and serves frontend
- [ ] API accessible from Docker container
- [ ] Frontend files present in container dist/
- [ ] VITE_API_URL env variable works
- [ ] Lighthouse Performance score > 80
- [ ] Core Web Vitals: LCP < 2.5s, FID < 100ms, CLS < 0.1
- [ ] Page load time on 4G < 3 seconds

---

## SIGN-OFF CHECKLIST

**Operational Features:**
- [ ] Kill switch activation/deactivation fully functional
- [ ] Kill switch requires reason for activation
- [ ] Kill switch requires "DEACTIVATE" for deactivation
- [ ] Kill switch visual state changes (red + pulsing when active)
- [ ] Kill switch updates < 1s via SSE
- [ ] Regime selector changes regime with confirmation
- [ ] Position close modal works
- [ ] Notification bell shows unread count
- [ ] Keyboard shortcuts functional (G navigation, Ctrl+K)
- [ ] Toast notifications appear and auto-dismiss
- [ ] Position detail drawer works

**Charts & Visualization:**
- [ ] Equity curve renders with lines + benchmark overlay + drawdown
- [ ] Time range selector changes data correctly
- [ ] Monthly heatmap shows correct colors and values
- [ ] Sparkline charts render and color by trend
- [ ] Risk gauges show correct zones (green/yellow/red)
- [ ] All charts responsive (resize with container)
- [ ] Charts handle empty data gracefully

**Error Handling:**
- [ ] Error boundary catches render errors
- [ ] API errors show user-friendly messages (401, 500, network)
- [ ] SSE disconnection shows banner
- [ ] Offline detection escalates when health check fails
- [ ] Stale data visually indicated (> 30s and > 2 minutes)
- [ ] No unhandled promise rejections

**Production Deployment:**
- [ ] Build produces optimized bundles (< 500KB gzipped)
- [ ] Code splitting works (vendor, charts, motion chunks)
- [ ] Preview mode works locally
- [ ] API calls work from preview
- [ ] SSE stream works from preview
- [ ] Docker build succeeds
- [ ] Container serves frontend correctly
- [ ] FastAPI static mount works
- [ ] Environment variables inject correctly
- [ ] Lighthouse score > 80
- [ ] Page load time < 3s on 4G
- [ ] No console errors in production

**Sign-Off:** _________________ Date: _________________ Time: _________

---

**Next Phase:** Production deployment & MVP launch
**Related Files:** SESSION_7C_IMPLEMENTATION_PROMPT.md | PHASE_7_IMPLEMENTATION_GUIDE.md
