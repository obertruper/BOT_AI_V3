import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAppStore } from '@/store/useAppStore';
import { 
  BarChart3, 
  TrendingUp, 
  Activity, 
  Brain, 
  Target, 
  Zap, 
  Wallet, 
  PieChart, 
  Settings,
  Menu,
  Home
} from 'lucide-react';

const Sidebar: React.FC = () => {
  const location = useLocation();
  const { sidebarCollapsed, setSidebarCollapsed } = useAppStore();

  const navigationItems = [
    { name: 'Dashboard', icon: Home, path: '/', color: 'text-blue-400' },
    { name: 'Trading', icon: TrendingUp, path: '/trading', color: 'text-green-400' },
    { name: 'Charts', icon: BarChart3, path: '/charts', color: 'text-purple-400' },
    { name: 'ML Panel', icon: Brain, path: '/ml', color: 'text-pink-400' },
    { name: 'Strategies', icon: Target, path: '/strategies', color: 'text-orange-400' },
    { name: 'Indicators', icon: Zap, path: '/indicators', color: 'text-yellow-400' },
    { name: 'Positions', icon: Wallet, path: '/positions', color: 'text-cyan-400' },
    { name: 'Analytics', icon: PieChart, path: '/analytics', color: 'text-indigo-400' },
    { name: 'Settings', icon: Settings, path: '/settings', color: 'text-gray-400' },
  ];

  const isActiveRoute = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className={`bg-gray-800 shadow-lg transition-all duration-300 fixed left-0 top-0 h-full z-30 ${
      sidebarCollapsed ? 'w-16' : 'w-64'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-gray-700">
        {!sidebarCollapsed && (
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              BOT_AI_V3
            </h1>
          </div>
        )}
        
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
        >
          <Menu className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="mt-6 px-3">
        <ul className="space-y-2">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const isActive = isActiveRoute(item.path);
            
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`flex items-center px-3 py-3 rounded-lg transition-colors group ${
                    isActive 
                      ? 'bg-gray-700 text-white' 
                      : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                  }`}
                >
                  <Icon className={`w-5 h-5 ${isActive ? item.color : 'group-hover:' + item.color}`} />
                  
                  {!sidebarCollapsed && (
                    <>
                      <span className="ml-3 font-medium">{item.name}</span>
                      {isActive && (
                        <div className="ml-auto w-2 h-2 bg-blue-500 rounded-full"></div>
                      )}
                    </>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* System Status Indicator */}
      {!sidebarCollapsed && (
        <div className="absolute bottom-4 left-4 right-4">
          <div className="bg-gray-700 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-300">System Status</span>
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            </div>
            <div className="text-xs text-gray-400">
              All systems operational
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Sidebar;