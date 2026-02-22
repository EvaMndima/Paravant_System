import React, { useRef, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Bell, Sun, Moon, ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { SidebarTrigger } from './Sidebar';
import { NotificationDropdown } from './NotificationDropdown';
import { RegimeChangeModal, REGIME_OPTIONS, type RegimeType } from '@/components/modals/RegimeChangeModal';
import { useTheme } from '@/contexts/ThemeContext';
import { useDashboardAlerts, useRegime, useSetRegime, useAcknowledgeAlert, useKillSwitch } from '@/hooks';
import { useToast } from '@/contexts/ToastContext';
import { cn } from '@/lib/utils';

interface HeaderProps {
  title?: string;
  className?: string;
}

export const Header: React.FC<HeaderProps> = ({
  title = 'Cockpit',
  className,
}) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [regimeModalOpen, setRegimeModalOpen] = useState(false);
  const _bellRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const { toggleMode } = useTheme();
  const { addToast } = useToast();

  // Data hooks — useDashboardAlerts(false) returns AlertEntry[] directly
  const alertsQuery = useDashboardAlerts(false);
  const alerts = alertsQuery.data ?? [];

  // Count unread: audit log AlertEntry doesn't have acknowledged field —
  // we show all recent alerts; dropdown lets user mark via API
  const unreadCount = alerts.length;

  const regimeQuery = useRegime();
  const currentRegime = (regimeQuery.data?.regime ?? 'unknown') as RegimeType;

  const setRegimeMutation = useSetRegime();
  const acknowledgeAlertMutation = useAcknowledgeAlert();
  const killSwitchQuery = useKillSwitch();
  const isKillSwitchActive = killSwitchQuery.data?.active ?? false;

  // Scroll-based glass effect
  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 10);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Handle regime change
  const handleRegimeConfirm = async (newRegime: RegimeType, note: string) => {
    await setRegimeMutation.mutateAsync({ regime: newRegime, note });
    addToast('success', 'Regime updated', `Market regime changed to ${newRegime.replace(/_/g, ' ')}`);
  };

  // Handle mark alert acknowledged
  const handleMarkRead = (alertId: string) => {
    acknowledgeAlertMutation.mutate(alertId);
  };

  const handleMarkAllRead = () => {
    alerts.forEach((a: import('@/types/api').AlertEntry) => acknowledgeAlertMutation.mutate(a.id));
  };

  // Get regime badge styles
  const regimeStyle = REGIME_OPTIONS.find((r) => r.value === currentRegime) ?? REGIME_OPTIONS[4];

  return (
    <>
      <motion.header
        initial={{ backgroundColor: 'rgba(255, 255, 255, 0)', borderBottomColor: 'rgba(0,0,0,0)' }}
        animate={{
          backgroundColor: isScrolled ? 'rgba(253, 251, 248, 0.8)' : 'rgba(255, 255, 255, 0)',
          backdropFilter: isScrolled ? 'blur(12px)' : 'blur(0px)',
          borderBottomColor: isScrolled ? 'rgba(30, 64, 74, 0.05)' : 'rgba(0,0,0,0)',
        }}
        transition={{ duration: 0.2 }}
        className={cn(
          'sticky top-0 z-40 w-full h-16 px-4 md:px-8 flex items-center justify-between transition-all',
          isScrolled
            ? 'bg-paper-100/80 dark:bg-obsidian-400/80 border-b border-deep-teal-800/5 dark:border-white/5'
            : 'bg-transparent',
          className,
        )}
      >
        {/* Left: Mobile Trigger & Title */}
        <div className="flex items-center gap-4">
          <SidebarTrigger />

          {/* Breadcrumb / Title */}
          <div className="flex items-center text-sm font-sans text-obsidian-400/50 dark:text-paper-100/50">
            <span className="hidden md:inline">Platform</span>
            <span className="hidden md:inline mx-2">/</span>
            <span className="font-medium text-obsidian-400 dark:text-paper-100">{title}</span>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Regime Badge / Selector */}
          {!regimeQuery.isLoading && (
            <button
              onClick={() => setRegimeModalOpen(true)}
              title={`Market regime: ${regimeStyle.label}. Click to change.`}
              className={cn(
                'hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-mono font-bold transition-all hover:opacity-80',
                regimeStyle.bg,
                regimeStyle.color,
              )}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-current" />
              <span className="hidden md:inline">{regimeStyle.label}</span>
            </button>
          )}

          {/* Kill Switch compact indicator — pulsing red dot when active, links to Risk page */}
          {isKillSwitchActive && (
            <button
              onClick={() => navigate('/risk')}
              title="Kill switch ACTIVE — click to view Risk page"
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-loss/10 border border-loss/30 text-xs font-mono font-bold text-loss hover:bg-loss/20 transition-colors"
              aria-label="Kill switch active"
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-loss opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-loss" />
              </span>
              <ShieldAlert className="w-3.5 h-3.5" />
              <span className="hidden md:inline">HALTED</span>
            </button>
          )}

          {/* Theme Toggle */}
          <button
            onClick={toggleMode}
            className="p-2 rounded-lg hover:bg-deep-teal-800/5 dark:hover:bg-white/10 transition-colors text-obsidian-400 dark:text-paper-100"
            aria-label="Toggle theme"
          >
            <div className="relative w-5 h-5">
              <Sun className="absolute inset-0 h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute inset-0 h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            </div>
          </button>

          {/* Notification Bell */}
          <div ref={_bellRef} className="relative">
            <button
              onClick={() => setNotifOpen((p) => !p)}
              className="relative p-2 rounded-lg hover:bg-deep-teal-800/5 dark:hover:bg-white/10 text-obsidian-400/80 dark:text-paper-100/80 transition-colors"
              aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount})` : ''}`}
              aria-haspopup="true"
              aria-expanded={notifOpen}
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute top-1 right-1 min-w-[18px] h-[18px] flex items-center justify-center bg-loss text-white text-[10px] font-bold rounded-full px-1 ring-2 ring-paper-100 dark:ring-obsidian-400"
                >
                  {unreadCount > 9 ? '9+' : unreadCount}
                </motion.span>
              )}
            </button>

            <NotificationDropdown
              isOpen={notifOpen}
              alerts={alerts}
              onClose={() => setNotifOpen(false)}
              onMarkRead={handleMarkRead}
              onMarkAllRead={handleMarkAllRead}
            />
          </div>
        </div>
      </motion.header>

      {/* Regime change confirmation modal */}
      <RegimeChangeModal
        isOpen={regimeModalOpen}
        currentRegime={currentRegime}
        onClose={() => setRegimeModalOpen(false)}
        onConfirm={handleRegimeConfirm}
      />
    </>
  );
};
