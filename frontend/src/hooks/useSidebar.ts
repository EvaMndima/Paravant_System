/**
 * useSidebar hook — in its own file so that Sidebar.tsx (which exports only
 * components) satisfies React Fast Refresh's requirement that a file export
 * only one type of thing (components OR hooks/utilities, not both).
 */
import { useContext } from 'react';
import { SidebarContext } from '@/contexts/SidebarContext';
import type { SidebarContextType } from '@/contexts/SidebarContext';

export type { SidebarContextType };

export function useSidebar(): SidebarContextType {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
}
