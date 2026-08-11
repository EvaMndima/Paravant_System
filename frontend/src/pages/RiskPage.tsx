import { motion } from 'framer-motion';
import { AlertTriangle, Download, TrendingDown } from 'lucide-react';
import { useDashboard } from '@/contexts/DashboardContext';
import { GlassCard, Badge, Button, Progress } from '@/components/ui';
import { DonutChart, SparklineChart } from '@/components/charts';
import { staggerContainer, fadeInUp } from '@/lib/animations';

// ── Static data ───────────────────────────────────────────────────────────────

const RISK_METRICS = [
  { title: 'Portfolio Beta',  value: 1.24,  format: 'raw' as const,    suffix: '',    sparkline: [1.1,1.15,1.2,1.18,1.22,1.2,1.24,1.24], note: 'vs BTC baseline' },
  { title: 'Sharpe Ratio',    value: 1.82,  format: 'raw' as const,    suffix: '',    sparkline: [2.1,2.0,1.9,1.95,1.88,1.85,1.80,1.82], note: 'Rolling 30d' },
  { title: 'Sortino Ratio',   value: 2.14,  format: 'raw' as const,    suffix: '',    sparkline: [2.4,2.3,2.2,2.25,2.18,2.15,2.12,2.14], note: 'Downside-adjusted' },
  { title: 'Max Drawdown',    value: -12.4, format: 'percent' as const, suffix: '%',   sparkline: [-8,-9,-10,-11,-11.5,-12,-12,-12.4], note: 'All-time peak-to-trough' },
  { title: 'Value at Risk',   value: -3.2,  format: 'percent' as const, suffix: '%',   sparkline: [-2.5,-2.8,-3.0,-3.1,-3.0,-3.15,-3.2,-3.2], note: '95% confidence, 1-day' },
];

const ASSET_EXPOSURE = [
  { name: 'BTC',  value: 38.2, color: '#f7931a' },
  { name: 'ETH',  value: 24.6, color: '#627eea' },
  { name: 'SOL',  value: 12.1, color: '#9945ff' },
  { name: 'BNB',  value: 11.8, color: '#f3ba2f' },
  { name: 'AVAX', value: 5.3,  color: '#e84142' },
  { name: 'XRP',  value: 3.1,  color: '#00aae4' },
  { name: 'DOGE', value: 2.0,  color: '#c2a633' },
  { name: 'USDT', value: 2.9,  color: '#26a17b' },
];

// Correlation matrix: 6 crypto assets
const CORR_ASSETS = ['BTC', 'ETH', 'SOL', 'BNB', 'AVAX', 'XRP'];
const CORR_MATRIX = [
  [1.00, 0.82, 0.76, 0.71, 0.68, 0.64],
  [0.82, 1.00, 0.84, 0.79, 0.75, 0.69],
  [0.76, 0.84, 1.00, 0.73, 0.77, 0.65],
  [0.71, 0.79, 0.73, 1.00, 0.69, 0.62],
  [0.68, 0.75, 0.77, 0.69, 1.00, 0.61],
  [0.64, 0.69, 0.65, 0.62, 0.61, 1.00],
];

const CONCENTRATION_RISK = [
  { symbol: 'BTC',  weight: 38.2, limit: 40, status: 'ok'   as const },
  { symbol: 'ETH',  weight: 24.6, limit: 30, status: 'ok'   as const },
  { symbol: 'SOL',  weight: 12.1, limit: 15, status: 'ok'   as const },
  { symbol: 'BNB',  weight: 11.8, limit: 15, status: 'ok'   as const },
  { symbol: 'AVAX', weight: 5.3,  limit: 10, status: 'ok'   as const },
  { symbol: 'XRP',  weight: 3.1,  limit: 10, status: 'ok'   as const },
];

const ACTIVE_ALERTS = [
  { id: '1', level: 'critical' as const, title: 'High Crypto Correlation', description: 'All assets correlated > 0.75 — portfolio diversification low during bear conditions.' },
  { id: '2', level: 'warning'  as const, title: 'ETH Drawdown Approaching Limit', description: 'ETHUSDT position at -1.70% today. Daily loss limit at 65%.' },
  { id: '3', level: 'warning'  as const, title: 'AVAX Unrealized Loss', description: 'AVAX position at -7.95% unrealized. Review stop-loss levels.' },
  { id: '4', level: 'info'     as const, title: 'VaR within Normal Range', description: 'Daily VaR at 3.2% of portfolio — within acceptable parameters.' },
];

function corrColor(v: number): string {
  if (v === 1.0) return 'bg-obsidian-200 text-paper-400';
  if (v >= 0.85) return 'bg-loss/60 text-paper-100';
  if (v >= 0.70) return 'bg-warning/30 text-warning';
  if (v >= 0.50) return 'bg-gain/20 text-gain';
  return 'bg-gain/10 text-gain';
}

const ALERT_STYLE: Record<string, string> = {
  critical: 'border-l-4 border-loss bg-loss/5',
  warning:  'border-l-4 border-warning bg-warning/5',
  info:     'border-l-4 border-info bg-info/5',
};

const ALERT_BADGE: Record<string, 'danger' | 'warning' | 'info'> = {
  critical: 'danger',
  warning:  'warning',
  info:     'info',
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function RiskPage() {
  const { openExportModal } = useDashboard();

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
          <h1 className="text-2xl font-semibold text-paper-100">Risk</h1>
          <p className="text-sm text-paper-400 mt-1">Exposure metrics, correlation analysis, and active alerts</p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={openExportModal}>
            <Download className="w-4 h-4 mr-1" /> Export
          </Button>
          <Button variant="secondary" size="sm">
            <TrendingDown className="w-4 h-4 mr-1" /> Stress Test
          </Button>
        </div>
      </motion.div>

      {/* Risk Metrics */}
      <motion.div variants={fadeInUp} className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {RISK_METRICS.map(m => (
          <GlassCard key={m.title} className="p-3">
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs text-paper-400">{m.title}</span>
            </div>
            <div className={`text-xl font-semibold mb-1 ${m.value < 0 ? 'text-loss' : 'text-paper-100'}`}>
              {m.value}{m.format === 'percent' ? '%' : ''}
            </div>
            <SparklineChart
              data={m.sparkline}
              width="100%"
              height={24}
              color={m.value < 0 ? 'loss' : 'neutral'}
            />
            <div className="text-xs text-paper-500 mt-1">{m.note}</div>
          </GlassCard>
        ))}
      </motion.div>

      {/* Exposure + Correlation */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Asset Exposure */}
        <motion.div variants={fadeInUp}>
          <GlassCard>
            <h2 className="text-sm font-medium text-paper-200 mb-3">Asset Exposure</h2>
            <DonutChart
              data={ASSET_EXPOSURE}
              height={200}
              showLegend
              centerContent={
                <div className="text-center">
                  <div className="text-sm font-semibold text-paper-100">8 assets</div>
                  <div className="text-xs text-paper-400">deployed</div>
                </div>
              }
            />
          </GlassCard>
        </motion.div>

        {/* Correlation Matrix */}
        <motion.div variants={fadeInUp}>
          <GlassCard>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-paper-200">Correlation Matrix</h2>
              <Badge variant="warning" size="sm">High correlation regime</Badge>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr>
                    <th className="text-left pb-1.5 pr-2 text-paper-500 font-normal w-10" />
                    {CORR_ASSETS.map(a => (
                      <th key={a} className="text-center pb-1.5 font-medium text-paper-400 w-10">{a}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {CORR_MATRIX.map((row, i) => (
                    <tr key={CORR_ASSETS[i]}>
                      <td className="pr-2 py-0.5 font-medium text-paper-300">{CORR_ASSETS[i]}</td>
                      {row.map((val, j) => (
                        <td key={j} className="py-0.5 px-0.5">
                          <div className={`text-center rounded py-1 font-medium ${corrColor(val)}`}>
                            {val.toFixed(2)}
                          </div>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-paper-500 mt-2">
              All assets highly correlated in current bear regime &mdash; diversification benefit limited.
            </p>
          </GlassCard>
        </motion.div>
      </div>

      {/* Concentration Risk + Active Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Concentration Risk */}
        <motion.div variants={fadeInUp}>
          <GlassCard>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-paper-200">Concentration Risk</h2>
              <span className="text-xs text-paper-400">HHI Index: <span className="text-paper-200 font-medium">2,140</span> (Moderate)</span>
            </div>
            <div className="space-y-3">
              {CONCENTRATION_RISK.map(c => (
                <div key={c.symbol}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-paper-300 font-medium">{c.symbol}</span>
                    <span className={c.weight > c.limit * 0.85 ? 'text-warning' : 'text-paper-400'}>
                      {c.weight.toFixed(1)}% / {c.limit}% limit
                    </span>
                  </div>
                  <Progress
                    value={c.weight}
                    max={c.limit}
                    variant={c.weight > c.limit * 0.9 ? 'warning' : 'default'}
                  />
                </div>
              ))}
            </div>
          </GlassCard>
        </motion.div>

        {/* Active Alerts */}
        <motion.div variants={fadeInUp}>
          <GlassCard>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-paper-200">Active Risk Alerts</h2>
              <Badge variant="danger" size="sm" dot pulsing>{ACTIVE_ALERTS.filter(a => a.level === 'critical').length} critical</Badge>
            </div>
            <div className="space-y-3">
              {ACTIVE_ALERTS.map(alert => (
                <div key={alert.id} className={`p-3 rounded-lg ${ALERT_STYLE[alert.level]}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <AlertTriangle className={`w-3.5 h-3.5 flex-shrink-0 ${alert.level === 'critical' ? 'text-loss' : alert.level === 'warning' ? 'text-warning' : 'text-info'}`} />
                    <span className="text-xs font-medium text-paper-100">{alert.title}</span>
                    <Badge variant={ALERT_BADGE[alert.level]} size="sm" className="ml-auto">{alert.level}</Badge>
                  </div>
                  <p className="text-xs text-paper-400">{alert.description}</p>
                </div>
              ))}
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </motion.div>
  );
}
