import React from 'react';
import { useSystemStatus } from '@/store/useAppStore';
import { Activity, Wifi, Database, Zap } from 'lucide-react';

const SystemStatusCard: React.FC = () => {
  const systemStatus = useSystemStatus();

  if (!systemStatus) {
    return (
      <div className="card animate-scale-in">
        <div className="flex items-center justify-center h-32">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'text-green-400';
      case 'degraded': return 'text-yellow-400';
      case 'stopped': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusBgColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-green-400/20';
      case 'degraded': return 'bg-yellow-400/20';
      case 'stopped': return 'bg-red-400/20';
      default: return 'bg-gray-400/20';
    }
  };

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h`;
    return `${hours}h ${minutes}m`;
  };

  const components = [
    { name: 'Trading Engine', status: systemStatus.components?.trading_engine, icon: Activity },
    { name: 'ML Manager', status: systemStatus.components?.ml_manager, icon: Zap },
    { name: 'Exchanges', status: systemStatus.components?.exchanges, icon: Wifi },
    { name: 'Risk Manager', status: systemStatus.components?.risk_manager, icon: Database },
  ];

  return (
    <div className="card animate-scale-in relative overflow-hidden">
      {/* Background gradient effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 to-purple-600/10 pointer-events-none"></div>
      <div className="relative z-10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-white flex items-center">
          <Activity className="w-5 h-5 mr-2 text-blue-400" />
          System Status
        </h3>
        
        <div className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBgColor(systemStatus.status)} ${getStatusColor(systemStatus.status)}`}>
          {systemStatus.status.toUpperCase()}
        </div>
      </div>

      {/* Main Status */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-gray-400">Uptime</span>
          <span className="text-white font-mono">{formatUptime(systemStatus.uptime)}</span>
        </div>
        
        <div className="flex items-center justify-between mb-2">
          <span className="text-gray-400">CPU Usage</span>
          <span className="text-white font-mono">{systemStatus.metrics?.cpu_usage?.toFixed(1)}%</span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-gray-400">Memory Usage</span>
          <span className="text-white font-mono">{systemStatus.metrics?.memory_usage?.toFixed(1)}%</span>
        </div>
      </div>

      {/* Progress Bars */}
      <div className="space-y-3 mb-6">
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">CPU</span>
            <span className="text-white">{systemStatus.metrics?.cpu_usage?.toFixed(0)}%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-3 overflow-hidden">
            <div 
              className={`h-3 rounded-full transition-all duration-500 relative overflow-hidden ${
                (systemStatus.metrics?.cpu_usage || 0) > 80 ? 'bg-red-500' : 
                (systemStatus.metrics?.cpu_usage || 0) > 60 ? 'bg-yellow-500' : 'bg-green-500'
              }`}
              style={{ width: `${systemStatus.metrics?.cpu_usage || 0}%` }}
            ></div>
          </div>
        </div>
        
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">Memory</span>
            <span className="text-white">{systemStatus.metrics?.memory_usage?.toFixed(0)}%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-3 overflow-hidden">
            <div 
              className={`h-3 rounded-full transition-all duration-500 relative overflow-hidden ${
                (systemStatus.metrics?.memory_usage || 0) > 80 ? 'bg-red-500' : 
                (systemStatus.metrics?.memory_usage || 0) > 60 ? 'bg-yellow-500' : 'bg-green-500'
              }`}
              style={{ width: `${systemStatus.metrics?.memory_usage || 0}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Components Status */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium text-gray-400 mb-3">Components</h4>
        <div className="grid grid-cols-2 gap-2">
          {components.map((component) => {
            const Icon = component.icon;
            return (
              <div key={component.name} className="flex items-center space-x-2 p-2 bg-gray-700/50 rounded-lg">
                <Icon className="w-4 h-4 text-gray-400" />
                <span className="text-xs text-gray-300 flex-1">{component.name}</span>
                <div className={`w-2 h-2 rounded-full ${component.status ? 'bg-green-400' : 'bg-red-400'}`}></div>
              </div>
            );
          })}
        </div>
      </div>
      </div>
    </div>
  );
};

export default SystemStatusCard;