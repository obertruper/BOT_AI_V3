import React, { useState } from 'react';
import { Globe, Key, Save, TestTube, Eye, EyeOff } from 'lucide-react';

interface SimpleExchangeSettingsProps {
  onSave: () => void;
}

const SimpleExchangeSettings: React.FC<SimpleExchangeSettingsProps> = ({ onSave }) => {
  const [exchanges] = useState([
    { name: 'bybit', displayName: 'Bybit', enabled: true, apiKey: '', apiSecret: '' },
    { name: 'binance', displayName: 'Binance', enabled: false, apiKey: '', apiSecret: '' },
    { name: 'okx', displayName: 'OKX', enabled: false, apiKey: '', apiSecret: '' }
  ]);
  const [showSecrets, setShowSecrets] = useState<{ [key: string]: boolean }>({});

  const toggleSecret = (exchangeName: string, field: string) => {
    const key = `${exchangeName}_${field}`;
    setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-white">Exchange API Settings</h3>
          <p className="text-gray-400 text-sm mt-1">Configure API credentials for cryptocurrency exchanges</p>
        </div>
        <button
          onClick={onSave}
          className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-white font-medium transition-colors"
        >
          <Save className="w-4 h-4" />
          <span>Save All</span>
        </button>
      </div>

      <div className="grid gap-6">
        {exchanges.map((exchange) => (
          <div key={exchange.name} className="card relative overflow-hidden">
            <div className={`absolute inset-0 opacity-5 ${
              exchange.enabled ? 'bg-gradient-to-r from-green-500 to-blue-500' : 'bg-gradient-to-r from-gray-500 to-gray-700'
            }`}></div>
            
            <div className="relative z-10 p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                    exchange.enabled ? 'bg-green-600' : 'bg-gray-600'
                  }`}>
                    <Globe className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold text-white">{exchange.displayName}</h4>
                    <p className="text-sm text-gray-400">{exchange.name}</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-4">
                  <button className="flex items-center space-x-2 px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm transition-colors">
                    <TestTube className="w-4 h-4" />
                    <span>Test</span>
                  </button>
                  
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={exchange.enabled}
                      readOnly
                      className="w-4 h-4 text-green-600 bg-gray-700 border-gray-600 rounded focus:ring-green-500 focus:ring-2"
                    />
                    <span className="text-sm text-gray-300">Enabled</span>
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <h5 className="text-md font-medium text-gray-300 flex items-center">
                    <Key className="w-4 h-4 mr-2" />
                    API Credentials
                  </h5>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">API Key</label>
                    <div className="relative">
                      <input
                        type={showSecrets[`${exchange.name}_api_key`] ? 'text' : 'password'}
                        placeholder="Enter API Key"
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => toggleSecret(exchange.name, 'api_key')}
                        className="absolute right-2 top-2 p-1 text-gray-400 hover:text-white transition-colors"
                      >
                        {showSecrets[`${exchange.name}_api_key`] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">API Secret</label>
                    <div className="relative">
                      <input
                        type={showSecrets[`${exchange.name}_api_secret`] ? 'text' : 'password'}
                        placeholder="Enter API Secret"
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => toggleSecret(exchange.name, 'api_secret')}
                        className="absolute right-2 top-2 p-1 text-gray-400 hover:text-white transition-colors"
                      >
                        {showSecrets[`${exchange.name}_api_secret`] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <h5 className="text-md font-medium text-gray-300">Configuration</h5>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Environment</label>
                    <select className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                      <option value="sandbox">Sandbox (Test)</option>
                      <option value="live">Live (Production)</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Rate Limit (per minute)</label>
                    <input
                      type="number"
                      defaultValue="100"
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-gray-700/50">
                <h5 className="text-md font-medium text-gray-300 mb-3">Supported Assets</h5>
                <div className="flex flex-wrap gap-2">
                  {['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'].map((asset, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-blue-600/20 text-blue-400 rounded-full text-sm border border-blue-600/30"
                    >
                      {asset}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SimpleExchangeSettings;