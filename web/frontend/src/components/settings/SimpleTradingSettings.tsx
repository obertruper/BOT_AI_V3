import React, { useState } from 'react';
import { TrendingUp, AlertTriangle, Target, Save } from 'lucide-react';

interface SimpleTradingSettingsProps {
  onSave: () => void;
}

const SimpleTradingSettings: React.FC<SimpleTradingSettingsProps> = ({ onSave }) => {
  const [tradingEnabled, setTradingEnabled] = useState(true);
  const [config] = useState({
    maxPositionSize: 1000,
    maxDailyLoss: 500,
    maxDrawdown: 20,
    stopLoss: 2,
    takeProfit: 4,
    leverage: 5,
    maxOpenPositions: 5,
    positionSize: 200,
    minBalance: 100
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-white">Trading Configuration</h3>
          <p className="text-gray-400 text-sm mt-1">Configure trading parameters and risk management</p>
        </div>
        <button
          onClick={onSave}
          className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-white font-medium transition-colors"
        >
          <Save className="w-4 h-4" />
          <span>Save Config</span>
        </button>
      </div>

      {/* Trading Status */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                tradingEnabled ? 'bg-green-600' : 'bg-gray-600'
              }`}>
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-white">Trading Status</h4>
                <p className="text-sm text-gray-400">Enable or disable automated trading</p>
              </div>
            </div>
            
            <label className="flex items-center space-x-3">
              <input
                type="checkbox"
                checked={tradingEnabled}
                onChange={(e) => setTradingEnabled(e.target.checked)}
                className="w-5 h-5 text-green-600 bg-gray-700 border-gray-600 rounded focus:ring-green-500 focus:ring-2"
              />
              <span className="text-white font-medium">
                {tradingEnabled ? 'Enabled' : 'Disabled'}
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* Risk Management */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-r from-red-600 to-orange-600 rounded-xl flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-white" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-white">Risk Management</h4>
              <p className="text-sm text-gray-400">Configure risk parameters and limits</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Max Position Size (USD)</label>
                <input
                  type="number"
                  defaultValue={config.maxPositionSize}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Max Daily Loss (USD)</label>
                <input
                  type="number"
                  defaultValue={config.maxDailyLoss}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Max Drawdown (%)</label>
                <input
                  type="number"
                  defaultValue={config.maxDrawdown}
                  step="0.1"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Stop Loss (%)</label>
                <input
                  type="number"
                  defaultValue={config.stopLoss}
                  step="0.1"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Take Profit (%)</label>
                <input
                  type="number"
                  defaultValue={config.takeProfit}
                  step="0.1"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Leverage</label>
                <select
                  defaultValue={config.leverage}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value={1}>1x</option>
                  <option value={2}>2x</option>
                  <option value={3}>3x</option>
                  <option value={5}>5x</option>
                  <option value={10}>10x</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Position Management */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
              <Target className="w-6 h-6 text-white" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-white">Position Management</h4>
              <p className="text-sm text-gray-400">Configure position sizing and limits</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Max Open Positions</label>
              <input
                type="number"
                defaultValue={config.maxOpenPositions}
                min="1"
                max="20"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Position Size (USD)</label>
              <input
                type="number"
                defaultValue={config.positionSize}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Min Balance Threshold (USD)</label>
              <input
                type="number"
                defaultValue={config.minBalance}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Info Notice */}
      <div className="bg-blue-600/10 border border-blue-600/30 rounded-xl p-4">
        <div className="text-blue-400 font-medium mb-1">Trading Configuration Notice</div>
        <p className="text-blue-300 text-sm">
          Changes to trading configuration will take effect immediately. Ensure all parameters are properly set before enabling trading.
        </p>
      </div>
    </div>
  );
};

export default SimpleTradingSettings;