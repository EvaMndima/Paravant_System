import { motion } from 'framer-motion'
import { useTheme } from '@/contexts/ThemeContext'
import { useToast } from '@/contexts/ToastContext'
import { cn, formatCurrency, formatPercent, formatNumber } from '@/lib/utils'
import { fadeInUp, staggerContainer, hoverCard, tapButton, scaleIn } from '@/lib/animations'
import type { AppTheme, ThemeMode } from '@/types'

const COLOR_SWATCHES = [
  { label: 'turquoise (accent)', cls: 'bg-turquoise' },
  { label: 'turquoise-bright', cls: 'bg-turquoise-bright' },
  { label: 'turquoise-dim', cls: 'bg-turquoise-dim' },
  { label: 'deep-teal', cls: 'bg-deep-teal-800' },
  { label: 'deep-teal-900', cls: 'bg-deep-teal-900' },
  { label: 'obsidian-400', cls: 'bg-obsidian-400' },
  { label: 'obsidian-300', cls: 'bg-obsidian-300' },
  { label: 'paper-100', cls: 'bg-paper-100' },
  { label: 'paper-200', cls: 'bg-paper-200' },
  { label: 'gain', cls: 'bg-gain' },
  { label: 'loss', cls: 'bg-loss' },
  { label: 'warning', cls: 'bg-warning' },
  { label: 'info', cls: 'bg-info' },
]

const THEMES: { id: AppTheme; label: string }[] = [
  { id: 'ocean', label: 'Ocean' },
  { id: 'sapphire', label: 'Sapphire' },
  { id: 'emerald', label: 'Emerald' },
  { id: 'onyx', label: 'Onyx' },
]

const MODES: { id: ThemeMode; label: string }[] = [
  { id: 'light', label: 'Light' },
  { id: 'dark', label: 'Dark' },
  { id: 'system', label: 'System' },
]

export default function DevPage() {
  const { mode, setMode, appTheme, setAppTheme } = useTheme()
  const { toast } = useToast()

  return (
    <div className="min-h-screen bg-paper-100 dark:bg-obsidian-400 p-8 transition-colors duration-300">
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="max-w-4xl mx-auto space-y-10"
      >

        {/* Header */}
        <motion.div variants={fadeInUp}>
          <p className="text-xs font-mono uppercase tracking-[0.2em] text-turquoise mb-2">
            Design System Validator
          </p>
          <h1
            className="font-display text-5xl text-deep-teal-800 dark:text-paper-100 mb-2"
            style={{ fontVariant: 'small-caps' }}
          >
            Paravant
          </h1>
          <p className="font-sans text-sm text-obsidian-400/60 dark:text-paper-100/60">
            Phase 0 + 1 — Tokens, fonts, dark mode, and animation verification
          </p>
        </motion.div>

        {/* Theme Controls */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6 space-y-4">
          <h2 className="font-sans font-semibold text-xs uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
            Theme Controls
          </h2>
          <div className="flex flex-wrap gap-3">
            <div className="space-y-2">
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 uppercase tracking-wider">Mode</p>
              <div className="flex gap-2">
                {MODES.map(({ id, label }) => (
                  <button
                    key={id}
                    onClick={() => setMode(id)}
                    className={cn(
                      "px-3 py-1.5 rounded-lg text-xs font-sans font-medium transition-all",
                      mode === id
                        ? "bg-turquoise text-white"
                        : "bg-deep-teal-800/10 dark:bg-white/10 text-obsidian-400 dark:text-paper-100 hover:bg-deep-teal-800/20 dark:hover:bg-white/20"
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 uppercase tracking-wider">Palette</p>
              <div className="flex gap-2">
                {THEMES.map(({ id, label }) => (
                  <button
                    key={id}
                    onClick={() => setAppTheme(id)}
                    className={cn(
                      "px-3 py-1.5 rounded-lg text-xs font-sans font-medium transition-all",
                      appTheme === id
                        ? "bg-turquoise text-white"
                        : "bg-deep-teal-800/10 dark:bg-white/10 text-obsidian-400 dark:text-paper-100 hover:bg-deep-teal-800/20 dark:hover:bg-white/20"
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </motion.section>

        {/* Color Swatches */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6 space-y-4">
          <h2 className="font-sans font-semibold text-xs uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
            Color Tokens
          </h2>
          <div className="grid grid-cols-4 sm:grid-cols-6 gap-3">
            {COLOR_SWATCHES.map(({ label, cls }) => (
              <div key={label} className="space-y-1.5">
                <div className={cn("h-10 w-full rounded-lg border border-black/5 dark:border-white/10", cls)} />
                <p className="text-[10px] font-mono text-obsidian-400/60 dark:text-paper-100/60 leading-tight">
                  {label}
                </p>
              </div>
            ))}
          </div>
        </motion.section>

        {/* Typography */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6 space-y-4">
          <h2 className="font-sans font-semibold text-xs uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
            Typography
          </h2>
          <div className="space-y-3">
            <div>
              <p className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40 mb-1">font-display (Cinzel)</p>
              <p className="font-display text-3xl text-deep-teal-800 dark:text-paper-100" style={{ fontVariant: 'small-caps' }}>
                Trading Cockpit
              </p>
            </div>
            <div>
              <p className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40 mb-1">font-sans (Inter)</p>
              <p className="font-sans text-base text-obsidian-400 dark:text-paper-100">
                The quick brown fox jumps over the lazy dog. Position sizing, risk management, alpha generation.
              </p>
            </div>
            <div>
              <p className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40 mb-1">font-mono (JetBrains Mono)</p>
              <p className="font-mono text-base text-obsidian-400 dark:text-paper-100 tabular-nums">
                $994,272.52 &nbsp;+1.24% &nbsp;BTCUSDT
              </p>
            </div>
          </div>
        </motion.section>

        {/* Formatters */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6 space-y-4">
          <h2 className="font-sans font-semibold text-xs uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
            Formatters
          </h2>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'formatCurrency(994272.52)', value: formatCurrency(994272.52) },
              { label: 'formatPercent(1.24)', value: formatPercent(1.24) },
              { label: 'formatNumber(1234567.89)', value: formatNumber(1234567.89) },
            ].map(({ label, value }) => (
              <div key={label} className="space-y-1">
                <p className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40">{label}</p>
                <p className="font-mono text-xl font-medium tabular-nums text-turquoise">{value}</p>
              </div>
            ))}
          </div>
        </motion.section>

        {/* Glass Panel Verification */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6 space-y-4">
          <h2 className="font-sans font-semibold text-xs uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
            KPI Card (glass-panel)
          </h2>
          <div className="glass-panel rounded-xl p-5 max-w-xs">
            <p className="text-xs font-mono font-bold uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-2">
              Net Liquidity
            </p>
            <p className="font-mono font-medium tracking-tighter tabular-nums text-3xl text-deep-teal-800 dark:text-paper-100">
              {formatCurrency(994272.52)}
            </p>
            <p className="text-sm font-mono text-gain mt-1">+1.24%</p>
          </div>
        </motion.section>

        {/* Animations */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6 space-y-4">
          <h2 className="font-sans font-semibold text-xs uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
            Animations
          </h2>
          <div className="flex flex-wrap gap-4 items-start">
            <motion.div
              variants={scaleIn}
              whileHover={hoverCard}
              className="glass-panel rounded-xl p-4 w-40 cursor-pointer"
            >
              <p className="text-xs font-mono text-obsidian-400/50 dark:text-paper-100/50 mb-1">scaleIn + hoverCard</p>
              <p className="font-sans font-medium text-sm text-obsidian-400 dark:text-paper-100">Hover me</p>
            </motion.div>

            <motion.button
              whileTap={tapButton}
              onClick={() => toast({ title: 'Toast fired!', description: 'Animation system is working.', type: 'success' })}
              className="px-5 py-3 rounded-xl bg-turquoise text-white font-sans font-medium text-sm shadow-lg hover:opacity-90 transition-opacity"
            >
              Fire Toast
            </motion.button>

            <motion.button
              whileTap={tapButton}
              onClick={() => toast({ title: 'Risk Breach', description: 'Max drawdown limit reached.', type: 'error', duration: 8000 })}
              className="px-5 py-3 rounded-xl bg-loss text-white font-sans font-medium text-sm shadow-lg hover:opacity-90 transition-opacity"
            >
              Error Toast
            </motion.button>

            <motion.button
              whileTap={tapButton}
              onClick={() => toast({ title: 'Strategy paused', description: 'Daily loss limit hit.', type: 'warning' })}
              className="px-5 py-3 rounded-xl bg-warning text-white font-sans font-medium text-sm shadow-lg hover:opacity-90 transition-opacity"
            >
              Warning Toast
            </motion.button>
          </div>
        </motion.section>

        {/* Status */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <h2 className="font-sans font-semibold text-xs uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-4">
            Validation Checklist
          </h2>
          <div className="grid grid-cols-2 gap-2 font-mono text-xs">
            {[
              'Cinzel font loaded',
              'Inter font loaded',
              'JetBrains Mono loaded',
              'Dark mode toggle works',
              'Theme palette switches',
              'CSS variables resolve',
              'glass-panel renders',
              'Tailwind v3 classes apply',
              'Framer Motion animates',
              'cn() merges classes',
              'formatCurrency works',
              'Toast system works',
            ].map((item) => (
              <div key={item} className="flex items-center gap-2 text-obsidian-400/70 dark:text-paper-100/70">
                <span className="text-gain">+</span>
                {item}
              </div>
            ))}
          </div>
        </motion.section>

      </motion.div>
    </div>
  )
}
