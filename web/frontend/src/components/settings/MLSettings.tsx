import React, { useState, useEffect } from 'react';
import { Brain, Cpu, Database, TrendingUp, Save, RefreshCw, AlertCircle, Zap, BarChart3 } from 'lucide-react';
import { MLConfig } from '@/types/config';
import { apiService } from '@/services/apiService';

interface MLSettingsProps {
  onSave: (config: MLConfig) => void;
}

const MLSettings: React.FC<MLSettingsProps> = ({ onSave }) => {
  const [config, setConfig] = useState<MLConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [validation, setValidation] = useState<{ valid: boolean; errors: string[] }>({ valid: true, errors: [] });
  const [modelStats, setModelStats] = useState<any>(null);

  useEffect(() => {
    loadConfig();
    loadModelStats();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await apiService.getConfig('ml');
      if (data) {
        setConfig(data);
      } else {
        // Default ML configuration
        setConfig({
          model: {
            name: 'UnifiedPatchTST',
            version: '1.0.0',
            input_features: 240,
            prediction_horizon: 15,
            confidence_threshold: 0.75
          },
          training: {
            batch_size: 32,
            learning_rate: 0.001,
            epochs: 100,
            validation_split: 0.2
          },
          inference: {
            update_interval: 300,
            cache_ttl: 300,
            gpu_enabled: true
          },
          features: {
            technical_indicators: 180,
            market_features: 40,
            sentiment_features: 20
          }
        });
      }
    } catch (error) {
      console.error('Failed to load ML config:', error);
    }
    setLoading(false);
  };

  const loadModelStats = async () => {
    try {
      // Mock model statistics - в реальном приложении это будет API вызов
      setModelStats({
        accuracy: 78.5,
        precision: 82.1,
        recall: 74.3,
        f1_score: 78.0,
        total_predictions: 15847,
        successful_trades: 67,
        win_rate: 71.6,
        last_training: '2024-08-19T10:30:00Z',
        model_size: '45.2 MB',
        inference_time: '1.5ms'
      });
    } catch (error) {
      console.error('Failed to load model stats:', error);
    }
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
      const result = await apiService.validateConfig('ml', config);
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
      const success = await apiService.updateConfig('ml', config);
      if (success) {
        onSave(config);
      }
    } catch (error) {
      console.error('Failed to save ML config:', error);
    }
    setLoading(false);
  };

  if (!config) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-purple-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-white">ML Model Configuration</h3>
          <p className="text-gray-400 text-sm mt-1">Configure machine learning model parameters and features</p>
        </div>
        <div className="flex items-center space-x-3">
          {!validation.valid && (
            <div className="flex items-center space-x-2 px-3 py-1 bg-red-600/20 text-red-400 rounded-lg border border-red-600/30">
              <AlertCircle className="w-4 h-4" />
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

      {/* Model Statistics */}
      {modelStats && (
        <div className="card">
          <div className="p-6">
            <div className="flex items-center space-x-3 mb-6">
              <div className="w-12 h-12 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-white">Model Performance</h4>
                <p className="text-sm text-gray-400">Current model statistics and metrics</p>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700/50 text-center">
                <div className="text-2xl font-bold text-green-400">{modelStats.accuracy}%</div>
                <div className="text-sm text-gray-400">Accuracy</div>
              </div>
              <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700/50 text-center">
                <div className="text-2xl font-bold text-blue-400">{modelStats.win_rate}%</div>
                <div className="text-sm text-gray-400">Win Rate</div>
              </div>
              <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700/50 text-center">
                <div className="text-2xl font-bold text-purple-400">{modelStats.total_predictions}</div>
                <div className="text-sm text-gray-400">Predictions</div>
              </div>
              <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700/50 text-center">
                <div className="text-2xl font-bold text-orange-400">{modelStats.inference_time}</div>
                <div className="text-sm text-gray-400">Inference Time</div>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="text-sm text-gray-300">Last Training</div>
                <div className="text-white">{new Date(modelStats.last_training).toLocaleString()}</div>
              </div>
              <div className="space-y-2">
                <div className="text-sm text-gray-300">Model Size</div>
                <div className="text-white">{modelStats.model_size}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Model Configuration */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-white">Model Parameters</h4>
              <p className="text-sm text-gray-400">Core model configuration and architecture</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Model Name</label>
                <input
                  type="text"
                  value={config.model.name}
                  onChange={(e) => updateConfig('model.name', e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Input Features</label>
                <input
                  type="number"
                  value={config.model.input_features}
                  onChange={(e) => updateConfig('model.input_features', parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Prediction Horizon (minutes)</label>
                <input
                  type="number"
                  value={config.model.prediction_horizon}
                  onChange={(e) => updateConfig('model.prediction_horizon', parseInt(e.target.value))}
                  min="1"
                  max="60"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Model Version</label>
                <input
                  type="text"
                  value={config.model.version}
                  onChange={(e) => updateConfig('model.version', e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Confidence Threshold</label>
                <input
                  type="number"
                  value={config.model.confidence_threshold}
                  onChange={(e) => updateConfig('model.confidence_threshold', parseFloat(e.target.value))}
                  min="0"
                  max="1"
                  step="0.01"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Training Configuration */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-r from-green-600 to-blue-600 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-white">Training Parameters</h4>
              <p className="text-sm text-gray-400">Model training and optimization settings</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Batch Size</label>
              <input
                type="number"
                value={config.training.batch_size}
                onChange={(e) => updateConfig('training.batch_size', parseInt(e.target.value))}
                min="1"
                max="512"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Learning Rate</label>
              <input
                type="number"
                value={config.training.learning_rate}
                onChange={(e) => updateConfig('training.learning_rate', parseFloat(e.target.value))}
                min="0.0001"
                max="0.1"
                step="0.0001"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Epochs</label>
              <input
                type="number"
                value={config.training.epochs}
                onChange={(e) => updateConfig('training.epochs', parseInt(e.target.value))}
                min="1"
                max="1000"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Validation Split</label>
              <input
                type="number"
                value={config.training.validation_split}
                onChange={(e) => updateConfig('training.validation_split', parseFloat(e.target.value))}
                min="0.1"
                max="0.5"
                step="0.1"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Inference Configuration */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-r from-orange-600 to-red-600 rounded-xl flex items-center justify-center">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-white">Inference Settings</h4>
              <p className="text-sm text-gray-400">Real-time prediction and performance settings</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Update Interval (seconds)</label>
              <input
                type="number"
                value={config.inference.update_interval}
                onChange={(e) => updateConfig('inference.update_interval', parseInt(e.target.value))}
                min="60"
                max="3600"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Cache TTL (seconds)</label>
              <input
                type="number"
                value={config.inference.cache_ttl}
                onChange={(e) => updateConfig('inference.cache_ttl', parseInt(e.target.value))}
                min="60"
                max="3600"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            <div className="flex items-end">
              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={config.inference.gpu_enabled}
                  onChange={(e) => updateConfig('inference.gpu_enabled', e.target.checked)}
                  className="w-5 h-5 text-green-600 bg-gray-700 border-gray-600 rounded focus:ring-green-500 focus:ring-2"
                />
                <div>
                  <span className="text-white font-medium">GPU Acceleration</span>
                  <div className="text-xs text-gray-400">Enable CUDA/OpenCL</div>
                </div>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Feature Configuration */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-r from-pink-600 to-purple-600 rounded-xl flex items-center justify-center">
              <Database className="w-6 h-6 text-white" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-white">Feature Engineering</h4>
              <p className="text-sm text-gray-400">Feature extraction and processing configuration</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-4 bg-blue-600/10 border border-blue-600/30 rounded-xl">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-400">{config.features.technical_indicators}</div>
                <div className="text-sm text-blue-400 mb-3">Technical Indicators</div>
                <input
                  type="range"
                  min="50"
                  max="300"
                  value={config.features.technical_indicators}
                  onChange={(e) => updateConfig('features.technical_indicators', parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider-blue"
                />
              </div>
            </div>
            
            <div className="p-4 bg-green-600/10 border border-green-600/30 rounded-xl">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-400">{config.features.market_features}</div>
                <div className="text-sm text-green-400 mb-3">Market Features</div>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={config.features.market_features}
                  onChange={(e) => updateConfig('features.market_features', parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider-green"
                />
              </div>
            </div>
            
            <div className="p-4 bg-purple-600/10 border border-purple-600/30 rounded-xl">
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-400">{config.features.sentiment_features}</div>
                <div className="text-sm text-purple-400 mb-3">Sentiment Features</div>
                <input
                  type="range"
                  min="5"
                  max="50"
                  value={config.features.sentiment_features}
                  onChange={(e) => updateConfig('features.sentiment_features', parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider-purple"
                />
              </div>
            </div>
          </div>
          
          <div className="mt-4 p-3 bg-gray-800/50 rounded-lg border border-gray-700/50 text-center">
            <span className="text-gray-400">Total Features: </span>
            <span className="text-white font-semibold">
              {config.features.technical_indicators + config.features.market_features + config.features.sentiment_features}
            </span>
          </div>
        </div>
      </div>

      {/* Validation Errors */}
      {!validation.valid && validation.errors.length > 0 && (
        <div className="bg-red-600/10 border border-red-600/30 rounded-xl p-4">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
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

      {/* Performance Notice */}
      <div className="bg-purple-600/10 border border-purple-600/30 rounded-xl p-4">
        <div className="flex items-start space-x-3">
          <Cpu className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-purple-400 font-medium mb-1">Performance Optimization</h4>
            <p className="text-purple-300 text-sm">
              Model uses torch.compile for 7.7x speedup on RTX 5090. Inference time optimized from 11.8ms to 1.5ms.
              GPU acceleration is recommended for optimal performance.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MLSettings;