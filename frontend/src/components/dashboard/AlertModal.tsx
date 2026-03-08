import React, { useState, useEffect } from 'react';
import {
  Bell, Mail, Smartphone, ArrowUpRight, ArrowDownRight,
  BarChart2, Zap, Trash2, Check,
  TrendingUp, TrendingDown,
} from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { cn, formatCurrency } from '@/lib/utils';

// --- Types ---

export type AlertCondition = 'price_above' | 'price_below' | 'pct_up' | 'pct_down' | 'volume' | 'custom';
export type AlertFrequency = 'once' | 'recurring';

export interface AlertConfig {
  id?: string;
  symbol: string;
  condition: AlertCondition;
  value: number;
  frequency: AlertFrequency;
  channels: {
    app: boolean;
    email: boolean;
    sms: boolean;
  };
  note: string;
}

export interface AlertModalProps {
  isOpen: boolean;
  onClose: () => void;
  symbol?: string;
  existingAlert?: AlertConfig;
  currentPrice?: number;
}

// Deterministic mock price derived from symbol char codes
const getMockPrice = (sym: string): number => {
  if (!sym) return 0;
  return sym.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) + sym.length * 10;
};

// --- Visualizer sub-component ---

interface VisualizerProps {
  currentPrice: number;
  targetValue: number;
  condition: AlertCondition;
}

const AlertVisualizer: React.FC<VisualizerProps> = ({ currentPrice, targetValue, condition }) => {
  if (!currentPrice || !targetValue || condition === 'volume') return null;

  const min = Math.min(currentPrice, targetValue) * 0.95;
  const max = Math.max(currentPrice, targetValue) * 1.05;
  const range = max - min || 1;

  const currentPos = ((currentPrice - min) / range) * 100;
  const targetPos = ((targetValue - min) / range) * 100;
  const isTargetAbove = targetValue > currentPrice;

  return (
    <div className="relative h-16 w-full bg-deep-teal-800/5 dark:bg-white/5 rounded-xl border border-deep-teal-800/10 dark:border-white/5 mt-4 overflow-hidden">
      <div className="absolute top-1/2 left-4 right-4 h-0.5 bg-obsidian-400/10 dark:bg-white/10 -translate-y-1/2" />

      <div
        className={cn('absolute top-1/2 h-0.5 -translate-y-1/2 opacity-50', isTargetAbove ? 'bg-gain' : 'bg-loss')}
        style={{
          left: `${Math.min(currentPos, targetPos)}%`,
          width: `${Math.abs(targetPos - currentPos)}%`,
        }}
      />

      <div
        className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-1 z-10 transition-all duration-500"
        style={{ left: `${currentPos}%` }}
      >
        <div className="w-1 h-3 bg-obsidian-400/40 dark:bg-paper-100/40 rounded-full" />
        <span className="text-[10px] font-mono text-obsidian-400/60 dark:text-paper-100/60 whitespace-nowrap">
          Current: {formatCurrency(currentPrice)}
        </span>
      </div>

      <div
        className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-1 z-20 transition-all duration-500"
        style={{ left: `${targetPos}%` }}
      >
        <div className={cn(
          'w-3 h-3 rounded-full border-2 border-paper-100 dark:border-obsidian-300 shadow-sm',
          isTargetAbove ? 'bg-gain' : 'bg-loss'
        )} />
        <span className={cn('text-[10px] font-mono font-bold whitespace-nowrap', isTargetAbove ? 'text-gain' : 'text-loss')}>
          Target: {formatCurrency(targetValue)}
        </span>
      </div>
    </div>
  );
};

// --- Main Component ---

export const AlertModal: React.FC<AlertModalProps> = ({
  isOpen,
  onClose,
  symbol = '',
  existingAlert,
  currentPrice: propPrice,
}) => {
  const [config, setConfig] = useState<AlertConfig>({
    symbol,
    condition: 'price_above',
    value: 0,
    frequency: 'once',
    channels: { app: true, email: true, sms: false },
    note: '',
  });
  const [currentPrice, setCurrentPrice] = useState(propPrice ?? 0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      if (existingAlert) {
        setConfig(existingAlert);
        setCurrentPrice(propPrice ?? getMockPrice(existingAlert.symbol));
      } else {
        const price = propPrice ?? getMockPrice(symbol);
        setCurrentPrice(price);
        setConfig({
          symbol,
          condition: 'price_above',
          value: price * 1.05,
          frequency: 'once',
          channels: { app: true, email: true, sms: false },
          note: '',
        });
      }
    }
  }, [isOpen, symbol, existingAlert, propPrice]);

  const handleSymbolChange = (val: string) => {
    const upper = val.toUpperCase();
    setConfig(prev => ({ ...prev, symbol: upper }));
    if (upper.length > 2) {
      const newPrice = getMockPrice(upper);
      setCurrentPrice(newPrice);
      if (config.value === 0) {
        setConfig(prev => ({ ...prev, value: newPrice * 1.05 }));
      }
    }
  };

  const handleSave = async () => {
    setIsSubmitting(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSubmitting(false);
    onClose();
  };

  const toggleChannel = (key: keyof AlertConfig['channels']) => {
    setConfig(prev => ({
      ...prev,
      channels: { ...prev.channels, [key]: !prev.channels[key] },
    }));
  };

  const conditionOptions: { id: AlertCondition; label: string; icon: React.ElementType }[] = [
    { id: 'price_above', label: 'Above', icon: ArrowUpRight },
    { id: 'price_below', label: 'Below', icon: ArrowDownRight },
    { id: 'pct_up', label: '% Up', icon: TrendingUp },
    { id: 'pct_down', label: '% Down', icon: TrendingDown },
    { id: 'volume', label: 'Volume', icon: BarChart2 },
    { id: 'custom', label: 'Custom', icon: Zap },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={existingAlert ? 'Edit Alert' : 'Create Alert'}
      description="Configure price triggers and notification preferences."
      size="md"
    >
      <div className="space-y-6">

        {/* Symbol + Current Price */}
        <div className="flex gap-4 items-start">
          <div className="flex-1">
            <Input
              label="Asset Symbol"
              placeholder="e.g. AAPL"
              value={config.symbol}
              onChange={(e) => handleSymbolChange(e.target.value)}
              className="uppercase font-bold tracking-wide"
            />
          </div>
          <div className="flex flex-col items-end pt-6">
            <span className="text-xs text-obsidian-400/50 dark:text-paper-100/50 uppercase tracking-widest font-mono">
              Current Price
            </span>
            <span className="text-xl font-mono font-medium text-obsidian-400 dark:text-paper-100">
              {currentPrice ? formatCurrency(currentPrice) : '---'}
            </span>
          </div>
        </div>

        {/* Condition Type */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-obsidian-400/70 dark:text-paper-100/70 ml-1">Condition</label>
          <div className="grid grid-cols-3 gap-2">
            {conditionOptions.map((opt) => {
              const Icon = opt.icon;
              return (
                <button
                  key={opt.id}
                  onClick={() => setConfig(prev => ({ ...prev, condition: opt.id }))}
                  className={cn(
                    'flex flex-col items-center justify-center gap-1 py-3 rounded-xl border transition-all duration-200',
                    config.condition === opt.id
                      ? 'bg-deep-teal-800/10 dark:bg-white/10 border-deep-teal-800 dark:border-turquoise-mist text-deep-teal-800 dark:text-turquoise-mist'
                      : 'bg-paper-50 dark:bg-white/5 border-transparent hover:bg-deep-teal-800/5 dark:hover:bg-white/5 text-obsidian-400/60 dark:text-paper-100/60'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span className="text-[10px] font-medium uppercase tracking-wide">{opt.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Trigger Value + Visualizer */}
        <div className="space-y-2">
          <Input
            label={
              config.condition.includes('pct')
                ? 'Percentage Change'
                : config.condition === 'volume'
                  ? 'Volume Threshold'
                  : 'Price Target'
            }
            type="number"
            value={config.value}
            onChange={(e) => setConfig(prev => ({ ...prev, value: parseFloat(e.target.value) }))}
            className="font-mono text-lg"
          />
          <AlertVisualizer currentPrice={currentPrice} targetValue={config.value} condition={config.condition} />
        </div>

        {/* Frequency + Channels */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-xs font-medium text-obsidian-400/70 dark:text-paper-100/70 ml-1">Frequency</label>
            <div className="flex bg-paper-50 dark:bg-white/5 p-1 rounded-xl border border-deep-teal-800/5 dark:border-white/5">
              {(['once', 'recurring'] as AlertFrequency[]).map(freq => (
                <button
                  key={freq}
                  onClick={() => setConfig(prev => ({ ...prev, frequency: freq }))}
                  className={cn(
                    'flex-1 py-2 text-xs font-medium rounded-lg transition-colors capitalize',
                    config.frequency === freq
                      ? 'bg-white dark:bg-obsidian-300 shadow-sm text-deep-teal-800 dark:text-paper-100'
                      : 'text-obsidian-400/60 dark:text-paper-100/60 hover:text-obsidian-400 dark:hover:text-paper-100'
                  )}
                >
                  {freq}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-obsidian-400/70 dark:text-paper-100/70 ml-1">Notify via</label>
            <div className="flex gap-2">
              {([
                { key: 'app', icon: Bell },
                { key: 'email', icon: Mail },
                { key: 'sms', icon: Smartphone },
              ] as { key: keyof AlertConfig['channels']; icon: React.ElementType }[]).map(({ key, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => toggleChannel(key)}
                  className={cn(
                    'flex-1 h-10 flex items-center justify-center rounded-xl border transition-colors',
                    config.channels[key]
                      ? 'bg-turquoise-mist/10 border-turquoise-mist text-deep-teal-800 dark:text-turquoise-mist'
                      : 'bg-paper-50 dark:bg-white/5 border-transparent text-obsidian-400/40 dark:text-paper-100/40'
                  )}
                >
                  <Icon className="w-4 h-4" />
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Note */}
        <Input
          label="Note (Optional)"
          placeholder="e.g. Sell if resistance breaks..."
          value={config.note}
          onChange={(e) => setConfig(prev => ({ ...prev, note: e.target.value }))}
        />

        {/* Footer */}
        <div className="flex items-center justify-between pt-4 border-t border-deep-teal-800/5 dark:border-white/5 mt-2">
          {existingAlert ? (
            <Button variant="ghost" className="text-loss hover:text-loss hover:bg-loss/10 px-3">
              <Trash2 className="w-4 h-4" />
            </Button>
          ) : <div />}

          <div className="flex gap-3">
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
            <Button
              variant="primary"
              onClick={handleSave}
              isLoading={isSubmitting}
              leftIcon={existingAlert ? <Check className="w-4 h-4" /> : <Bell className="w-4 h-4" />}
            >
              {existingAlert ? 'Update Alert' : 'Create Alert'}
            </Button>
          </div>
        </div>

      </div>
    </Modal>
  );
};
