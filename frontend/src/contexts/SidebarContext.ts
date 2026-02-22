/**
 * Shared SidebarContext — extracted to a dedicated file so that:
 * - Sidebar.tsx can import it for the Provider implementation
 * - useSidebar.ts can import it for the hook
 * - Neither file mixes component and hook exports (fixes React Fast Refresh warning)
 */
import { createContext } from 'react';

export interface SidebarContextType {
  isCollapsed: boolean;
  toggleCollapse: () => void;
  isMobileOpen: boolean;
  toggleMobile: () => void;
  closeMobile: () => void;
}

export const SidebarContext = createContext<SidebarContextType | undefined>(undefined);
