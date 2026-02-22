/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Deep Teal (Primary accent)
        'deep-teal': {
          50: '#f7fdfc',
          100: '#ebf8f7',
          200: '#cceeed',
          300: '#a8dfe4',
          400: '#6fc4d0',
          500: '#45a3ba',
          600: '#348297',
          700: '#2a6577',
          800: '#24515f',
          900: '#1e404a',
        },
        // Obsidian (Dark backgrounds)
        'obsidian': {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d0d0d0',
          400: '#a3a3a3',
          500: '#707070',
          600: '#404040',
          700: '#262626',
          800: '#171717',
          900: '#0a0a0a',
        },
        // Paper (Light backgrounds)
        'paper': {
          50: '#fefdfb',
          100: '#fdfbf8',
          200: '#faf5ef',
          300: '#f5ebe2',
          400: '#e8dace',
          500: '#d9c5ad',
          600: '#c4a88c',
          700: '#a88a6b',
          800: '#8a6f54',
          900: '#6b5642',
        },
        // Turquoise Mist (Accent highlight)
        'turquoise-mist': {
          50: '#f0fdfb',
          100: '#d9f5f0',
          200: '#a8e7e1',
          300: '#6dd5ca',
          400: '#45bfb0',
          500: '#2fa699',
          600: '#2a8a80',
          700: '#246f67',
          800: '#1f5954',
          900: '#19443f',
        },
        // Semantic colors (universal)
        'gain': '#10b981',
        'loss': '#ef4444',
        'neutral': '#f59e0b',
        // Semantic aliases — used throughout components as bg-success, text-warning, etc.
        'success': '#10b981',  // alias for gain
        'warning': '#f59e0b',  // alias for neutral (amber)
        'info': '#3498DB',     // informational blue (from design guide)
      },
      fontFamily: {
        'display': ['Cinzel', 'serif'],
        'serif': ['Cinzel', 'serif'],
        'sans': ['Inter', 'sans-serif'],
        'mono': ['JetBrains Mono', 'monospace'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
      },
      backdropBlur: {
        'xl': '20px',
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
      },
    },
  },
  plugins: [],
}
