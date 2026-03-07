# Phase 0: Clean Slate — Project Setup

## Goal
Delete the broken frontend and create a fresh Vite + React + TypeScript project with the EXACT theme system from the AI Studio prototype.

## Pre-requisites
- Node.js 18+
- The AI Studio prototype at `docs/design/references/`

---

## Step 0.1: Delete Old Frontend

```bash
# From project root
rm -rf frontend/
```

## Step 0.2: Create Fresh Vite Project

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
```

## Step 0.3: Install Dependencies

```bash
# Core
npm install react-router-dom@6 lucide-react clsx tailwind-merge framer-motion recharts @tanstack/react-query

# Dev
npm install -D tailwindcss@3 postcss autoprefixer @types/react @types/react-dom
npx tailwindcss init -p
```

**IMPORTANT:** Use Tailwind v3 (not v4). The prototype was built with v3 and all classes are v3 syntax. Using v4 caused issues previously.

## Step 0.4: Configure Tailwind

**File: `frontend/tailwind.config.js`**

Port the EXACT config from `docs/design/references/index.html` lines 19-77:

```javascript
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
```

## Step 0.5: Configure CSS Variables

**File: `frontend/src/index.css`**

Port from `docs/design/references/index.html` lines 82-188:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* OCEAN (Default) */
    --accent-primary: 42 157 143;
    --accent-highlight: 61 185 169;
    --accent-dim: 31 122 109;
    --accent-secondary: 15 61 62;
    --accent-dark: 10 40 41;
    --bg-light: 248 245 242;
    --bg-dark: 16 20 19;
    --bg-card-dark: 22 25 24;
  }

  /* SAPPHIRE */
  [data-theme="sapphire"] {
    --accent-primary: 59 130 246;
    --accent-secondary: 23 37 84;
  }
  html.dark[data-theme="sapphire"] {
    --accent-primary: 96 165 250;
    --bg-dark: 2 6 23;
    --bg-card-dark: 15 23 42;
  }

  /* EMERALD */
  [data-theme="emerald"] {
    --accent-primary: 16 185 129;
    --accent-secondary: 6 78 59;
  }
  html.dark[data-theme="emerald"] {
    --accent-primary: 52 211 153;
    --bg-dark: 2 44 34;
    --bg-card-dark: 6 78 59;
  }

  /* ONYX */
  [data-theme="onyx"] {
    --accent-primary: 212 175 55;
    --accent-secondary: 24 24 27;
  }
  html.dark[data-theme="onyx"] {
    --accent-primary: 252 211 77;
    --bg-dark: 0 0 0;
    --bg-card-dark: 10 10 10;
    --accent-secondary: 39 39 42;
  }

  body {
    @apply bg-paper-100 text-obsidian-400 antialiased font-sans transition-colors duration-300;
  }
  html.dark body {
    @apply bg-obsidian-400 text-paper-100;
  }

  /* Compact Mode */
  body.compact {
    font-size: 0.95em;
  }

  /* Custom Scrollbar */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  ::-webkit-scrollbar-track {
    @apply bg-transparent;
  }
  ::-webkit-scrollbar-thumb {
    @apply bg-deep-teal-800/20 rounded-full;
  }
  html.dark ::-webkit-scrollbar-thumb {
    @apply bg-white/10;
  }
}

@layer utilities {
  .glass-panel {
    @apply bg-paper-100/80 dark:bg-obsidian-300/60 backdrop-blur-xl border border-deep-teal-800/10 dark:border-white/10 shadow-lg dark:shadow-2xl;
  }
}
```

## Step 0.6: Configure Fonts

**File: `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>PARAVANT | AI Trading Cockpit</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600;700&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

## Step 0.7: Configure Path Aliases

**File: `frontend/tsconfig.json`** (add paths):
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

**File: `frontend/vite.config.ts`**:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

## Step 0.8: Verify Setup

Create a minimal test:

**File: `frontend/src/App.tsx`**:
```tsx
function App() {
  return (
    <div className="min-h-screen bg-paper-100 dark:bg-obsidian-400 p-8 transition-colors">
      <button
        onClick={() => document.documentElement.classList.toggle('dark')}
        className="mb-8 px-4 py-2 rounded-xl bg-deep-teal-800/10 dark:bg-white/10 text-deep-teal-800 dark:text-turquoise-mist font-sans"
      >
        Toggle Dark Mode
      </button>

      <h1 className="font-display text-4xl text-deep-teal-800 dark:text-paper-100 mb-4" style={{ fontVariant: 'small-caps' }}>
        System Status
      </h1>

      <p className="font-sans text-obsidian-400/60 dark:text-paper-100/60 mb-8">
        Design system verification page
      </p>

      <div className="glass-panel rounded-2xl p-6 max-w-sm">
        <p className="text-xs font-mono font-bold uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-2">
          Net Liquidity
        </p>
        <p className="font-mono font-medium tracking-tighter tabular-nums text-3xl text-deep-teal-800 dark:text-paper-100">
          $994,272.52
        </p>
        <p className="text-sm font-mono text-gain mt-1">+1.24%</p>
      </div>
    </div>
  )
}
export default App
```

## Validation Checklist

- [ ] `npm run dev` starts on port 3000
- [ ] Page shows cream/paper background in light mode
- [ ] Page shows near-black background in dark mode
- [ ] Toggle button switches modes
- [ ] "System Status" renders in Cinzel font, small-caps
- [ ] "$994,272.52" renders in JetBrains Mono, tabular-nums
- [ ] Body text renders in Inter
- [ ] Glass panel has blur effect and subtle border
- [ ] "+1.24%" renders in green (#2ECC71)
- [ ] Custom scrollbar visible (thin, themed)
- [ ] No Tailwind errors in console
