import React, { useState } from 'react';
import { Save, RotateCcw, Info } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';
import type { StrategyType } from './StrategyCard';

// Parameter definition for each strategy type
interface ParamDef {
  key: string;
  label: string;
  description: string;
  min: number;
  max: number;
  step: number;
  unit?: string;
}

const strategyParams: Record<string, ParamDef[]> = {
  Simple_MA: [
    { key: 'fast_period', label: 'Fast MA Period', description: 'Lookback for fast moving average', min: 5, max: 50, step: 1, unit: 'bars' },
    { key: 'slow_period', label: 'Slow MA Period', description: 'Lookback for slow moving average', min: 20, max: 200, step: 1, unit: 'bars' },
  ],
  Donchian_BB: [
    { key: 'bb_period', label: 'BB Period', description: 'Bollinger Band lookback window', min: 10, max: 50, step: 1, unit: 'bars' },
    { key: 'bb_std', label: 'BB Std Dev', description: 'Standard deviation multiplier', min: 1, max: 4, step: 0.1 },
    { key: 'donchian_period', label: 'Donchian Period', description: 'Donchian channel lookback', min: 5, max: 50, step: 1, unit: 'bars' },
  ],
  Scalper_RSI: [
    { key: 'rsi_period', label: 'RSI Period', description: 'RSI calculation window', min: 7, max: 21, step: 1, unit: 'bars' },
    { key: 'rsi_overbought', label: 'Overbought Level', description: 'RSI threshold to go short', min: 60, max: 90, step: 1 },
    { key: 'rsi_oversold', label: 'Oversold Level', description: 'RSI threshold to go long', min: 10, max: 40, step: 1 },
  ],
  Conservative_EMA: [
    { key: 'ema_fast', label: 'Fast EMA', description: 'Fast EMA period', min: 8, max: 30, step: 1, unit: 'bars' },
    { key: 'ema_slow', label: 'Slow EMA', description: 'Slow EMA period', min: 20, max: 100, step: 1, unit: 'bars' },
    { key: 'atr_multiplier', label: 'ATR Multiplier', description: 'Stop loss ATR distance', min: 1, max: 5, step: 0.5 },
  ],
  Momentum_MACD: [
    { key: 'macd_fast', label: 'MACD Fast', description: 'MACD fast EMA period', min: 8, max: 20, step: 1, unit: 'bars' },
    { key: 'macd_slow', label: 'MACD Slow', description: 'MACD slow EMA period', min: 20, max: 40, step: 1, unit: 'bars' },
    { key: 'macd_signal', label: 'Signal Period', description: 'MACD signal line period', min: 5, max: 15, step: 1, unit: 'bars' },
  ],
  BreakoutRetest: [
    { key: 'breakout_period', label: 'Breakout Lookback', description: 'Period for detecting breakout levels', min: 10, max: 60, step: 1, unit: 'bars' },
    { key: 'retest_pct', label: 'Retest Tolerance', description: 'How close price must return to level', min: 0.1, max: 2, step: 0.1, unit: '%' },
    { key: 'volume_factor', label: 'Volume Confirm', description: 'Min volume spike multiplier for breakout', min: 1.2, max: 3, step: 0.1, unit: 'x' },
  ],
};

// Default values for each strategy
const defaultValues: Record<string, Record<string, number>> = {
  Simple_MA: { fast_period: 10, slow_period: 50 },
  Donchian_BB: { bb_period: 20, bb_std: 2, donchian_period: 20 },
  Scalper_RSI: { rsi_period: 14, rsi_overbought: 70, rsi_oversold: 30 },
  Conservative_EMA: { ema_fast: 12, ema_slow: 26, atr_multiplier: 2 },
  Momentum_MACD: { macd_fast: 12, macd_slow: 26, macd_signal: 9 },
  BreakoutRetest: { breakout_period: 20, retest_pct: 0.5, volume_factor: 1.5 },
};

const riskParamDefs: ParamDef[] = [
  { key: 'max_position_pct', label: 'Max Position Size', description: 'Maximum % of capital per trade', min: 1, max: 20, step: 0.5, unit: '%' },
  { key: 'stop_loss_pct', label: 'Stop Loss', description: 'Automatic stop loss distance', min: 0.5, max: 10, step: 0.5, unit: '%' },
  { key: 'take_profit_pct', label: 'Take Profit', description: 'Target profit distance', min: 1, max: 20, step: 0.5, unit: '%' },
];

export interface StrategyConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  strategyId: string;
  strategyName: string;
  strategyType: StrategyType;
  onSave?: (strategyId: string, params: Record<string, number>, risk: Record<string, number>) => void;
}

// Number input with step controls
const ParamInput: React.FC<{
  def: ParamDef;
  value: number;
  onChange: (key: string, value: number) => void;
}> = ({ def, value, onChange }) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseFloat(e.target.value);
    if (!isNaN(v)) onChange(def.key, v);
  };

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="text-xs font-mono font-medium text-obsidian-400/70 dark:text-paper-100/70">
          {def.label}
        </label>
        {def.unit && (
          <span className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40 bg-deep-teal-800/5 dark:bg-white/5 px-1.5 py-0.5 rounded">
            {def.unit}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <input
          type="range"
          min={def.min}
          max={def.max}
          step={def.step}
          value={value}
          onChange={handleChange}
          className="flex-1 h-1.5 rounded-full appearance-none bg-deep-teal-800/10 dark:bg-white/10 accent-[color:var(--accent-primary)]"
        />
        <div className="w-16 shrink-0">
          <Input
            type="number"
            min={def.min}
            max={def.max}
            step={def.step}
            value={value}
            onChange={handleChange}
            className="text-center text-sm font-mono py-1.5"
          />
        </div>
      </div>
      <p className="text-[10px] text-obsidian-400/40 dark:text-paper-100/40 font-sans flex items-start gap-1">
        <Info className="w-3 h-3 mt-0.5 shrink-0" />
        {def.description}
      </p>
    </div>
  );
};

export const StrategyConfigModal: React.FC<StrategyConfigModalProps> = ({
  isOpen,
  onClose,
  strategyId,
  strategyName,
  strategyType: _strategyType,
  onSave,
}) => {
  const params = strategyParams[strategyName] ?? strategyParams['Simple_MA'];
  const defaults = defaultValues[strategyName] ?? defaultValues['Simple_MA'];

  const [paramValues, setParamValues] = useState<Record<string, number>>(defaults);
  const [riskValues, setRiskValues] = useState<Record<string, number>>({
    max_position_pct: 5,
    stop_loss_pct: 2,
    take_profit_pct: 4,
  });
  const [activeTab, setActiveTab] = useState<'params' | 'risk'>('params');
  const [isDirty, setIsDirty] = useState(false);

  const handleParamChange = (key: string, value: number) => {
    setParamValues(prev => ({ ...prev, [key]: value }));
    setIsDirty(true);
  };

  const handleRiskChange = (key: string, value: number) => {
    setRiskValues(prev => ({ ...prev, [key]: value }));
    setIsDirty(true);
  };

  const handleReset = () => {
    setParamValues(defaults);
    setRiskValues({ max_position_pct: 5, stop_loss_pct: 2, take_profit_pct: 4 });
    setIsDirty(false);
  };

  const handleSave = () => {
    onSave?.(strategyId, paramValues, riskValues);
    setIsDirty(false);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Configure: ${strategyName}`}
      description="Adjust strategy parameters and risk settings"
      size="md"
    >
      <div className="space-y-6">
        {/* Tabs */}
        <div className="flex gap-1 p-1 bg-deep-teal-800/5 dark:bg-white/5 rounded-xl">
          {(['params', 'risk'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'flex-1 py-2 px-4 text-xs font-mono font-bold uppercase tracking-widest rounded-lg transition-all duration-200',
                activeTab === tab
                  ? 'bg-deep-teal-800 dark:bg-turquoise-mist text-paper-100 dark:text-obsidian-400 shadow-md'
                  : 'text-obsidian-400/60 dark:text-paper-100/60 hover:text-obsidian-400 dark:hover:text-paper-100'
              )}
            >
              {tab === 'params' ? 'Parameters' : 'Risk Rules'}
            </button>
          ))}
        </div>

        {/* Content */}
        {activeTab === 'params' && (
          <div className="space-y-5">
            {params.map(def => (
              <ParamInput
                key={def.key}
                def={def}
                value={paramValues[def.key] ?? def.min}
                onChange={handleParamChange}
              />
            ))}
          </div>
        )}

        {activeTab === 'risk' && (
          <div className="space-y-5">
            {riskParamDefs.map(def => (
              <ParamInput
                key={def.key}
                def={def}
                value={riskValues[def.key] ?? def.min}
                onChange={handleRiskChange}
              />
            ))}
            {/* Risk ratio indicator */}
            <div className="p-3 rounded-xl bg-deep-teal-800/5 dark:bg-white/5 border border-deep-teal-800/5 dark:border-white/5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-obsidian-400/60 dark:text-paper-100/60 uppercase tracking-widest">
                  Risk / Reward Ratio
                </span>
                <Badge
                  variant={riskValues.take_profit_pct / riskValues.stop_loss_pct >= 2 ? 'success' : 'warning'}
                  size="sm"
                >
                  1 : {(riskValues.take_profit_pct / riskValues.stop_loss_pct).toFixed(1)}
                </Badge>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-deep-teal-800/5 dark:border-white/5">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReset}
            leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
            className="text-obsidian-400/60 dark:text-paper-100/60"
          >
            Reset defaults
          </Button>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={onClose}>Cancel</Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSave}
              disabled={!isDirty}
              leftIcon={<Save className="w-3.5 h-3.5" />}
            >
              Save changes
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
};

export interface StrategyConfigState {
  isOpen: boolean;
  strategyId: string;
  strategyName: string;
  strategyType: StrategyType;
}
