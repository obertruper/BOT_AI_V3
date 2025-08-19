import React from 'react';
import { TrendingUp } from 'lucide-react';

const Trading: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Trading Panel</h1>
          <p className="text-gray-400 mt-1">
            Manual trading controls and order management
          </p>
        </div>
      </div>

      <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 text-center">
        <TrendingUp className="w-16 h-16 text-green-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-white mb-2">Trading Panel</h3>
        <p className="text-gray-400">
          Advanced trading interface coming soon with manual order placement, position management, and real-time market data.
        </p>
      </div>
    </div>
  );
};

export default Trading;