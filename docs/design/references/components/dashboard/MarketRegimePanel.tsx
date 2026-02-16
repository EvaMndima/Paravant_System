import React from 'react';
import { 
  Activity, BarChart2, TrendingUp, Network, Scale, 
  BarChart3
} from 'lucide-react';
import { GlassCard } from '../ui/GlassCard';
import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';

export interface MarketRegimeData {
  type: string;
  confidence: number;
  duration: string;
  indicators: {
    vix: { value: number; label: string; status: string };
    breadth: { value: string; label: string; status: string };
    trend: { value: string; label: string; status: string };
    correlation: { value: number; label: string; status: string };
    putCall: { value: number; label: string; status: string };
  };
  commentary: string;
}

interface MarketRegimePanelProps {
  data: MarketRegimeData;
  className?: string;
}

export const MarketRegimePanel: React.FC<MarketRegimePanelProps> = ({ data, className }) => {
  
  const indicatorConfig: Record<string, { icon: React.ElementType, name: string }> = {
    vix: { icon: Activity, name: 'Volatility (VIX)' },
    breadth: { icon: BarChart2, name: 'Market Breadth' },
    trend: { icon: TrendingUp, name: 'Trend Strength' },
    correlation: { icon: Network, name: 'Correlation' },
    putCall: { icon: Scale, name: 'Put/Call Ratio' }
  };

  return (
    <GlassCard className={cn("h-full flex flex-col relative overflow-hidden", className)} variant="dark">
      {/* Background graphic */}
      <div className="absolute top-0 right-0 p-6 opacity-5 pointer-events-none">
          <BarChart3 className="w-40 h-40" />
      </div>

      <div className="relative z-10 space-y-6">
          {/* Header */}
          <div>
            <h3 className="text-xs font-mono uppercase tracking-widest text-turquoise-mist mb-2">Current Assessment</h3>
            <div className="flex items-center gap-3 mb-1">
                <Badge variant="success" className="text-sm px-3 py-1 bg-gain/20 text-gain border-gain/30">
                  {data.type}
                </Badge>
                <span className="text-xs font-mono opacity-70">{data.confidence}% Conf.</span>
            </div>
            <p className="text-[10px] opacity-50 font-mono">{data.duration}</p>
          </div>

          {/* Indicators Grid */}
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(data.indicators).map(([key, indicator]) => {
                const config = indicatorConfig[key];
                const Icon = config?.icon || Activity;
                const ind = indicator as { value: string | number, label: string, status: string };
                
                return (
                  <div key={key} className="p-2.5 rounded-lg bg-white/5 border border-white/10 flex flex-col gap-1.5">
                      <div className="flex justify-between items-center">
                        <div className="flex items-center gap-1.5 text-[10px] opacity-60 uppercase tracking-wide">
                            <Icon className="w-3 h-3" />
                            <span>{key}</span>
                        </div>
                        <div className={cn("w-1.5 h-1.5 rounded-full shadow-[0_0_5px_currentColor]", ind.status === 'good' ? 'bg-gain text-gain' : ind.status === 'neutral' ? 'bg-warning text-warning' : 'bg-loss text-loss')} />
                      </div>
                      
                      <div>
                        <div className="font-mono font-bold text-sm text-paper-100">{ind.value}</div>
                        <div className="text-[10px] text-turquoise-mist truncate">{ind.label}</div>
                      </div>
                  </div>
                );
            })}
          </div>

          {/* Commentary */}
          <div className="pt-4 border-t border-white/10">
            <h4 className="text-xs font-mono uppercase tracking-widest text-turquoise-mist mb-2">Curator Commentary</h4>
            <div className="relative pl-3 border-l-2 border-white/20">
                <p className="text-xs text-paper-100/80 leading-relaxed italic">
                  "{data.commentary}"
                </p>
            </div>
          </div>
      </div>
    </GlassCard>
  );
};