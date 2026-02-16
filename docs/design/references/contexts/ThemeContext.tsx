
import React, { createContext, useContext, useEffect, useState } from 'react';
import { MotionGlobalConfig } from 'framer-motion';
import { ThemeMode, AppTheme, ThemeContextType } from '../types';

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Theme Mode (Light/Dark)
  const [mode, setMode] = useState<ThemeMode>(() => 
    (localStorage.getItem('themeMode') as ThemeMode) || 'system'
  );
  
  // App Theme (Color Palette)
  const [appTheme, setAppTheme] = useState<AppTheme>(() => 
    (localStorage.getItem('appTheme') as AppTheme) || 'ocean'
  );

  // Compact Mode State
  const [compactMode, setCompactMode] = useState<boolean>(() => 
    localStorage.getItem('compactMode') === 'true'
  );

  // Reduced Motion State
  const [reducedMotion, setReducedMotion] = useState<boolean>(() => 
    localStorage.getItem('reducedMotion') === 'true'
  );

  // Apply Theme Mode (Light/Dark)
  useEffect(() => {
    const root = window.document.documentElement;
    const applyMode = () => {
      const isDark = 
        mode === 'dark' || 
        (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
      
      root.classList.remove('light', 'dark');
      root.classList.add(isDark ? 'dark' : 'light');
    };

    applyMode();
    localStorage.setItem('themeMode', mode);

    if (mode === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => applyMode();
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [mode]);

  // Apply App Theme (Color Palette) via Data Attribute
  useEffect(() => {
    const root = window.document.documentElement;
    root.setAttribute('data-theme', appTheme);
    localStorage.setItem('appTheme', appTheme);
  }, [appTheme]);

  // Apply Compact Mode
  useEffect(() => {
    if (compactMode) {
      document.body.classList.add('compact');
    } else {
      document.body.classList.remove('compact');
    }
    localStorage.setItem('compactMode', String(compactMode));
  }, [compactMode]);

  // Apply Reduced Motion
  useEffect(() => {
    MotionGlobalConfig.skipAnimations = reducedMotion;
    localStorage.setItem('reducedMotion', String(reducedMotion));
  }, [reducedMotion]);

  return (
    <ThemeContext.Provider value={{ 
      mode, setMode,
      appTheme, setAppTheme,
      compactMode, setCompactMode,
      reducedMotion, setReducedMotion
    }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
