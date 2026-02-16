
import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { 
  Search, TrendingUp, TrendingDown, Activity, 
  ArrowUpRight, ArrowDownRight, Globe, Zap, FileText,
  BarChart2, Bell
} from 'lucide-react';

import { PageHeader } from '../layout/PageHeader';
import { GlassCard } from '../ui/GlassCard';
import { MetricCard } from '../ui/MetricCard';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { SearchInput } from '../ui/SearchInput';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/Tabs';
import { DataTable, Column } from '../dashboard/DataTable';
import { SparklineChart } from '../dashboard/charts/SparklineChart';
import { cn, formatCurrency, formatNumber, formatPercent } from '../../lib/utils';
import { staggerContainer, fadeInUp } from '../../lib/animations';
import { useDashboard } from '../../contexts/DashboardContext';

// --- Types ---

interface MarketIndex {
  name: string;
  value: number;
  change: number;
  changePercent: number;
  data: number[];
}

interface Sector {
  name: string;
  performance: number;
  topMover: string;
  moverChange: number;
}

interface Stock {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  marketCap: string;
}

interface NewsItem {
  id: string;
  headline: string;
  source: string;
  time: string;
  sentiment: 'bullish' | 'bearish' | 'neutral';
}

// --- Mock Data ---

const indicesData: MarketIndex[] = [
  { 
    name: 'S&P 500', 
    value: 5203.45, 
    change: 45.20, 
    changePercent: 0.87, 
    data: [5150, 5160, 5145, 5180, 5190, 5185, 5203] 
  },
  { 
    name: 'NASDAQ', 
    value: 16420.10, 
    change: 210.50, 
    changePercent: 1.30, 
    data: [16100, 16200, 16150, 16300, 16350, 16320, 16420] 
  },
  { 
    name: 'DOW JONES', 
    value: 39100.80, 
    change: -120.40, 
    changePercent: -0.31, 
    data: [39300, 39250, 39280, 39200, 39150, 39180, 39100] 
  },
  { 
    name: 'RUSSELL 2000', 
    value: 2054.30, 
    change: 12.10, 
    changePercent: 0.59, 
    data: [2030, 2035, 2025, 2040, 2045, 2040, 2054] 
  },
  { 
    name: 'VIX', 
    value: 13.45, 
    change: -0.85, 
    changePercent: -5.94, 
    data: [14.5, 14.2, 14.8, 14.0, 13.8, 13.6, 13.45] 
  }
];

const sectorsData: Sector[] = [
  { name: 'Technology', performance: 1.45, topMover: 'NVDA', moverChange: 3.2 },
  { name: 'Financials', performance: -0.25, topMover: 'JPM', moverChange: -0.8 },
  { name: 'Healthcare', performance: 0.45, topMover: 'LLY', moverChange: 1.2 },
  { name: 'Energy', performance: 0.85, topMover: 'XOM', moverChange: 1.5 },
  { name: 'Consumer Disc.', performance: 1.10, topMover: 'AMZN', moverChange: 1.8 },
  { name: 'Real Estate', performance: -0.65, topMover: 'PLD', moverChange: -1.1 },
];

const generateStocks = (count: number, bias: 'gain' | 'loss' | 'mixed'): Stock[] => {
  return Array.from({ length: count }).map((_, i) => {
    const isGain = bias === 'gain' ? true : bias === 'loss' ? false : Math.random() > 0.5;
    const changeDir = isGain ? 1 : -1;
    const price = 50 + Math.random() * 450;
    const percent = Math.random() * 5 * changeDir;
    
    return {
      symbol: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK.B', 'LLY', 'V'][i % 10],
      name: ['Apple Inc.', 'Microsoft', 'Alphabet', 'Amazon', 'Tesla', 'Meta', 'NVIDIA', 'Berkshire', 'Eli Lilly', 'Visa'][i % 10],
      price: price,
      change: price * (percent / 100),
      changePercent: percent,
      volume: 1000000 + Math.random() * 50000000,
      marketCap: `${(0.1 + Math.random() * 2.5).toFixed(1)}T`
    };
  });
};

const watchlistData = generateStocks(8, 'mixed');
const topMoversData = generateStocks(8, 'gain').sort((a, b) => b.changePercent - a.changePercent);
const mostActiveData = generateStocks(8, 'mixed').sort((a, b) => b.volume - a.volume);

const newsData: NewsItem[] = [
  { id: '1', headline: 'Fed Signals Potential Rate Cut in Q3 as Inflation Cools', source: 'Bloomberg', time: '10m ago', sentiment: 'bullish' },
  { id: '2', headline: 'Tech Sector Rallies on New AI Chip Announcements', source: 'Reuters', time: '35m ago', sentiment: 'bullish' },
  { id: '3', headline: 'Oil Prices Stabilize Amidst Geopolitical Tensions', source: 'WSJ', time: '1h ago', sentiment: 'neutral' },
  { id: '4', headline: 'Retail Sales Data Misses Expectations, raising recession fears', source: 'CNBC', time: '2h ago', sentiment: 'bearish' },
  { id: '5', headline: 'European Markets Close Mixed as ECB Holds Rates', source: 'Financial Times', time: '3h ago', sentiment: 'neutral' },
  { id: '6', headline: 'Gold Hits All-Time High as Safe Haven Demand Surges', source: 'Bloomberg', time: '4h ago', sentiment: 'bullish' },
  { id: '7', headline: 'EV Makers Cut Prices in Bid to Boost Q4 Volume', source: 'Reuters', time: '5h ago', sentiment: 'bearish' },
];

// --- Sub-Components ---

const SectorCard: React.FC<{ sector: Sector }> = ({ sector }) => {
  const isPositive = sector.performance >= 0;
  
  return (
    <GlassCard 
      variant="subtle" 
      padding="sm" 
      enableHover 
      className={cn(
        "relative overflow-hidden border-l-2",
        isPositive ? "border-l-gain" : "border-l-loss"
      )}
    >
      <div className="flex justify-between items-start mb-2">
        <span className="font-sans font-medium text-sm text-obsidian-400 dark:text-paper-100">{sector.name}</span>
        <Badge variant={isPositive ? 'success' : 'danger'} size="sm">
          {isPositive ? '+' : ''}{sector.performance.toFixed(2)}%
        </Badge>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-obsidian-400/50 dark:text-paper-100/50 uppercase tracking-wider font-mono">Top Mover</span>
        <div className="flex items-center gap-1.5 font-mono">
          <span className="font-bold text-deep-teal-800 dark:text-turquoise-mist">{sector.topMover}</span>
          <span className={sector.moverChange >= 0 ? "text-gain" : "text-loss"}>
            {sector.moverChange >= 0 ? '+' : ''}{sector.moverChange}%
          </span>
        </div>
      </div>
    </GlassCard>
  );
};

const NewsListItem: React.FC<{ item: NewsItem }> = ({ item }) => (
  <div className="group flex gap-3 p-3 rounded-lg hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors cursor-pointer">
    <div className={cn(
      "w-1 rounded-full self-stretch flex-shrink-0",
      item.sentiment === 'bullish' ? 'bg-gain' : item.sentiment === 'bearish' ? 'bg-loss' : 'bg-obsidian-400/30 dark:bg-paper-100/30'
    )} />
    <div className="flex-1 space-y-1">
      <h4 className="text-sm font-medium text-obsidian-400 dark:text-paper-100 group-hover:text-deep-teal-800 dark:group-hover:text-turquoise-mist transition-colors line-clamp-2">
        {item.headline}
      </h4>
      <div className="flex items-center gap-2 text-[10px] font-mono text-obsidian-400/50 dark:text-paper-100/50 uppercase tracking-wide">
        <span>{item.source}</span>
        <span>•</span>
        <span>{item.time}</span>
      </div>
    </div>
  </div>
);

// --- Main Page Component ---

export const RegimePage = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const { openAlertModal } = useDashboard();

  const columns: Column<Stock>[] = [
    {
      key: 'symbol',
      header: 'Symbol',
      sortable: true,
      render: (val, row) => (
        <div className="flex items-center gap-3">
          <div>
            <div className="font-bold font-sans text-obsidian-400 dark:text-paper-100">{val}</div>
            <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50">{row.name}</div>
          </div>
        </div>
      )
    },
    {
      key: 'price',
      header: 'Price',
      align: 'right',
      sortable: true,
      render: (val) => <span className="font-mono font-medium">{formatCurrency(val)}</span>
    },
    {
      key: 'changePercent',
      header: 'Change',
      align: 'right',
      sortable: true,
      render: (val) => {
        const isPos = val >= 0;
        return (
          <div className={cn("font-mono flex items-center justify-end gap-1", isPos ? "text-gain" : "text-loss")}>
            {isPos ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {Math.abs(val).toFixed(2)}%
          </div>
        )
      }
    },
    {
      key: 'volume',
      header: 'Volume',
      align: 'right',
      sortable: true,
      className: "hidden md:table-cell",
      render: (val) => <span className="font-mono text-obsidian-400/60 dark:text-paper-100/60">{(val / 1000000).toFixed(1)}M</span>
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      width: '80px',
      render: (_, row) => (
        <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
           <button 
             onClick={(e) => {
               e.stopPropagation();
               openAlertModal(row.symbol, row.price);
             }}
             className="p-1.5 rounded-full hover:bg-deep-teal-800/10 dark:hover:bg-white/10 text-obsidian-400/50 hover:text-deep-teal-800 dark:hover:text-turquoise-mist transition-colors"
           >
             <Bell className="w-3.5 h-3.5" />
           </button>
        </div>
      )
    }
  ];

  return (
    <motion.div
      initial="initial"
      animate="animate"
      exit={{ opacity: 0 }}
      variants={staggerContainer}
      className="space-y-8 pt-2 pb-10"
    >
      {/* 1. Page Header */}
      <PageHeader
        title="Regime"
        description="Market regime indicators, sector performance, and regime-adjusted signals."
        actions={
          <div className="w-full md:w-80">
            <SearchInput 
              placeholder="Search symbol, index, or asset..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        }
      />

      {/* 2. Market Indices Row - Using adjusted grid for new MetricCard size */}
      <motion.div variants={fadeInUp} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {indicesData.map((index, i) => (
          <MetricCard
            key={index.name}
            title={index.name}
            value={index.value}
            change={index.changePercent}
            changeLabel=""
            format="number"
            delay={i * 0.05}
            sparkline={
              <SparklineChart 
                data={index.data} 
                color={index.changePercent >= 0 ? 'gain' : 'loss'} 
                height="100%"
                showArea={true}
              />
            }
          />
        ))}
      </motion.div>

      {/* 3. Morning Briefing Banner */}
      <motion.div variants={fadeInUp}>
        <GlassCard variant="dark" className="relative overflow-hidden w-full flex flex-col md:flex-row items-center justify-between gap-6 p-6">
           <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
              <Zap className="w-32 h-32 rotate-12" />
           </div>
           
           <div className="relative z-10 flex items-start gap-5 max-w-3xl">
              <div className="hidden sm:flex shrink-0 w-12 h-12 rounded-full bg-white/10 items-center justify-center text-turquoise-mist">
                 <FileText className="w-6 h-6" />
              </div>
              <div>
                 <h3 className="font-display text-xl text-paper-100 mb-2">Morning Briefing</h3>
                 <p className="text-sm md:text-base text-paper-100/70 leading-relaxed">
                    Volatility is increasing in Asian markets following central bank announcements. 
                    Technology sectors are showing strong pre-market momentum, while Energy consolidates near resistance levels.
                    Read the full AI-generated analysis for today's session.
                 </p>
              </div>
           </div>

           <Button variant="primary" className="relative z-10 shrink-0 w-full md:w-auto">
              Read Analysis
           </Button>
        </GlassCard>
      </motion.div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        
        {/* Left Column: Sectors & Watchlist */}
        <div className="xl:col-span-2 space-y-8">
          
          {/* 4. Sector Heatmap */}
          <motion.div variants={fadeInUp}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display text-lg text-obsidian-400 dark:text-paper-100">Sector Performance</h3>
              <button className="text-xs font-mono uppercase tracking-widest text-turquoise-mist hover:text-turquoise-bright">View All</button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {sectorsData.map((sector) => (
                <SectorCard key={sector.name} sector={sector} />
              ))}
            </div>
          </motion.div>

          {/* 5. Watchlists */}
          <motion.div variants={fadeInUp}>
             <GlassCard className="min-h-[500px] flex flex-col" padding="none">
               <Tabs defaultValue="watchlist" className="flex flex-col h-full">
                 <div className="px-6 py-4 border-b border-deep-teal-800/5 dark:border-white/5 flex flex-wrap gap-4 items-center justify-between">
                   <div className="flex items-center gap-2">
                     <Activity className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
                     <h3 className="font-display text-lg font-medium text-obsidian-400 dark:text-paper-100">Market Movers</h3>
                   </div>
                   <TabsList variant="pill">
                     <TabsTrigger value="watchlist">My Watchlist</TabsTrigger>
                     <TabsTrigger value="gainers">Top Gainers</TabsTrigger>
                     <TabsTrigger value="active">Most Active</TabsTrigger>
                   </TabsList>
                 </div>
                 
                 <div className="flex-1 p-0">
                    <TabsContent value="watchlist" className="mt-0 h-full">
                       <DataTable 
                         columns={columns} 
                         data={watchlistData} 
                       />
                    </TabsContent>
                    <TabsContent value="gainers" className="mt-0 h-full">
                       <DataTable 
                         columns={columns} 
                         data={topMoversData} 
                       />
                    </TabsContent>
                    <TabsContent value="active" className="mt-0 h-full">
                       <DataTable 
                         columns={columns} 
                         data={mostActiveData} 
                       />
                    </TabsContent>
                 </div>
               </Tabs>
             </GlassCard>
          </motion.div>

        </div>

        {/* Right Column: News */}
        <div className="space-y-8 h-full">
          
          <motion.div variants={fadeInUp} className="xl:h-full">
             <GlassCard className="xl:h-full flex flex-col" padding="none">
                
                {/* Header */}
                <div className="px-5 py-4 border-b border-deep-teal-800/5 dark:border-white/5 flex items-center justify-between">
                   <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-obsidian-400 dark:text-paper-100" />
                      <h3 className="font-display text-base font-medium">Market News</h3>
                   </div>
                   <Badge variant="neutral" dot pulsing>Live</Badge>
                </div>
                
                {/* Sentiment Visualization */}
                <div className="px-5 py-3 border-b border-deep-teal-800/5 dark:border-white/5 bg-deep-teal-800/5 dark:bg-white/5">
                   <div className="flex justify-between items-center mb-2">
                      <span className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/60 dark:text-paper-100/60">
                         Sentiment
                      </span>
                      <span className="text-xs font-bold text-gain">Bullish</span>
                   </div>
                   <div className="h-1.5 w-full bg-loss/20 rounded-full overflow-hidden flex">
                      <div className="h-full bg-gain" style={{ width: '65%' }} />
                   </div>
                </div>
                
                {/* News List */}
                <div className="p-4 space-y-1 flex-1 overflow-y-auto custom-scrollbar max-h-[500px] xl:max-h-none">
                  {newsData.map(item => (
                    <NewsListItem key={item.id} item={item} />
                  ))}
                </div>
                
                {/* Footer */}
                <div className="mt-auto p-4 border-t border-deep-teal-800/5 dark:border-white/5">
                   <Button variant="ghost" className="w-full text-xs uppercase tracking-widest">
                     Read Bloomberg Terminal
                   </Button>
                </div>
             </GlassCard>
          </motion.div>

        </div>
      </div>

    </motion.div>
  );
};
