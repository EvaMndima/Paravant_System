import { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Bell, BellOff, AlertTriangle, Wifi, Clock, Download } from 'lucide-react';
import { useDashboard } from '@/contexts/DashboardContext';
import { GlassCard, Badge, Button, Progress } from '@/components/ui';
import { staggerContainer, fadeInUp } from '@/lib/animations';

// ── Types ─────────────────────────────────────────────────────────────────────

type AlertTab = 'price' | 'risk' | 'system' | 'history';

interface PriceAlert {
  id: string;
  symbol: string;
  condition: 'above' | 'below';
  targetPrice: number;
  currentPrice: number;
  status: 'active' | 'near' | 'muted';
}

interface RiskAlert {
  id: string;
  type: string;
  description: string;
  level: 'critical' | 'warning';
  triggeredAt: string;
}

interface SystemAlert {
  id: string;
  type: string;
  message: string;
  level: 'error' | 'warning' | 'info';
  time: string;
}

interface HistoryEntry {
  id: string;
  symbol: string;
  type: string;
  message: string;
  triggeredAt: string;
  status: 'triggered' | 'expired' | 'dismissed';
}

// ── Static data ───────────────────────────────────────────────────────────────

const PRICE_ALERTS: PriceAlert[] = [
  { id: '1', symbol: 'BTC',  condition: 'above', targetPrice: 65000, currentPrice: 62840, status: 'active' },
  { id: '2', symbol: 'ETH',  condition: 'below', targetPrice: 3100,  currentPrice: 3185,  status: 'near'   },
  { id: '3', symbol: 'SOL',  condition: 'above', targetPrice: 155,   currentPrice: 148,   status: 'active' },
  { id: '4', symbol: 'BNB',  condition: 'below', targetPrice: 560,   currentPrice: 584,   status: 'active' },
  { id: '5', symbol: 'AVAX', condition: 'below', targetPrice: 35,    currentPrice: 38.2,  status: 'near'   },
  { id: '6', symbol: 'XRP',  condition: 'above', targetPrice: 0.60,  currentPrice: 0.524, status: 'active' },
  { id: '7', symbol: 'DOGE', condition: 'below', targetPrice: 0.14,  currentPrice: 0.162, status: 'muted'  },
];

const RISK_ALERTS: RiskAlert[] = [
  { id: '1', type: 'Correlation Risk',  description: 'All 6 positions correlated > 0.75 in bear regime', level: 'critical', triggeredAt: '14:32' },
  { id: '2', type: 'Daily Drawdown',    description: 'Portfolio daily loss at 62% of 1.5% limit',        level: 'warning',  triggeredAt: '13:58' },
  { id: '3', type: 'Position Exposure', description: 'BTC position at 38.2% — approaching 40% soft cap', level: 'warning',  triggeredAt: '12:10' },
  { id: '4', type: 'Strategy Stopped',  description: 'RAMR stopped due to regime mismatch',              level: 'warning',  triggeredAt: '09:30' },
];

const SYSTEM_ALERTS: SystemAlert[] = [
  { id: '1', type: 'API Rate Limit',     message: 'Binance API at 72% rate limit capacity', level: 'warning', time: '14:45' },
  { id: '2', type: 'WebSocket Reconnect', message: 'Market stream reconnected after 2s drop', level: 'info',    time: '13:22' },
  { id: '3', type: 'Paper Mode Active',  message: 'System running in paper trading mode — no real orders', level: 'info', time: '09:00' },
];

const HISTORY: HistoryEntry[] = [
  { id: '1',  symbol: 'BTC',  type: 'Price Alert',  message: 'BTC crossed above $62,000',     triggeredAt: '2026-04-29 18:40', status: 'triggered' },
  { id: '2',  symbol: 'ETH',  type: 'Risk Alert',   message: 'ETH daily loss limit 80%',       triggeredAt: '2026-04-29 15:12', status: 'triggered' },
  { id: '3',  symbol: 'SOL',  type: 'Price Alert',  message: 'SOL below $140 alert expired',   triggeredAt: '2026-04-28 22:00', status: 'expired'   },
  { id: '4',  symbol: 'AVAX', type: 'System Alert', message: 'Binance maintenance window',     triggeredAt: '2026-04-28 03:00', status: 'triggered' },
  { id: '5',  symbol: 'BNB',  type: 'Price Alert',  message: 'BNB crossed above $580',         triggeredAt: '2026-04-27 11:30', status: 'triggered' },
  { id: '6',  symbol: 'XRP',  type: 'Price Alert',  message: 'XRP alert dismissed',            triggeredAt: '2026-04-27 09:15', status: 'dismissed' },
  { id: '7',  symbol: 'DOGE', type: 'Price Alert',  message: 'DOGE below $0.155',              triggeredAt: '2026-04-26 20:45', status: 'triggered' },
  { id: '8',  symbol: 'ETH',  type: 'Risk Alert',   message: 'Correlation warning triggered',  triggeredAt: '2026-04-26 14:00', status: 'triggered' },
];

function pctToTarget(alert: PriceAlert): number {
  if (alert.condition === 'above') {
    return Math.min(100, (alert.currentPrice / alert.targetPrice) * 100);
  }
  // For 'below': closer to target = higher bar fill starting from 100%
  return Math.min(100, Math.max(0, 100 - ((alert.currentPrice - alert.targetPrice) / alert.targetPrice) * 100 * 10));
}

const STATUS_BADGE: Record<string, 'success' | 'warning' | 'neutral'> = {
  active:  'success',
  near:    'warning',
  muted:   'neutral',
};

const HISTORY_BADGE: Record<string, 'success' | 'neutral' | 'info'> = {
  triggered: 'success',
  expired:   'neutral',
  dismissed: 'info',
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function AlertsPage() {
  const { openAlertModal, openExportModal } = useDashboard();
  const [activeTab, setActiveTab] = useState<AlertTab>('price');

  const stats = {
    active:   PRICE_ALERTS.filter(a => a.status === 'active').length + RISK_ALERTS.length,
    triggered: HISTORY.filter(h => h.status === 'triggered').length,
    risk:      RISK_ALERTS.length,
    muted:    PRICE_ALERTS.filter(a => a.status === 'muted').length,
  };

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="space-y-4"
    >
      {/* Header */}
      <motion.div variants={fadeInUp} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-paper-100">Alerts</h1>
          <p className="text-sm text-paper-400 mt-1">Price alerts, risk warnings, and system notifications</p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={openExportModal}>
            <Download className="w-4 h-4 mr-1" /> Export
          </Button>
          <Button variant="primary" size="sm" onClick={() => openAlertModal()}>
            <Plus className="w-4 h-4 mr-1" /> New Alert
          </Button>
        </div>
      </motion.div>

      {/* Stats */}
      <motion.div variants={fadeInUp} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Active Alerts',    value: stats.active,    icon: Bell,          variant: 'info' as const },
          { label: 'Triggered Today',  value: stats.triggered, icon: AlertTriangle, variant: 'success' as const },
          { label: 'Risk Warnings',    value: stats.risk,      icon: AlertTriangle, variant: 'danger' as const },
          { label: 'Muted',            value: stats.muted,     icon: BellOff,       variant: 'neutral' as const },
        ].map(s => (
          <GlassCard key={s.label} className="p-4 flex items-center gap-3">
            <div className="p-2 rounded-lg bg-obsidian-300">
              <s.icon className="w-4 h-4 text-paper-400" />
            </div>
            <div>
              <div className="text-xl font-semibold text-paper-100">{s.value}</div>
              <div className="text-xs text-paper-400">{s.label}</div>
            </div>
          </GlassCard>
        ))}
      </motion.div>

      {/* Tabs */}
      <motion.div variants={fadeInUp}>
        <div className="flex gap-1 border-b border-obsidian-200 pb-0">
          {(['price', 'risk', 'system', 'history'] as AlertTab[]).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm capitalize transition-colors border-b-2 -mb-px ${
                activeTab === tab
                  ? 'border-turquoise text-turquoise font-medium'
                  : 'border-transparent text-paper-400 hover:text-paper-200'
              }`}
            >
              {tab === 'price' ? 'Price Alerts' : tab === 'history' ? 'History' : tab === 'risk' ? 'Risk Alerts' : 'System'}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Price Alerts */}
      {activeTab === 'price' && (
        <motion.div variants={staggerContainer} className="space-y-3">
          {PRICE_ALERTS.map(alert => {
            const progress = pctToTarget(alert);
            const priceDisplay = (p: number) => p >= 1 ? `$${p.toLocaleString()}` : `$${p.toFixed(4)}`;
            return (
              <motion.div key={alert.id} variants={fadeInUp}>
                <GlassCard className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-paper-100">{alert.symbol}</span>
                        <Badge variant={STATUS_BADGE[alert.status]} size="sm" dot={alert.status === 'near'} pulsing={alert.status === 'near'}>
                          {alert.status}
                        </Badge>
                      </div>
                      <div className="text-xs text-paper-400 mt-0.5">
                        Alert when {alert.condition} {priceDisplay(alert.targetPrice)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-paper-100">{priceDisplay(alert.currentPrice)}</div>
                      <div className="text-xs text-paper-500">current</div>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Progress
                      value={progress}
                      max={100}
                      variant={alert.status === 'near' ? 'warning' : 'default'}
                    />
                    <div className="flex justify-between text-xs text-paper-500">
                      <span>{progress.toFixed(1)}% to trigger</span>
                      <span>Target: {priceDisplay(alert.targetPrice)}</span>
                    </div>
                  </div>
                </GlassCard>
              </motion.div>
            );
          })}
          <motion.div variants={fadeInUp}>
            <button
              onClick={() => openAlertModal()}
              className="w-full p-4 rounded-xl border border-dashed border-obsidian-200 text-paper-400 hover:text-paper-200 hover:border-turquoise/40 transition-colors text-sm flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" /> Add price alert
            </button>
          </motion.div>
        </motion.div>
      )}

      {/* Risk Alerts */}
      {activeTab === 'risk' && (
        <motion.div variants={staggerContainer} className="space-y-3">
          {RISK_ALERTS.map(alert => (
            <motion.div key={alert.id} variants={fadeInUp}>
              <GlassCard className={`p-4 border-l-4 ${alert.level === 'critical' ? 'border-loss' : 'border-warning'}`}>
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className={`w-4 h-4 flex-shrink-0 mt-0.5 ${alert.level === 'critical' ? 'text-loss' : 'text-warning'}`} />
                    <div>
                      <div className="text-sm font-medium text-paper-100">{alert.type}</div>
                      <p className="text-xs text-paper-400 mt-0.5">{alert.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                    <span className="text-xs text-paper-500">{alert.triggeredAt}</span>
                    <Badge variant={alert.level === 'critical' ? 'danger' : 'warning'} size="sm">{alert.level}</Badge>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* System Alerts */}
      {activeTab === 'system' && (
        <motion.div variants={staggerContainer} className="space-y-3">
          {SYSTEM_ALERTS.map(alert => (
            <motion.div key={alert.id} variants={fadeInUp}>
              <GlassCard className="p-4">
                <div className="flex items-start gap-3">
                  {alert.type.includes('WebSocket') || alert.type.includes('API')
                    ? <Wifi className="w-4 h-4 text-paper-400 flex-shrink-0 mt-0.5" />
                    : <Clock className="w-4 h-4 text-paper-400 flex-shrink-0 mt-0.5" />}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-medium text-paper-100">{alert.type}</span>
                      <Badge
                        variant={alert.level === 'error' ? 'danger' : alert.level === 'warning' ? 'warning' : 'info'}
                        size="sm"
                      >
                        {alert.level}
                      </Badge>
                    </div>
                    <p className="text-xs text-paper-400">{alert.message}</p>
                  </div>
                  <span className="text-xs text-paper-500 flex-shrink-0">{alert.time}</span>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* History */}
      {activeTab === 'history' && (
        <motion.div variants={fadeInUp}>
          <GlassCard>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-paper-400 border-b border-obsidian-200">
                    <th className="text-left pb-3 font-medium">Symbol</th>
                    <th className="text-left pb-3 font-medium">Type</th>
                    <th className="text-left pb-3 font-medium">Message</th>
                    <th className="text-right pb-3 font-medium">Time</th>
                    <th className="text-right pb-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {HISTORY.map(h => (
                    <tr key={h.id} className="border-b border-obsidian-200/50 last:border-0 hover:bg-obsidian-300/20 transition-colors">
                      <td className="py-2.5 font-medium text-paper-100">{h.symbol}</td>
                      <td className="py-2.5 text-xs text-paper-400">{h.type}</td>
                      <td className="py-2.5 text-paper-300 max-w-xs truncate">{h.message}</td>
                      <td className="py-2.5 text-right text-xs text-paper-500">{h.triggeredAt}</td>
                      <td className="py-2.5 text-right">
                        <Badge variant={HISTORY_BADGE[h.status]} size="sm">{h.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </motion.div>
      )}
    </motion.div>
  );
}
