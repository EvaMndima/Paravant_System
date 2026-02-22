
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Search,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { DataTable } from '@/components/ui/DataTable';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { ApiErrorDisplay } from '@/components/ui/ApiErrorDisplay';
import { formatCurrency } from '@/lib/utils';
import { useOrderList, useCancelOrder } from '@/hooks';
import { useToast } from '@/contexts/ToastContext';
import type { OrderResponse } from '@/types/api';

export const OrdersPage: React.FC = () => {
  const [filter, setFilter] = useState('');
  const [statusTab, setStatusTab] = useState<
    'ALL' | 'pending' | 'filled' | 'cancelled'
  >('ALL');

  // Backend supports status filtering via API
  const { data: orderData, isLoading, isError, error, refetch } = useOrderList(
    statusTab === 'ALL' ? undefined : statusTab
  );
  const cancelMutation = useCancelOrder();
  const { addToast } = useToast();

  const handleCancel = (orderId: string) => {
    cancelMutation.mutate(orderId, {
      onSuccess: () => {
        addToast('success', 'Order Cancelled', `Order ${orderId.slice(0, 8)} cancelled`);
      },
      onError: (error) => {
        addToast('error', 'Cancellation Failed', error.message);
      },
    });
  };

  // Client-side search filtering
  const filteredOrders = (orderData?.orders ?? []).filter((order) => {
    const matchesSearch =
      order.symbol.toLowerCase().includes(filter.toLowerCase()) ||
      order.id.toLowerCase().includes(filter.toLowerCase());
    return matchesSearch;
  });

  const columns = [
    {
      key: 'id',
      header: 'Order ID',
      render: (val: unknown) => (
        <span className="font-mono text-xs opacity-60">{(val as string).slice(0, 8)}</span>
      ),
    },
    {
      key: 'created_at',
      header: 'Time',
      render: (val: unknown) =>
        val ? (
          <span className="text-xs font-mono opacity-60">
            {new Date(val as string).toLocaleTimeString()}
          </span>
        ) : (
          <span className="text-xs opacity-30">-</span>
        ),
    },
    {
      key: 'symbol',
      header: 'Symbol',
      render: (val: unknown) => <span className="font-bold">{val as string}</span>,
    },
    {
      key: 'side',
      header: 'Side',
      render: (val: unknown) => (
        <span
          className={`text-xs font-bold px-2 py-0.5 rounded flex items-center gap-1 w-fit ${
            val === 'BUY' ? 'bg-gain/20 text-gain' : 'bg-loss/20 text-loss'
          }`}
        >
          {val === 'BUY' ? (
            <ArrowUpRight className="w-3 h-3" />
          ) : (
            <ArrowDownRight className="w-3 h-3" />
          )}
          {val as string}
        </span>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (val: unknown) => <Badge variant="outline">{val as string}</Badge>,
    },
    {
      key: 'quantity',
      header: 'Qty',
      render: (val: unknown, row: OrderResponse) => (
        <div className="flex flex-col text-xs font-mono">
          <span>{val as number}</span>
          <span className="opacity-50">Filled: {row.filled_quantity}</span>
        </div>
      ),
    },
    {
      key: 'price',
      header: 'Price',
      render: (val: unknown) => (
        <span className="font-mono">
          {(val as number | null) && (val as number) > 0 ? formatCurrency(val as number) : 'Market'}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (val: unknown) => {
        const status = val as string;
        let color = 'text-obsidian-400';
        let icon = Clock;
        if (status === 'filled') {
          color = 'text-gain';
          icon = CheckCircle2;
        } else if (status === 'cancelled' || status === 'rejected') {
          color = 'text-loss';
          icon = XCircle;
        } else if (status === 'pending' || status === 'submitted') {
          color = 'text-warning';
          icon = Clock;
        }

        const Icon = icon;
        return (
          <div className={`flex items-center gap-1.5 text-xs font-medium ${color}`}>
            <Icon className="w-3.5 h-3.5" />
            {status.replace('_', ' ').toUpperCase()}
          </div>
        );
      },
    },
    {
      key: 'actions',
      header: '',
      render: (_: unknown, row: OrderResponse) => {
        const isOpen = ['pending', 'submitted'].includes(row.status);
        return isOpen ? (
          <Button
            variant="danger"
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={() => handleCancel(row.id)}
            isLoading={cancelMutation.isPending}
          >
            Cancel
          </Button>
        ) : null;
      },
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6 pb-12"
    >
      {isError && (
        <ApiErrorDisplay error={error as Error} onRetry={refetch} />
      )}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-medium text-deep-teal-800 dark:text-paper-100 mb-1">
            Orders
          </h1>
          <p className="text-obsidian-400/60 dark:text-paper-100/60 font-sans">
            Manage open orders and view execution history.
          </p>
        </div>
        <div className="text-xs font-mono text-obsidian-400/50 dark:text-paper-100/50">
          {filteredOrders.length} orders
        </div>
      </div>

      <GlassCard
        variant="default"
        padding="none"
        className="overflow-hidden min-h-[600px] flex flex-col"
      >
        {/* Toolbar */}
        <div className="p-4 border-b border-deep-teal-800/5 dark:border-white/5 flex flex-col md:flex-row gap-4 justify-between">
          <div className="flex bg-deep-teal-800/5 dark:bg-white/5 p-1 rounded-lg w-fit">
            {(['ALL', 'pending', 'filled', 'cancelled'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setStatusTab(tab)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                  statusTab === tab
                    ? 'bg-white dark:bg-deep-teal-900 shadow-sm text-deep-teal-800 dark:text-turquoise-mist'
                    : 'text-obsidian-400 hover:text-deep-teal-800 dark:text-paper-100/60 dark:hover:text-paper-100'
                }`}
              >
                {tab === 'ALL' ? 'All' : tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          <div className="relative w-full md:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-obsidian-400/50" />
            <Input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Search symbol or order ID..."
              className="pl-9"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="p-6">
            <Skeleton className="h-96 w-full" />
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={filteredOrders}
            className="flex-1 border-none"
            emptyMessage="No orders found matching your criteria."
          />
        )}
      </GlassCard>
    </motion.div>
  );
};
