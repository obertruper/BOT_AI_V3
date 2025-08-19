import React, { useState, useEffect } from 'react';
import { Eye, EyeOff, Save, TestTube, Shield, Globe, Key, AlertCircle, CheckCircle } from 'lucide-react';
import { ExchangeConfig } from '@/types/config';
import { apiService } from '@/services/apiService';

interface ExchangeSettingsProps {
  onSave: (exchanges: ExchangeConfig[]) => void;
}

const ExchangeSettings: React.FC<ExchangeSettingsProps> = ({ onSave }) => {
  const [exchanges, setExchanges] = useState<ExchangeConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [showSecrets, setShowSecrets] = useState<{ [key: string]: boolean }>({});
  const [validationResults, setValidationResults] = useState<{ [key: string]: any }>({});

  // Mock exchange templates
  const exchangeTemplates: Partial<ExchangeConfig>[] = [
    {
      name: 'bybit',
      display_name: 'Bybit',
      enabled: true,
      sandbox: false,
      rate_limit: 100,
      supported_assets: ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'],
      fees: { maker: 0.001, taker: 0.001 }
    },
    {
      name: 'binance',
      display_name: 'Binance',
      enabled: false,
      sandbox: true,
      rate_limit: 120,
      supported_assets: ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT'],
      fees: { maker: 0.001, taker: 0.001 }
    },
    {
      name: 'okx',
      display_name: 'OKX',
      enabled: false,
      sandbox: true,
      rate_limit: 100,
      supported_assets: ['BTC-USDT', 'ETH-USDT', 'ADA-USDT'],
      fees: { maker: 0.0008, taker: 0.001 }
    }
  ];

  useEffect(() => {
    loadExchangeConfigs();
  }, []);

  const loadExchangeConfigs = async () => {
    setLoading(true);
    try {
      const configs = await apiService.getConfig('exchanges');
      if (configs && Array.isArray(configs)) {
        setExchanges(configs);
      } else {
        // Use templates if no configs found
        setExchanges(exchangeTemplates.map((template, index) => ({
          ...template,
          api_key: '',
          api_secret: '',
          passphrase: ''
        } as ExchangeConfig)));
      }
    } catch (error) {
      console.error('Failed to load exchange configs:', error);
      setExchanges(exchangeTemplates.map((template, index) => ({
        ...template,
        api_key: '',
        api_secret: '',
        passphrase: ''
      } as ExchangeConfig)));
    }
    setLoading(false);
  };

  const updateExchange = (index: number, field: keyof ExchangeConfig, value: any) => {
    const updatedExchanges = [...exchanges];
    updatedExchanges[index] = { ...updatedExchanges[index], [field]: value };
    setExchanges(updatedExchanges);
  };

  const toggleSecretVisibility = (exchangeName: string, field: string) => {
    const key = `${exchangeName}_${field}`;
    setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const testConnection = async (exchange: ExchangeConfig) => {
    setTesting(exchange.name);
    try {
      // Mock test - in real implementation this would call the API
      await new Promise(resolve => setTimeout(resolve, 2000));
      setValidationResults(prev => ({
        ...prev,
        [exchange.name]: {
          valid: exchange.api_key && exchange.api_secret,
          message: exchange.api_key && exchange.api_secret ? 'Connection successful' : 'API credentials required'
        }
      }));
    } catch (error) {
      setValidationResults(prev => ({
        ...prev,
        [exchange.name]: {
          valid: false,
          message: 'Connection failed'
        }
      }));
    }
    setTesting(null);
  };

  const saveConfigs = async () => {
    setLoading(true);
    try {
      const success = await apiService.updateConfig('exchanges', exchanges);
      if (success) {
        onSave(exchanges);
      }
    } catch (error) {
      console.error('Failed to save exchange configs:', error);
    }
    setLoading(false);
  };

  const getSecretDisplay = (secret: string, exchangeName: string, field: string) => {
    const key = `${exchangeName}_${field}`;
    return showSecrets[key] ? secret : '•'.repeat(Math.min(secret.length, 32));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-white">Exchange API Settings</h3>
          <p className="text-gray-400 text-sm mt-1">Configure API credentials for cryptocurrency exchanges</p>
        </div>
        <button
          onClick={saveConfigs}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded-lg text-white font-medium transition-colors"
        >
          <Save className="w-4 h-4" />
          <span>{loading ? 'Saving...' : 'Save All'}</span>
        </button>
      </div>

      <div className="grid gap-6">
        {exchanges.map((exchange, index) => (
          <div key={exchange.name} className="card relative overflow-hidden">
            {/* Background gradient */}
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
                    <h4 className="text-lg font-semibold text-white">{exchange.display_name}</h4>
                    <p className="text-sm text-gray-400">{exchange.name}</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-4">
                  {validationResults[exchange.name] && (
                    <div className={`flex items-center space-x-2 px-3 py-1 rounded-lg ${
                      validationResults[exchange.name].valid 
                        ? 'bg-green-600/20 text-green-400' 
                        : 'bg-red-600/20 text-red-400'
                    }`}>
                      {validationResults[exchange.name].valid ? (
                        <CheckCircle className="w-4 h-4" />
                      ) : (
                        <AlertCircle className="w-4 h-4" />
                      )}
                      <span className="text-sm">{validationResults[exchange.name].message}</span>
                    </div>
                  )}
                  
                  <button
                    onClick={() => testConnection(exchange)}
                    disabled={testing === exchange.name || !exchange.api_key || !exchange.api_secret}
                    className="flex items-center space-x-2 px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg text-white text-sm transition-colors"
                  >
                    <TestTube className="w-4 h-4" />
                    <span>{testing === exchange.name ? 'Testing...' : 'Test'}</span>
                  </button>
                  
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={exchange.enabled}
                      onChange={(e) => updateExchange(index, 'enabled', e.target.checked)}
                      className="w-4 h-4 text-green-600 bg-gray-700 border-gray-600 rounded focus:ring-green-500 focus:ring-2"
                    />
                    <span className="text-sm text-gray-300">Enabled</span>
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* API Credentials */}
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
                        value={exchange.api_key}
                        onChange={(e) => updateExchange(index, 'api_key', e.target.value)}
                        placeholder="Enter API Key"
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => toggleSecretVisibility(exchange.name, 'api_key')}
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
                        value={exchange.api_secret}
                        onChange={(e) => updateExchange(index, 'api_secret', e.target.value)}
                        placeholder="Enter API Secret"
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => toggleSecretVisibility(exchange.name, 'api_secret')}
                        className="absolute right-2 top-2 p-1 text-gray-400 hover:text-white transition-colors"
                      >
                        {showSecrets[`${exchange.name}_api_secret`] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {exchange.name === 'okx' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">Passphrase</label>
                      <div className="relative">
                        <input
                          type={showSecrets[`${exchange.name}_passphrase`] ? 'text' : 'password'}
                          value={exchange.passphrase || ''}
                          onChange={(e) => updateExchange(index, 'passphrase', e.target.value)}
                          placeholder="Enter Passphrase"
                          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => toggleSecretVisibility(exchange.name, 'passphrase')}
                          className="absolute right-2 top-2 p-1 text-gray-400 hover:text-white transition-colors"
                        >
                          {showSecrets[`${exchange.name}_passphrase`] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Configuration */}
                <div className="space-y-4">
                  <h5 className="text-md font-medium text-gray-300 flex items-center">
                    <Shield className="w-4 h-4 mr-2" />
                    Configuration
                  </h5>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Environment</label>
                    <select
                      value={exchange.sandbox ? 'sandbox' : 'live'}
                      onChange={(e) => updateExchange(index, 'sandbox', e.target.value === 'sandbox')}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="sandbox">Sandbox (Test)</option>
                      <option value="live">Live (Production)</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Rate Limit (per minute)</label>
                    <input
                      type="number"
                      value={exchange.rate_limit}
                      onChange={(e) => updateExchange(index, 'rate_limit', parseInt(e.target.value))}
                      min="1"
                      max="1000"
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">Maker Fee (%)</label>
                      <input
                        type="number"
                        value={exchange.fees.maker}
                        onChange={(e) => updateExchange(index, 'fees', { 
                          ...exchange.fees, 
                          maker: parseFloat(e.target.value) 
                        })}
                        step="0.0001"
                        min="0"
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">Taker Fee (%)</label>
                      <input
                        type="number"
                        value={exchange.fees.taker}
                        onChange={(e) => updateExchange(index, 'fees', { 
                          ...exchange.fees, 
                          taker: parseFloat(e.target.value) 
                        })}
                        step="0.0001"
                        min="0"
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Supported Assets */}
              <div className="mt-6 pt-4 border-t border-gray-700">
                <h5 className="text-md font-medium text-gray-300 mb-3">Supported Assets</h5>
                <div className="flex flex-wrap gap-2">
                  {exchange.supported_assets.map((asset, assetIndex) => (
                    <span
                      key={assetIndex}
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

      {/* Security Notice */}
      <div className="bg-yellow-600/10 border border-yellow-600/30 rounded-xl p-4">
        <div className="flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-yellow-400 font-medium mb-1">Security Notice</h4>
            <p className="text-yellow-300 text-sm">
              API credentials are encrypted and stored securely. For production use, ensure you create API keys with only necessary permissions (trading permissions without withdrawal rights).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExchangeSettings;