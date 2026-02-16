
import React, { useState, useEffect, useRef } from 'react';
import { motion, useScroll, useMotionValueEvent } from 'framer-motion';
import { Bell, User, Settings, HelpCircle, LogOut, Search, Plus, AlertTriangle, Command } from 'lucide-react';
import { SidebarTrigger } from './Sidebar';
import { SearchInput } from '../ui/SearchInput';
import { Avatar } from '../ui/Avatar';
import { Dropdown } from '../ui/Dropdown';
import { Badge } from '../ui/Badge';
import { Tooltip } from '../ui/Tooltip';
import { Logo } from '../ui/Logo';
import { NotificationsPanel, NotificationItem } from './NotificationsPanel';
import { cn } from '../../lib/utils';
import { smoothSpring } from '../../lib/animations';
import { useDashboard } from '../../contexts/DashboardContext';

interface HeaderProps {
  title?: string;
  showSearch?: boolean;
  className?: string;
  onNavigate?: (view: string) => void;
}

// --- Mock Notifications ---
const generateMockNotifications = (): NotificationItem[] => [
  {
    id: '1',
    type: 'trade',
    title: 'Alpha Seeker opened LONG NVDA',
    message: 'Executed market buy 450 shares @ $890.25 based on RSI divergence.',
    timestamp: new Date(Date.now() - 1000 * 60 * 2), // 2 mins ago
    read: false
  },
  {
    id: '2',
    type: 'alert',
    title: 'Price Alert: BTC > $67,000',
    message: 'Bitcoin has crossed the resistance level of 67k with high volume.',
    timestamp: new Date(Date.now() - 1000 * 60 * 15), // 15 mins ago
    read: false
  },
  {
    id: '3',
    type: 'curator',
    title: 'Allocation Adjustment',
    message: 'Curator increased Momentum allocation by 5% due to regime shift.',
    timestamp: new Date(Date.now() - 1000 * 60 * 60), // 1 hour ago
    read: true
  },
  {
    id: '4',
    type: 'system',
    title: 'API Latency Warning',
    message: 'Market data feed latency spiked to 145ms. Performance degraded.',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2.5), // 2.5 hours ago
    read: true
  },
  {
    id: '5',
    type: 'trade',
    title: 'Macro Sentinel closed SHORT TSLA',
    message: 'Take profit target reached at $175.40. Realized P&L: +$2,880.',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 4), // 4 hours ago
    read: true
  }
];

export const Header: React.FC<HeaderProps> = ({ 
  title = "Dashboard", 
  showSearch = true,
  className,
  onNavigate
}) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const { openAlertModal, openEmergencyPanel, openShortcuts, navigateToSettingsTab } = useDashboard();
  
  // Notification State
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>(generateMockNotifications());
  
  const unreadCount = notifications.filter(n => !n.read).length;

  const handleMarkRead = (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const handleMarkAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  // Track scroll for glass effect
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Dropdown Menu Items
  const userMenuItems = [
    { 
      label: 'Profile', 
      icon: User, 
      onClick: () => {
        navigateToSettingsTab('profile');
        onNavigate?.('Settings');
      } 
    },
    {
      label: (
        <div className="flex items-center justify-between w-full">
          <span>Notifications</span>
          {unreadCount > 0 && (
            <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-loss text-[10px] font-bold text-white px-1">
              {unreadCount}
            </span>
          )}
        </div>
      ),
      icon: Bell,
      onClick: () => onNavigate?.('Notifications')
    },
    { 
      label: 'Settings', 
      icon: Settings, 
      onClick: () => {
        navigateToSettingsTab('appearance');
        onNavigate?.('Settings');
      } 
    },
    { 
      label: 'Shortcuts', 
      icon: Command, 
      onClick: () => openShortcuts() 
    },
    { 
      label: 'Help & Support', 
      icon: HelpCircle, 
      onClick: () => {
        navigateToSettingsTab('help');
        onNavigate?.('Settings');
      } 
    },
    { type: 'divider' as const },
    { label: 'Log Out', icon: LogOut, danger: true, onClick: () => console.log('Logout') },
  ];

  return (
    <motion.header
      initial={{ backgroundColor: "rgba(255, 255, 255, 0)", borderBottomColor: "rgba(0,0,0,0)" }}
      animate={{ 
        backgroundColor: isScrolled 
          ? "var(--header-bg-scrolled)" 
          : "rgba(255, 255, 255, 0)",
        backdropFilter: isScrolled ? "blur(12px)" : "blur(0px)",
        borderBottomColor: isScrolled 
          ? "var(--header-border-scrolled)" 
          : "rgba(0,0,0,0)"
      }}
      transition={{ duration: 0.2 }}
      style={{
        ['--header-bg-scrolled' as string]: 'rgba(var(--bg-paper-100), 0.8)',
      }}
      className={cn(
        "sticky top-0 z-40 w-full h-16 px-4 md:px-8 flex items-center justify-between transition-all",
        isScrolled 
          ? "bg-paper-100/80 dark:bg-obsidian-400/80 border-b border-deep-teal-800/5 dark:border-white/5" 
          : "bg-transparent",
        className
      )}
    >
      {/* Left: Mobile Trigger & Title */}
      <div className="flex items-center gap-4">
        <SidebarTrigger />
        
        <div className="flex items-center gap-2">
          {/* Mobile Logo (Icon Only) */}
          <div className="md:hidden">
            <Logo showText={false} iconClassName="w-8 h-8" />
          </div>
          
          {/* Breadcrumb / Title */}
          <div className="hidden md:flex items-center text-sm font-sans text-obsidian-400/50 dark:text-paper-100/50">
            <span>Platform</span>
            <span className="mx-2">/</span>
            <span className="font-medium text-obsidian-400 dark:text-paper-100">{title}</span>
          </div>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-3 md:gap-5">
        {/* Search */}
        {showSearch && (
          <div className="hidden md:block w-64 lg:w-80">
            <SearchInput 
              id="global-search" // Added ID for global focus
              placeholder="Search markets, agents... (Ctrl+K)" 
              className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent focus:bg-paper-100 dark:focus:bg-obsidian-300"
            />
          </div>
        )}
        {showSearch && (
          <button className="md:hidden p-2 text-obsidian-400/60 dark:text-paper-100/60">
            <Search className="w-5 h-5" />
          </button>
        )}

        {/* Global Alert Button */}
        <button 
           onClick={() => openAlertModal()}
           className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-deep-teal-800/5 dark:bg-white/5 hover:bg-deep-teal-800/10 dark:hover:bg-white/10 text-xs font-medium text-obsidian-400 dark:text-paper-100 transition-colors"
        >
           <Bell className="w-3.5 h-3.5" />
           New Alert
        </button>

        {/* Emergency Control Button */}
        <Tooltip content="Emergency Controls (Ctrl+Shift+K)" side="bottom">
          <button 
            onClick={openEmergencyPanel}
            className="group relative p-2 rounded-lg bg-orange-500/10 hover:bg-red-500/20 text-orange-500 hover:text-red-500 transition-all border border-orange-500/20 hover:border-red-500/50"
          >
            <AlertTriangle className="w-5 h-5" />
            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[9px] font-bold text-white shadow-sm">
              12
            </span>
          </button>
        </Tooltip>

        {/* Notifications */}
        <div className="relative">
          <button 
            onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
            className={cn(
              "p-2 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-turquoise-mist/50 relative",
              isNotificationsOpen 
                ? "bg-deep-teal-800/10 dark:bg-white/10 text-deep-teal-800 dark:text-paper-100" 
                : "hover:bg-deep-teal-800/5 dark:hover:bg-white/5 text-obsidian-400/80 dark:text-paper-100/80"
            )}
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-loss rounded-full shadow-sm ring-2 ring-paper-100 dark:ring-obsidian-400" />
            )}
          </button>

          {/* Panel */}
          <NotificationsPanel 
            isOpen={isNotificationsOpen} 
            onClose={() => setIsNotificationsOpen(false)}
            notifications={notifications}
            onMarkRead={handleMarkRead}
            onMarkAllRead={handleMarkAllRead}
            onNavigate={onNavigate}
            onOpenSettings={() => {
              navigateToSettingsTab('notifications');
              if (onNavigate) onNavigate('Settings');
            }}
          />
        </div>

        {/* User Profile */}
        <Dropdown
          align="end"
          trigger={
            <div className="flex items-center gap-3 pl-2 border-l border-deep-teal-800/10 dark:border-white/10">
              <Avatar 
                src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80" 
                name="Director" 
                size="md" 
                status="online"
                className="cursor-pointer"
              />
            </div>
          }
          items={userMenuItems}
        />
      </div>
    </motion.header>
  );
};
