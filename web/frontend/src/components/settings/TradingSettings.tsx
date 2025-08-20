import React, { useState, useEffect } from 'react';
import { TrendingUp, DollarSign, Target, AlertTriangle, Save, RefreshCw } from 'lucide-react';
import { TradingConfig } from '@/types/config';
import { apiService } from '@/services/apiService';

interface TradingSettingsProps {
  onSave: (config: TradingConfig) => void;
}

const TradingSettings: React.FC<TradingSettingsProps> = ({ onSave }) => {
  const [config, setConfig] = useState<TradingConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [validation, setValidation] = useState<{ valid: boolean; errors: string[] }>({ valid: true, errors: [] });

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await apiService.getConfig('trading');
      if (data) {
        setConfig(data);
      } else {
        // Default configuration
        setConfig({
          trading_enabled: true,
          exchanges: {
            bybit: { enabled: true, sandbox: false, rate_limit: 100 },
            binance: { enabled: false, sandbox: true, rate_limit: 120 },
            okx: { enabled: false, sandbox: true, rate_limit: 100 }
          },
          risk_management: {
            max_position_size: 1000,
            max_daily_loss: 500,
            max_drawdown: 20,
            stop_loss_percentage: 2,
            take_profit_percentage: 4,
            leverage: 5
          },
          position_management: {
            max_open_positions: 5,
            position_size_usd: 200,
            min_balance_threshold: 100
          }
        });
      }
    } catch (error) {
      console.error('Failed to load trading config:', error);
    }
    setLoading(false);
  };

  const updateConfig = (path: string, value: any) => {
    if (!config) return;
    
    const keys = path.split('.');
    const newConfig = { ...config };
    let current: any = newConfig;
    
    for (let i = 0; i < keys.length - 1; i++) {
      current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = value;
    
    setConfig(newConfig);
  };

  const validateConfig = async () => {
    if (!config) return;
    
    try {
      const result = await apiService.validateConfig('trading', config);
      setValidation(result);
      return result.valid;
    } catch (error) {
      setValidation({ valid: false, errors: ['Validation failed'] });
      return false;
    }
  };

  const saveConfig = async () => {
    if (!config) return;
    
    const isValid = await validateConfig();
    if (!isValid) return;
    
    setLoading(true);
    try {
      const success = await apiService.updateConfig('trading', config);
      if (success) {
        onSave(config);
      }
    } catch (error) {
      console.error('Failed to save trading config:', error);
    }
    setLoading(false);
  };

  if (!config) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-white">Trading Configuration</h3>
          <p className="text-gray-400 text-sm mt-1">Configure trading parameters and risk management</p>
        </div>
        <div className="flex items-center space-x-3">
          {!validation.valid && (
            <div className="flex items-center space-x-2 px-3 py-1 bg-red-600/20 text-red-400 rounded-lg border border-red-600/30">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-sm">{validation.errors.length} errors</span>
            </div>
          )}
          <button
            onClick={saveConfig}
            disabled={loading || !validation.valid}
            className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded-lg text-white font-medium transition-colors"
          >
            <Save className="w-4 h-4" />
            <span>{loading ? 'Saving...' : 'Save Config'}</span>
          </button>
        </div>
      </div>

      {/* Trading Status */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                config.trading_enabled ? 'bg-green-600' : 'bg-gray-600'
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
                checked={config.trading_enabled}
                onChange={(e) => updateConfig('trading_enabled', e.target.checked)}
                className="w-5 h-5 text-green-600 bg-gray-700 border-gray-600 rounded focus:ring-green-500 focus:ring-2"
              />
              <span className="text-white font-medium">
                {config.trading_enabled ? 'Enabled' : 'Disabled'}
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
                  value={config.risk_management.max_position_size}
                  onChange={(e) => updateConfig('risk_management.max_position_size', parseFloat(e.target.value))}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Max Daily Loss (USD)</label>
                <input
                  type="number"
                  value={config.risk_management.max_daily_loss}
                  onChange={(e) => updateConfig('risk_management.max_daily_loss', parseFloat(e.target.value))}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Max Drawdown (%)</label>
                <input
                  type="number"
                  value={config.risk_management.max_drawdown}
                  onChange={(e) => updateConfig('risk_management.max_drawdown', parseFloat(e.target.value))}
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
                  value={config.risk_management.stop_loss_percentage}
                  onChange={(e) => updateConfig('risk_management.stop_loss_percentage', parseFloat(e.target.value))}
                  step="0.1"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Take Profit (%)</label>
                <input
                  type="number"
                  value={config.risk_management.take_profit_percentage}
                  onChange={(e) => updateConfig('risk_management.take_profit_percentage', parseFloat(e.target.value))}
                  step="0.1"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Leverage</label>
                <select
                  value={config.risk_management.leverage}
                  onChange={(e) => updateConfig('risk_management.leverage', parseInt(e.target.value))}
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
                value={config.position_management.max_open_positions}
                onChange={(e) => updateConfig('position_management.max_open_positions', parseInt(e.target.value))}
                min="1"
                max="20"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Position Size (USD)</label>
              <input
                type="number"
                value={config.position_management.position_size_usd}
                onChange={(e) => updateConfig('position_management.position_size_usd', parseFloat(e.target.value))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Min Balance Threshold (USD)</label>
              <input
                type="number"
                value={config.position_management.min_balance_threshold}
                onChange={(e) => updateConfig('position_management.min_balance_threshold', parseFloat(e.target.value))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Validation Errors */}
      {!validation.valid && validation.errors.length > 0 && (
        <div className="bg-red-600/10 border border-red-600/30 rounded-xl p-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-red-400 font-medium mb-2">Configuration Errors</h4>
              <ul className="space-y-1">
                {validation.errors.map((error, index) => (
                  <li key={index} className="text-red-300 text-sm">• {error}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Info Notice */}
      <div className="bg-blue-600/10 border border-blue-600/30 rounded-xl p-4">
        <div className="flex items-start space-x-3">
          <DollarSign className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-blue-400 font-medium mb-1">Trading Configuration Notice</h4>
            <p className="text-blue-300 text-sm">
              Changes to trading configuration will take effect immediately. Ensure all parameters are properly set before enabling trading.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradingSettings;