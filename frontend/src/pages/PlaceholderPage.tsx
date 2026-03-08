import React from 'react';
import { PageHeader } from '@/components/layout/PageHeader';
import { GlassCard } from '@/components/ui/GlassCard';

interface PlaceholderPageProps {
  title: string;
  description: string;
}

export const PlaceholderPage: React.FC<PlaceholderPageProps> = ({ title, description }) => {
  return (
    <>
      <PageHeader title={title} description={description} />
      <GlassCard className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <p className="text-obsidian-400/40 dark:text-paper-100/40 font-mono text-sm uppercase tracking-widest">
            Coming Soon
          </p>
          <p className="text-obsidian-400/60 dark:text-paper-100/60 text-sm max-w-md">
            This page will be built in a future session. The layout shell is working correctly.
          </p>
        </div>
      </GlassCard>
    </>
  );
};
