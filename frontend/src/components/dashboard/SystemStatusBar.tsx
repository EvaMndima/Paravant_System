import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown, ChevronUp, Wifi, WifiOff, Database,
  MessageCircle, Server, Clock, Activity,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

export type ServiceStatus = 'online' | 'degraded' | 'offline';

export interface ServiceHealth {
  name: string;
  status: ServiceStatus;
  latencyMs?: number;
  lastChecked: string;
  details?: string;
}

export interface SystemStatusBarProps {
  services?: ServiceHealth[];
  uptime?: string;
  lastDataSync?: string;
  collapsible?: boolean;
  defaultExpanded?: boolean;
  className?: string;
}

const mockServices: ServiceHealth[] = [
  { name: 'Binance API', status: 'online', latencyMs: 42, lastChecked: 'just now', details: 'Testnet — Spot trading active' },
  { name: 'Telegram Bot', status: 'online', latencyMs: 118, lastChecked: '30s ago', details: 'Alerts channel connected' },
  { name: 'Database', status: 'online', latencyMs: 3, lastChecked: 'just now', details: 'SQLite — 284 MB' },
  { name: 'WebSocket Feed', status: 'degraded', latencyMs: 850, lastChecked: '5s ago', details: 'High latency — polling fallback active' },
];

const serviceIcons: Record<string, React.ElementType> = {
  'Binance API': Wifi,
  'Telegram Bot': MessageCircle,
  'Database': Database,
  'WebSocket Feed': Activity,
};

const statusConfig: Record<ServiceStatus, {
  dot: string;
  badge: 'success' | 'warning' | 'danger';
  label: string;
  pulse: boolean;
}> = {
  online: { dot: 'bg-gain', badge: 'success', label: 'Online', pulse: true },
  degraded: { dot: 'bg-warning', badge: 'warning', label: 'Degraded', pulse: false },
  offline: { dot: 'bg-loss', badge: 'danger', label: 'Offline', pulse: false },
};

// Derive overall system health from individual services
function getSystemStatus(services: ServiceHealth[]): ServiceStatus {
  if (services.some(s => s.status === 'offline')) return 'offline';
  if (services.some(s => s.status === 'degraded')) return 'degraded';
  return 'online';
}

const LatencyBadge: React.FC<{ ms: number }> = ({ ms }) => {
  const color = ms < 100 ? 'text-gain' : ms < 500 ? 'text-warning' : 'text-loss';
  return (
    <span className={cn('text-[10px] font-mono', color)}>
      {ms}ms
    </span>
  );
};

export const SystemStatusBar: React.FC<SystemStatusBarProps> = ({
  services = mockServices,
  uptime = '14d 6h 22m',
  lastDataSync = 'just now',
  collapsible = true,
  defaultExpanded = false,
  className,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [tickTime, setTickTime] = useState(0);

  // Simulate live tick every 5 seconds for the "just now" feel
  useEffect(() => {
    const interval = setInterval(() => setTickTime(t => t + 1), 5000);
    return () => clearInterval(interval);
  }, []);

  const systemStatus = getSystemStatus(services);
  const sysConfig = statusConfig[systemStatus];
  const onlineCount = services.filter(s => s.status === 'online').length;

  return (
    <GlassCard variant="subtle" padding="sm" className={cn('', className)}>
      {/* Compact summary row */}
      <div className="flex items-center gap-3 px-1">
        {/* System health dot */}
        <div className="relative flex h-2.5 w-2.5 shrink-0">
          {sysConfig.pulse && (
            <span className={cn('animate-ping absolute inline-flex h-full w-full rounded-full opacity-60', sysConfig.dot)} />
          )}
          <span className={cn('relative inline-flex rounded-full h-2.5 w-2.5', sysConfig.dot)} />
        </div>

        {/* System label */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Server className="w-3.5 h-3.5 text-obsidian-400/40 dark:text-paper-100/40 shrink-0" />
          <span className="text-xs font-mono font-medium text-obsidian-400 dark:text-paper-100 truncate">
            System {systemStatus === 'online' ? 'Operational' : systemStatus === 'degraded' ? 'Degraded' : 'Down'}
          </span>
          <Badge variant={sysConfig.badge} size="sm">
            {onlineCount}/{services.length} services
          </Badge>
        </div>

        {/* Uptime + sync */}
        <div className="hidden sm:flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40">
            <Clock className="w-3 h-3" />
            Uptime: {uptime}
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40">
            <Activity className="w-3 h-3" />
            Sync: {lastDataSync}
          </div>
        </div>

        {/* Expand toggle */}
        {collapsible && (
          <button
            onClick={() => setExpanded(v => !v)}
            className="p-1 rounded-lg text-obsidian-400/40 dark:text-paper-100/40 hover:text-obsidian-400 dark:hover:text-paper-100 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors shrink-0"
            aria-label={expanded ? 'Collapse service details' : 'Expand service details'}
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        )}
      </div>

      {/* Expanded service rows */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-2 border-t border-deep-teal-800/5 dark:border-white/5 pt-3">
              {services.map((service, idx) => {
                const cfg = statusConfig[service.status];
                const ServiceIcon = serviceIcons[service.name] ?? Wifi;

                return (
                  <motion.div
                    key={service.name}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.04 }}
                    className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors"
                  >
                    {/* Icon */}
                    <div className={cn(
                      'p-1.5 rounded-lg shrink-0',
                      service.status === 'online'
                        ? 'bg-gain/10 text-gain'
                        : service.status === 'degraded'
                          ? 'bg-warning/10 text-warning'
                          : 'bg-loss/10 text-loss'
                    )}>
                      {service.status === 'offline'
                        ? <WifiOff className="w-3.5 h-3.5" />
                        : <ServiceIcon className="w-3.5 h-3.5" />
                      }
                    </div>

                    {/* Name + details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-medium text-obsidian-400 dark:text-paper-100">
                          {service.name}
                        </span>
                        <Badge variant={cfg.badge} size="sm">{cfg.label}</Badge>
                      </div>
                      {service.details && (
                        <span className="text-[10px] font-sans text-obsidian-400/40 dark:text-paper-100/40 truncate block">
                          {service.details}
                        </span>
                      )}
                    </div>

                    {/* Latency + time */}
                    <div className="text-right shrink-0 space-y-0.5">
                      {service.latencyMs !== undefined && (
                        <LatencyBadge ms={service.latencyMs} />
                      )}
                      <div className="text-[10px] font-mono text-obsidian-400/30 dark:text-paper-100/30 block">
                        {service.lastChecked}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
};
