import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  BarChart3,
  Bot,
  TrendingUp,
  ShoppingCart,
  Settings,
  Home,
  Activity,
  Wallet,
  AlertTriangle,
} from 'lucide-react';
import { useTradingStore } from '@/store/tradingStore';

const Navigation: React.FC = () => {
  const location = useLocation();
  const { wsConnected, systemStatus } = useTradingStore();

  const navItems = [
    { path: '/', label: 'Дашборд', icon: Home },
    { path: '/traders', label: 'Трейдеры', icon: Bot },
    { path: '/positions', label: 'Позиции', icon: TrendingUp },
    { path: '/orders', label: 'Ордера', icon: ShoppingCart },
    { path: '/analytics', label: 'Аналитика', icon: BarChart3 },
    { path: '/settings', label: 'Настройки', icon: Settings },
  ];

  return (
    <nav className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo и основная навигация */}
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Bot className="h-8 w-8 text-blue-500" />
              <span className="ml-2 text-xl font-bold text-gray-900 dark:text-white">
                BOT Trading v3.0
              </span>
            </div>

            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`${
                      isActive
                        ? 'border-blue-500 text-gray-900 dark:text-white'
                        : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'
                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors duration-200`}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Статусы и индикаторы */}
          <div className="flex items-center space-x-4">
            {/* WebSocket статус */}
            <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium ${
              wsConnected
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                wsConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`} />
              <span>{wsConnected ? 'Online' : 'Offline'}</span>
            </div>

            {/* Системный статус */}
            {systemStatus && (
              <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                <div className="flex items-center space-x-1">
                  <Activity className="h-3 w-3" />
                  <span>CPU: {systemStatus.system_metrics.cpu_usage.toFixed(1)}%</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Wallet className="h-3 w-3" />
                  <span>RAM: {systemStatus.system_metrics.memory_usage.toFixed(1)}%</span>
                </div>
                <div className={`flex items-center space-x-1 ${
                  systemStatus.status === 'running'
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-yellow-600 dark:text-yellow-400'
                }`}>
                  {systemStatus.status === 'running' ? (
                    <Activity className="h-3 w-3" />
                  ) : (
                    <AlertTriangle className="h-3 w-3" />
                  )}
                  <span>{systemStatus.status === 'running' ? 'Running' : 'Stopped'}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Мобильная навигация */}
      <div className="sm:hidden">
        <div className="pt-2 pb-3 space-y-1 bg-gray-50 dark:bg-gray-800">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`${
                  isActive
                    ? 'bg-blue-50 dark:bg-blue-900 border-blue-500 text-blue-700 dark:text-blue-200'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-gray-300 hover:text-gray-700 dark:hover:text-gray-300'
                } block pl-3 pr-4 py-2 border-l-4 text-sm font-medium transition-colors duration-200`}
              >
                <div className="flex items-center">
                  <Icon className="h-4 w-4 mr-3" />
                  {item.label}
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
