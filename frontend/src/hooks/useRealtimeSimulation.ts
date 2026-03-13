import { useState, useEffect } from 'react';
import type { MarketItem } from '@/components/dashboard/MarketTicker';
import type { WatchlistItem } from '@/components/dashboard/Watchlist';
import type { ActivityItem } from '@/components/dashboard/ActivityFeed';
import { useToast } from '@/contexts/ToastContext';

// Minimal strategy shape needed for the simulation tick.
// StrategiesPage imports this type from here to stay in sync.
export interface StrategySummary {
  id: string;
  name: string;
  status: 'active' | 'paused' | 'stopped';
  pnlDay: number;
  pnlTotal: number;
  sparkline: number[];
  [key: string]: unknown; // allow extra fields from the page
}

/**
 * Drives simulated real-time data updates across three update tiers:
 *
 *  - 3 s  — market prices and watchlist (high frequency)
 *  - 5 s  — strategy P&L and sparklines (medium frequency)
 *  - 20 s — activity feed events + occasional toast (low frequency)
 *
 * All intervals are cleared on unmount. In Phase 8 (API Integration)
 * this hook is replaced by real-time data from /api/v1/events (SSE)
 * and React-Query polling hooks.
 */
export const useRealtimeSimulation = (
  initialMarketData: MarketItem[],
  initialWatchlist: WatchlistItem[],
  initialStrategies: StrategySummary[],
  initialActivity: ActivityItem[],
) => {
  const { toast } = useToast();

  const [marketData,  setMarketData]  = useState<MarketItem[]>(initialMarketData);
  const [watchlist,   setWatchlist]   = useState<WatchlistItem[]>(initialWatchlist);
  const [strategies,  setStrategies]  = useState<StrategySummary[]>(initialStrategies);
  const [activity,    setActivity]    = useState<ActivityItem[]>(initialActivity);
  const [lastSync,    setLastSync]    = useState(0);

  // Sync counter — counts seconds since last price update
  useEffect(() => {
    const t = setInterval(() => setLastSync(s => (s > 30 ? 0 : s + 1)), 1000);
    return () => clearInterval(t);
  }, []);

  // Tier 1 — market prices + watchlist (every 3 s)
  useEffect(() => {
    const t = setInterval(() => {
      setMarketData(prev =>
        prev.map(item => {
          const delta      = (Math.random() - 0.5) * item.value * 0.002;
          const newValue   = item.value + delta;
          const newChange  = item.change + delta;
          const base       = item.value - item.change;
          return {
            ...item,
            value:         newValue,
            change:        newChange,
            changePercent: base !== 0 ? (newChange / base) * 100 : 0,
          };
        }),
      );

      setWatchlist(prev =>
        prev.map(item => {
          const delta      = (Math.random() - 0.5) * item.price * 0.003;
          const newPrice   = item.price + delta;
          const newChange  = item.change + delta;
          const base       = item.price - item.change;
          return {
            ...item,
            price:         newPrice,
            change:        newChange,
            changePercent: base !== 0 ? (newChange / base) * 100 : 0,
          };
        }),
      );

      setLastSync(0);
    }, 3000);

    return () => clearInterval(t);
  }, []);

  // Tier 2 — strategy P&L + sparklines (every 5 s, ~30% of active strategies)
  useEffect(() => {
    const t = setInterval(() => {
      setStrategies(prev =>
        prev.map(strategy => {
          if (strategy.status !== 'active' || Math.random() > 0.3) return strategy;
          const pnlDelta = (Math.random() - 0.45) * 150; // slight positive bias
          return {
            ...strategy,
            pnlDay:    strategy.pnlDay    + pnlDelta,
            pnlTotal:  strategy.pnlTotal  + pnlDelta,
            sparkline: [...strategy.sparkline.slice(1), (Math.random() - 0.45) * 100],
          };
        }),
      );
    }, 5000);

    return () => clearInterval(t);
  }, []);

  // Tier 3 — activity feed + occasional toast (every 20 s, 40% chance)
  useEffect(() => {
    const t = setInterval(() => {
      if (Math.random() > 0.6) {
        const types = ['trade', 'alert', 'agent'] as const;
        const type  = types[Math.floor(Math.random() * types.length)];

        const newItem: ActivityItem = {
          id:          Math.random().toString(36).slice(2, 11),
          type,
          title:       type === 'trade' ? 'Position Adjusted'
                     : type === 'alert' ? 'Volatility Warning'
                     : 'Agent Signal',
          description: type === 'trade' ? 'Rebalanced sector exposure'
                     : type === 'alert' ? 'VIX spike detected > 18.5'
                     : 'High-probability entry identified',
          timestamp:   new Date(),
        };

        setActivity(prev => [newItem, ...prev].slice(0, 20));

        if (type === 'agent') {
          toast({
            title:       'New Signal Generated',
            description: 'Strategy identified a high-probability entry.',
            type:        'info',
          });
        }
      }
    }, 20000);

    return () => clearInterval(t);
  }, [toast]);

  return { marketData, watchlist, strategies, activity, lastSync };
};
