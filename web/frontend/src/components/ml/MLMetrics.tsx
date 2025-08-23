import React from 'react';
import { TrendingUp, TrendingDown, Brain, Target, Zap, Clock } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  color: string;
  description?: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ 
  title, 
  value, 
  change, 
  icon, 
  color,
  description 
}) => {
  const formatChange = (change: number) => {
    const sign = change >= 0 ? '+' : '';
    return `${sign}${change.toFixed(2)}%`;
  };

  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-lg ${color}`}>
          {icon}
        </div>
        {change !== undefined && (
          <div className={`flex items-center text-sm ${
            change >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {change >= 0 ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
            {formatChange(change)}
          </div>
        )}
      </div>
      <div>
        <div className="text-2xl font-bold text-white mb-1">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
        <div className="text-gray-400 text-sm font-medium mb-1">{title}</div>
        {description && (
          <div className="text-gray-500 text-xs">{description}</div>
        )}
      </div>
    </div>
  );
};

interface MLMetricsProps {
  metrics: {
    accuracy: number;
    precision: number;
    recall: number;
    f1Score: number;
    predictionsCount: number;
    lastUpdated: string;
    modelName: string;
    avgConfidence: number;
    successRate: number;
  };
}

const MLMetrics: React.FC<MLMetricsProps> = ({ metrics }) => {
  const formatPercentage = (value: number) => `${(value * 100).toFixed(1)}%`;
  
  const metricsData = [
    {
      title: 'Model Accuracy',
      value: formatPercentage(metrics.accuracy),
      change: 2.4,
      icon: <Target className="w-6 h-6 text-white" />,
      color: 'bg-blue-600',
      description: 'Overall prediction accuracy'
    },
    {
      title: 'Precision',
      value: formatPercentage(metrics.precision),
      change: 1.2,
      icon: <Brain className="w-6 h-6 text-white" />,
      color: 'bg-purple-600',
      description: 'Positive prediction accuracy'
    },
    {
      title: 'Recall',
      value: formatPercentage(metrics.recall),
      change: -0.8,
      icon: <Zap className="w-6 h-6 text-white" />,
      color: 'bg-green-600',
      description: 'True positive detection rate'
    },
    {
      title: 'F1 Score',
      value: formatPercentage(metrics.f1Score),
      change: 0.6,
      icon: <TrendingUp className="w-6 h-6 text-white" />,
      color: 'bg-orange-600',
      description: 'Harmonic mean of precision and recall'
    },
    {
      title: 'Predictions Today',
      value: metrics.predictionsCount,
      icon: <Clock className="w-6 h-6 text-white" />,
      color: 'bg-cyan-600',
      description: 'Total predictions generated'
    },
    {
      title: 'Avg Confidence',
      value: formatPercentage(metrics.avgConfidence),
      change: 1.8,
      icon: <Target className="w-6 h-6 text-white" />,
      color: 'bg-pink-600',
      description: 'Average prediction confidence'
    }
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">ML Model Performance</h2>
          <p className="text-gray-400 mt-1">
            Real-time metrics for {metrics.modelName}
          </p>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-400">Last Updated</div>
          <div className="text-white font-medium">
            {new Date(metrics.lastUpdated).toLocaleTimeString()}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {metricsData.map((metric, index) => (
          <MetricCard key={index} {...metric} />
        ))}
      </div>

      {/* Model Status Indicator */}
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">Model Status</h3>
            <div className="flex items-center space-x-4">
              <div className="flex items-center">
                <div className="w-3 h-3 rounded-full bg-green-400 mr-2"></div>
                <span className="text-sm text-gray-300">Active</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 rounded-full bg-blue-400 mr-2"></div>
                <span className="text-sm text-gray-300">Training</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 rounded-full bg-yellow-400 mr-2"></div>
                <span className="text-sm text-gray-300">Updating Features</span>
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-green-400">
              {formatPercentage(metrics.successRate)}
            </div>
            <div className="text-sm text-gray-400">Success Rate</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MLMetrics;