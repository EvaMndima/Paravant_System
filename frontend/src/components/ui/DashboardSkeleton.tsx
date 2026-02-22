
// React unused
import { Skeleton } from './Skeleton';
import { GlassCard } from './GlassCard';

export const DashboardSkeleton = () => {
  return (
    <div className="space-y-6 pb-12 animate-pulse">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48 bg-obsidian-400/10 dark:bg-paper-100/10" />
          <Skeleton className="h-4 w-64 bg-obsidian-400/10 dark:bg-paper-100/10" />
        </div>
        <Skeleton className="h-9 w-32 bg-obsidian-400/10 dark:bg-paper-100/10" />
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <GlassCard key={i} className="h-32 p-4 space-y-4">
            <div className="flex justify-between">
              <Skeleton className="h-4 w-24 bg-obsidian-400/10 dark:bg-paper-100/10" />
              <Skeleton className="h-4 w-4 rounded-full bg-obsidian-400/10 dark:bg-paper-100/10" />
            </div>
            <Skeleton className="h-8 w-32 bg-obsidian-400/10 dark:bg-paper-100/10" />
          </GlassCard>
        ))}
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-96">
        <GlassCard className="lg:col-span-2 p-6 space-y-4">
            <Skeleton className="h-6 w-32 mb-4 bg-obsidian-400/10 dark:bg-paper-100/10" />
            <Skeleton className="h-full w-full rounded-lg bg-obsidian-400/5 dark:bg-paper-100/5" />
        </GlassCard>
        <GlassCard className="p-6 space-y-4">
            <Skeleton className="h-6 w-24 mb-4 bg-obsidian-400/10 dark:bg-paper-100/10" />
             {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-3">
                    <Skeleton className="h-8 w-8 rounded-full bg-obsidian-400/10 dark:bg-paper-100/10" />
                    <div className="space-y-1 flex-1">
                        <Skeleton className="h-3 w-full bg-obsidian-400/10 dark:bg-paper-100/10" />
                        <Skeleton className="h-2 w-1/2 bg-obsidian-400/10 dark:bg-paper-100/10" />
                    </div>
                </div>
            ))}
        </GlassCard>
      </div>
    </div>
  );
};
