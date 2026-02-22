
import React from 'react';
import { motion } from 'framer-motion';
import {
  Building2,
  Plus,
  ShieldCheck,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { ApiErrorDisplay } from '@/components/ui/ApiErrorDisplay';
import { formatCurrency } from '@/lib/utils';
import { useAccounts, useAccountBalance } from '@/hooks';
import type { AccountResponse } from '@/types/api';

const AccountCard = ({ account }: { account: AccountResponse }) => {
  const { data: balance, isLoading: balanceLoading } = useAccountBalance(account.id);

  return (
    <GlassCard variant="default" className="relative group overflow-hidden">
      {/* Account Header */}
      <div className="flex justify-between items-start mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-deep-teal-800/5 dark:bg-white/5 flex items-center justify-center text-deep-teal-800 dark:text-turquoise-mist">
            <Building2 className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-display font-bold text-lg text-deep-teal-800 dark:text-paper-100 flex items-center gap-2">
              {account.name}
              <Badge
                variant={account.status === 'active' ? 'success' : 'neutral'}
                className="text-[10px] h-5 px-1.5"
              >
                {account.status.toUpperCase()}
              </Badge>
            </h3>
            <div className="flex items-center gap-2 text-sm text-obsidian-400/60 dark:text-paper-100/60">
              <span>{account.broker}</span>
              <span>•</span>
              <span className="flex items-center gap-1 text-success">
                <ShieldCheck className="w-3 h-3" /> {account.profile}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Balance Info */}
      {balanceLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : (
        <div className="space-y-4">
          <div>
            <div className="text-sm text-obsidian-400/60 dark:text-paper-100/60 mb-1">
              Total Equity
            </div>
            <div className="text-3xl font-display font-bold text-deep-teal-800 dark:text-paper-100">
              {formatCurrency(balance?.equity_usdt || 0)}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 py-4 border-t border-b border-deep-teal-800/10 dark:border-white/10">
            <div>
              <div className="text-xs text-obsidian-400/60 dark:text-paper-100/60 mb-0.5">
                Available Balance
              </div>
              <div className="font-mono font-medium">
                {formatCurrency(balance?.balance_usdt || 0)}
              </div>
            </div>
            <div>
              <div className="text-xs text-obsidian-400/60 dark:text-paper-100/60 mb-0.5">
                Available Margin
              </div>
              <div className="font-mono font-medium">
                {formatCurrency(balance?.available_margin || 0)}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-2">
              <span className="text-sm text-obsidian-400/60 dark:text-paper-100/60">
                Open Positions Value
              </span>
              <span className="text-sm font-bold font-mono">
                {formatCurrency(balance?.open_positions_value || 0)}
              </span>
            </div>
            <span className="text-xs font-mono opacity-50">
              {balance?.timestamp
                ? new Date(balance.timestamp).toLocaleTimeString()
                : 'N/A'}
            </span>
          </div>
        </div>
      )}
    </GlassCard>
  );
};

export const AccountsPage: React.FC = () => {
  const { data: accounts, isLoading, isError, error, refetch } = useAccounts();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-8 pb-12"
    >
      {isError && <ApiErrorDisplay error={error as Error} onRetry={refetch} />}
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-medium text-deep-teal-800 dark:text-paper-100 mb-1">
            Accounts
          </h1>
          <p className="text-obsidian-400/60 dark:text-paper-100/60 font-sans">
            Manage exchange connections and view balances.
          </p>
        </div>
        <Button variant="primary" className="gap-2" disabled>
          <Plus className="w-4 h-4" /> Connect Exchange
        </Button>
      </div>

      {/* Accounts Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-80 rounded-2xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {(accounts ?? []).map((account) => (
            <AccountCard key={account.id} account={account} />
          ))}

          {/* Add New Account Card */}
          <button className="group relative min-h-[300px] rounded-2xl border-2 border-dashed border-deep-teal-800/10 dark:border-white/10 hover:border-turquoise-mist/50 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-all flex flex-col items-center justify-center gap-4">
            <div className="w-16 h-16 rounded-full bg-deep-teal-800/5 dark:bg-white/5 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
              <Plus className="w-8 h-8 text-obsidian-400/60 dark:text-paper-100/40 group-hover:text-turquoise-mist" />
            </div>
            <div className="text-center">
              <h3 className="font-display font-medium text-deep-teal-800 dark:text-paper-100">
                Add Account
              </h3>
              <p className="text-sm text-obsidian-400/60 dark:text-paper-100/60">
                Connect a new exchange API key
              </p>
            </div>
          </button>
        </div>
      )}
    </motion.div>
  );
};
