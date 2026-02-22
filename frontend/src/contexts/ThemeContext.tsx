import React, { createContext, useContext, useEffect, useState } from 'react';
import { MotionGlobalConfig } from 'framer-motion';

// Theme types
export type ThemeMode = 'light' | 'dark' | 'system';
export type AccentTheme = 'ocean' | 'sapphire' | 'emerald' | 'amber' | 'slate';

interface ThemeState {
  mode: ThemeMode;
  accent: AccentTheme;
  compactMode: boolean;
  reducedMotion: boolean;
}

interface ThemeContextType extends ThemeState {
  setMode: (mode: ThemeMode) => void;
  setAccent: (accent: AccentTheme) => void;
  setCompactMode: (enabled: boolean) => void;
  setReducedMotion: (enabled: boolean) => void;
  toggleMode: () => void;
  toggleCompactMode: () => void;
  toggleReducedMotion: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// eslint-disable-next-line react-refresh/only-export-components -- context hook must be co-located with provider
export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Initialize state from localStorage
  const [mode, setModeState] = useState<ThemeMode>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('theme-mode');
      if (saved === 'light' || saved === 'dark' || saved === 'system') {
        return saved;
      }
    }
    return 'system';
  });

  const [accent, setAccentState] = useState<AccentTheme>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('theme-accent');
      if (saved === 'ocean' || saved === 'sapphire' || saved === 'emerald' || saved === 'amber' || saved === 'slate') {
        return saved;
      }
    }
    return 'ocean';
  });

  const [compactMode, setCompactModeState] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('theme-compact');
      return saved === 'true';
    }
    return false;
  });

  const [reducedMotion, setReducedMotionState] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('theme-reduced-motion');
      if (saved !== null) {
        return saved === 'true';
      }
      // Check system preference
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
    return false;
  });

  // Apply mode (light/dark/system) to HTML element
  useEffect(() => {
    const applyMode = (effectiveMode: 'light' | 'dark') => {
      document.documentElement.classList.toggle('dark', effectiveMode === 'dark');
    };

    if (mode === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      applyMode(mediaQuery.matches ? 'dark' : 'light');

      const listener = (e: MediaQueryListEvent) => {
        applyMode(e.matches ? 'dark' : 'light');
      };
      mediaQuery.addEventListener('change', listener);
      return () => mediaQuery.removeEventListener('change', listener);
    } else {
      applyMode(mode);
    }
  }, [mode]);

  // Apply accent theme to HTML element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', accent);
  }, [accent]);

  // Apply compact mode to body element
  useEffect(() => {
    document.body.classList.toggle('compact-mode', compactMode);
  }, [compactMode]);

  // Apply reduced motion preference
  useEffect(() => {
    MotionGlobalConfig.skipAnimations = reducedMotion;
  }, [reducedMotion]);

  // Setters with localStorage persistence
  const setMode = (newMode: ThemeMode) => {
    setModeState(newMode);
    localStorage.setItem('theme-mode', newMode);
  };

  const setAccent = (newAccent: AccentTheme) => {
    setAccentState(newAccent);
    localStorage.setItem('theme-accent', newAccent);
  };

  const setCompactMode = (enabled: boolean) => {
    setCompactModeState(enabled);
    localStorage.setItem('theme-compact', enabled.toString());
  };

  const setReducedMotion = (enabled: boolean) => {
    setReducedMotionState(enabled);
    localStorage.setItem('theme-reduced-motion', enabled.toString());
  };

  // Toggle functions
  const toggleMode = () => {
    const modes: ThemeMode[] = ['light', 'dark', 'system'];
    const currentIndex = modes.indexOf(mode);
    const nextMode = modes[(currentIndex + 1) % modes.length];
    setMode(nextMode);
  };

  const toggleCompactMode = () => {
    setCompactMode(!compactMode);
  };

  const toggleReducedMotion = () => {
    setReducedMotion(!reducedMotion);
  };

  const value: ThemeContextType = {
    mode,
    accent,
    compactMode,
    reducedMotion,
    setMode,
    setAccent,
    setCompactMode,
    setReducedMotion,
    toggleMode,
    toggleCompactMode,
    toggleReducedMotion,
  };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};
