import React from 'react';
import { useSystemStatus } from '@/store/useAppStore';
import { TrendingUp, TrendingDown, DollarSign, Target, Award, AlertTriangle } from 'lucide-react';

const PerformanceOverview: React.FC = () => {
  const systemStatus = useSystemStatus();

  const performanceData = [
    {
      label: 'Total PnL',
      value: systemStatus?.metrics?.total_pnl || 0,
      icon: DollarSign,
      color: (systemStatus?.metrics?.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400',
      bgColor: (systemStatus?.metrics?.total_pnl || 0) >= 0 ? 'bg-green-400/20' : 'bg-red-400/20',
      format: (value: number) => `$${value.toFixed(2)}`,
    },
    {
      label: 'Daily PnL',
      value: systemStatus?.metrics?.daily_pnl || 0,
      icon: (systemStatus?.metrics?.daily_pnl || 0) >= 0 ? TrendingUp : TrendingDown,
      color: (systemStatus?.metrics?.daily_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400',
      bgColor: (systemStatus?.metrics?.daily_pnl || 0) >= 0 ? 'bg-green-400/20' : 'bg-red-400/20',
      format: (value: number) => `$${value.toFixed(2)}`,
    },
    {
      label: 'Win Rate',
      value: systemStatus?.metrics?.win_rate || 0,
      icon: Award,
      color: (systemStatus?.metrics?.win_rate || 0) > 50 ? 'text-green-400' : 'text-yellow-400',
      bgColor: (systemStatus?.metrics?.win_rate || 0) > 50 ? 'bg-green-400/20' : 'bg-yellow-400/20',
      format: (value: number) => `${value.toFixed(1)}%`,
    },
    {
      label: 'Active Positions',
      value: systemStatus?.metrics?.active_positions || 0,
      icon: Target,
      color: 'text-blue-400',
      bgColor: 'bg-blue-400/20',
      format: (value: number) => value.toString(),
    },
  ];

  const getPerformanceStatus = () => {
    const totalPnL = systemStatus?.metrics?.total_pnl || 0;
    const winRate = systemStatus?.metrics?.win_rate || 0;
    
    if (totalPnL > 0 && winRate > 60) return { status: 'Excellent', color: 'text-green-400', icon: Award };
    if (totalPnL > 0 && winRate > 50) return { status: 'Good', color: 'text-blue-400', icon: TrendingUp };
    if (totalPnL >= 0) return { status: 'Stable', color: 'text-yellow-400', icon: Target };
    return { status: 'Needs Attention', color: 'text-red-400', icon: AlertTriangle };
  };

  const performance = getPerformanceStatus();
  const PerformanceIcon = performance.icon;

  return (
    <div className="card animate-scale-in relative overflow-hidden">
      {/* Background gradient effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-green-600/10 to-emerald-600/10 pointer-events-none"></div>
      <div className="relative z-10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-white flex items-center">
          <TrendingUp className="w-5 h-5 mr-2 text-green-400" />
          Performance
        </h3>
        
        <div className={`flex items-center space-x-2 px-3 py-1 rounded-full ${performance.color === 'text-green-400' ? 'bg-green-400/20' : performance.color === 'text-red-400' ? 'bg-red-400/20' : 'bg-yellow-400/20'}`}>
          <PerformanceIcon className={`w-4 h-4 ${performance.color}`} />
          <span className={`text-sm font-medium ${performance.color}`}>
            {performance.status}
          </span>
        </div>
      </div>

      {/* Performance Metrics Grid */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {performanceData.map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.label} className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl blur-xl"
                   style={{
                     background: `linear-gradient(135deg, ${metric.color.replace('text-', '').replace('400', '500')} 0%, transparent 100%)`
                   }}></div>
              <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 border border-gray-700/50 hover:border-gray-600/50 transition-all duration-300">
                <div className="flex items-center justify-between mb-2">
                  <div className={`p-2 rounded-lg bg-gray-900/50`}>
                    <Icon className={`w-5 h-5 ${metric.color}`} />
                  </div>
                  <div className={`px-3 py-1.5 rounded-lg text-sm font-bold ${metric.bgColor} ${metric.color}`}>
                    {metric.format(metric.value)}
                  </div>
                </div>
                <div className="text-sm text-gray-400 font-medium">{metric.label}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Performance Chart */}
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 border border-gray-700/50">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-gray-300">7-Day Performance</span>
          <span className="text-xs text-gray-500 px-2 py-1 bg-gray-900/50 rounded-lg">Live Data</span>
        </div>
        <div className="h-20 relative overflow-hidden rounded-lg">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 via-green-600/20 to-purple-600/20 animate-pulse"></div>
          <div className="relative h-full flex items-center justify-center">
            <div className="text-center">
              <span className="text-gray-400 text-sm font-medium">Performance Chart</span>
              <div className="mt-1 flex items-center justify-center space-x-1">
                <div className="w-1 h-4 bg-blue-400 rounded animate-pulse"></div>
                <div className="w-1 h-6 bg-green-400 rounded animate-pulse delay-75"></div>
                <div className="w-1 h-5 bg-purple-400 rounded animate-pulse delay-150"></div>
                <div className="w-1 h-7 bg-blue-400 rounded animate-pulse delay-200"></div>
                <div className="w-1 h-4 bg-green-400 rounded animate-pulse delay-300"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="mt-4 pt-4 border-t border-gray-700/50">
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-3 bg-gray-800/50 rounded-lg backdrop-blur-sm border border-gray-700/50">
            <div className="text-lg font-bold text-white">
              {systemStatus?.metrics?.weekly_pnl ? `$${systemStatus.metrics.weekly_pnl.toFixed(2)}` : '$0.00'}
            </div>
            <div className="text-xs text-gray-400 font-medium">Weekly PnL</div>
          </div>
          <div className="text-center p-3 bg-gray-800/50 rounded-lg backdrop-blur-sm border border-gray-700/50">
            <div className="text-lg font-bold text-white">
              {systemStatus ? Math.floor(systemStatus.uptime / 86400) : 0}
            </div>
            <div className="text-xs text-gray-400 font-medium">Days Active</div>
          </div>
          <div className="text-center p-3 bg-gray-800/50 rounded-lg backdrop-blur-sm border border-gray-700/50">
            <div className="text-lg font-bold text-white">
              {systemStatus?.metrics?.active_positions || 0}
            </div>
            <div className="text-xs text-gray-400 font-medium">Positions</div>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
};

export default PerformanceOverview;