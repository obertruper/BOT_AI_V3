import React, { useState, useEffect } from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
  ReferenceLine,
  Cell
} from 'recharts';
import { ArrowUp, ArrowDown, Minus, TrendingUp, AlertCircle } from 'lucide-react';

interface PredictionData {
  symbol: string;
  signalType: 'LONG' | 'SHORT' | 'NEUTRAL';
  confidence: number;
  strength: number;
  currentPrice: number;
  predictions: {
    probabilities?: {
      timeframes: string[];
      data: number[][];
    };
    returns?: {
      '15m': number;
      '1h': number;
      '4h': number;
      '12h': number;
    };
  };
  stopLoss?: number;
  takeProfit?: number;
  riskLevel: string;
}

interface PredictionVisualizationProps {
  data: PredictionData[];
  selectedSymbol?: string;
  onSymbolSelect?: (symbol: string) => void;
}

const SignalIndicator: React.FC<{ 
  signal: 'LONG' | 'SHORT' | 'NEUTRAL'; 
  confidence: number;
  strength: number;
}> = ({ signal, confidence, strength }) => {
  const getSignalColor = () => {
    switch (signal) {
      case 'LONG': return 'text-green-400';
      case 'SHORT': return 'text-red-400';
      default: return 'text-yellow-400';
    }
  };

  const getSignalIcon = () => {
    switch (signal) {
      case 'LONG': return <ArrowUp className="w-5 h-5" />;
      case 'SHORT': return <ArrowDown className="w-5 h-5" />;
      default: return <Minus className="w-5 h-5" />;
    }
  };

  const getBgColor = () => {
    switch (signal) {
      case 'LONG': return 'bg-green-600';
      case 'SHORT': return 'bg-red-600';
      default: return 'bg-yellow-600';
    }
  };

  return (
    <div className="flex items-center space-x-3">
      <div className={`p-2 rounded-lg ${getBgColor()}`}>
        {getSignalIcon()}
      </div>
      <div>
        <div className={`font-bold text-lg ${getSignalColor()}`}>
          {signal}
        </div>
        <div className="text-sm text-gray-400">
          Confidence: {(confidence * 100).toFixed(1)}%
        </div>
        <div className="text-sm text-gray-400">
          Strength: {strength.toFixed(3)}
        </div>
      </div>
    </div>
  );
};

const TimeframeProbabilities: React.FC<{ 
  probabilities: { timeframes: string[]; data: number[][] } 
}> = ({ probabilities }) => {
  const chartData = probabilities.timeframes.map((tf, index) => ({
    timeframe: tf,
    SHORT: probabilities.data[index][0],
    NEUTRAL: probabilities.data[index][1],
    LONG: probabilities.data[index][2],
  }));

  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h3 className="text-lg font-semibold text-white mb-4">
        Direction Probabilities by Timeframe
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="timeframe" stroke="#9CA3AF" />
          <YAxis stroke="#9CA3AF" />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1F2937',
              border: '1px solid #374151',
              borderRadius: '8px',
              color: '#F9FAFB',
            }}
            formatter={(value: number) => [`${(value * 100).toFixed(1)}%`, '']}
          />
          <Legend />
          <Bar dataKey="SHORT" stackId="a" fill="#EF4444" />
          <Bar dataKey="NEUTRAL" stackId="a" fill="#F59E0B" />
          <Bar dataKey="LONG" stackId="a" fill="#10B981" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

const ReturnsChart: React.FC<{ 
  returns: { '15m': number; '1h': number; '4h': number; '12h': number } 
}> = ({ returns }) => {
  const chartData = Object.entries(returns).map(([timeframe, value]) => ({
    timeframe,
    return: value,
    isPositive: value >= 0
  }));

  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h3 className="text-lg font-semibold text-white mb-4">
        Predicted Returns by Timeframe
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="timeframe" stroke="#9CA3AF" />
          <YAxis 
            stroke="#9CA3AF" 
            tickFormatter={(value) => `${(value * 100).toFixed(2)}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1F2937',
              border: '1px solid #374151',
              borderRadius: '8px',
              color: '#F9FAFB',
            }}
            formatter={(value: number) => [`${(value * 100).toFixed(4)}%`, 'Return']}
          />
          <ReferenceLine y={0} stroke="#6B7280" strokeDasharray="2 2" />
          <Bar dataKey="return">
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.isPositive ? '#10B981' : '#EF4444'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

const RiskLevels: React.FC<{ 
  riskLevel: string; 
  stopLoss?: number; 
  takeProfit?: number; 
  currentPrice: number;
}> = ({ riskLevel, stopLoss, takeProfit, currentPrice }) => {
  const getRiskColor = () => {
    switch (riskLevel.toLowerCase()) {
      case 'low': return 'text-green-400 bg-green-600';
      case 'medium': return 'text-yellow-400 bg-yellow-600';
      case 'high': return 'text-red-400 bg-red-600';
      default: return 'text-gray-400 bg-gray-600';
    }
  };

  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
        <AlertCircle className="w-5 h-5 mr-2" />
        Risk Management
      </h3>
      
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-gray-400">Risk Level</span>
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${getRiskColor()}`}>
            {riskLevel.toUpperCase()}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center p-4 bg-gray-700 rounded-lg">
            <div className="text-sm text-gray-400 mb-1">Current Price</div>
            <div className="text-lg font-bold text-white">
              ${currentPrice.toLocaleString()}
            </div>
          </div>

          {stopLoss && (
            <div className="text-center p-4 bg-gray-700 rounded-lg">
              <div className="text-sm text-gray-400 mb-1">Stop Loss</div>
              <div className="text-lg font-bold text-red-400">
                ${stopLoss.toLocaleString()}
              </div>
              <div className="text-xs text-gray-500">
                {(((stopLoss - currentPrice) / currentPrice) * 100).toFixed(2)}%
              </div>
            </div>
          )}

          {takeProfit && (
            <div className="text-center p-4 bg-gray-700 rounded-lg">
              <div className="text-sm text-gray-400 mb-1">Take Profit</div>
              <div className="text-lg font-bold text-green-400">
                ${takeProfit.toLocaleString()}
              </div>
              <div className="text-xs text-gray-500">
                {(((takeProfit - currentPrice) / currentPrice) * 100).toFixed(2)}%
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const PredictionVisualization: React.FC<PredictionVisualizationProps> = ({
  data,
  selectedSymbol,
  onSymbolSelect
}) => {
  const [activeSymbol, setActiveSymbol] = useState(selectedSymbol || data[0]?.symbol);
  
  useEffect(() => {
    if (selectedSymbol) {
      setActiveSymbol(selectedSymbol);
    }
  }, [selectedSymbol]);

  const selectedPrediction = data.find(d => d.symbol === activeSymbol);

  if (!selectedPrediction) {
    return (
      <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 text-center">
        <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-white mb-2">No Data Available</h3>
        <p className="text-gray-400">No prediction data available for the selected symbol.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Symbol Selector */}
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
        <div className="flex flex-wrap gap-2">
          {data.map((prediction) => (
            <button
              key={prediction.symbol}
              onClick={() => {
                setActiveSymbol(prediction.symbol);
                onSymbolSelect?.(prediction.symbol);
              }}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                prediction.symbol === activeSymbol
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {prediction.symbol}
            </button>
          ))}
        </div>
      </div>

      {/* Current Prediction Overview */}
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">{selectedPrediction.symbol} Analysis</h2>
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-5 h-5 text-gray-400" />
            <span className="text-gray-400">Real-time ML Prediction</span>
          </div>
        </div>

        <SignalIndicator 
          signal={selectedPrediction.signalType}
          confidence={selectedPrediction.confidence}
          strength={selectedPrediction.strength}
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {selectedPrediction.predictions.probabilities && (
          <TimeframeProbabilities probabilities={selectedPrediction.predictions.probabilities} />
        )}

        {selectedPrediction.predictions.returns && (
          <ReturnsChart returns={selectedPrediction.predictions.returns} />
        )}
      </div>

      {/* Risk Management */}
      <RiskLevels
        riskLevel={selectedPrediction.riskLevel}
        stopLoss={selectedPrediction.stopLoss}
        takeProfit={selectedPrediction.takeProfit}
        currentPrice={selectedPrediction.currentPrice}
      />
    </div>
  );
};

export default PredictionVisualization;