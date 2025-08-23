import React, { useState, useEffect } from 'react';
import { 
  Brain, 
  Activity, 
  Settings, 
  BarChart3, 
  RefreshCw,
  Download,
  AlertCircle,
  CheckCircle,
  Clock
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

import MLMetrics from '../components/ml/MLMetrics';
import PredictionVisualization from '../components/ml/PredictionVisualization';
import MLChart from '../components/ml/MLChart';

// API functions
const fetchMLMetrics = async () => {
  const response = await axios.get('/api/ml-viz/metrics');
  return response.data;
};

const fetchMLPredictions = async (symbols: string[]) => {
  const predictions = await Promise.all(
    symbols.map(async (symbol) => {
      try {
        const response = await axios.get(`/api/ml-viz/predictions/${symbol}?chart_type=interactive`);
        return {
          symbol,
          ...response.data.metadata.prediction,
          currentPrice: response.data.chart_data?.current_price || 0,
          predictions: response.data.chart_data?.probabilities ? {
            probabilities: response.data.chart_data.probabilities,
            returns: response.data.chart_data.returns
          } : {},
          riskLevel: 'medium', // Default value
        };
      } catch (error) {
        console.error(`Error fetching predictions for ${symbol}:`, error);
        return null;
      }
    })
  );
  return predictions.filter(p => p !== null);
};

const fetchFeatureImportance = async (symbol: string) => {
  const response = await axios.get(`/api/ml-viz/features/${symbol}?limit=20`);
  return response.data;
};

interface TabProps {
  id: string;
  label: string;
  icon: React.ReactNode;
  isActive: boolean;
  onClick: (id: string) => void;
}

const Tab: React.FC<TabProps> = ({ id, label, icon, isActive, onClick }) => (
  <button
    onClick={() => onClick(id)}
    className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors ${
      isActive
        ? 'bg-blue-600 text-white'
        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
    }`}
  >
    {icon}
    <span>{label}</span>
  </button>
);

const MLPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [symbols] = useState(['BTCUSDT', 'ETHUSDT', 'SOLUSDT']);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // API Queries
  const { 
    data: mlMetrics, 
    isLoading: metricsLoading, 
    error: metricsError,
    refetch: refetchMetrics
  } = useQuery({
    queryKey: ['ml-metrics'],
    queryFn: fetchMLMetrics,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { 
    data: predictions, 
    isLoading: predictionsLoading, 
    error: predictionsError,
    refetch: refetchPredictions
  } = useQuery({
    queryKey: ['ml-predictions', symbols],
    queryFn: () => fetchMLPredictions(symbols),
    refetchInterval: 60000, // Refresh every minute
  });

  const { 
    data: featureImportance, 
    isLoading: featuresLoading,
    refetch: refetchFeatures 
  } = useQuery({
    queryKey: ['feature-importance', selectedSymbol],
    queryFn: () => fetchFeatureImportance(selectedSymbol),
    enabled: activeTab === 'features',
  });

  // Manual refresh all data
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([
        refetchMetrics(),
        refetchPredictions(),
        refetchFeatures()
      ]);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Generate comprehensive report
  const handleGenerateReport = async () => {
    try {
      const response = await axios.post('/api/ml-viz/generate-report', null, {
        params: {
          symbols: symbols,
          include_features: true
        }
      });
      
      // Poll for report completion
      const reportId = response.data.report_id;
      const pollReport = async () => {
        const statusResponse = await axios.get(`/api/ml-viz/report/${reportId}`);
        if (statusResponse.data.status === 'completed') {
          // Download the report
          window.open(`/api/ml-viz/download/${reportId}`, '_blank');
        } else {
          setTimeout(pollReport, 2000);
        }
      };
      
      setTimeout(pollReport, 2000);
      alert('Report generation started. Download will begin automatically when ready.');
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Error generating report. Please try again.');
    }
  };

  const tabs = [
    { 
      id: 'overview', 
      label: 'Overview', 
      icon: <Brain className="w-5 h-5" /> 
    },
    { 
      id: 'predictions', 
      label: 'Predictions', 
      icon: <BarChart3 className="w-5 h-5" /> 
    },
    { 
      id: 'features', 
      label: 'Features', 
      icon: <Activity className="w-5 h-5" /> 
    },
    { 
      id: 'settings', 
      label: 'Settings', 
      icon: <Settings className="w-5 h-5" /> 
    }
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <div className="space-y-6">
            {metricsError && (
              <div className="bg-red-900/20 border border-red-500 rounded-xl p-4 flex items-center space-x-3">
                <AlertCircle className="w-5 h-5 text-red-400" />
                <span className="text-red-400">Error loading ML metrics</span>
              </div>
            )}
            
            {metricsLoading ? (
              <div className="bg-gray-800 rounded-xl p-8 text-center border border-gray-700">
                <RefreshCw className="w-8 h-8 text-gray-400 mx-auto mb-4 animate-spin" />
                <p className="text-gray-400">Loading ML metrics...</p>
              </div>
            ) : mlMetrics ? (
              <MLMetrics metrics={mlMetrics} />
            ) : null}

            {/* Quick Predictions Summary */}
            {predictions && predictions.length > 0 && (
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-4">Current Signals</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {predictions.slice(0, 3).map((pred) => (
                    <div key={pred.symbol} className="bg-gray-700 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-white">{pred.symbol}</span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          pred.signalType === 'LONG' ? 'bg-green-600 text-white' :
                          pred.signalType === 'SHORT' ? 'bg-red-600 text-white' :
                          'bg-yellow-600 text-white'
                        }`}>
                          {pred.signalType}
                        </span>
                      </div>
                      <div className="text-sm text-gray-400">
                        Confidence: {(pred.confidence * 100).toFixed(1)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      case 'predictions':
        return (
          <div className="space-y-6">
            {predictionsError && (
              <div className="bg-red-900/20 border border-red-500 rounded-xl p-4 flex items-center space-x-3">
                <AlertCircle className="w-5 h-5 text-red-400" />
                <span className="text-red-400">Error loading predictions</span>
              </div>
            )}
            
            {predictionsLoading ? (
              <div className="bg-gray-800 rounded-xl p-8 text-center border border-gray-700">
                <RefreshCw className="w-8 h-8 text-gray-400 mx-auto mb-4 animate-spin" />
                <p className="text-gray-400">Loading predictions...</p>
              </div>
            ) : predictions && predictions.length > 0 ? (
              <PredictionVisualization 
                data={predictions}
                selectedSymbol={selectedSymbol}
                onSymbolSelect={setSelectedSymbol}
              />
            ) : (
              <div className="bg-gray-800 rounded-xl p-8 text-center border border-gray-700">
                <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-white mb-2">No Predictions Available</h3>
                <p className="text-gray-400">Unable to load prediction data at this time.</p>
              </div>
            )}
          </div>
        );

      case 'features':
        return (
          <div className="space-y-6">
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4">
                Feature Importance - {selectedSymbol}
              </h3>
              
              {featuresLoading ? (
                <div className="text-center py-8">
                  <RefreshCw className="w-8 h-8 text-gray-400 mx-auto mb-4 animate-spin" />
                  <p className="text-gray-400">Loading feature analysis...</p>
                </div>
              ) : featureImportance ? (
                <div className="space-y-3">
                  {featureImportance.slice(0, 15).map((feature: any, index: number) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-700 rounded-lg">
                      <div>
                        <span className="text-white font-medium">{feature.feature_name}</span>
                        <span className="text-gray-400 text-sm ml-2">({feature.category})</span>
                      </div>
                      <div className="flex items-center space-x-3">
                        <div className="w-32 bg-gray-600 rounded-full h-2">
                          <div 
                            className="bg-blue-500 h-2 rounded-full" 
                            style={{ width: `${feature.importance_score * 100}%` }}
                          />
                        </div>
                        <span className="text-white text-sm w-16 text-right">
                          {(feature.importance_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-400">No feature data available</p>
                </div>
              )}
            </div>
          </div>
        );

      case 'settings':
        return (
          <div className="space-y-6">
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4">Model Configuration</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Model Type
                  </label>
                  <select className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white">
                    <option>UnifiedPatchTST</option>
                    <option>LSTM</option>
                    <option>Transformer</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Prediction Interval (seconds)
                  </label>
                  <input 
                    type="number" 
                    defaultValue="60"
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Confidence Threshold
                  </label>
                  <input 
                    type="range" 
                    min="0" 
                    max="100" 
                    defaultValue="75"
                    className="w-full"
                  />
                  <span className="text-sm text-gray-400">75%</span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Auto-Retrain
                  </label>
                  <input 
                    type="checkbox" 
                    defaultChecked
                    className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded"
                  />
                  <span className="ml-2 text-sm text-gray-300">Enable automatic retraining</span>
                </div>
              </div>
            </div>

            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4">Actions</h3>
              <div className="flex flex-wrap gap-4">
                <button 
                  onClick={handleGenerateReport}
                  className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span>Generate Report</span>
                </button>
                <button className="flex items-center space-x-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors">
                  <CheckCircle className="w-4 h-4" />
                  <span>Validate Model</span>
                </button>
                <button className="flex items-center space-x-2 bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg transition-colors">
                  <RefreshCw className="w-4 h-4" />
                  <span>Retrain Model</span>
                </button>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">ML Control Panel</h1>
          <p className="text-gray-400 mt-1">
            Machine learning model monitoring and configuration
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-sm text-gray-400">
            <Clock className="w-4 h-4" />
            <span>Last updated: {new Date().toLocaleTimeString()}</span>
          </div>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center space-x-2 bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Status Indicator */}
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-green-400"></div>
              <span className="text-sm text-gray-300">ML System Online</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-blue-400"></div>
              <span className="text-sm text-gray-300">Real-time Predictions</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
              <span className="text-sm text-gray-300">Feature Engineering Active</span>
            </div>
          </div>
          <div className="text-sm text-gray-400">
            Monitoring {symbols.length} symbols
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
        <div className="flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <Tab
              key={tab.id}
              id={tab.id}
              label={tab.label}
              icon={tab.icon}
              isActive={activeTab === tab.id}
              onClick={setActiveTab}
            />
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {renderTabContent()}
    </div>
  );
};

export default MLPanel;