import React from 'react';
import { useAppStore, useSystemStatus } from '@/store/useAppStore';
import { Bell, Power, RefreshCw, Wifi, WifiOff } from 'lucide-react';

interface HeaderProps {
  title: string;
}

const Header: React.FC<HeaderProps> = ({ title }) => {
  const { isSystemConnected, notifications } = useAppStore();
  const systemStatus = useSystemStatus();
  
  const unreadNotifications = notifications.filter(n => !n.id).length;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'text-green-400';
      case 'degraded': return 'text-yellow-400';
      case 'stopped': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <header className="bg-gray-800 shadow-lg border-b border-gray-700">
      <div className="flex items-center justify-between px-6 py-4">
        {/* Page Title */}
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-white">{title}</h1>
          <div className="flex items-center space-x-2">
            {isSystemConnected ? (
              <Wifi className="w-4 h-4 text-green-400" />
            ) : (
              <WifiOff className="w-4 h-4 text-red-400" />
            )}
            <span className="text-sm text-gray-400">
              {isSystemConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* System Info & Actions */}
        <div className="flex items-center space-x-6">
          {/* System Status */}
          {systemStatus && (
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-400">
                <div className="flex items-center space-x-2">
                  <span>Status:</span>
                  <span className={`font-semibold ${getStatusColor(systemStatus.status)}`}>
                    {systemStatus.status.toUpperCase()}
                  </span>
                </div>
                <div className="text-xs text-gray-500">
                  Uptime: {formatUptime(systemStatus.uptime)}
                </div>
              </div>
              
              {/* Key Metrics */}
              <div className="flex items-center space-x-4 text-sm">
                <div className="text-center">
                  <div className="text-blue-400 font-semibold">
                    {systemStatus.metrics?.active_positions || 0}
                  </div>
                  <div className="text-xs text-gray-500">Positions</div>
                </div>
                <div className="text-center">
                  <div className={`font-semibold ${
                    (systemStatus.metrics?.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    ${(systemStatus.metrics?.total_pnl || 0).toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500">Total PnL</div>
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center space-x-3">
            {/* Notifications */}
            <button className="relative p-2 rounded-lg hover:bg-gray-700 transition-colors">
              <Bell className="w-5 h-5 text-gray-400 hover:text-white" />
              {unreadNotifications > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                  {unreadNotifications}
                </span>
              )}
            </button>

            {/* Refresh */}
            <button 
              className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
              title="Refresh Data"
            >
              <RefreshCw className="w-5 h-5 text-gray-400 hover:text-white" />
            </button>

            {/* System Control */}
            <button 
              className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
              title="System Control"
            >
              <Power className="w-5 h-5 text-gray-400 hover:text-white" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;