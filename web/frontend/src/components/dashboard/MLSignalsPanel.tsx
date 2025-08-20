import React from 'react';
import { useMLSignals } from '@/store/useAppStore';
import { Brain, TrendingUp, TrendingDown, Clock, Zap, Award } from 'lucide-react';

const MLSignalsPanel: React.FC = () => {
  const mlSignals = useMLSignals();

  const getSignalColor = (signalType: string) => {
    if (signalType === 'LONG' || signalType === 'buy') return 'text-green-400';
    if (signalType === 'SHORT' || signalType === 'sell') return 'text-red-400';
    return 'text-gray-400'; // FLAT/NEUTRAL
  };

  const getSignalBgColor = (signalType: string) => {
    if (signalType === 'LONG' || signalType === 'buy') return 'bg-green-400/20';
    if (signalType === 'SHORT' || signalType === 'sell') return 'bg-red-400/20';
    return 'bg-gray-400/20'; // FLAT/NEUTRAL
  };

  const getSignalIcon = (signalType: string) => {
    if (signalType === 'LONG' || signalType === 'buy') return TrendingUp;
    if (signalType === 'SHORT' || signalType === 'sell') return TrendingDown;
    return Clock; // FLAT/NEUTRAL
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400';
    if (confidence >= 0.6) return 'text-yellow-400';
    return 'text-red-400';
  };


  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'LOW': return 'text-green-400';
      case 'MEDIUM': return 'text-yellow-400';
      case 'HIGH': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getQualityScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    return 'text-red-400';
  };

  const recentSignals = mlSignals.slice(0, 6);
  const longSignals = mlSignals.filter(s => s.signal_type === 'LONG' || s.signal_type === 'buy').length;
  const shortSignals = mlSignals.filter(s => s.signal_type === 'SHORT' || s.signal_type === 'sell').length;
  const flatSignals = mlSignals.filter(s => s.signal_type === 'FLAT' || s.signal_type === 'NEUTRAL').length;
  const avgConfidence = mlSignals.length > 0 
    ? mlSignals.reduce((sum, s) => sum + s.confidence, 0) / mlSignals.length 
    : 0;

  return (
    <div className="card animate-scale-in relative overflow-hidden">
      {/* Background gradient effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-pink-600/10 to-purple-600/10 pointer-events-none"></div>
      <div className="relative z-10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-white flex items-center">
          <Brain className="w-5 h-5 mr-2 text-pink-400" />
          ML Signals
        </h3>
        
        <div className="flex items-center space-x-3">
          <div className={`px-3 py-2 rounded-lg ${avgConfidence >= 0.8 ? 'bg-green-400/20' : avgConfidence >= 0.6 ? 'bg-yellow-400/20' : 'bg-red-400/20'} backdrop-blur-sm`}>
            <div className="text-xs text-gray-300 font-medium">Avg Confidence</div>
            <div className={`text-lg font-bold ${getConfidenceColor(avgConfidence)}`}>
              {(avgConfidence * 100).toFixed(1)}%
            </div>
          </div>
        </div>
      </div>

      {/* Signal Summary */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/20 to-pink-600/20 rounded-xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 text-center border border-gray-700/50 hover:border-purple-500/50 transition-all">
            <div className="text-2xl font-bold text-white">{mlSignals.length}</div>
            <div className="text-xs text-gray-400 font-medium">Total Signals</div>
          </div>
        </div>
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-green-600/20 to-emerald-600/20 rounded-xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 text-center border border-gray-700/50 hover:border-green-500/50 transition-all">
            <div className="text-2xl font-bold text-green-400">{longSignals}</div>
            <div className="text-xs text-gray-400 font-medium">LONG сигналы</div>
          </div>
        </div>
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-red-600/20 to-rose-600/20 rounded-xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 text-center border border-gray-700/50 hover:border-red-500/50 transition-all">
            <div className="text-2xl font-bold text-red-400">{shortSignals}</div>
            <div className="text-xs text-gray-400 font-medium">SHORT сигналы</div>
          </div>
        </div>
      </div>

      {/* Recent Signals */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-gray-400 mb-3 flex items-center">
          <Clock className="w-4 h-4 mr-2" />
          Recent Signals
        </h4>
        
        {recentSignals.length > 0 ? (
          recentSignals.map((signal) => {
            const SignalIcon = getSignalIcon(signal.signal_type);
            const signalColor = getSignalColor(signal.signal_type);
            const signalBgColor = getSignalBgColor(signal.signal_type);
            const confidenceColor = getConfidenceColor(signal.confidence);

            return (
              <div key={signal.id} className="relative group">
                <div className="absolute inset-0 bg-gradient-to-r opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl blur-lg"
                     style={{
                       background: signal.signal_type === 'buy' 
                         ? 'linear-gradient(90deg, rgba(34,197,94,0.1) 0%, rgba(16,185,129,0.1) 100%)'
                         : 'linear-gradient(90deg, rgba(239,68,68,0.1) 0%, rgba(220,38,38,0.1) 100%)'
                     }}></div>
                <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 border border-gray-700/50 hover:border-gray-600/50 transition-all">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className="relative">
                        <div className="w-12 h-12 bg-gradient-to-br from-pink-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                          <SignalIcon className={`w-6 h-6 text-white`} />
                        </div>
                        <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-gray-900 rounded-full flex items-center justify-center">
                          <div className={`w-3 h-3 rounded-full ${signal.signal_type === 'buy' ? 'bg-green-400' : 'bg-red-400'} animate-pulse`}></div>
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-white">{signal.symbol}</div>
                        <div className={`inline-flex text-xs px-2 py-1 rounded-lg font-medium ${signalBgColor} ${signalColor}`}>
                          {signal.signal_type.toUpperCase()}
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className={`text-lg font-bold ${confidenceColor}`}>
                        {(signal.confidence * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-gray-400 font-medium">Confidence</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="p-2 bg-gray-900/30 rounded-lg">
                      <div className="text-xs text-gray-400 mb-1">Predicted Price</div>
                      <div className="text-sm font-semibold text-white">${signal.predicted_price.toFixed(2)}</div>
                    </div>
                    <div className="p-2 bg-gray-900/30 rounded-lg">
                      <div className="text-xs text-gray-400 mb-1">Current Price</div>
                      <div className="text-sm font-semibold text-white">${signal.current_price.toFixed(2)}</div>
                    </div>
                  </div>

                  {/* Additional Signal Info */}
                  <div className="flex items-center justify-between pt-3 border-t border-gray-700/50">
                  <div className="flex items-center space-x-4 text-xs text-gray-400">
                    <div className="flex items-center space-x-1">
                      <Clock className="w-3 h-3" />
                      <span>{new Date(signal.created_at).toLocaleTimeString()}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Zap className="w-3 h-3" />
                      <span>{signal.timeframe}</span>
                    </div>
                    {signal.quality_score && (
                      <div className="flex items-center space-x-1">
                        <Award className="w-3 h-3" />
                        <span className={getQualityScoreColor(signal.quality_score)}>
                          {(signal.quality_score * 100).toFixed(0)}
                        </span>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {signal.risk_level && (
                      <span className={`text-xs px-2 py-1 rounded bg-gray-600 ${getRiskLevelColor(signal.risk_level)}`}>
                        {signal.risk_level}
                      </span>
                    )}
                    {signal.executed && (
                      <span className="text-xs px-2 py-1 rounded bg-green-600 text-green-100">
                        Executed
                      </span>
                    )}
                  </div>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="text-center py-12 bg-gray-800/30 rounded-xl border border-gray-700/50">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-pink-600/20 to-purple-600/20 rounded-full mb-4">
              <Brain className="w-10 h-10 text-pink-400" />
            </div>
            <div className="text-gray-300 font-medium text-lg">No ML signals available</div>
            <div className="text-sm text-gray-500 mt-2">Signals will appear here when the ML model generates predictions</div>
          </div>
        )}
      </div>

      {/* ML Model Status */}
      <div className="mt-6 pt-4 border-t border-gray-700/50">
        <div className="bg-gradient-to-r from-purple-600/10 to-pink-600/10 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-300">ML Model Status</span>
            <div className="flex items-center space-x-2 px-2 py-1 bg-green-400/20 rounded-lg">
              <div className="w-2 h-2 bg-green-400 rounded-full pulse-dot"></div>
              <span className="text-xs text-green-400 font-medium">Active</span>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            <div className="p-2 bg-gray-900/30 rounded-lg">
              <div className="text-xs text-gray-400 mb-1">Features</div>
              <div className="text-lg font-bold text-white">240</div>
            </div>
            <div className="p-2 bg-gray-900/30 rounded-lg">
              <div className="text-xs text-gray-400 mb-1">Model Version</div>
              <div className="text-lg font-bold text-white">
                {recentSignals[0]?.model_version || 'v3.0'}
              </div>
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
};

export default MLSignalsPanel;