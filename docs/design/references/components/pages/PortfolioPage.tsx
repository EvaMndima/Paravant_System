
import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { 
  Download, RefreshCw, Wallet, PieChart as PieChartIcon, 
  TrendingUp, Layers 
} from 'lucide-react';
import { PageHeader } from '../layout/PageHeader';
import { GlassCard } from '../ui/GlassCard';
import { MetricCard } from '../ui/MetricCard';
import { Button } from '../ui/Button';
import { DonutChart } from '../dashboard/charts/DonutChart';
import { BenchmarkChart } from '../dashboard/charts/BenchmarkChart';
import { DataTable, Column } from '../dashboard/DataTable';
import { SearchInput } from '../ui/SearchInput';
import { Tabs, TabsList, TabsTrigger } from '../ui/Tabs';
import { Badge } from '../ui/Badge';
import { ExportModal, ExportConfig } from '../dashboard/ExportModal';
import { useToast } from '../../contexts/ToastContext';
import { cn, formatCurrency, formatNumber } from '../../lib/utils';
import { staggerContainer, fadeInUp } from '../../lib/animations';
import { useDashboard, PositionDetails } from '../../contexts/DashboardContext';

// --- Types ---

interface Holding {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  assetType: 'Stock' | 'ETF' | 'Option' | 'Cash' | 'Crypto';
  quantity: number;
  avgCost: number;
  price: number;
  value: number;
  pnl: number;
  pnlPercent: number;
  weight: number;
}

// --- Mock Data ---

const generateHoldings = (): Holding[] => [
  { id: '1', symbol: 'NVDA', name: 'NVIDIA Corp', sector: 'Technology', assetType: 'Stock', quantity: 450, avgCost: 420.50, price: 890.25, value: 400612.50, pnl: 211387.50, pnlPercent: 111.71, weight: 24.5 },
  { id: '2', symbol: 'MSFT', name: 'Microsoft Corp', sector: 'Technology', assetType: 'Stock', quantity: 1200, avgCost: 310.00, price: 425.10, value: 510120.00, pnl: 138120.00, pnlPercent: 37.13, weight: 18.2 },
  { id: '3', symbol: 'BTC', name: 'Bitcoin', sector: 'Crypto', assetType: 'Crypto', quantity: 8.5, avgCost: 42000.00, price: 67500.00, value: 573750.00, pnl: 216750.00, pnlPercent: 60.71, weight: 15.8 },
  { id: '4', symbol: 'USD', name: 'US Dollar', sector: 'Cash', assetType: 'Cash', quantity: 245000, avgCost: 1.00, price: 1.00, value: 245000.00, pnl: 0, pnlPercent: 0, weight: 10.5 },
  { id: '5', symbol: 'TSLA', name: 'Tesla Inc', sector: 'Consumer Cyclical', assetType: 'Stock', quantity: 800, avgCost: 245.00, price: 175.40, value: 140320.00, pnl: -55680.00, pnlPercent: -28.41, weight: 8.5 },
  { id: '6', symbol: 'AAPL', name: 'Apple Inc', sector: 'Technology', assetType: 'Stock', quantity: 1500, avgCost: 155.00, price: 172.50, value: 258750.00, pnl: 26250.00, pnlPercent: 11.29, weight: 12.1 },
  { id: '7', symbol: 'JPM', name: 'JPMorgan Chase', sector: 'Financial', assetType: 'Stock', quantity: 600, avgCost: 145.00, price: 195.20, value: 117120.00, pnl: 30120.00, pnlPercent: 34.62, weight: 4.2 },
  { id: '8', symbol: 'V', name: 'Visa Inc', sector: 'Financial', assetType: 'Stock', quantity: 300, avgCost: 220.00, price: 280.50, value: 84150.00, pnl: 18150.00, pnlPercent: 27.50, weight: 3.1 },
  { id: '9', symbol: 'UNH', name: 'UnitedHealth', sector: 'Healthcare', assetType: 'Stock', quantity: 150, avgCost: 480.00, price: 460.20, value: 69030.00, pnl: -2970.00, pnlPercent: -4.12, weight: 2.5 },
  { id: '10', symbol: 'LLY', name: 'Eli Lilly', sector: 'Healthcare', assetType: 'Stock', quantity: 100, avgCost: 550.00, price: 780.00, value: 78000.00, pnl: 23000.00, pnlPercent: 41.81, weight: 2.8 },
  { id: '11', symbol: 'SPY', name: 'SPDR S&P 500', sector: 'Index', assetType: 'ETF', quantity: 200, avgCost: 410.00, price: 512.30, value: 102460.00, pnl: 20460.00, pnlPercent: 24.95, weight: 3.8 },
  { id: '12', symbol: 'QQQ', name: 'Invesco QQQ', sector: 'Index', assetType: 'ETF', quantity: 150, avgCost: 350.00, price: 440.15, value: 66022.50, pnl: 13522.50, pnlPercent: 25.78, weight: 2.4 },
  { id: '13', symbol: 'XOM', name: 'Exxon Mobil', sector: 'Energy', assetType: 'Stock', quantity: 500, avgCost: 105.00, price: 115.50, value: 57750.00, pnl: 5250.00, pnlPercent: 10.00, weight: 2.1 },
  { id: '14', symbol: 'AMD', name: 'Advanced Micro', sector: 'Technology', assetType: 'Stock', quantity: 400, avgCost: 110.00, price: 180.40, value: 72160.00, pnl: 28160.00, pnlPercent: 64.00, weight: 2.6 },
  { id: '15', symbol: 'AMZN', name: 'Amazon.com', sector: 'Consumer Cyclical', assetType: 'Stock', quantity: 600, avgCost: 130.00, price: 178.20, value: 106920.00, pnl: 28920.00, pnlPercent: 37.07, weight: 3.9 },
];

const benchmarkData = [
  { date: 'Jan', portfolio: 0, benchmark: 0 },
  { date: 'Feb', portfolio: 5, benchmark: 3 },
  { date: 'Mar', portfolio: 8, benchmark: 5 },
  { date: 'Apr', portfolio: 6, benchmark: 4 },
  { date: 'May', portfolio: 12, benchmark: 6 },
  { date: 'Jun', portfolio: 18, benchmark: 9 },
  { date: 'Jul', portfolio: 25, benchmark: 11 },
  { date: 'Aug', portfolio: 22, benchmark: 10 },
  { date: 'Sep', portfolio: 28, benchmark: 12 },
  { date: 'Oct', portfolio: 35, benchmark: 14 },
  { date: 'Nov', portfolio: 42, benchmark: 16 },
  { date: 'Dec', portfolio: 48, benchmark: 18 },
];

// --- Allocation Data Helpers ---

const getSectorAllocation = (holdings: Holding[]) => {
  const sectors: Record<string, number> = {};
  holdings.forEach(h => {
    sectors[h.sector] = (sectors[h.sector] || 0) + h.value;
  });
  
  const colors = ['#2A9D8F', '#264653', '#E9C46A', '#F4A261', '#E76F51', '#2ECC71', '#3498DB'];
  
  return Object.entries(sectors)
    .sort(([, a], [, b]) => b - a)
    .map(([name, value], i) => ({
      name,
      value,
      color: colors[i % colors.length]
    }));
};

const getAssetAllocation = (holdings: Holding[]) => {
  const assets: Record<string, number> = {};
  holdings.forEach(h => {
    assets[h.assetType] = (assets[h.assetType] || 0) + h.value;
  });
  
  return Object.entries(assets)
    .sort(([, a], [, b]) => b - a)
    .map(([name, value], i) => ({
      name,
      value,
      color: i === 0 ? '#2A9D8F' : i === 1 ? '#0F3D3E' : i === 2 ? '#E9C46A' : '#9CA3AF'
    }));
};

// --- Component ---

export const PortfolioPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [timeRange, setTimeRange] = useState('1Y');
  const [isExportOpen, setIsExportOpen] = useState(false);
  const { openPositionDrawer } = useDashboard();
  const { toast } = useToast();
  
  const holdings = useMemo(() => generateHoldings(), []);
  
  const filteredHoldings = useMemo(() => {
    if (!searchTerm) return holdings;
    const lower = searchTerm.toLowerCase();
    return holdings.filter(h => 
      h.symbol.toLowerCase().includes(lower) || 
      h.name.toLowerCase().includes(lower) ||
      h.sector.toLowerCase().includes(lower)
    );
  }, [holdings, searchTerm]);

  const sectorData = useMemo(() => getSectorAllocation(holdings), [holdings]);
  const assetData = useMemo(() => getAssetAllocation(holdings), [holdings]);
  const totalValue = holdings.reduce((sum, h) => sum + h.value, 0);

  const handleExport = (config: ExportConfig) => {
    toast({
      title: 'Export Started',
      description: `Generating ${config.format.toUpperCase()} report from ${config.startDate} to ${config.endDate}...`,
      type: 'info'
    });
  };

  // Table Columns
  const columns: Column<Holding>[] = [
    {
      key: 'symbol',
      header: 'Instrument',
      sortable: true,
      render: (_, row) => (
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-9 h-9 rounded-full flex items-center justify-center text-[10px] font-bold border",
            row.assetType === 'Cash' ? "bg-gain/10 text-gain border-gain/20" :
            row.assetType === 'Crypto' ? "bg-warning/10 text-warning border-warning/20" :
            "bg-deep-teal-800/5 dark:bg-white/5 border-deep-teal-800/10 dark:border-white/10 text-deep-teal-800 dark:text-turquoise-mist"
          )}>
            {row.symbol.substring(0, 2)}
          </div>
          <div>
            <div className="font-bold font-sans text-obsidian-400 dark:text-paper-100">{row.symbol}</div>
            <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-sans">{row.name}</div>
          </div>
        </div>
      )
    },
    {
      key: 'sector',
      header: 'Sector',
      sortable: true,
      render: (val) => (
        <Badge variant="neutral" size="sm" className="font-sans font-normal opacity-80">{val}</Badge>
      )
    },
    {
      key: 'quantity',
      header: 'Qty',
      align: 'right',
      sortable: true,
      render: (val) => formatNumber(val)
    },
    {
      key: 'avgCost',
      header: 'Avg Cost',
      align: 'right',
      sortable: true,
      render: (val) => <span className="text-obsidian-400/60 dark:text-paper-100/60">{formatCurrency(val)}</span>
    },
    {
      key: 'price',
      header: 'Price',
      align: 'right',
      sortable: true,
      render: (val) => <span className="font-medium">{formatCurrency(val)}</span>
    },
    {
      key: 'value',
      header: 'Mkt Value',
      align: 'right',
      sortable: true,
      render: (val) => <span className="font-bold text-obsidian-400 dark:text-paper-100">{formatCurrency(val)}</span>
    },
    {
      key: 'pnl',
      header: 'P&L',
      align: 'right',
      sortable: true,
      render: (val, row) => (
        <div className="flex flex-col items-end">
          <span className={cn("font-medium", val >= 0 ? "text-gain" : "text-loss")}>
            {val >= 0 ? '+' : ''}{formatCurrency(val)}
          </span>
          <div className={cn("text-[10px]", val >= 0 ? "text-gain" : "text-loss")}>
            {row.pnlPercent.toFixed(2)}%
          </div>
        </div>
      )
    },
    {
      key: 'weight',
      header: 'Weight',
      align: 'right',
      sortable: true,
      width: '120px',
      render: (val) => (
        <div className="w-24 ml-auto">
          <div className="flex justify-end mb-1">
             <span className="text-[10px] font-mono opacity-70">{val.toFixed(2)}%</span>
          </div>
          <div className="h-1.5 w-full bg-obsidian-400/5 dark:bg-white/10 rounded-full overflow-hidden">
            <div 
              className="h-full bg-deep-teal-600 dark:bg-turquoise-mist rounded-full" 
              style={{ width: `${Math.min(val, 100)}%` }}
            />
          </div>
        </div>
      )
    }
  ];

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="space-y-8 pt-2 pb-10"
    >
      {/* 1. Header */}
      <PageHeader
        title="Portfolio Analysis"
        description="Detailed breakdown of your holdings, allocation, and performance metrics."
        actions={
          <div className="flex items-center gap-3">
            <Button variant="secondary" leftIcon={<RefreshCw className="w-4 h-4" />}>
              Rebalance
            </Button>
            <Button variant="primary" leftIcon={<Download className="w-4 h-4" />} onClick={() => setIsExportOpen(true)}>
              Export Report
            </Button>
          </div>
        }
      />

      {/* 2. Summary Cards */}
      <motion.div variants={fadeInUp} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Net Liquidity"
          value={totalValue}
          prefix="$"
          variant="dark"
          icon={Wallet}
        />
        <MetricCard
          title="Total Unrealized P&L"
          value={605230.50}
          prefix="$"
          change={12.5}
          changeLabel="All time"
          icon={TrendingUp}
        />
        <MetricCard
          title="Active Positions"
          value={holdings.length}
          format="raw"
          icon={Layers}
        />
        <MetricCard
          title="Cash Available"
          value={245000}
          prefix="$"
          icon={PieChartIcon}
          suffix="USD"
        />
      </motion.div>

      {/* 3. Allocation Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <motion.div variants={fadeInUp}>
          <GlassCard className="h-full flex flex-col">
            <div className="mb-6 flex items-center justify-between">
              <h3 className="font-display text-lg">Sector Allocation</h3>
              <Badge variant="neutral">By Value</Badge>
            </div>
            <div className="flex-1 min-h-[300px]">
              <DonutChart 
                data={sectorData} 
                height={300}
                centerContent={
                  <div className="text-center">
                    <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50 uppercase tracking-widest mb-1">Total Assets</div>
                    <div className="text-xl font-mono font-bold">{formatCurrency(totalValue / 1000000)}M</div>
                  </div>
                }
              />
            </div>
          </GlassCard>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <GlassCard className="h-full flex flex-col">
            <div className="mb-6 flex items-center justify-between">
              <h3 className="font-display text-lg">Asset Class Allocation</h3>
              <Badge variant="neutral">By Type</Badge>
            </div>
            <div className="flex-1 min-h-[300px]">
              <DonutChart 
                data={assetData} 
                height={300}
                innerRadius="60%"
                outerRadius="80%"
                centerContent={
                  <div className="text-center">
                    <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50 uppercase tracking-widest mb-1">Exposure</div>
                    <div className="text-xl font-mono font-bold">Long Only</div>
                  </div>
                }
              />
            </div>
          </GlassCard>
        </motion.div>
      </div>

      {/* 4. Holdings Table */}
      <motion.div variants={fadeInUp}>
        <GlassCard className="flex flex-col gap-6" padding="lg">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <h3 className="font-display text-xl">Current Holdings</h3>
            <div className="w-full md:w-72">
              <SearchInput 
                placeholder="Search symbol, name, or sector..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onClear={() => setSearchTerm('')}
              />
            </div>
          </div>
          
          <DataTable 
            columns={columns} 
            data={filteredHoldings} 
            className="min-h-[400px]"
            onRowClick={(row) => openPositionDrawer(row as PositionDetails)}
          />
        </GlassCard>
      </motion.div>

      {/* 5. Performance Chart */}
      <motion.div variants={fadeInUp}>
        <GlassCard className="flex flex-col gap-6" padding="lg">
           <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
               <h3 className="font-display text-xl">Performance Attribution</h3>
               <p className="text-sm text-obsidian-400/50 dark:text-paper-100/50 mt-1">
                 Portfolio vs S&P 500 Benchmark (SPY)
               </p>
            </div>
            
            <div className="w-full md:w-auto">
               <Tabs defaultValue="1Y" onValueChange={setTimeRange} className="w-full">
                 <TabsList variant="pill" className="w-full md:w-auto grid grid-cols-6 md:flex">
                   {['1M', '3M', '6M', 'YTD', '1Y', 'ALL'].map(t => (
                     <TabsTrigger key={t} value={t} className="flex-1 md:flex-none justify-center">{t}</TabsTrigger>
                   ))}
                 </TabsList>
               </Tabs>
            </div>
          </div>

          <div className="h-[400px] w-full mt-4">
             <BenchmarkChart data={benchmarkData} height={400} />
          </div>
        </GlassCard>
      </motion.div>

      <ExportModal 
        isOpen={isExportOpen} 
        onClose={() => setIsExportOpen(false)} 
        onExport={handleExport}
        title="Export Portfolio Report"
      />

    </motion.div>
  );
};
