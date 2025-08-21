import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/services/apiService';
import SystemStatusCard from '@/components/dashboard/SystemStatusCard';
import PerformanceOverview from '@/components/dashboard/PerformanceOverview';
import ActivePositions from '@/components/dashboard/ActivePositions';
import MLSignalsPanel from '@/components/dashboard/MLSignalsPanel';
import MarketOverview from '@/components/dashboard/MarketOverview';
import TradingActivity from '@/components/dashboard/TradingActivity';
import RealTimeChart from '@/components/dashboard/RealTimeChart';
import MLCacheMetrics from '@/components/dashboard/MLCacheMetrics';
import MLDirectionDistribution from '@/components/dashboard/MLDirectionDistribution';
import { EnhancedPositionTracker } from '@/components/dashboard/EnhancedPositionTracker';

const Dashboard: React.FC = () => {
  // Initialize store (WebSocket connection will handle updates)

  // System Status Query
  useQuery({
    queryKey: ['systemStatus'],
    queryFn: apiService.getSystemStatus,
    refetchInterval: 5000,
  });

  // Positions Query
  useQuery({
    queryKey: ['positions'],
    queryFn: apiService.getActivePositions,
    refetchInterval: 5000,
  });

  // ML Signals Query
  useQuery({
    queryKey: ['mlSignals'],
    queryFn: apiService.getMLSignals,
    refetchInterval: 10000,
  });

  // Market Data Query
  useQuery({
    queryKey: ['marketData'],
    queryFn: () => apiService.getMarketData(),
    refetchInterval: 30000,
  });

  // Exchange Status Query
  useQuery({
    queryKey: ['exchanges'],
    queryFn: apiService.getExchanges,
    refetchInterval: 15000,
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Trading Dashboard</h1>
          <p className="text-gray-400 mt-1">
            Real-time monitoring and control of BOT_AI_V3 trading system
          </p>
        </div>
        
        <div className="flex items-center space-x-3">
          <div className="text-right">
            <div className="text-sm text-gray-400">Last Update</div>
            <div className="text-white font-mono">
              {new Date().toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>

      {/* Top Row - System Status & Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <SystemStatusCard />
        <PerformanceOverview />
        <MarketOverview />
      </div>

      {/* Middle Row - Real-Time Chart */}
      <div className="grid grid-cols-1 gap-6">
        <RealTimeChart symbol="BTCUSDT" />
      </div>

      {/* Lower Row - Positions & ML Signals */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <ActivePositions />
        <MLSignalsPanel />
      </div>

      {/* ML Analytics Row */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <MLCacheMetrics />
        <MLDirectionDistribution />
      </div>

      {/* Enhanced Position Tracker */}
      <div className="grid grid-cols-1 gap-6">
        <EnhancedPositionTracker />
      </div>

      {/* Bottom Row - Trading Activity */}
      <div className="grid grid-cols-1 gap-6">
        <TradingActivity />
      </div>
    </div>
  );
};

export default Dashboard;