
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Palette,
  Bell,
  TrendingUp,
  Server,
  CheckCircle,
  XCircle,
  Clock,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Toggle } from '@/components/ui/Toggle';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { useTheme } from '@/contexts/ThemeContext';
import type { ThemeMode, AccentTheme } from '@/contexts/ThemeContext';
import { useHealthCheck, useSystemStatus } from '@/hooks';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

// ---------------------------------------------------------------------------
// Appearance Tab — wired to ThemeContext
// ---------------------------------------------------------------------------

const AppearanceSection: React.FC = () => {
  const { mode, accent, compactMode, reducedMotion, setMode, setAccent, setCompactMode, setReducedMotion } =
    useTheme();

  const modes: Array<{ id: ThemeMode; label: string }> = [
    { id: 'light', label: 'Light' },
    { id: 'dark', label: 'Dark' },
    { id: 'system', label: 'System' },
  ];

  const accents: Array<{ id: AccentTheme; label: string; color: string }> = [
    { id: 'ocean', label: 'Ocean', color: 'bg-cyan-400' },
    { id: 'sapphire', label: 'Sapphire', color: 'bg-blue-500' },
    { id: 'emerald', label: 'Emerald', color: 'bg-emerald-500' },
    { id: 'amber', label: 'Amber', color: 'bg-amber-500' },
    { id: 'slate', label: 'Slate', color: 'bg-slate-500' },
  ];

  return (
    <div className="space-y-8 max-w-xl">
      <SectionHeading>Appearance</SectionHeading>

      {/* Theme mode */}
      <SettingRow
        label="Theme Mode"
        description="Select your preferred interface theme"
      >
        <div className="flex gap-1 bg-deep-teal-800/5 dark:bg-white/5 p-1 rounded-xl">
          {modes.map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                mode === m.id
                  ? 'bg-deep-teal-800 text-white dark:bg-turquoise-mist dark:text-deep-teal-900 shadow'
                  : 'text-obsidian-400/70 dark:text-paper-100/50 hover:opacity-80'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </SettingRow>

      {/* Accent theme */}
      <SettingRow label="Accent Theme" description="Primary colour used across the UI">
        <div className="flex gap-2">
          {accents.map((a) => (
            <button
              key={a.id}
              onClick={() => setAccent(a.id)}
              title={a.label}
              className={`w-8 h-8 rounded-full ${a.color} flex items-center justify-center transition-all ${
                accent === a.id
                  ? 'ring-2 ring-offset-2 ring-offset-paper-100 dark:ring-offset-obsidian-400 ring-current scale-110'
                  : 'opacity-60 hover:opacity-100'
              }`}
            >
              {accent === a.id && (
                <span className="w-2 h-2 rounded-full bg-white/80 block" />
              )}
            </button>
          ))}
        </div>
      </SettingRow>

      {/* Compact mode */}
      <SettingRow label="Compact Mode" description="Reduce spacing to show more data on screen">
        <Toggle
          checked={compactMode}
          onChange={setCompactMode}
        />
      </SettingRow>

      {/* Reduced motion */}
      <SettingRow label="Reduced Motion" description="Disable animations for accessibility">
        <Toggle
          checked={reducedMotion}
          onChange={setReducedMotion}
        />
      </SettingRow>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Notifications Tab — local preferences (no backend API in MVP)
// ---------------------------------------------------------------------------

const NotificationsSection: React.FC = () => {
  const [alertLevel, setAlertLevel] = useState('important');
  const [tradeAlerts, setTradeAlerts] = useState(true);
  const [riskAlerts, setRiskAlerts] = useState(true);
  const [systemAlerts, setSystemAlerts] = useState(true);

  return (
    <div className="space-y-8 max-w-xl">
      <SectionHeading>Notifications</SectionHeading>

      <SettingRow label="Alert Level" description="Minimum severity to show in the alert feed">
        <Select
          value={alertLevel}
          onChange={(e) => setAlertLevel(e.target.value)}
          options={[
            { value: 'all', label: 'All events' },
            { value: 'important', label: 'Important only' },
            { value: 'critical', label: 'Critical only' },
          ]}
          className="w-44"
        />
      </SettingRow>

      <div className="space-y-4">
        <Toggle
          checked={tradeAlerts}
          onChange={setTradeAlerts}
          label="Trade Execution Alerts"
          description="Notify when orders are filled or rejected"
        />
        <Toggle
          checked={riskAlerts}
          onChange={setRiskAlerts}
          label="Risk Breach Alerts"
          description="Notify when risk limits are approached or breached"
        />
        <Toggle
          checked={systemAlerts}
          onChange={setSystemAlerts}
          label="System Status Alerts"
          description="Notify on connectivity loss or system events"
        />
      </div>

      <p className="text-xs opacity-40 font-mono">
        Notification preferences are stored locally. Telegram alert delivery is configured server-side.
      </p>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Trading Tab — local preferences (no backend API in MVP)
// ---------------------------------------------------------------------------

const TradingSection: React.FC = () => {
  const [paperDays, setPaperDays] = useState('30');
  const [autoClose, setAutoClose] = useState(false);

  return (
    <div className="space-y-8 max-w-xl">
      <SectionHeading>Trading Preferences</SectionHeading>

      <SettingRow
        label="Default Paper Period"
        description="Number of days for paper trading validation runs"
      >
        <Select
          value={paperDays}
          onChange={(e) => setPaperDays(e.target.value)}
          options={[
            { value: '7', label: '7 days' },
            { value: '14', label: '14 days' },
            { value: '30', label: '30 days' },
            { value: '90', label: '90 days' },
          ]}
          className="w-36"
        />
      </SettingRow>

      <Toggle
        checked={autoClose}
        onChange={setAutoClose}
        label="Auto-Close on Shutdown"
        description="Automatically close all positions when the system stops"
      />

      <p className="text-xs opacity-40 font-mono">
        Trading preferences are stored locally. Strategy parameters are configured per-strategy on the Strategies page.
      </p>
    </div>
  );
};

// ---------------------------------------------------------------------------
// System Info Tab — wired to health API + system status
// ---------------------------------------------------------------------------

const SystemInfoSection: React.FC = () => {
  // useHealthCheck fires on mount (Tier 3 on-demand pattern — lazy tab mount)
  const { data: health, isLoading: healthLoading } = useHealthCheck('full');
  const { data: systemStatus, isLoading: statusLoading } = useSystemStatus();

  if (healthLoading || statusLoading) {
    return (
      <div className="space-y-4 max-w-xl">
        <SectionHeading>System Info</SectionHeading>
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-28 w-full rounded-xl" />
      </div>
    );
  }

  const checks = health?.checks ?? {
    database: false,
    broker_connection: false,
    data_feed: false,
  };

  const checkLabels: Record<keyof typeof checks, string> = {
    database: 'Database',
    broker_connection: 'Broker Connection',
    data_feed: 'Market Data Feed',
  };

  return (
    <div className="space-y-6 max-w-xl">
      <SectionHeading>System Info</SectionHeading>

      {/* Overall health status */}
      <div className="flex items-center gap-3 p-4 rounded-xl bg-deep-teal-800/5 dark:bg-white/5">
        <div
          className={`w-3 h-3 rounded-full flex-shrink-0 ${
            health?.status === 'healthy' ? 'bg-success' : 'bg-loss'
          }`}
        />
        <div>
          <div className="font-medium text-sm">System Status</div>
          <div className="text-xs opacity-60 font-mono mt-0.5">
            {health?.status?.toUpperCase() ?? 'UNKNOWN'}
          </div>
        </div>
        <Badge
          variant={health?.status === 'healthy' ? 'success' : 'danger'}
          className="ml-auto"
        >
          {health?.status?.toUpperCase() ?? 'UNKNOWN'}
        </Badge>
      </div>

      {/* Subsystem checks */}
      <div>
        <div className="text-xs font-mono font-bold uppercase tracking-widest opacity-40 mb-3">
          Subsystems
        </div>
        {(Object.keys(checkLabels) as Array<keyof typeof checks>).map((key) => (
          <div
            key={key}
            className="flex items-center justify-between py-2.5 border-b border-deep-teal-800/5 dark:border-white/5"
          >
            <span className="text-sm">{checkLabels[key]}</span>
            <div className="flex items-center gap-1.5">
              {checks[key] ? (
                <>
                  <CheckCircle className="w-4 h-4 text-success" />
                  <span className="text-xs font-mono text-success">OK</span>
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4 text-loss" />
                  <span className="text-xs font-mono text-loss">FAIL</span>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Runtime info */}
      <div>
        <div className="text-xs font-mono font-bold uppercase tracking-widest opacity-40 mb-3">
          Runtime
        </div>
        <InfoRow label="Version" value="0.1.0 (MVP)" />
        <InfoRow
          label="Uptime"
          value={
            systemStatus?.uptime_seconds != null
              ? formatUptime(systemStatus.uptime_seconds)
              : '—'
          }
          icon={<Clock className="w-3.5 h-3.5" />}
        />
        <InfoRow
          label="Trading Mode"
          value={(systemStatus?.mode ?? '—').toUpperCase()}
        />
        <InfoRow
          label="Last Health Check"
          value={health?.timestamp ? new Date(health.timestamp).toLocaleString() : '—'}
        />
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Shared layout helpers (scoped to this file — not exported)
// ---------------------------------------------------------------------------

const SectionHeading: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3 className="text-lg font-display font-medium border-b border-deep-teal-800/10 dark:border-white/10 pb-2">
    {children}
  </h3>
);

const SettingRow: React.FC<{
  label: string;
  description?: string;
  children: React.ReactNode;
}> = ({ label, description, children }) => (
  <div className="flex items-center justify-between gap-4">
    <div>
      <div className="font-medium text-sm">{label}</div>
      {description && (
        <div className="text-xs opacity-50 mt-0.5">{description}</div>
      )}
    </div>
    <div className="flex-shrink-0">{children}</div>
  </div>
);

const InfoRow: React.FC<{
  label: string;
  value: string;
  icon?: React.ReactNode;
}> = ({ label, value, icon }) => (
  <div className="flex items-center justify-between py-2 border-b border-deep-teal-800/5 dark:border-white/5">
    <span className="text-sm opacity-70">{label}</span>
    <span className="text-sm font-mono flex items-center gap-1.5">
      {icon}
      {value}
    </span>
  </div>
);

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type TabId = 'appearance' | 'notifications' | 'trading' | 'system';

interface TabDef {
  id: TabId;
  label: string;
  icon: React.ElementType;
}

const TABS: TabDef[] = [
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'trading', label: 'Trading', icon: TrendingUp },
  { id: 'system', label: 'System Info', icon: Server },
];

export const SettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('appearance');

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6 pb-12"
    >
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-medium text-deep-teal-800 dark:text-paper-100 mb-1">
          Settings
        </h1>
        <p className="text-obsidian-400/60 dark:text-paper-100/60 font-sans">
          Configure appearance, notification preferences, and view system status.
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar navigation */}
        <GlassCard
          variant="default"
          className="lg:w-56 p-2 flex flex-row lg:flex-col gap-1 h-fit overflow-x-auto"
        >
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-deep-teal-800 text-white shadow-md dark:bg-turquoise-mist dark:text-deep-teal-900'
                  : 'text-obsidian-400 hover:bg-deep-teal-800/5 dark:text-paper-100/60 dark:hover:bg-white/5'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </GlassCard>

        {/* Content area — lazy mount pattern: sections only render when active */}
        <GlassCard variant="default" className="flex-1 min-h-[500px]">
          {activeTab === 'appearance' && <AppearanceSection />}
          {activeTab === 'notifications' && <NotificationsSection />}
          {activeTab === 'trading' && <TradingSection />}
          {activeTab === 'system' && <SystemInfoSection />}
        </GlassCard>
      </div>
    </motion.div>
  );
};
