import React, { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import { useWebSocketConnection } from '@/hooks/useWebSocket';
import { useAppStore } from '@/store/useAppStore';

interface LayoutProps {
  children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { sidebarCollapsed } = useAppStore();
  
  // Initialize WebSocket connection
  useWebSocketConnection();

  const getPageTitle = (pathname: string) => {
    const routes: Record<string, string> = {
      '/': 'Dashboard',
      '/trading': 'Trading Panel',
      '/charts': 'Market Charts',
      '/ml': 'ML Control Panel',
      '/strategies': 'Trading Strategies',
      '/indicators': 'Technical Indicators',
      '/positions': 'Positions & Orders',
      '/analytics': 'Performance Analytics',
      '/settings': 'System Settings',
    };
    return routes[pathname] || 'BOT_AI_V3';
  };

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      <Sidebar />
      
      <div className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ${
        sidebarCollapsed ? 'ml-16' : 'ml-64'
      }`}>
        <Header title={getPageTitle(location.pathname)} />
        
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-900">
          <div className="container mx-auto px-6 py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;