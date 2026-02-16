
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  LayoutDashboard, LineChart, Wallet, ShieldCheck, Cpu, 
  ChevronLeft, ChevronRight, Sun, Moon, LogOut, Menu, X, History, Bot,
  Bell
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Avatar } from '../ui/Avatar';
import { Tooltip } from '../ui/Tooltip';
import { Logo } from '../ui/Logo';

// --- Context ---

interface SidebarContextType {
  isCollapsed: boolean;
  toggleCollapse: () => void;
  isMobileOpen: boolean;
  toggleMobile: () => void;
  closeMobile: () => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export const useSidebar = () => {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
};

export const SidebarProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Initialize lazily to avoid layout shift and context errors
  const [isCollapsed, setIsCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      const savedState = localStorage.getItem('sidebar-collapsed');
      return savedState ? JSON.parse(savedState) : false;
    }
    return false;
  });

  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const toggleCollapse = () => {
    setIsCollapsed((prev) => {
      const newState = !prev;
      localStorage.setItem('sidebar-collapsed', JSON.stringify(newState));
      return newState;
    });
  };

  const toggleMobile = () => setIsMobileOpen((prev) => !prev);
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

// --- Helper Components ---

const ThemeToggle = () => {
  return (
    <button
      onClick={() => {
        const html = document.documentElement;
        if (html.classList.contains('dark')) {
          html.classList.remove('dark');
          localStorage.setItem('theme', 'light');
        } else {
          html.classList.add('dark');
          localStorage.setItem('theme', 'dark');
        }
      }}
      className="p-2 rounded-lg hover:bg-deep-teal-800/5 dark:hover:bg-white/10 transition-colors text-obsidian-400 dark:text-paper-100"
      aria-label="Toggle theme"
    >
      <div className="relative w-5 h-5">
        <Sun className="absolute inset-0 h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
        <Moon className="absolute inset-0 h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      </div>
    </button>
  );
};

export const SidebarTrigger = ({ className }: { className?: string }) => {
  const { toggleMobile } = useSidebar();
  return (
    <button 
      onClick={toggleMobile}
      className={cn("p-2 rounded-lg hover:bg-deep-teal-800/5 dark:hover:bg-white/10 md:hidden", className)}
    >
      <Menu className="w-6 h-6 text-deep-teal-800 dark:text-paper-100" />
    </button>
  );
};

// --- Main Component ---

export interface SidebarProps {
  currentView?: string;
  onNavigate?: (view: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  currentView = 'Cockpit', 
  onNavigate 
}) => {
  const { isCollapsed, toggleCollapse, isMobileOpen, closeMobile } = useSidebar();
  // We use prop-based navigation now, but fallback to local state if not provided (for storybook/isolation)
  const [localTab, setLocalTab] = useState('Cockpit');
  
  const activeTab = onNavigate ? currentView : localTab;
  const handleNav = (label: string) => {
    if (onNavigate) {
      onNavigate(label);
    } else {
      setLocalTab(label);
    }
    if (window.innerWidth < 768) {
      closeMobile();
    }
  };

  // UPDATED: Added 'Alerts' to main navigation
  const navItems = [
    { icon: LayoutDashboard, label: 'Cockpit' },
    { icon: Cpu, label: 'System' },
    { icon: Bot, label: 'Agents' },
    { icon: Wallet, label: 'Portfolio' },
    { icon: LineChart, label: 'Markets' },
    { icon: ShieldCheck, label: 'Risk' },
    { icon: Bell, label: 'Alerts' },
    { icon: History, label: 'Trade History' },
  ];

  const SidebarContent = ({ isMobile = false }: { isMobile?: boolean }) => {
    // Force expanded on mobile so the drawer always looks correct, 
    // regardless of the desktop collapsed state preference.
    const collapsed = isMobile ? false : isCollapsed;

    return (
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className={cn("flex items-center h-20 px-6 transition-all duration-300", collapsed ? "justify-center px-0" : "justify-between")}>
          <div className={cn("flex items-center gap-3 overflow-hidden", collapsed ? "w-10 justify-center" : "w-auto")}>
              {/* BRAND LOGO */}
              <Logo 
                showText={!collapsed} 
                iconClassName="w-8 h-8"
                textClassName="text-lg"
              />
          </div>
          
          {/* Mobile Close Button */}
          <button className="md:hidden p-1" onClick={closeMobile}>
              <X className="w-5 h-5 text-obsidian-400 dark:text-paper-100" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-6 space-y-2">
          {navItems.map((item) => {
            const isActive = activeTab === item.label;
            
            const ButtonContent = (
              <button
                onClick={() => handleNav(item.label)}
                className={cn(
                  "relative w-full flex items-center rounded-xl transition-all duration-300 group outline-none focus-visible:ring-2 focus-visible:ring-turquoise-mist/50",
                  collapsed ? "justify-center h-12 w-12 mx-auto" : "space-x-3 px-4 py-3"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeNavIndicator"
                    className="absolute inset-0 bg-deep-teal-800/5 dark:bg-white/10 rounded-xl"
                    initial={false}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                
                <item.icon 
                  className={cn(
                    "relative z-10 w-5 h-5 transition-colors duration-300", 
                    isActive 
                      ? "text-deep-teal-800 dark:text-turquoise-mist" 
                      : "text-obsidian-400/60 dark:text-paper-100/60 group-hover:text-deep-teal-800 dark:group-hover:text-paper-100"
                  )} 
                  strokeWidth={isActive ? 2 : 1.5} 
                />
                
                {!collapsed && (
                  <span className={cn(
                    "relative z-10 font-sans font-medium tracking-wide text-sm transition-colors duration-300 whitespace-nowrap",
                    isActive 
                      ? "text-deep-teal-800 dark:text-turquoise-mist" 
                      : "text-obsidian-400/60 dark:text-paper-100/60 group-hover:text-deep-teal-800 dark:group-hover:text-paper-100"
                  )}>
                    {item.label}
                  </span>
                )}
              </button>
            );

            if (collapsed) {
                return (
                    <Tooltip 
                      key={item.label} 
                      content={item.label} 
                      side="right" 
                      triggerClassName="w-full flex justify-center"
                    >
                        {ButtonContent}
                    </Tooltip>
                )
            }

            return <React.Fragment key={item.label}>{ButtonContent}</React.Fragment>;
          })}
        </nav>

        {/* Footer */}
        <div className="p-3 space-y-4">
          <div className="h-px w-full bg-deep-teal-800/5 dark:bg-white/5" />

          {/* Controls & Profile */}
          <div className={cn("flex flex-col gap-4", collapsed ? "items-center" : "px-2")}>
              
              {/* Collapse Toggle & Theme */}
              <div className={cn("flex items-center w-full", collapsed ? "flex-col gap-4" : "justify-between")}>
                  {/* Theme Toggle - Visible on both Mobile and Desktop */}
                  <div>
                    <ThemeToggle />
                  </div>
                  
                  {/* Desktop Collapse Button */}
                  <button
                      onClick={toggleCollapse}
                      className="hidden md:flex p-2 rounded-lg text-obsidian-400/40 dark:text-paper-100/40 hover:text-deep-teal-800 dark:hover:text-paper-100 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors"
                  >
                      {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
                  </button>
              </div>

              {/* User Profile */}
              <div className={cn(
                  "flex items-center gap-3 p-2 rounded-xl transition-colors hover:bg-deep-teal-800/5 dark:hover:bg-white/5 cursor-pointer",
                  collapsed && "justify-center p-0 hover:bg-transparent"
              )}>
                  <Avatar 
                      src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80" 
                      name="Director" 
                      size={collapsed ? "sm" : "md"} 
                      status="online"
                  />
                  
                  {!collapsed && (
                      <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-deep-teal-800 dark:text-paper-100 truncate">
                              Alexander V.
                          </p>
                          <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 truncate">
                              Director of Alpha
                          </p>
                      </div>
                  )}
                  
                  {!collapsed && (
                      <LogOut className="w-4 h-4 text-obsidian-400/40 hover:text-loss transition-colors" />
                  )}
              </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <>
      {/* --- Mobile Drawer (Slide-in) --- */}
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
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 z-50 w-72 bg-paper-100 dark:bg-obsidian-400 border-r border-deep-teal-800/10 dark:border-white/10 md:hidden"
            >
                <SidebarContent isMobile={true} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* --- Desktop Sidebar (Sticky/Animated) --- */}
      <motion.aside
        initial={false}
        animate={{ width: isCollapsed ? 80 : 280 }} // 5rem vs 17.5rem
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="hidden md:block h-screen sticky top-0 left-0 z-30 flex-shrink-0 border-r border-deep-teal-800/5 dark:border-white/5 bg-paper-100/80 dark:bg-obsidian-400/80 backdrop-blur-xl"
      >
        <SidebarContent />
      </motion.aside>
    </>
  );
};
