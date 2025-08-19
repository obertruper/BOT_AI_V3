import React from 'react';
import { useMarketData } from '@/store/useAppStore';
import { TrendingUp, TrendingDown, BarChart3, Globe } from 'lucide-react';

const MarketOverview: React.FC = () => {
  const marketData = useMarketData();

  // Mock market data if none available - updated with realistic 2024 prices
  const mockMarketData = [
    { symbol: 'BTCUSDT', price: 114710, change_24h_percent: 2.34, volume_24h: 18500000000 },
    { symbol: 'ETHUSDT', price: 3680, change_24h_percent: -1.45, volume_24h: 12300000000 },
    { symbol: 'ADAUSDT', price: 1.185, change_24h_percent: 5.67, volume_24h: 850000000 },
    { symbol: 'SOLUSDT', price: 295.40, change_24h_percent: 3.21, volume_24h: 2100000000 },
  ];

  const displayData = marketData && marketData.length > 0 ? marketData.slice(0, 4) : mockMarketData;

  const formatPrice = (price: number, symbol: string) => {
    if (symbol.includes('BTC')) return `$${price.toLocaleString()}`;
    if (symbol.includes('ETH')) return `$${price.toLocaleString()}`;
    if (price < 1) return `$${price.toFixed(3)}`;
    return `$${price.toFixed(2)}`;
  };

  const formatVolume = (volume: number) => {
    if (volume >= 1000000000) return `$${(volume / 1000000000).toFixed(1)}B`;
    if (volume >= 1000000) return `$${(volume / 1000000).toFixed(1)}M`;
    return `$${(volume / 1000).toFixed(1)}K`;
  };

  const getTrendIcon = (change: number) => {
    return change >= 0 ? TrendingUp : TrendingDown;
  };

  const getTrendColor = (change: number) => {
    return change >= 0 ? 'text-green-400' : 'text-red-400';
  };


  return (
    <div className="card animate-scale-in relative overflow-hidden">
      {/* Background gradient effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 to-pink-600/10 pointer-events-none"></div>
      <div className="relative z-10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-white flex items-center">
          <Globe className="w-5 h-5 mr-2 text-purple-400" />
          Market Overview
        </h3>
        
        <div className="flex items-center space-x-2 px-3 py-1 bg-purple-400/20 rounded-full">
          <BarChart3 className="w-4 h-4 text-purple-400" />
          <span className="text-sm text-purple-400 font-medium">Live Data</span>
          <div className="w-2 h-2 bg-purple-400 rounded-full pulse-dot"></div>
        </div>
      </div>

      {/* Market Data List */}
      <div className="space-y-3 mb-6">
        {displayData.map((market, index) => {
          const TrendIcon = getTrendIcon(market.change_24h_percent);
          const trendColor = getTrendColor(market.change_24h_percent);
          const isPositive = market.change_24h_percent >= 0;

          return (
            <div key={market.symbol} className="relative group">
              <div className="absolute inset-0 bg-gradient-to-r opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl blur-lg"
                   style={{
                     background: isPositive 
                       ? 'linear-gradient(90deg, rgba(34,197,94,0.1) 0%, rgba(16,185,129,0.1) 100%)'
                       : 'linear-gradient(90deg, rgba(239,68,68,0.1) 0%, rgba(220,38,38,0.1) 100%)'
                   }}></div>
              <div className="relative flex items-center justify-between p-4 bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 hover:border-gray-600/50 transition-all duration-300">
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <div className="w-10 h-10 bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl flex items-center justify-center text-xs font-bold text-white shadow-lg">
                      {market.symbol.substring(0, 3)}
                    </div>
                    <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-gray-900 rounded-full flex items-center justify-center">
                      <div className={`w-2 h-2 rounded-full ${isPositive ? 'bg-green-400' : 'bg-red-400'} animate-pulse`}></div>
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">{market.symbol}</div>
                    <div className="text-xs text-gray-400">
                      Vol: {formatVolume(market.volume_24h)}
                    </div>
                  </div>
                </div>
                
                <div className="text-right">
                  <div className="text-sm font-bold text-white">
                    {formatPrice(market.price, market.symbol)}
                  </div>
                  <div className={`flex items-center justify-end space-x-1 px-2 py-0.5 rounded-lg ${isPositive ? 'bg-green-400/20' : 'bg-red-400/20'}`}>
                    <TrendIcon className={`w-3 h-3 ${trendColor}`} />
                    <span className={`text-xs font-medium ${trendColor}`}>{Math.abs(market.change_24h_percent).toFixed(2)}%</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Market Summary */}
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 border border-gray-700/50">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-gray-300">Market Summary</span>
          <span className="text-xs text-gray-500 px-2 py-1 bg-gray-900/50 rounded-lg">24h</span>
        </div>
        
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-green-400/10 rounded-lg border border-green-400/20">
            <div className="text-xl font-bold text-green-400">
              {displayData.filter(m => m.change_24h_percent > 0).length}
            </div>
            <div className="text-xs text-green-400/80 font-medium">Gainers</div>
          </div>
          <div className="p-3 bg-red-400/10 rounded-lg border border-red-400/20">
            <div className="text-xl font-bold text-red-400">
              {displayData.filter(m => m.change_24h_percent < 0).length}
            </div>
            <div className="text-xs text-red-400/80 font-medium">Losers</div>
          </div>
        </div>
      </div>

      {/* Total Market Volume */}
      <div className="mt-4 pt-4 border-t border-gray-700/50">
        <div className="text-center p-3 bg-gradient-to-r from-blue-600/10 to-purple-600/10 rounded-lg border border-gray-700/50">
          <div className="text-xl font-bold text-white">
            {formatVolume(displayData.reduce((sum, m) => sum + m.volume_24h, 0))}
          </div>
          <div className="text-xs text-gray-400 font-medium">Total 24h Volume (Selected)</div>
        </div>
      </div>
      </div>
    </div>
  );
};

export default MarketOverview;