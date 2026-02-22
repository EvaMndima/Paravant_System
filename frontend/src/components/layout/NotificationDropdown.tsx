/**
 * NotificationDropdown — Alert notification panel triggered by the header bell icon.
 *
 * Uses AlertEntry type from the API (audit log format: id, timestamp, action, actor, details).
 *
 * Features (per 7.3.4):
 * - Recent alerts with action label + relative timestamp
 * - Click notification → navigate to /alerts
 * - "Acknowledge" per alert (calls onMarkRead)
 * - "Acknowledge All" button
 * - "View All" link → /alerts page
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Bell, CheckCheck, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AlertEntry } from '@/types/api';
import { cn } from '@/lib/utils';

export interface NotificationDropdownProps {
  isOpen: boolean;
  alerts: AlertEntry[];
  onClose: () => void;
  onMarkRead: (alertId: string) => void;
  onMarkAllRead: () => void;
}

function formatRelativeTime(isoString: string): string {
  try {
    const elapsed = Date.now() - new Date(isoString).getTime();
    const minutes = Math.floor(elapsed / 60_000);
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  } catch {
    return '';
  }
}

/** Derive a display label and color cue from the audit log action string */
function getActionStyle(action: string): { dot: string; label: string } {
  const a = action.toLowerCase();
  if (a.includes('kill') || a.includes('halt')) return { dot: 'bg-loss animate-pulse', label: '🚨 ' + action };
  if (a.includes('error') || a.includes('fail')) return { dot: 'bg-loss', label: action };
  if (a.includes('warn')) return { dot: 'bg-warning', label: action };
  if (a.includes('trade') || a.includes('order') || a.includes('fill')) return { dot: 'bg-gain', label: action };
  return { dot: 'bg-white/30', label: action };
}

export const NotificationDropdown: React.FC<NotificationDropdownProps> = ({
  isOpen,
  alerts,
  onClose,
  onMarkRead,
  onMarkAllRead,
}) => {
  const navigate = useNavigate();

  const handleAlertClick = (alert: AlertEntry) => {
    onMarkRead(alert.id);
    onClose();
    navigate('/alerts');
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-[90]"
            onClick={onClose}
            aria-hidden="true"
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -8 }}
            transition={{ type: 'spring', stiffness: 400, damping: 35 }}
            className={cn(
              'absolute right-0 top-full mt-2 z-[100]',
              'w-80 rounded-2xl shadow-2xl',
              'bg-obsidian-300/95 backdrop-blur-xl border border-white/10',
            )}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
              <div className="flex items-center gap-2">
                <Bell className="w-4 h-4 text-paper-100/60" />
                <span className="text-sm font-medium">Recent Activity</span>
                {alerts.length > 0 && (
                  <span className="text-[10px] font-mono font-bold bg-loss text-white rounded-full px-1.5 py-0.5 leading-none">
                    {alerts.length}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {alerts.length > 0 && (
                  <button
                    onClick={onMarkAllRead}
                    className="flex items-center gap-1 text-[11px] text-paper-100/50 hover:text-paper-100 transition-colors"
                    title="Acknowledge all"
                  >
                    <CheckCheck className="w-3.5 h-3.5" />
                    All
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="p-0.5 rounded hover:bg-white/10 transition-colors"
                  aria-label="Close notifications"
                >
                  <X className="w-4 h-4 text-paper-100/50" />
                </button>
              </div>
            </div>

            {/* Alert list */}
            <div className="max-h-80 overflow-y-auto">
              {alerts.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 gap-2">
                  <Bell className="w-8 h-8 text-paper-100/20" />
                  <p className="text-xs text-paper-100/40 font-mono">No recent activity</p>
                </div>
              ) : (
                <ul>
                  {alerts.slice(0, 10).map((alert) => {
                    const style = getActionStyle(alert.action);
                    return (
                      <li key={alert.id}>
                        <button
                          onClick={() => handleAlertClick(alert)}
                          className={cn(
                            'w-full flex items-start gap-3 px-4 py-3 text-left transition-colors',
                            'hover:bg-white/5 border-b border-white/5 last:border-none',
                          )}
                        >
                          {/* Action color dot */}
                          <div className="flex-shrink-0 mt-1.5">
                            <div className={cn('w-2 h-2 rounded-full', style.dot)} />
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-paper-100 truncate">
                              {style.label}
                            </p>
                            {alert.actor && (
                              <p className="text-[11px] text-paper-100/40 truncate mt-0.5">
                                by {alert.actor}
                              </p>
                            )}
                            <p className="text-[10px] font-mono text-paper-100/30 mt-0.5">
                              {formatRelativeTime(alert.timestamp)}
                            </p>
                          </div>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2.5 border-t border-white/10">
              <button
                onClick={() => { onClose(); navigate('/alerts'); }}
                className="flex items-center gap-1.5 text-xs text-paper-100/50 hover:text-paper-100 transition-colors w-full justify-center py-1"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                View all alerts
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
