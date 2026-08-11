/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'turquoise': {
          DEFAULT: 'rgb(var(--accent-primary) / <alpha-value>)',
          mist: 'rgb(var(--accent-primary) / <alpha-value>)',
          bright: 'rgb(var(--accent-highlight) / <alpha-value>)',
          dim: 'rgb(var(--accent-dim) / <alpha-value>)',
          glow: 'rgba(var(--accent-primary), 0.4)',
        },
        'deep-teal': {
          DEFAULT: 'rgb(var(--accent-secondary) / <alpha-value>)',
          800: 'rgb(var(--accent-secondary) / <alpha-value>)',
          900: 'rgb(var(--accent-dark) / <alpha-value>)',
          50: '#E8F4F4', 100: '#C5E0E0', 200: '#9ECBCB', 300: '#77B5B5',
          400: '#509F9F', 500: '#2A9D8F', 600: '#1F7A6D', 700: '#15574C',
          950: '#051415',
        },
        'obsidian': {
          DEFAULT: 'rgb(var(--bg-dark) / <alpha-value>)',
          200: 'rgb(var(--bg-border) / <alpha-value>)',
          300: 'rgb(var(--bg-card-dark) / <alpha-value>)',
          400: 'rgb(var(--bg-dark) / <alpha-value>)',
        },
        'paper': {
          DEFAULT: 'rgb(var(--bg-light) / <alpha-value>)',
          100: 'rgb(var(--bg-light) / <alpha-value>)',
          50: '#FDFCFB', 200: '#F0EBE6', 300: '#E5DDD5', 400: '#D9CFC4', 500: '#C9BAA8',
        },
        'gain': '#2ECC71',
        'loss': '#E74C3C',
        'warning': '#F39C12',
        'info': '#3498DB',
      },
      fontFamily: {
        'display': ['Cinzel', 'Playfair Display', 'serif'],
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        'slide-up': 'slideUp 0.5s ease-out forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      }
    }
  },
  plugins: [],
}
