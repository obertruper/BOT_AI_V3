import React from 'react';
import { BarChart3 } from 'lucide-react';

const Charts: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Market Charts</h1>
          <p className="text-gray-400 mt-1">
            Advanced charting and technical analysis tools
          </p>
        </div>
      </div>

      <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 text-center">
        <BarChart3 className="w-16 h-16 text-purple-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-white mb-2">Advanced Charts</h3>
        <p className="text-gray-400">
          Interactive charts with technical indicators, drawing tools, and multi-timeframe analysis coming soon.
        </p>
      </div>
    </div>
  );
};

export default Charts;