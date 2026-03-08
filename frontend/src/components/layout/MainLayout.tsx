import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar, getLabelFromPath } from './Sidebar';
import { Header } from './Header';

export const MainLayout: React.FC = () => {
  const location = useLocation();
  const pageLabel = getLabelFromPath(location.pathname);

  return (
    <div className="flex min-h-screen bg-paper-100 dark:bg-obsidian-400">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <Header title={pageLabel} />

        <main
          id="main-content"
          className="flex-1 overflow-y-auto"
        >
          <div className="max-w-[1440px] mx-auto p-4 md:p-6 lg:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
