import React, { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import { cn, formatNumber } from '@/lib/utils';

export interface MarketItem {
  symbol: string;
  value: number;
  change: number;
  changePercent: number;
}

export interface MarketTickerProps {
  items: MarketItem[];
  speed?: 'slow' | 'normal' | 'fast';
  pauseOnHover?: boolean;
  className?: string;
}

// Sub-component to handle individual flash logic per item
const TickerItem: React.FC<{ item: MarketItem }> = ({ item }) => {
  const prevValue = useRef(item.value);
  const [flash, setFlash] = useState<'green' | 'red' | null>(null);

  useEffect(() => {
    if (item.value > prevValue.current) {
      setFlash('green');
    } else if (item.value < prevValue.current) {
      setFlash('red');
    }
    prevValue.current = item.value;

    const timer = setTimeout(() => setFlash(null), 1000);
    return () => clearTimeout(timer);
  }, [item.value]);

  const isPositive = item.change >= 0;
  const Icon = item.change === 0 ? Minus : (isPositive ? ArrowUpRight : ArrowDownRight);

  return (
    <div className="inline-flex items-center gap-3 px-6 py-2 border-r border-deep-teal-800/5 dark:border-white/5 last:border-0">
      <span className="font-sans font-bold text-xs text-obsidian-400/70 dark:text-paper-100/70 tracking-wide">
        {item.symbol}
      </span>
      <div className="flex items-center gap-2">
        <span
          className={cn(
            'font-mono text-sm font-medium transition-colors duration-300',
            flash === 'green' ? 'text-gain' : flash === 'red' ? 'text-loss' : 'text-obsidian-400 dark:text-paper-100'
          )}
        >
          {formatNumber(item.value)}
        </span>
        <span className={cn(
          'flex items-center gap-0.5 text-[10px] font-mono',
          isPositive ? 'text-gain' : 'text-loss'
        )}>
          <Icon className="w-2.5 h-2.5" />
          <span>{Math.abs(item.changePercent).toFixed(2)}%</span>
        </span>
      </div>
    </div>
  );
};

export const MarketTicker: React.FC<MarketTickerProps> = ({
  items,
  speed = 'normal',
  pauseOnHover = true,
  className,
}) => {
  const durationClass = {
    slow: 'duration-[60s]',
    normal: 'duration-[40s]',
    fast: 'duration-[20s]',
  }[speed];

  return (
    <div
      className={cn(
        'relative w-full overflow-hidden bg-paper-100/50 dark:bg-obsidian-400/50 backdrop-blur-sm border-y border-deep-teal-800/5 dark:border-white/5',
        className
      )}
    >
      {/* Fade-out edges */}
      <div className="absolute left-0 top-0 bottom-0 w-16 bg-gradient-to-r from-paper-100 dark:from-obsidian-400 to-transparent z-10 pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-paper-100 dark:from-obsidian-400 to-transparent z-10 pointer-events-none" />

      <div
        className={cn(
          'flex whitespace-nowrap',
          pauseOnHover && 'hover:pause-animation'
        )}
      >
        {/* Two copies of the ticker for seamless looping */}
        <div className={cn('flex animate-marquee', durationClass)}>
          {items.map((item, i) => (
            <TickerItem key={`a-${item.symbol}-${i}`} item={item} />
          ))}
        </div>
        <div className={cn('flex animate-marquee', durationClass)} aria-hidden="true">
          {items.map((item, i) => (
            <TickerItem key={`b-${item.symbol}-${i}`} item={item} />
          ))}
        </div>
      </div>

      <style>{`
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-100%); }
        }
        .animate-marquee {
          animation: marquee linear infinite;
        }
        .hover\\:pause-animation:hover .animate-marquee {
          animation-play-state: paused;
        }
      `}</style>
    </div>
  );
};
