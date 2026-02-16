
import { useEffect, useState } from 'react';
import { useDashboard } from '../contexts/DashboardContext';

export const useGlobalShortcuts = (onNavigate: (view: string) => void) => {
  const { toggleShortcuts, openEmergencyPanel, closeAlertModal, closePositionDrawer, isShortcutsOpen, closeShortcuts } = useDashboard();
  const [waitingForSecondKey, setWaitingForSecondKey] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input
      const target = e.target as HTMLElement;
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return;

      // 1. Modifier based Shortcuts
      
      // Emergency Panel: Ctrl + Shift + K
      if (e.ctrlKey && e.shiftKey && (e.key === 'K' || e.key === 'k')) {
        e.preventDefault();
        openEmergencyPanel();
        return;
      }

      // Search: Ctrl + K (or Cmd + K)
      if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        const searchInput = document.getElementById('global-search');
        if (searchInput) {
          searchInput.focus();
        }
        return;
      }

      // Help Modal: ?
      if (e.key === '?') {
        e.preventDefault();
        toggleShortcuts();
        return;
      }

      // Close Modals: Esc
      if (e.key === 'Escape') {
        if (isShortcutsOpen) closeShortcuts();
        // Other close actions are often handled by the modals themselves, 
        // but we can enforce global close logic here if needed.
        return;
      }

      // 2. Sequence Shortcuts (G then ...)
      
      if (waitingForSecondKey) {
        // We were waiting for a second key, now we process it
        switch (e.key.toLowerCase()) {
          case 'c':
            onNavigate('Cockpit');
            break;
          case 'a':
            onNavigate('Agents');
            break;
          case 'p':
            onNavigate('Portfolio');
            break;
          case 't':
            onNavigate('Trade History');
            break;
          case 'm':
            onNavigate('Markets');
            break;
          case 'r':
            onNavigate('Risk');
            break;
          case 's':
            onNavigate('Settings');
            break;
        }
        // Reset state regardless of match
        setWaitingForSecondKey(false);
        return;
      }

      // Start Sequence: G
      if (e.key.toLowerCase() === 'g' && !e.ctrlKey && !e.altKey && !e.metaKey) {
        setWaitingForSecondKey(true);
        
        // Timeout to cancel sequence if user is too slow (1.5s)
        setTimeout(() => setWaitingForSecondKey(false), 1500);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [waitingForSecondKey, onNavigate, toggleShortcuts, openEmergencyPanel, isShortcutsOpen, closeShortcuts]);

  return;
};
