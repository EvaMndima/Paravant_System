import React, { useState } from 'react';
import { Save, Server, Bell, Shield, Zap } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Toggle } from '@/components/ui/Toggle';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

export interface SettingsState {
  binanceApiKey: string;
  binanceApiSecret: string;
  telegramBotToken: string;
  telegramChatId: string;
  tradingMode: 'paper' | 'live';
  defaultSymbol: string;
  maxDailyLossPct: number;
  maxDrawdownPct: number;
  telegramAlerts: boolean;
  tradeAlerts: boolean;
  systemAlerts: boolean;
  riskAlerts: boolean;
}

export interface SettingsFormProps {
  initialValues?: Partial<SettingsState>;
  onSave?: (values: SettingsState) => void;
  className?: string;
}

const DEFAULT: SettingsState = {
  binanceApiKey: '',
  binanceApiSecret: '',
  telegramBotToken: '',
  telegramChatId: '',
  tradingMode: 'paper',
  defaultSymbol: 'BTCUSDT',
  maxDailyLossPct: 5,
  maxDrawdownPct: 15,
  telegramAlerts: true,
  tradeAlerts: true,
  systemAlerts: true,
  riskAlerts: true,
};

const SYMBOL_OPTIONS = [
  { value: 'BTCUSDT', label: 'BTCUSDT' },
  { value: 'ETHUSDT', label: 'ETHUSDT' },
  { value: 'BNBUSDT', label: 'BNBUSDT' },
];

interface SectionProps {
  icon: React.ElementType;
  title: string;
  description: string;
  children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({ icon: Icon, title, description, children }) => (
  <GlassCard variant="subtle" padding="md" className="space-y-4">
    <div className="flex items-start gap-3 pb-3 border-b border-deep-teal-800/5 dark:border-white/5">
      <div className="p-2 rounded-xl bg-turquoise-mist/10 text-turquoise-mist shrink-0">
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <h3 className="text-sm font-sans font-semibold text-obsidian-400 dark:text-paper-100">{title}</h3>
        <p className="text-xs font-sans text-obsidian-400/50 dark:text-paper-100/50 mt-0.5">{description}</p>
      </div>
    </div>
    {children}
  </GlassCard>
);

interface ToggleRowProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}

const ToggleRow: React.FC<ToggleRowProps> = ({ label, description, checked, onChange }) => (
  <div className="flex items-center justify-between gap-4">
    <div className="min-w-0">
      <p className="text-sm font-sans text-obsidian-400 dark:text-paper-100">{label}</p>
      {description && (
        <p className="text-xs font-sans text-obsidian-400/50 dark:text-paper-100/50 mt-0.5">{description}</p>
      )}
    </div>
    <Toggle checked={checked} onCheckedChange={onChange} size="sm" />
  </div>
);

export const SettingsForm: React.FC<SettingsFormProps> = ({
  initialValues,
  onSave,
  className,
}) => {
  const [values, setValues] = useState<SettingsState>({ ...DEFAULT, ...initialValues });
  const [isDirty, setIsDirty] = useState(false);
  const [saved, setSaved] = useState(false);

  const update = <K extends keyof SettingsState>(key: K, val: SettingsState[K]) => {
    setValues(prev => ({ ...prev, [key]: val }));
    setIsDirty(true);
  };

  const handleSave = () => {
    onSave?.(values);
    setIsDirty(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* API Configuration */}
      <Section icon={Server} title="API Configuration" description="Binance Testnet credentials — never commit these to source control">
        <div className="space-y-3">
          <Input
            label="API Key"
            type="password"
            value={values.binanceApiKey}
            onChange={e => update('binanceApiKey', e.target.value)}
            placeholder="Enter Binance API key"
          />
          <Input
            label="API Secret"
            type="password"
            value={values.binanceApiSecret}
            onChange={e => update('binanceApiSecret', e.target.value)}
            placeholder="Enter Binance API secret"
          />
        </div>
      </Section>

      {/* Trading Mode */}
      <Section icon={Zap} title="Trading Mode" description="Paper mode simulates execution with real market data — no real funds at risk">
        <div className="space-y-3">
          <div className="flex gap-2">
            {(['paper', 'live'] as const).map(mode => (
              <button
                key={mode}
                type="button"
                onClick={() => update('tradingMode', mode)}
                className={cn(
                  'flex-1 py-2.5 rounded-xl text-sm font-mono font-bold uppercase tracking-widest border transition-all duration-150',
                  values.tradingMode === mode
                    ? mode === 'live'
                      ? 'border-loss/40 bg-loss/10 text-loss'
                      : 'border-turquoise-mist/40 bg-turquoise-mist/10 text-deep-teal-800 dark:text-turquoise-mist'
                    : 'border-deep-teal-800/10 dark:border-white/10 text-obsidian-400/50 dark:text-paper-100/50 hover:border-deep-teal-800/20'
                )}
              >
                {mode === 'live' && values.tradingMode === 'live' && (
                  <span className="inline-block w-2 h-2 rounded-full bg-loss animate-pulse mr-2" />
                )}
                {mode}
              </button>
            ))}
          </div>
          {values.tradingMode === 'live' && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-loss/10 border border-loss/20">
              <Badge variant="danger" size="sm">Warning</Badge>
              <span className="text-xs font-sans text-loss/80">Live mode executes real orders with real funds.</span>
            </div>
          )}
          <Select
            label="Default Symbol"
            options={SYMBOL_OPTIONS}
            value={values.defaultSymbol}
            onChange={v => update('defaultSymbol', v)}
          />
        </div>
      </Section>

      {/* Risk Limits */}
      <Section icon={Shield} title="Risk Limits" description="System-wide caps — breached limits halt new order placement">
        <div className="space-y-3">
          <Input
            label="Max Daily Loss (%)"
            type="number"
            min={1}
            max={50}
            step={0.5}
            value={values.maxDailyLossPct}
            onChange={e => update('maxDailyLossPct', parseFloat(e.target.value))}
          />
          <Input
            label="Max Drawdown (%)"
            type="number"
            min={1}
            max={50}
            step={1}
            value={values.maxDrawdownPct}
            onChange={e => update('maxDrawdownPct', parseFloat(e.target.value))}
          />
        </div>
      </Section>

      {/* Notifications */}
      <Section icon={Bell} title="Notifications" description="Telegram bot token and alert preferences">
        <div className="space-y-3">
          <Input
            label="Telegram Bot Token"
            type="password"
            value={values.telegramBotToken}
            onChange={e => update('telegramBotToken', e.target.value)}
            placeholder="123456:ABC-DEF..."
          />
          <Input
            label="Chat ID"
            value={values.telegramChatId}
            onChange={e => update('telegramChatId', e.target.value)}
            placeholder="-100123456789"
          />
          <div className="pt-2 space-y-3 border-t border-deep-teal-800/5 dark:border-white/5">
            <ToggleRow label="Trade alerts" description="Notify on every execution" checked={values.tradeAlerts} onChange={v => update('tradeAlerts', v)} />
            <ToggleRow label="Risk alerts" description="Notify on drawdown / limit breaches" checked={values.riskAlerts} onChange={v => update('riskAlerts', v)} />
            <ToggleRow label="System alerts" description="Notify on service status changes" checked={values.systemAlerts} onChange={v => update('systemAlerts', v)} />
            <ToggleRow label="All Telegram alerts" description="Master switch for Telegram channel" checked={values.telegramAlerts} onChange={v => update('telegramAlerts', v)} />
          </div>
        </div>
      </Section>

      {/* Save footer */}
      <div className="flex items-center justify-end gap-3 pt-2">
        {saved && <span className="text-xs font-mono text-gain">Settings saved</span>}
        <Button
          variant="primary"
          size="md"
          onClick={handleSave}
          disabled={!isDirty}
          leftIcon={<Save className="w-4 h-4" />}
        >
          Save Settings
        </Button>
      </div>
    </div>
  );
};
