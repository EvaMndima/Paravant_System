import React, { useState } from 'react';
import { SidebarContext } from '@/contexts/SidebarContext';
import { useSidebar } from '@/hooks/useSidebar';
import { NavLink } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  TrendingUp,
  Cpu,
  ShieldAlert,
  ListOrdered,
  Bell,
  Wallet,
  Settings,
  TestTube,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  AlertTriangle,
} from 'lucide-react';
import { KillSwitchModal } from '@/components/modals/KillSwitchModal';
import { useKillSwitch, useActivateKillSwitch, useDeactivateKillSwitch } from '@/hooks';
import { useToast } from '@/contexts/ToastContext';
import { cn } from '@/lib/utils';


export const SidebarProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      const savedState = localStorage.getItem('sidebar-collapsed');
      return savedState ? JSON.parse(savedState) : false;
    }
    return false;
  });

  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const toggleCollapse = () => {
    setIsCollapsed((prev: boolean) => {
      const newState = !prev;
      localStorage.setItem('sidebar-collapsed', JSON.stringify(newState));
      return newState;
    });
  };

  const toggleMobile = () => setIsMobileOpen((prev: boolean) => !prev);
  const closeMobile = () => setIsMobileOpen(false);

  return (
    <SidebarContext.Provider value={{
      isCollapsed,
      toggleCollapse,
      isMobileOpen,
      toggleMobile,
      closeMobile
    }}>
      {children}
    </SidebarContext.Provider>
  );
};

// Mobile Trigger
export const SidebarTrigger = ({ className }: { className?: string }) => {
  const { toggleMobile } = useSidebar();
  return (
    <button
      onClick={toggleMobile}
      className={cn('p-2 rounded-lg hover:bg-deep-teal-800/5 dark:hover:bg-white/10 md:hidden', className)}
    >
      <Menu className="w-6 h-6 text-deep-teal-800 dark:text-paper-100" />
    </button>
  );
};

// Production navigation items (per plan)
const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Cockpit' },
  { path: '/portfolio', icon: TrendingUp, label: 'Portfolio' },
  { path: '/strategies', icon: Cpu, label: 'Strategies' },
  { path: '/risk', icon: ShieldAlert, label: 'Risk' },
  { path: '/orders', icon: ListOrdered, label: 'Orders' },
  { path: '/alerts', icon: Bell, label: 'Alerts' },
  { path: '/accounts', icon: Wallet, label: 'Accounts' },
  { path: '/settings', icon: Settings, label: 'Settings' },
  { path: '/backtest', icon: TestTube, label: 'Backtest' },
];

// ---------------------------------------------------------------------------
// Kill switch button + modal, co-located for simplicity
// ---------------------------------------------------------------------------

const KillSwitchSection: React.FC<{ collapsed: boolean }> = ({ collapsed }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const killSwitchQuery = useKillSwitch();
  const activateMutation = useActivateKillSwitch();
  const deactivateMutation = useDeactivateKillSwitch();
  const { addToast } = useToast();

  const isActive = killSwitchQuery.data?.active ?? false;

  const handleConfirm = async (reason: string) => {
    if (isActive) {
      // Deactivate — API takes the confirmation code
      await deactivateMutation.mutateAsync('DEACTIVATE');
      console.info('[KillSwitch] Deactivated at', new Date().toISOString());
      addToast('success', 'Kill switch deactivated', 'Trading has resumed.');
    } else {
      // Activate — API takes reason string directly
      await activateMutation.mutateAsync(reason);
      console.info('[KillSwitch] Activated at', new Date().toISOString(), 'reason:', reason);
      addToast('error', '🚨 Kill switch ACTIVE', 'All trading halted. Reason: ' + reason);
    }
    setModalOpen(false);
  };

  const handleError = (error: unknown) => {
    const msg = error instanceof Error ? error.message : 'Operation failed';
    addToast('error', 'Kill switch error', msg);
    // Modal stays open on error (handled by not calling setModalOpen(false))
  };

  // Wrap confirm to catch errors and keep modal open
  const handleConfirmSafe = async (reason: string) => {
    try {
      await handleConfirm(reason);
    } catch (err) {
      handleError(err);
      throw err; // Re-throw so KillSwitchModal sees the failure
    }
  };

  return (
    <>
      <button
        data-kill-switch-trigger
        onClick={() => setModalOpen(true)}
        className={cn(
          'w-full flex items-center gap-3 p-3 rounded-xl transition-all duration-300',
          isActive
            ? 'bg-loss text-white animate-pulse shadow-lg shadow-loss/30'
            : 'bg-orange-500/10 hover:bg-red-500/20 text-orange-500 hover:text-red-500 border border-orange-500/20 hover:border-red-500/50',
          collapsed && 'justify-center p-2',
        )}
        role={isActive ? 'alert' : 'button'}
        aria-live={isActive ? 'assertive' : 'off'}
        aria-label={isActive ? 'Kill switch is ACTIVE — click to deactivate' : 'Activate kill switch'}
      >
        <AlertTriangle className="w-5 h-5 flex-shrink-0" />
        {!collapsed && (
          <span className="text-sm font-medium whitespace-nowrap">
            {isActive ? '🚨 KILL SWITCH ACTIVE' : 'Kill Switch'}
          </span>
        )}
      </button>

      <KillSwitchModal
        isOpen={modalOpen}
        isActive={isActive}
        onConfirm={handleConfirmSafe}
        onCancel={() => setModalOpen(false)}
      />
    </>
  );
};

// ---------------------------------------------------------------------------
// Sidebar Content Component
// ---------------------------------------------------------------------------

const SidebarContent: React.FC<{
  isMobile?: boolean;
  isCollapsed: boolean;
  closeMobile: () => void;
  toggleCollapse: () => void;
}> = ({ isMobile = false, isCollapsed, closeMobile, toggleCollapse }) => {
  const collapsed = isMobile ? false : isCollapsed;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className={cn('flex items-center h-20 px-6 transition-all duration-300', collapsed ? 'justify-center px-0' : 'justify-between')}>
        <div className={cn('flex items-center gap-3 overflow-hidden', collapsed ? 'w-10 justify-center' : 'w-auto')}>
          {/* Logo */}
          <div className="text-2xl font-serif font-bold text-deep-teal-800 dark:text-turquoise-mist">
            {collapsed ? 'P' : 'PARAVANT'}
          </div>
        </div>

        {/* Mobile Close Button */}
        <button className="md:hidden p-1" onClick={closeMobile}>
          <X className="w-5 h-5 text-obsidian-400 dark:text-paper-100" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-6 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            onClick={() => isMobile && closeMobile()}
            className={({ isActive }) =>
              cn(
                'relative flex items-center rounded-xl transition-all duration-300 group outline-none focus-visible:ring-2 focus-visible:ring-turquoise-mist/50',
                collapsed ? 'justify-center h-12 w-12 mx-auto' : 'space-x-3 px-4 py-3',
                isActive
                  ? 'text-deep-teal-800 dark:text-turquoise-mist'
                  : 'text-obsidian-400/60 dark:text-paper-100/60',
              )
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.div
                    layoutId="activeNavIndicator"
                    className="absolute inset-0 bg-deep-teal-800/5 dark:bg-white/10 rounded-xl"
                    initial={false}
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                  />
                )}

                <item.icon
                  className={cn(
                    'relative z-10 w-5 h-5 transition-colors duration-300',
                    isActive
                      ? 'text-deep-teal-800 dark:text-turquoise-mist'
                      : 'text-obsidian-400/60 dark:text-paper-100/60 group-hover:text-deep-teal-800 dark:group-hover:text-paper-100',
                  )}
                  strokeWidth={isActive ? 2 : 1.5}
                />

                {!collapsed && (
                  <span className={cn(
                    'relative z-10 font-sans font-medium tracking-wide text-sm transition-colors duration-300 whitespace-nowrap',
                    isActive
                      ? 'text-deep-teal-800 dark:text-turquoise-mist'
                      : 'text-obsidian-400/60 dark:text-paper-100/60 group-hover:text-deep-teal-800 dark:group-hover:text-paper-100',
                  )}>
                    {item.label}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer - Kill Switch */}
      <div className="p-3 space-y-4">
        <div className="h-px w-full bg-deep-teal-800/5 dark:bg-white/5" />

        {/* Kill Switch (always visible at bottom) */}
        <KillSwitchSection collapsed={collapsed} />

        {/* Collapse Toggle (Desktop only) */}
        <button
          onClick={toggleCollapse}
          className="hidden md:flex w-full justify-center p-2 rounded-lg text-obsidian-400/40 dark:text-paper-100/40 hover:text-deep-teal-800 dark:hover:text-paper-100 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors"
        >
          {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
        </button>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Sidebar Component
// ---------------------------------------------------------------------------

export const Sidebar: React.FC = () => {
  const { isCollapsed, toggleCollapse, isMobileOpen, closeMobile } = useSidebar();

  return (
    <>
      {/* Mobile Drawer */}
      <AnimatePresence>
        {isMobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={closeMobile}
              className="fixed inset-0 z-40 bg-obsidian-400/60 backdrop-blur-sm md:hidden"
            />
            {/* Drawer */}
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 z-50 w-72 bg-paper-100 dark:bg-obsidian-400 border-r border-deep-teal-800/10 dark:border-white/10 md:hidden"
            >
              <SidebarContent isMobile={true} isCollapsed={isCollapsed} closeMobile={closeMobile} toggleCollapse={toggleCollapse} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Desktop Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: isCollapsed ? 80 : 280 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className="hidden md:block h-screen sticky top-0 left-0 z-30 flex-shrink-0 border-r border-deep-teal-800/5 dark:border-white/5 bg-paper-100/80 dark:bg-obsidian-400/80 backdrop-blur-xl"
      >
        <SidebarContent isCollapsed={isCollapsed} closeMobile={closeMobile} toggleCollapse={toggleCollapse} />
      </motion.aside>
    </>
  );
};
