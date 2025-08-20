import React from 'react';
import { usePositions } from '@/store/useAppStore';
import { TrendingUp, TrendingDown, Target, DollarSign, Clock, Shield } from 'lucide-react';

const ActivePositions: React.FC = () => {
  const positions = usePositions();

  const formatPnL = (pnl: number) => {
    const sign = pnl >= 0 ? '+' : '';
    return `${sign}$${pnl.toFixed(2)}`;
  };

  const formatPnLPercentage = (pnlPercentage: number) => {
    const sign = pnlPercentage >= 0 ? '+' : '';
    return `${sign}${pnlPercentage.toFixed(2)}%`;
  };

  const getPnLColor = (pnl: number) => {
    return pnl >= 0 ? 'text-green-400' : 'text-red-400';
  };


  const getSideColor = (side: string) => {
    return side === 'long' ? 'text-green-400' : 'text-red-400';
  };

  const getSideBgColor = (side: string) => {
    return side === 'long' ? 'bg-green-400/20' : 'bg-red-400/20';
  };

  const totalPnL = positions.reduce((sum, pos) => sum + pos.pnl, 0);
  const totalValue = positions.reduce((sum, pos) => sum + (pos.size * pos.current_price), 0);

  return (
    <div className="card animate-scale-in relative overflow-hidden">
      {/* Background gradient effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 to-cyan-600/10 pointer-events-none"></div>
      <div className="relative z-10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-white flex items-center">
          <Target className="w-5 h-5 mr-2 text-blue-400" />
          Active Positions
        </h3>
        
        <div className="flex items-center space-x-3">
          <div className={`px-4 py-2 rounded-lg ${totalPnL >= 0 ? 'bg-green-400/20' : 'bg-red-400/20'} backdrop-blur-sm border ${totalPnL >= 0 ? 'border-green-400/30' : 'border-red-400/30'}`}>
            <div className="text-xs text-gray-300 font-medium">Total PnL</div>
            <div className={`text-lg font-bold ${getPnLColor(totalPnL)}`}>
              {formatPnL(totalPnL)}
            </div>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 to-cyan-600/20 rounded-xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 text-center border border-gray-700/50 hover:border-blue-500/50 transition-all">
            <div className="text-2xl font-bold text-white">{positions.length}</div>
            <div className="text-xs text-gray-400 font-medium">Open Positions</div>
          </div>
        </div>
        <div className="relative group">
          <div className={`absolute inset-0 bg-gradient-to-br ${totalPnL >= 0 ? 'from-green-600/20 to-emerald-600/20' : 'from-red-600/20 to-rose-600/20'} rounded-xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity`}></div>
          <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 text-center border border-gray-700/50 hover:border-gray-600/50 transition-all">
            <div className={`text-2xl font-bold ${getPnLColor(totalPnL)}`}>
              {formatPnL(totalPnL)}
            </div>
            <div className="text-xs text-gray-400 font-medium">Total PnL</div>
          </div>
        </div>
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/20 to-pink-600/20 rounded-xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 text-center border border-gray-700/50 hover:border-purple-500/50 transition-all">
            <div className="text-2xl font-bold text-white">${totalValue.toFixed(0)}</div>
            <div className="text-xs text-gray-400 font-medium">Total Value</div>
          </div>
        </div>
      </div>

      {/* Positions List */}
      <div className="space-y-3">
        {positions.length > 0 ? (
          positions.map((position) => {
            const PnLIcon = position.pnl >= 0 ? TrendingUp : TrendingDown;
            const pnlColor = getPnLColor(position.pnl);
            const sideColor = getSideColor(position.side);
            const sideBgColor = getSideBgColor(position.side);

            return (
              <div key={position.id} className="relative group">
                <div className="absolute inset-0 bg-gradient-to-r opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl blur-lg"
                     style={{
                       background: position.pnl >= 0 
                         ? 'linear-gradient(90deg, rgba(34,197,94,0.1) 0%, rgba(16,185,129,0.1) 100%)'
                         : 'linear-gradient(90deg, rgba(239,68,68,0.1) 0%, rgba(220,38,38,0.1) 100%)'
                     }}></div>
                <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 border border-gray-700/50 hover:border-gray-600/50 transition-all">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className="relative">
                        <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-xl flex items-center justify-center text-sm font-bold text-white shadow-lg">
                          {position.symbol.substring(0, 3)}
                        </div>
                        <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-gray-900 rounded-full flex items-center justify-center">
                          <div className={`w-3 h-3 rounded-full ${position.side === 'long' ? 'bg-green-400' : 'bg-red-400'} animate-pulse`}></div>
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-white">{position.symbol}</div>
                        <div className={`inline-flex text-xs px-2 py-1 rounded-lg font-medium ${sideBgColor} ${sideColor}`}>
                          {position.side.toUpperCase()}
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className={`text-lg font-bold ${pnlColor} flex items-center justify-end space-x-1`}>
                        <PnLIcon className="w-4 h-4" />
                        <span>{formatPnL(position.pnl)}</span>
                      </div>
                      <div className={`text-xs font-medium px-2 py-0.5 rounded-lg inline-flex ${position.pnl >= 0 ? 'bg-green-400/20' : 'bg-red-400/20'} ${pnlColor}`}>
                        {formatPnLPercentage(position.pnl_percentage)}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3 text-xs">
                    <div className="p-2 bg-gray-900/30 rounded-lg">
                      <div className="flex items-center space-x-1 text-gray-400 mb-1">
                        <DollarSign className="w-3 h-3" />
                        <span>Size</span>
                      </div>
                      <div className="text-white font-semibold">{position.size.toFixed(4)}</div>
                    </div>
                    
                    <div className="p-2 bg-gray-900/30 rounded-lg">
                      <div className="flex items-center space-x-1 text-gray-400 mb-1">
                        <Target className="w-3 h-3" />
                        <span>Entry</span>
                      </div>
                      <div className="text-white font-semibold">${position.entry_price.toFixed(2)}</div>
                    </div>
                    
                    <div className="p-2 bg-gray-900/30 rounded-lg">
                      <div className="flex items-center space-x-1 text-gray-400 mb-1">
                        <TrendingUp className="w-3 h-3" />
                        <span>Current</span>
                      </div>
                      <div className="text-white font-semibold">${position.current_price.toFixed(2)}</div>
                    </div>
                  </div>

                  {/* Additional Info */}
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-700/50">
                    <div className="flex items-center space-x-3">
                      <div className="flex items-center space-x-1 px-2 py-1 bg-gray-900/30 rounded-lg">
                        <Clock className="w-3 h-3 text-gray-400" />
                        <span className="text-xs text-gray-400">{new Date(position.created_at).toLocaleDateString()}</span>
                      </div>
                      <div className="flex items-center space-x-1 px-2 py-1 bg-gray-900/30 rounded-lg">
                        <Shield className="w-3 h-3 text-yellow-400" />
                        <span className="text-xs text-yellow-400 font-medium">{position.leverage}x</span>
                      </div>
                    </div>
                    
                    <div className="text-xs text-gray-400 px-2 py-1 bg-gray-900/30 rounded-lg font-medium">
                      {position.exchange}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="text-center py-12 bg-gray-800/30 rounded-xl border border-gray-700/50">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-600/20 to-cyan-600/20 rounded-full mb-4">
              <Target className="w-10 h-10 text-blue-400" />
            </div>
            <div className="text-gray-300 font-medium text-lg">No active positions</div>
            <div className="text-sm text-gray-500 mt-2">Positions will appear here when trading is active</div>
          </div>
        )}
      </div>
      </div>
    </div>
  );
};

export default ActivePositions;