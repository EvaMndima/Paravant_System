# SESSION 7C: OPERATIONAL FEATURES, CHARTS & DEPLOYMENT
## Weeks 15-16 | 16 Tasks | ~42 Hours | Interactive Features & Production Build
**Objective:** Build all operational controls, chart components, error handling, and production deployment configuration.

**Duration:** ~42 hours
**Delivery:** Complete, production-ready frontend with all features, charts, error handling, responsive design, and deployment config
**Tool Strategy:** Claude Code for all tasks (safety-critical logic, state management, deployment config)

---

## ⚡ QUICK START

```bash
# Recommended execution order:
# Section 7.3 (Operational Features): 7.3.1 → 7.3.2 → 7.3.3 → ... → 7.3.8
# Section 7.4 (Charts): 7.4.1 → 7.4.2 → 7.4.3 → 7.4.4
# Section 7.5 (Polish & Deployment): 7.5.1 → 7.5.2 → 7.5.3 → 7.5.4

# Parallel opportunities:
#   - Chart components (7.4.1-7.4.4) can run in parallel
#   - Error handling (7.5.1) can start while charts build
#   - Deployment config (7.5.4) can start anytime after 7.1.1
```

---

## SECTION 7.3: OPERATIONAL FEATURES
### *Estimated: 28 hours*

Features that make the dashboard a real operational tool with critical safety controls and power user workflows.

---

## TASK 7.3.1: Build Emergency Panel (Kill Switch Modal)

**Effort:** 3 hours
**Status:** Not Started
**Dependencies:** [7.1.2, 7.1.6]
**Tool:** Claude Code (safety-critical logic requires precision)

### Kill Switch Modals

The kill switch is the most important control in the system. It must be:
- Always accessible (sidebar button, never hidden)
- Visually alarming (red, pulsing when active)
- Fast to activate (one click + confirm)
- Slow to deactivate (type "DEACTIVATE" to prevent accidental resume)

### Activation flow

```typescript
// User clicks "KILL SWITCH" in sidebar
// → Modal opens: "Activate Kill Switch?"
// → "This will halt ALL trading immediately."
// → Reason text field (required)
// → [Cancel] [ACTIVATE — HALT ALL TRADING]
// → API call: POST /risk/kill-switch/activate
// → Response includes transaction_id + server_timestamp (logged for audit)
// → Success: close modal, sidebar button turns red/pulsing
// → SSE pushes kill_switch_changed event
```

### Deactivation flow

```typescript
// User clicks pulsing "KILL SWITCH ACTIVE" in sidebar
// → Modal opens: "Deactivate Kill Switch?"
// → "Type DEACTIVATE to confirm trading can resume."
// → Text input field (must match "DEACTIVATE" exactly)
// → [Cancel] [Confirm Deactivation]
// → API call: POST /risk/kill-switch/deactivate
// → Response includes transaction_id + server_timestamp
// → Success: close modal, sidebar button returns to normal
// → SSE pushes kill_switch_changed event
```

### Implementation

```typescript
// src/components/modals/KillSwitchModal.tsx
interface KillSwitchModalProps {
  isOpen: boolean
  isActive: boolean  // Is kill switch currently active?
  onConfirm: (reason: string) => Promise<void>
  onCancel: () => void
}

export function KillSwitchModal({ isOpen, isActive, onConfirm, onCancel }: KillSwitchModalProps) {
  const [reason, setReason] = useState('')
  const [deactivateConfirm, setDeactivateConfirm] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleActivate = async () => {
    if (!reason.trim()) {
      addToast({ type: 'warning', title: 'Reason required' })
      return
    }
    setIsLoading(true)
    try {
      await onConfirm(reason)
      setReason('')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeactivate = async () => {
    if (deactivateConfirm !== 'DEACTIVATE') {
      addToast({ type: 'warning', title: 'Must type DEACTIVATE exactly' })
      return
    }
    setIsLoading(true)
    try {
      await onConfirm('')  // Deactivation doesn't need reason
      setDeactivateConfirm('')
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <Modal isOpen={isOpen} onClose={onCancel}>
      {!isActive ? (
        <div className="space-y-4">
          <h2 className="text-xl font-serif">🚨 Activate Kill Switch?</h2>
          <p className="text-obsidian-600 dark:text-obsidian-300">
            This will halt ALL trading immediately. Open positions remain open but no new trades can be executed.
          </p>
          <div>
            <label className="block text-sm font-medium mb-2">Reason (required)</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g., Market flash crash, system error, manual intervention"
              className="w-full px-4 py-2 rounded-lg glass-panel focus:ring-2 focus:ring-loss"
              rows={3}
            />
          </div>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={onCancel}>Cancel</Button>
            <Button variant="emergency" isLoading={isLoading} onClick={handleActivate}>
              🚨 HALT ALL TRADING
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <h2 className="text-xl font-serif">🚨 Deactivate Kill Switch?</h2>
          <p className="text-obsidian-600 dark:text-obsidian-300">
            Type <code className="bg-obsidian-900 px-2 py-1 rounded">DEACTIVATE</code> to confirm trading can resume.
          </p>
          <div>
            <Input
              type="text"
              value={deactivateConfirm}
              onChange={(e) => setDeactivateConfirm(e.target.value)}
              placeholder="Type DEACTIVATE"
              className={deactivateConfirm !== '' && deactivateConfirm !== 'DEACTIVATE' ? 'ring-2 ring-loss' : ''}
            />
          </div>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={onCancel}>Cancel</Button>
            <Button
              variant="primary"
              isLoading={isLoading}
              disabled={deactivateConfirm !== 'DEACTIVATE'}
              onClick={handleDeactivate}
            >
              Confirm Deactivation
            </Button>
          </div>
        </div>
      )}
    </Modal>
  )
}
```

### Visual states in sidebar

```typescript
// Sidebar.tsx — Kill switch button visual states
const killSwitch = useKillSwitch()

return (
  <button
    className={cn(
      'w-full py-3 rounded-lg font-serif font-bold transition-all',
      killSwitch.data?.is_active
        ? 'bg-loss text-white animate-pulse shadow-lg shadow-loss/50'
        : 'bg-deep-teal-100 text-deep-teal-900 hover:bg-deep-teal-200'
    )}
    onClick={() => setShowKillSwitchModal(true)}
    role="alert"
    aria-live={killSwitch.data?.is_active ? 'assertive' : 'off'}
  >
    {killSwitch.data?.is_active ? '🚨 KILL SWITCH ACTIVE' : '🚨 Kill Switch'}
  </button>
)
```

### Acceptance Criteria

- [ ] Kill switch button always visible in sidebar
- [ ] Activation: one-click + reason + confirm
- [ ] Deactivation: requires typing "DEACTIVATE" exactly
- [ ] Visual state clearly different when active (red, pulsing)
- [ ] Kill switch state updates instantly via SSE (no polling delay)
- [ ] API response transaction_id logged to console for audit trail
- [ ] Error handling if API call fails (don't close modal)
- [ ] Accessible via keyboard (button is focusable, Tab works)
- [ ] Uses `role="alert"` and `aria-live="assertive"` when active
- [ ] Modal focus trapped (Tab cycles within modal only)

---

## TASK 7.3.2: Build Regime Selector

**Effort:** 2 hours
**Status:** Not Started
**Dependencies:** [7.1.3, 7.1.6]
**Tool:** Claude Code

### Regime dropdown in header

```typescript
// Header.tsx — Regime selector
const regime = useRegime()
const [showRegimeModal, setShowRegimeModal] = useState(false)

const handleChangeRegime = async (newRegime: string) => {
  try {
    await regime.setRegime({ regime: newRegime, note: 'Manual user change' })
    setShowRegimeModal(false)
    addToast({ type: 'success', title: `Regime changed to ${newRegime}` })
  } catch (error) {
    addToast({ type: 'error', title: 'Failed to change regime' })
  }
}

return (
  <div className="flex items-center gap-2">
    <button onClick={() => setShowRegimeModal(true)} className="flex items-center gap-2 px-3 py-2 glass-panel rounded-lg">
      <span className="text-xs font-mono uppercase">Regime</span>
      <Badge variant={getRegimeVariant(regime.data?.current)}>{regime.data?.current}</Badge>
    </button>
    <RegimeChangeModal
      isOpen={showRegimeModal}
      currentRegime={regime.data?.current}
      options={regime.data?.available_options}
      onSelect={handleChangeRegime}
      onClose={() => setShowRegimeModal(false)}
    />
  </div>
)
```

### Color coding

- trending_up: green
- trending_down: red
- ranging: yellow
- volatile: orange
- unknown: gray

### Acceptance Criteria

- [ ] Current regime displayed in header as badge
- [ ] Dropdown shows all options with colors
- [ ] Change triggers confirmation modal with affected strategies count
- [ ] Optional note field in confirmation
- [ ] API call on confirm updates backend
- [ ] Dashboard updates after regime change
- [ ] Regime history accessible

---

## TASK 7.3.3: Build Position Close Modal

**Effort:** 1.5 hours
**Status:** Not Started
**Dependencies:** [7.1.2, 7.2.1]
**Tool:** Claude Code

### Close position flow

```
User clicks [Close] on position row
→ Modal: "Close Position: BTCUSDT LONG?"
→ Shows: quantity, entry price, current price, unrealized P&L
→ Close type: Market (immediate) or Limit (specify price)
→ [Cancel] [Close Position]
→ API call: POST /positions/{id}/close
→ Success: position removed from list, P&L recorded
```

### Implementation

```typescript
export function PositionCloseModal({ isOpen, position, onClose, onConfirm }: PositionCloseModalProps) {
  const [closeType, setCloseType] = useState<'market' | 'limit'>('market')
  const [limitPrice, setLimitPrice] = useState(position?.current_price.toString() || '')

  const handleClose = async () => {
    await onConfirm({
      position_id: position.id,
      close_type: closeType,
      limit_price: closeType === 'limit' ? parseFloat(limitPrice) : undefined,
    })
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="space-y-4">
        <h2 className="text-xl font-serif">Close Position: {position?.symbol}</h2>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>Quantity: {position?.quantity}</div>
          <div>Entry: {formatCurrency(position?.entry_price)}</div>
          <div>Current: {formatCurrency(position?.current_price)}</div>
          <div className={cn('font-medium', position?.unrealized_pnl > 0 ? 'text-gain' : 'text-loss')}>
            P&L: {formatCurrency(position?.unrealized_pnl)}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Close Type</label>
          <div className="flex gap-2">
            <Button
              variant={closeType === 'market' ? 'primary' : 'secondary'}
              onClick={() => setCloseType('market')}
              size="sm"
            >
              Market (Immediate)
            </Button>
            <Button
              variant={closeType === 'limit' ? 'primary' : 'secondary'}
              onClick={() => setCloseType('limit')}
              size="sm"
            >
              Limit (Specify Price)
            </Button>
          </div>
        </div>

        {closeType === 'limit' && (
          <div>
            <label className="block text-sm font-medium mb-2">Limit Price</label>
            <Input
              type="number"
              value={limitPrice}
              onChange={(e) => setLimitPrice(e.target.value)}
              placeholder={position?.current_price.toString()}
            />
          </div>
        )}

        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={handleClose}>Close Position</Button>
        </div>
      </div>
    </Modal>
  )
}
```

### Acceptance Criteria

- [ ] Shows position details in modal
- [ ] Market close option (immediate)
- [ ] Limit close option (specify price)
- [ ] API call on confirm
- [ ] Position removed from list after close
- [ ] Error handling if close fails

---

## TASK 7.3.4: Build Notification Bell

**Effort:** 2 hours
**Status:** Not Started
**Dependencies:** [7.1.3, 7.1.6]
**Tool:** Claude Code

### Features

- Bell icon in header with unread count badge
- Dropdown panel showing last 10 notifications
- Severity icon + relative timestamp + title
- Click notification → navigate to relevant page
- Mark individual as read
- "Mark All as Read" button
- "View All" link to Alerts page

### Implementation

```typescript
// Header.tsx — Notification bell
const alerts = useAlerts(10)
const unreadCount = alerts.data?.filter(a => !a.acknowledged).length || 0

return (
  <div className="relative">
    <button className="relative p-2 glass-panel rounded-lg">
      🔔
      {unreadCount > 0 && (
        <span className="absolute top-0 right-0 bg-loss text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
          {unreadCount}
        </span>
      )}
    </button>
    <NotificationDropdown alerts={alerts.data} />
  </div>
)

// NotificationDropdown.tsx
export function NotificationDropdown({ alerts }: { alerts: Alert[] }) {
  return (
    <div className="absolute right-0 top-full mt-2 w-80 glass-panel rounded-lg shadow-xl z-50">
      <div className="max-h-80 overflow-y-auto">
        {alerts.map(alert => (
          <div key={alert.id} className="px-4 py-3 border-b border-deep-teal-200 dark:border-deep-teal-800 cursor-pointer hover:bg-deep-teal-50 dark:hover:bg-deep-teal-900/30">
            <div className="flex gap-2">
              <span className="text-xl">{getSeverityEmoji(alert.level)}</span>
              <div className="flex-1">
                <p className="font-medium text-sm">{alert.title}</p>
                <p className="text-xs text-obsidian-600 dark:text-obsidian-300">{formatRelativeTime(alert.created_at)}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="px-4 py-3 border-t border-deep-teal-200 dark:border-deep-teal-800 flex justify-between">
        <Button variant="ghost" size="sm" onClick={() => markAllAsRead()}>Mark All as Read</Button>
        <Button variant="ghost" size="sm" onClick={() => navigate('/alerts')}>View All</Button>
      </div>
    </div>
  )
}
```

### Acceptance Criteria

- [ ] Bell icon with unread count badge
- [ ] Dropdown panel shows last 10 notifications
- [ ] Click navigates to relevant page
- [ ] Mark as read (individual + all)
- [ ] Critical notifications don't auto-dismiss (manual acknowledge only)
- [ ] Badge updates instantly via SSE

---

## TASK 7.3.5: Build Strategy Quick Actions

**Effort:** 2 hours
**Status:** Not Started
**Dependencies:** [7.2.3, 7.2.4]
**Tool:** Claude Code

### Actions

- **Pause:** Confirmation → API call → strategy status updates
- **Resume:** Confirmation → API call → strategy status updates
- **Retire:** Requires typing strategy name → API call → strategy archived

### Acceptance Criteria

- [ ] Pause/resume available in strategy list cards
- [ ] Pause/resume available in strategy detail page
- [ ] Retire requires name confirmation (destructive action)
- [ ] API calls succeed and UI updates
- [ ] Strategy list refreshes after action
- [ ] Toasts confirm success/failure

---

## TASK 7.3.6: Build Keyboard Shortcuts

**Effort:** 1.5 hours
**Status:** Not Started
**Dependencies:** [7.1.3, 7.3.1]
**Tool:** Claude Code

### Shortcuts

```
Navigation:
  G then H  → Go to Cockpit (Home)
  G then P  → Go to Portfolio
  G then S  → Go to Strategies
  G then R  → Go to Risk
  G then O  → Go to Orders

Actions:
  Ctrl+K    → Toggle kill switch modal
  Ctrl+/    → Show keyboard shortcuts help
  Escape    → Close any open modal

Dashboard:
  R         → Refresh current page data
  D         → Toggle dark mode
```

### Implementation

```typescript
// useGlobalShortcuts.ts hook
export function useGlobalShortcuts() {
  const navigate = useNavigate()
  const [showHelp, setShowHelp] = useState(false)
  const [gPressed, setGPressed] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Skip if input is focused
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return

      // Ctrl+K — toggle kill switch modal
      if (e.ctrlKey && e.key === 'k') {
        e.preventDefault()
        document.querySelector('[data-kill-switch-trigger]')?.click()
      }

      // Ctrl+/ — show help
      if (e.ctrlKey && e.key === '/') {
        e.preventDefault()
        setShowHelp(true)
      }

      // G then X navigation
      if (e.key === 'g' && !gPressed) {
        e.preventDefault()
        setGPressed(true)
        setTimeout(() => setGPressed(false), 2000)
      } else if (gPressed && e.key in SHORTCUT_MAP) {
        e.preventDefault()
        navigate(SHORTCUT_MAP[e.key])
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [gPressed])

  return { showHelp, setShowHelp }
}
```

### Acceptance Criteria

- [ ] All navigation shortcuts work
- [ ] Kill switch shortcut opens modal
- [ ] Shortcuts disabled in input fields
- [ ] Help modal lists all shortcuts
- [ ] No conflicts with browser shortcuts (F5 for refresh still works)

---

## TASK 7.3.7: Build Position Detail Drawer

**Effort:** 2.5 hours
**Status:** Not Started
**Dependencies:** [7.2.1]
**Tool:** Antigravity (layout) → Claude Code (data)

### Drawer content

- Position metadata: symbol, side, quantity, entry time
- Price info: entry, current, stop loss, take profit
- P&L: unrealized, with chart of price movement since entry
- Strategy info: name, link to strategy detail
- Order history for this position
- Close position button

### Acceptance Criteria

- [ ] Drawer slides in from right
- [ ] All position details displayed
- [ ] Price movement mini-chart renders
- [ ] Close position button (opens close modal)
- [ ] Link to strategy detail page
- [ ] Click outside or Escape closes drawer

---

## TASK 7.3.8: Build Toast Notifications

**Effort:** 1.5 hours
**Status:** Not Started
**Dependencies:** [7.1.1]
**Tool:** Claude Code

### ToastContext and ToastContainer

```typescript
type ToastType = 'success' | 'error' | 'warning' | 'info' | 'critical'

interface Toast {
  id: string
  type: ToastType
  title: string
  message?: string
  duration?: number  // ms, default 5000
}

// Usage:
const { addToast } = useToast()
addToast({ type: 'success', title: 'Kill switch deactivated' })
```

### Display

- Toast stack in bottom-right corner
- Auto-dismiss after duration (default 5s)
- Manual dismiss via X button
- Framer-motion enter/exit animation
- Max 3 visible at once (queue extras)
- Critical toasts: persist until manually dismissed

### Acceptance Criteria

- [ ] Toasts render in bottom-right
- [ ] Auto-dismiss after duration
- [ ] Manual dismiss works
- [ ] Animated enter/exit
- [ ] Max 3 visible (queue extras)
- [ ] Used for all user action confirmations

---

## SECTION 7.4: CHARTS & DATA VISUALIZATION
### *Estimated: 14 hours*

Dedicated chart components reused across multiple pages.

---

## TASK 7.4.1: Build Equity Curve Chart Component

**Effort:** 4 hours
**Status:** Not Started
**Dependencies:** [7.1.6]
**Tool:** Claude Code (Recharts config + data)

### Features

- Main line: portfolio equity over time (area fill with gradient)
- Benchmark overlay: Buy-and-hold BTC (dashed line, different color)
- Drawdown underwater chart: inverted area chart below (red fill)
- Time range selector: 1W / 1M / 3M / 6M / 1Y / ALL
- Tooltip: date, equity value, benchmark value, drawdown %
- Trade markers: optional dots at entry/exit points

### Implementation using Recharts

```typescript
export function EquityCurveChart({
  data,
  range,
  onRangeChange,
  showBenchmark = true,
  showDrawdown = true,
}: EquityCurveChartProps) {
  return (
    <div className="space-y-4">
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={data}>
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-gain)" stopOpacity={0.3} />
              <stop offset="95%" stopColor="var(--color-gain)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" />
          <YAxis />
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" />
          <Tooltip content={<CustomTooltip />} />
          <Area dataKey="equity" fill="url(#equityGradient)" stroke="var(--color-gain)" />
          {showBenchmark && <Line dataKey="benchmark" stroke="var(--color-accent)" strokeDasharray="5 5" />}
        </ComposedChart>
      </ResponsiveContainer>

      {showDrawdown && (
        <ResponsiveContainer width="100%" height={150}>
          <AreaChart data={data}>
            <Area dataKey="drawdown" fill="var(--color-loss)" stroke="none" />
          </AreaChart>
        </ResponsiveContainer>
      )}

      <div className="flex gap-2">
        {['1W', '1M', '3M', '6M', '1Y', 'ALL'].map(r => (
          <Button
            key={r}
            variant={range === r ? 'primary' : 'secondary'}
            onClick={() => onRangeChange(r)}
            size="sm"
          >
            {r}
          </Button>
        ))}
      </div>
    </div>
  )
}
```

### Acceptance Criteria

- [ ] Equity line renders smoothly with gradient fill
- [ ] Benchmark overlay toggleable
- [ ] Drawdown chart renders below (synchronized x-axis)
- [ ] Time range selector changes data
- [ ] Custom tooltip styled per DESIGN_GUIDE
- [ ] Responsive to container width
- [ ] Handles empty data gracefully
- [ ] Chart colors from CSS variables (theme-aware)

---

## TASK 7.4.2: Build Monthly Returns Heatmap Component

**Effort:** 3 hours
**Status:** Not Started
**Dependencies:** [7.1.6]
**Tool:** Claude Code (color calculation)

### Implementation: Custom component (not Recharts — it's a grid, not a chart)

```
         Jan    Feb    Mar    Apr    May    Jun
2023    +2.3%  -1.1%  +4.5%  +0.8%  -2.0%  +3.2%
2024    +1.8%  +3.1%  -0.3%  +2.7%  +1.4%  ...
```

### Color scale

- Negative: red (intensity scales with magnitude)
- Zero: white/neutral
- Positive: green (intensity scales with magnitude)
- Each cell shows return % and trade count in smaller text

### Acceptance Criteria

- [ ] Grid renders with correct year/month structure
- [ ] Color scale correctly maps to return values
- [ ] Cell shows return % and trade count
- [ ] Hover tooltip shows detailed info
- [ ] Responsive (horizontal scroll on small screens)
- [ ] Theme-aware colors

---

## TASK 7.4.3: Build Sparkline Chart Component

**Effort:** 2 hours
**Status:** Not Started
**Dependencies:** [7.1.2]
**Tool:** Claude Code

### File: `src/components/charts/SparklineChart.tsx`

**Props:**
```typescript
interface SparklineChartProps {
  data: number[]           // Array of values
  color?: string           // Override color (default: gain/loss based on trend)
  width?: number           // Default: fill container
  height?: number          // Default: 40
  showArea?: boolean       // Default: true
  animated?: boolean       // Default: true (path draw animation)
}
```

### Implementation: Lightweight SVG (not Recharts — too heavy for inline use)

- Simple polyline SVG with optional area fill
- Auto-scales to data range
- Color based on first-to-last trend (green if up, red if down)
- Gradient mask overlay to fade into card background

### Acceptance Criteria

- [ ] Renders inline within MetricCard
- [ ] Auto-scales to data range
- [ ] Color reflects overall trend
- [ ] Gradient fade at edges
- [ ] Lightweight (no Recharts overhead)
- [ ] Handles empty/single-point data

---

## TASK 7.4.4: Build Risk Gauge Component

**Effort:** 3 hours
**Status:** Not Started
**Dependencies:** [7.1.2]
**Tool:** Claude Code (SVG math)

### File: `src/components/charts/GaugeChart.tsx`

**Props:**
```typescript
interface GaugeChartProps {
  value: number            // Current value
  max: number              // Maximum value
  label: string            // "Drawdown", "Daily Loss", etc.
  unit?: string            // "%" default
  thresholds?: {
    warning: number        // Yellow zone start (default: 50% of max)
    critical: number       // Red zone start (default: 80% of max)
  }
  size?: number            // Diameter in pixels (default: 150)
}
```

### Implementation: Custom SVG arc

- Semi-circle (180 degrees)
- Three color zones: green → yellow → red
- Current value indicator (thick arc overlay)
- Center text: current value (large) + max value (small)
- Animated on mount (arc draws to current value)

### Acceptance Criteria

- [ ] Gauge renders with correct proportions
- [ ] Color zones match thresholds
- [ ] Current value displayed prominently in center
- [ ] Max value shown as reference
- [ ] Animated arc on mount (smooth transition)
- [ ] Responsive to container
- [ ] Theme-aware colors

---

## SECTION 7.5: POLISH & DEPLOYMENT
### *Estimated: 14 hours*

Final touches — error handling, loading states, responsive design, and production build.

---

## TASK 7.5.1: Implement Global Error Handling

**Effort:** 2.5 hours
**Status:** Not Started
**Dependencies:** [7.2.1-7.2.10]
**Tool:** Claude Code

### Features

#### 1. Error Boundary

```typescript
class ErrorBoundary extends React.Component {
  // Catches errors in child component tree
  // Shows: "Something went wrong" + error detail + "Reload" button
  // Logs error to console for debugging
}
```

#### 2. API Error Display

- Network error: "Unable to connect to server. Check your connection."
- 401: "Session expired. Please reload."
- 500: "Server error. The team has been notified." (with retry button)
- Show in a GlassCard with warning styling

#### 3. Offline / Disconnected Detection

**Primary signal:** SSE connection status from `useEventStream` hook
- `status === 'connected'` → no banner
- `status === 'disconnected'` → show "Live connection lost. Reconnecting..." banner with amber styling

**Secondary signal:** REST health endpoint ping every 30 seconds
- If health ping also fails → escalate to "Connection lost. Data may be stale." banner with red styling
- Automatically hides when SSE reconnects or health ping succeeds
- SSE reconnection attempt count shown: "Reconnecting (attempt 3)..."

#### 4. Stale Data Indicator

When SSE is disconnected and data may be outdated:
- Small "Last updated: X minutes ago" text on cards driven by SSE
- Yellow tint on stale cards (> 30 seconds since last SSE event)
- Red tint on very stale cards (> 2 minutes)

### Implementation

```typescript
// src/App.tsx
export function App() {
  const { status: sseStatus } = useEventStream(API_KEY)
  const [healthStatus, setHealthStatus] = useState<'ok' | 'down'>('ok')
  const [reconnectAttempt, setReconnectAttempt] = useState(0)

  // Poll health endpoint every 30s when SSE disconnected
  useEffect(() => {
    if (sseStatus === 'disconnected') {
      const interval = setInterval(async () => {
        try {
          await api.health.quick()
          setHealthStatus('ok')
        } catch {
          setHealthStatus('down')
        }
      }, 30000)
      return () => clearInterval(interval)
    } else {
      setHealthStatus('ok')
    }
  }, [sseStatus])

  return (
    <>
      {sseStatus === 'disconnected' && (
        <ConnectionBanner
          status={healthStatus}
          reconnectAttempt={reconnectAttempt}
          onClose={() => {}}  // Auto-hides when reconnected
        />
      )}
      <ErrorBoundary>
        {/* App content */}
      </ErrorBoundary>
    </>
  )
}

// ConnectionBanner.tsx
export function ConnectionBanner({ status, reconnectAttempt }: ConnectionBannerProps) {
  const bgColor = status === 'down' ? 'bg-loss/10 border-loss/30' : 'bg-neutral/10 border-neutral/30'
  const textColor = status === 'down' ? 'text-loss' : 'text-neutral'

  return (
    <div className={cn('fixed top-4 left-1/2 -translate-x-1/2 px-4 py-3 rounded-lg glass-panel border', bgColor)}>
      <p className={cn('text-sm font-medium', textColor)}>
        {status === 'down'
          ? '❌ Connection lost. Data may be stale.'
          : `⚠️ Live connection lost. Reconnecting (attempt ${reconnectAttempt})...`}
      </p>
    </div>
  )
}
```

### Acceptance Criteria

- [ ] Error boundary catches rendering crashes
- [ ] API errors show user-friendly messages
- [ ] Disconnection banner appears when SSE drops
- [ ] Offline banner escalates when REST health check also fails
- [ ] Banners auto-hide when SSE reconnects
- [ ] Stale data visually indicated on cards that haven't updated
- [ ] Retry mechanisms for transient errors
- [ ] No unhandled promise rejections in console

---

## TASK 7.5.2: Implement Loading States & Skeletons

**Effort:** 2.5 hours
**Status:** Not Started
**Dependencies:** [7.1.2, 7.2.1-7.2.10]
**Tool:** Antigravity (skeleton visuals) → Claude Code (loading logic)

### Loading patterns

#### 1. Initial Page Load — Full skeleton layout matching page structure

- Cockpit: 6 skeleton MetricCards + skeleton table + skeleton cards
- Portfolio: skeleton chart + skeleton heatmap
- Each skeleton matches the shape of the real component

#### 2. Refresh/Polling — No skeletons, data updates in-place

- Previous data shown while refetching
- No "flash" of loading state on refetch

#### 3. Action Loading — Button loading state

- Spinner replaces button text
- Button disabled during action
- Success/error toast after completion

#### 4. Progressive Loading — Components load independently

- Hero metrics load first (fastest)
- Charts load after (slower)
- No component blocks another

### Skeleton Components

```typescript
// Skeleton component from 7.1.2 already provides base
// Create page-specific skeletons:
// - CockpitSkeleton (6 metric cards + table + widgets)
// - PortfolioSkeleton (charts + heatmap)
// - StrategiesListSkeleton (strategy cards grid)
// - RiskSkeleton (gauges + circuit breakers)

export function CockpitSkeleton() {
  return (
    <div className="space-y-6">
      {/* Hero metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array(6).fill(0).map((_, i) => <Skeleton key={i} className="h-[140px]" />)}
      </div>

      {/* Risk + Regime widgets */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>

      {/* Positions table */}
      <Skeleton className="h-96" />
    </div>
  )
}
```

### Acceptance Criteria

- [ ] Every page has a matching skeleton layout
- [ ] Skeletons match real component shapes
- [ ] No layout shift when data loads (skeletons are same size)
- [ ] Polling doesn't show skeletons (previous data persists)
- [ ] Buttons show loading spinner during actions
- [ ] Components load independently (no waterfall)
- [ ] Skeleton animation smooth (pulse effect)

---

## TASK 7.5.3: Implement Responsive Design

**Effort:** 3 hours
**Status:** Not Started
**Dependencies:** [7.2.1-7.2.10]
**Tool:** Claude Code

### Breakpoint targets

| Screen | Width | Sidebar | Content Grid | Behavior |
|--------|-------|---------|-------------|----------|
| Desktop | ≥1440px | 280px expanded | 3-4 columns | Full layout |
| Laptop | 1024-1439px | 280px expanded | 2-3 columns | Full layout |
| Tablet | 768-1023px | 80px collapsed (icons) | 2 columns | Compact |
| Mobile | <768px | Hidden (hamburger) | 1 column | Stack everything |

### Key responsive adjustments

- MetricCards: 4 per row → 2 per row → 1 per row
- Positions table: horizontal scroll on small screens
- Charts: reduce height, simplify tooltips
- Modals: full-screen on mobile
- Sidebar: auto-collapse on tablet, hidden on mobile with hamburger

### Testing

```bash
# Test at these widths:
# Desktop: 1920px
# Laptop: 1366px
# Tablet: 768px
# Mobile: 375px

# No horizontal scroll at any breakpoint
# All content readable
# Buttons clickable (min 44px touch target)
```

### Acceptance Criteria

- [ ] Dashboard usable at 1920px, 1366px, 768px
- [ ] Sidebar responsive (expanded → collapsed → hidden)
- [ ] Grid layouts adapt to screen width
- [ ] Charts resize without breaking
- [ ] Tables scroll horizontally on small screens
- [ ] Modals adapt to screen size
- [ ] No horizontal page scroll at any breakpoint
- [ ] Touch targets min 44px (mobile)

---

## TASK 7.5.4: Frontend Build & Deployment Config

**Effort:** 2 hours
**Status:** Not Started
**Dependencies:** [7.2.1-7.5.3]
**Tool:** Claude Code

### Build configuration

#### 1. Vite production config

```typescript
// vite.config.ts
export default defineConfig({
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

#### 2. FastAPI serves built frontend

```python
# In production, serve frontend files
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

#### 3. Environment variable handling

- `VITE_API_URL` for API base URL (defaults to relative `/api/v1`)
- SSE endpoint uses same base URL: `${VITE_API_URL}/events/stream`
- Build-time variable injection

#### 4. Docker integration

```dockerfile
# Frontend build stage
FROM node:18 AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Backend stage
FROM python:3.11-slim
COPY --from=frontend /app/frontend/dist /app/frontend/dist
# ... rest of backend setup
```

#### 5. Vite dev proxy — SSE handling

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
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
}
```

#### 6. Bundle analysis (dev dependency)

```bash
npm install -D rollup-plugin-visualizer
# Add to vite.config.ts:
# import { visualizer } from 'rollup-plugin-visualizer'
# plugins: [react(), visualizer()]
# Run: npm run build -- --mode analyze
```

### npm scripts

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "analyze": "vite build --mode analyze",
    "lint": "eslint src --ext ts,tsx"
  }
}
```

### Acceptance Criteria

- [ ] `npm run build` produces optimized bundle
- [ ] Code splitting: vendor, charts, motion in separate chunks
- [ ] Lazy-loaded pages: Backtest, Settings, Portfolio (loaded on route visit)
- [ ] Source maps generated for debugging
- [ ] FastAPI serves frontend at root `/`
- [ ] API calls work in production (same-origin, no CORS issues)
- [ ] SSE stream works through Vite dev proxy (no buffering)
- [ ] SSE stream works in production (same-origin via FastAPI static mount)
- [ ] Initial bundle < 300KB gzipped (before lazy chunks)
- [ ] Total bundle (all chunks) < 500KB gzipped
- [ ] Docker multi-stage build works
- [ ] Environment variables inject correctly
- [ ] `npm run analyze` produces bundle visualization report

---

## ✅ SESSION 7C COMPLETION CHECKLIST

**Session 7C is complete when:**

### Operational Features
- [ ] Kill switch activation/deactivation works from sidebar
- [ ] Kill switch deactivation requires typing "DEACTIVATE"
- [ ] Kill switch state updates instantly via SSE
- [ ] Kill switch button uses `aria-live="assertive"` when active
- [ ] Market regime selector in header works
- [ ] Position close from dashboard works
- [ ] Notification bell with unread count works
- [ ] Keyboard shortcuts functional
- [ ] Toast notifications for all user actions
- [ ] Position detail drawer slides in from right

### Charts
- [ ] Equity curve renders with real data + benchmark overlay + drawdown
- [ ] Monthly heatmap renders with correct color scale
- [ ] Sparkline charts work inline in MetricCards
- [ ] Risk gauges render with correct color zones

### Error Handling & UX
- [ ] Error boundary catches rendering crashes
- [ ] SSE disconnection banner appears + auto-hides on reconnect
- [ ] Offline banner escalates when REST health check fails
- [ ] Stale data visually indicated on components
- [ ] Loading skeletons on all pages
- [ ] Error states for failed API calls

### Responsive Design
- [ ] Dashboard works at 1920px, 1366px, 768px
- [ ] Sidebar responsive
- [ ] No horizontal scroll at any breakpoint
- [ ] Touch targets min 44px

### Deployment
- [ ] `npm run build` produces optimized bundle
- [ ] Bundle sizes: initial < 300KB, total < 500KB (gzipped)
- [ ] FastAPI serves frontend
- [ ] Docker build works
- [ ] Environment variables inject correctly

---

## 📊 SESSION 7C SUMMARY

| Task | Hours | Deliverable |
|------|-------|-------------|
| 7.3.1 | 3h | Kill switch modal with activation/deactivation |
| 7.3.2 | 2h | Regime selector in header |
| 7.3.3 | 1.5h | Position close modal |
| 7.3.4 | 2h | Notification bell with dropdown |
| 7.3.5 | 2h | Strategy quick actions (pause/resume/retire) |
| 7.3.6 | 1.5h | Keyboard shortcuts (G navigation, Ctrl+K) |
| 7.3.7 | 2.5h | Position detail drawer |
| 7.3.8 | 1.5h | Toast notification system |
| 7.4.1 | 4h | Equity curve chart with Recharts |
| 7.4.2 | 3h | Monthly returns heatmap |
| 7.4.3 | 2h | Sparkline chart (lightweight SVG) |
| 7.4.4 | 3h | Risk gauge component |
| 7.5.1 | 2.5h | Global error handling + offline detection |
| 7.5.2 | 2.5h | Loading skeletons on all pages |
| 7.5.3 | 3h | Responsive design (mobile/tablet/desktop) |
| 7.5.4 | 2h | Build config + deployment (Docker, FastAPI) |
| **TOTAL** | **~42h** | **Complete, production-ready frontend** |

---

## FINAL PHASE 7 STATUS

When all three sessions complete:

✅ **Foundation (7A):** React project, design system, components, API client, data hooks
✅ **Core Pages (7B):** 10 pages with real data integration
✅ **Features & Polish (7C):** Operational controls, charts, error handling, responsive, deployment-ready

**Total:** 111 hours, 32 tasks, 5 sections → **Production-grade Investor Cockpit Dashboard**

---

**Next Phase:** Production verification & MVP launch
**Related Files:** 07_PHASE_7_FRONTEND.md | DESIGN_GUIDE.md | PHASE_7_IMPLEMENTATION_GUIDE.md
