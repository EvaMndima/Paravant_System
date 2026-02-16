
import { useState, useEffect, useRef } from 'react';
import { MarketItem } from '../components/dashboard/MarketTicker';
import { WatchlistItem } from '../components/dashboard/Watchlist';
import { ActivityItem } from '../components/dashboard/ActivityFeed';
import { StrategySummary } from '../components/pages/StrategiesPage';
import { useToast } from '../contexts/ToastContext';

export const useRealtimeSimulation = (
  initialMarketData: MarketItem[],
  initialWatchlist: WatchlistItem[],
  initialStrategies: StrategySummary[],
  initialActivity: ActivityItem[]
) => {
  const { toast } = useToast();
  const [marketData, setMarketData] = useState<MarketItem[]>(initialMarketData);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>(initialWatchlist);
  const [strategies, setStrategies] = useState<StrategySummary[]>(initialStrategies);
  const [activity, setActivity] = useState<ActivityItem[]>(initialActivity);
  const [lastSync, setLastSync] = useState(0);

  // Sync Timer
  useEffect(() => {
    const timer = setInterval(() => {
      setLastSync(prev => (prev > 30 ? 0 : prev + 1));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // 1. High Frequency: Market Prices (every 2-4s)
  useEffect(() => {
    const interval = setInterval(() => {
      setMarketData(prev => prev.map(item => {
        // Random walk
        const change = (Math.random() - 0.5) * (item.value * 0.002);
        const newValue = item.value + change;
        const newChange = item.change + change;
        const newPercent = (newChange / (item.value - item.change)) * 100;
        
        return {
          ...item,
          value: newValue,
          change: newChange,
          changePercent: newPercent
        };
      }));

      setWatchlist(prev => prev.map(item => {
        const change = (Math.random() - 0.5) * (item.price * 0.003);
        const newPrice = item.price + change;
        const newChange = item.change + change;
        const newPercent = (newChange / (item.price - item.change)) * 100;

        return {
          ...item,
          price: newPrice,
          change: newChange,
          changePercent: newPercent
        };
      }));
      
      setLastSync(0); // Reset sync on update
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  // 2. Medium Frequency: Agent P&L (every 5s)
  useEffect(() => {
    const interval = setInterval(() => {
      setStrategies(prev => {
        // Only update a few strategies at a time to avoid chaos
        return prev.map(strategy => {
          if (strategy.status !== 'active' || Math.random() > 0.3) return strategy;

          const pnlChange = (Math.random() - 0.45) * 150; // Slight positive bias
          return {
            ...strategy,
            pnlDay: strategy.pnlDay + pnlChange,
            pnlTotal: strategy.pnlTotal + pnlChange,
            // Update sparkline
            sparkline: [...strategy.sparkline.slice(1), (Math.random() - 0.45) * 100]
          };
        });
      });
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // 3. Low Frequency: Activity & Signals (every 20s)
  useEffect(() => {
    const interval = setInterval(() => {
      if (Math.random() > 0.6) {
        // Generate new activity
        const types = ['trade', 'alert', 'agent'] as const;
        const type = types[Math.floor(Math.random() * types.length)];
        
        const newActivity: ActivityItem = {
          id: Math.random().toString(36).substr(2, 9),
          type,
          title: type === 'trade' ? 'Position Adjusted' : type === 'alert' ? 'Volatility Warning' : 'Agent Signal',
          description: type === 'trade' ? 'Rebalanced tech sector exposure' : 'VIX spike detected > 18.5',
          timestamp: new Date()
        };

        setActivity(prev => [newActivity, ...prev].slice(0, 20));

        // Occasional Toast
        if (type === 'agent') {
           toast({
             title: 'New Signal Generated',
             description: 'Alpha Seeker identified a high-probability entry.',
             type: 'info'
           });
        }
      }
    }, 20000);
    return () => clearInterval(interval);
  }, []);

  return { marketData, watchlist, strategies, activity, lastSync };
};
