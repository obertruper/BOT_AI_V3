import React from 'react';

const Settings: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Settings</h1>
          <p className="text-gray-400 mt-1">
            Settings management and configuration
          </p>
        </div>
      </div>

      <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 text-center">
        <h3 className="text-xl font-semibold text-white mb-2">Settings</h3>
        <p className="text-gray-400">
          Settings interface coming soon.
        </p>
      </div>
    </div>
  );
};

export default Settings;
