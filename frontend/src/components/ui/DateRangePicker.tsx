import React, { useState } from 'react';
import { Calendar, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface DateRange {
  from: string; // ISO date string YYYY-MM-DD
  to: string;
}

export type DateRangePreset = '1D' | '7D' | '30D' | '90D' | '1Y' | 'custom';

export interface DateRangePickerProps {
  value?: DateRange;
  onChange?: (range: DateRange, preset: DateRangePreset) => void;
  label?: string;
  className?: string;
  disabled?: boolean;
}

const PRESETS: { key: DateRangePreset; label: string; days?: number }[] = [
  { key: '1D',  label: 'Today',    days: 0 },
  { key: '7D',  label: '7 Days',   days: 7 },
  { key: '30D', label: '30 Days',  days: 30 },
  { key: '90D', label: '90 Days',  days: 90 },
  { key: '1Y',  label: '1 Year',   days: 365 },
  { key: 'custom', label: 'Custom' },
];

function toIso(d: Date): string {
  return d.toISOString().split('T')[0];
}

function addDays(base: Date, days: number): Date {
  const d = new Date(base);
  d.setDate(d.getDate() - days);
  return d;
}

function formatDisplay(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export const DateRangePicker: React.FC<DateRangePickerProps> = ({
  value,
  onChange,
  label,
  className,
  disabled = false,
}) => {
  const today = toIso(new Date());
  const [open, setOpen] = useState(false);
  const [activePreset, setActivePreset] = useState<DateRangePreset>('30D');
  const [customFrom, setCustomFrom] = useState(value?.from ?? toIso(addDays(new Date(), 30)));
  const [customTo, setCustomTo] = useState(value?.to ?? today);

  const current = value ?? { from: customFrom, to: customTo };

  const handlePreset = (preset: typeof PRESETS[number]) => {
    if (preset.key === 'custom') {
      setActivePreset('custom');
      return;
    }
    const to = new Date();
    const from = preset.days === 0 ? new Date() : addDays(to, preset.days!);
    const range: DateRange = { from: toIso(from), to: toIso(to) };
    setActivePreset(preset.key);
    onChange?.(range, preset.key);
    setOpen(false);
  };

  const handleCustomApply = () => {
    onChange?.({ from: customFrom, to: customTo }, 'custom');
    setOpen(false);
  };

  return (
    <div className={cn('relative inline-block', className)}>
      {label && (
        <label className="block text-xs font-mono font-medium text-obsidian-400/70 dark:text-paper-100/70 uppercase tracking-widest mb-1.5">
          {label}
        </label>
      )}

      {/* Trigger */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen(v => !v)}
        className={cn(
          'inline-flex items-center gap-2 h-9 px-3 rounded-xl border text-sm font-sans',
          'bg-deep-teal-800/5 dark:bg-white/5 transition-colors duration-150',
          'focus:outline-none focus:ring-2 focus:ring-turquoise-mist/40',
          open
            ? 'border-turquoise-mist/50 text-obsidian-400 dark:text-paper-100'
            : 'border-deep-teal-800/15 dark:border-white/10 text-obsidian-400/70 dark:text-paper-100/70 hover:border-deep-teal-800/30',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <Calendar className="w-3.5 h-3.5 shrink-0 text-obsidian-400/40 dark:text-paper-100/40" />
        <span className="text-xs font-mono">
          {formatDisplay(current.from)}
          {current.from !== current.to && ` — ${formatDisplay(current.to)}`}
        </span>
        <ChevronDown className={cn('w-3.5 h-3.5 shrink-0 text-obsidian-400/40 dark:text-paper-100/40 transition-transform', open && 'rotate-180')} />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className={cn(
          'absolute z-50 mt-1.5 w-64 rounded-xl border border-deep-teal-800/10 dark:border-white/10',
          'bg-paper-100 dark:bg-obsidian-300 shadow-xl p-3 space-y-3'
        )}>
          {/* Preset chips */}
          <div className="grid grid-cols-3 gap-1.5">
            {PRESETS.map(p => (
              <button
                key={p.key}
                type="button"
                onClick={() => handlePreset(p)}
                className={cn(
                  'py-1.5 rounded-lg text-xs font-mono font-medium transition-colors duration-150',
                  activePreset === p.key
                    ? 'bg-turquoise-mist text-white'
                    : 'bg-deep-teal-800/5 dark:bg-white/5 text-obsidian-400/70 dark:text-paper-100/70 hover:bg-deep-teal-800/10 dark:hover:bg-white/10'
                )}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Custom date inputs */}
          {activePreset === 'custom' && (
            <div className="space-y-2 pt-1 border-t border-deep-teal-800/5 dark:border-white/5">
              <div className="space-y-1">
                <label className="text-[10px] font-mono text-obsidian-400/50 dark:text-paper-100/50 uppercase tracking-widest">From</label>
                <input
                  type="date"
                  value={customFrom}
                  max={customTo}
                  onChange={e => setCustomFrom(e.target.value)}
                  className={cn(
                    'w-full h-8 px-2.5 rounded-lg border text-xs font-mono',
                    'border-deep-teal-800/15 dark:border-white/10',
                    'bg-deep-teal-800/5 dark:bg-white/5',
                    'text-obsidian-400 dark:text-paper-100',
                    'focus:outline-none focus:ring-2 focus:ring-turquoise-mist/40'
                  )}
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-mono text-obsidian-400/50 dark:text-paper-100/50 uppercase tracking-widest">To</label>
                <input
                  type="date"
                  value={customTo}
                  min={customFrom}
                  max={today}
                  onChange={e => setCustomTo(e.target.value)}
                  className={cn(
                    'w-full h-8 px-2.5 rounded-lg border text-xs font-mono',
                    'border-deep-teal-800/15 dark:border-white/10',
                    'bg-deep-teal-800/5 dark:bg-white/5',
                    'text-obsidian-400 dark:text-paper-100',
                    'focus:outline-none focus:ring-2 focus:ring-turquoise-mist/40'
                  )}
                />
              </div>
              <button
                type="button"
                onClick={handleCustomApply}
                className="w-full h-8 rounded-lg bg-turquoise-mist text-white text-xs font-mono font-bold uppercase tracking-widest hover:bg-turquoise-mist/90 transition-colors"
              >
                Apply
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
