
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  Info,
  AlertOctagon,
  CheckCircle2,
  Bell,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Skeleton } from '@/components/ui/Skeleton';
import { ApiErrorDisplay } from '@/components/ui/ApiErrorDisplay';
import { useDashboardAlerts, useAcknowledgeAlert } from '@/hooks';
import { useToast } from '@/contexts/ToastContext';

export const AlertsPage: React.FC = () => {
  const [filter, setFilter] = useState<'ALL' | 'risk' | 'system' | 'strategy'>('ALL');
  const { data: alerts, isLoading, isError, error, refetch } = useDashboardAlerts();
  const acknowledgeMutation = useAcknowledgeAlert();
  const { addToast } = useToast();

  const handleAcknowledge = (alertId: string) => {
    acknowledgeMutation.mutate(alertId, {
      onSuccess: () => {
        addToast('success', 'Alert Acknowledged', 'Alert marked as read');
      },
      onError: (error) => {
        addToast('error', 'Acknowledgement Failed', error.message);
      },
    });
  };

  // Filter by action type (backend uses audit log format with action field)
  const filteredAlerts = (alerts ?? []).filter((alert) => {
    if (filter === 'ALL') return true;
    if (filter === 'risk')
      return (
        alert.action.includes('kill_switch') ||
        alert.action.includes('risk') ||
        alert.action.includes('breach')
      );
    if (filter === 'system')
      return alert.action.includes('system') || alert.action.includes('health');
    if (filter === 'strategy') return alert.action.includes('strategy');
    return true;
  });

  const AlertIcon = ({ action }: { action: string }) => {
    const isRisk =
      action.includes('kill') || action.includes('risk') || action.includes('breach');
    const isWarning = action.includes('warn') || action.includes('limit');

    if (isRisk)
      return <AlertOctagon className="w-5 h-5 text-loss" />;
    if (isWarning) return <AlertTriangle className="w-5 h-5 text-warning" />;
    return <Info className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6 pb-12"
    >
      {isError && <ApiErrorDisplay error={error as Error} onRetry={refetch} />}
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-medium text-deep-teal-800 dark:text-paper-100 mb-1">
            System Alerts
          </h1>
          <p className="text-obsidian-400/60 dark:text-paper-100/60 font-sans">
            Real-time notifications and system events.
          </p>
        </div>
        <div className="text-xs font-mono text-obsidian-400/50 dark:text-paper-100/50">
          {filteredAlerts.length} alerts
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 pb-2 overflow-x-auto">
        {(['ALL', 'risk', 'system', 'strategy'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`px-4 py-1.5 rounded-full text-xs font-medium border transition-all ${
              filter === tab
                ? 'bg-deep-teal-800 text-white border-deep-teal-800 dark:bg-turquoise-mist dark:text-deep-teal-900'
                : 'bg-transparent border-deep-teal-800/10 dark:border-white/10 text-obsidian-400 dark:text-paper-100/60 hover:border-deep-teal-800/30'
            }`}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Alert Stream */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-2xl" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {filteredAlerts.length > 0 ? (
            filteredAlerts.map((alert, index) => {
              const isRisk =
                alert.action.includes('kill') ||
                alert.action.includes('risk') ||
                alert.action.includes('breach');
              const isWarning =
                alert.action.includes('warn') || alert.action.includes('limit');

              return (
                <motion.div
                  key={alert.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <GlassCard
                    variant="default"
                    className="flex items-start gap-4 transition-all border-l-4"
                    style={{
                      borderLeftColor: isRisk
                        ? '#e74c3c'
                        : isWarning
                          ? '#e67e22'
                          : '#2a9d8f',
                    }}
                  >
                    <div className="mt-1 flex-shrink-0">
                      <AlertIcon action={alert.action} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <h4
                            className={`text-sm font-bold ${
                              isRisk
                                ? 'text-loss'
                                : isWarning
                                  ? 'text-warning'
                                  : 'text-deep-teal-800 dark:text-turquoise-mist'
                            }`}
                          >
                            {alert.action.replace(/_/g, ' ').toUpperCase()}
                          </h4>
                          <p className="text-sm text-obsidian-400 dark:text-paper-100 mt-1">
                            By {alert.actor}
                            {alert.details &&
                              typeof alert.details === 'object' &&
                              Object.keys(alert.details).length > 0 && (
                                <span className="text-xs font-mono opacity-60 ml-2">
                                  {Object.entries(alert.details)
                                    .slice(0, 2)
                                    .map(([k, v]) => `${k}: ${v}`)
                                    .join(', ')}
                                </span>
                              )}
                          </p>
                        </div>
                        <span className="text-xs font-mono opacity-50 whitespace-nowrap">
                          {new Date(alert.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleAcknowledge(alert.id)}
                      className="mt-1 text-obsidian-400/40 hover:text-success transition-colors"
                      title="Mark as read"
                      disabled={acknowledgeMutation.isPending}
                    >
                      <CheckCircle2 className="w-5 h-5" />
                    </button>
                  </GlassCard>
                </motion.div>
              );
            })
          ) : (
            <div className="flex flex-col items-center justify-center py-20 opacity-40">
              <Bell className="w-12 h-12 mb-4" />
              <p>No alerts found</p>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
};
