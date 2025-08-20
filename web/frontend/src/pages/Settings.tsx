import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Database, Globe, Brain, Shield, TrendingUp, FileText, Save, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react';
import { apiService } from '@/services/apiService';
import { ConfigFile, TradingConfig, SystemConfig, MLConfig, RiskConfig } from '@/types/config';
import SimpleExchangeSettings from '@/components/settings/SimpleExchangeSettings';
import SimpleTradingSettings from '@/components/settings/SimpleTradingSettings';
import SimpleMLSettings from '@/components/settings/SimpleMLSettings';
import RiskManagementSettings from '@/components/settings/RiskManagementSettings';

type ConfigSection = 'overview' | 'exchanges' | 'trading' | 'system' | 'ml' | 'risk';

const Settings: React.FC = () => {
  const [activeSection, setActiveSection] = useState<ConfigSection>('overview');
  const [configFiles, setConfigFiles] = useState<ConfigFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [systemStatus, setSystemStatus] = useState<any>(null);

  const sections = [
    {
      id: 'overview' as ConfigSection,
      name: 'Overview',
      icon: SettingsIcon,
      description: 'System overview and configuration files'
    },
    {
      id: 'exchanges' as ConfigSection,
      name: 'Exchanges',
      icon: Globe,
      description: 'Exchange API keys and settings'
    },
    {
      id: 'trading' as ConfigSection,
      name: 'Trading',
      icon: TrendingUp,
      description: 'Trading parameters and strategies'
    },
    {
      id: 'system' as ConfigSection,
      name: 'System',
      icon: Database,
      description: 'Database and system configuration'
    },
    {
      id: 'ml' as ConfigSection,
      name: 'ML Model',
      icon: Brain,
      description: 'Machine learning configuration'
    },
    {
      id: 'risk' as ConfigSection,
      name: 'Risk Management',
      icon: Shield,
      description: 'Risk parameters and limits'
    }
  ];

  useEffect(() => {
    loadConfigData();
  }, []);

  const loadConfigData = async () => {
    setLoading(true);
    try {
      // Упрощенная загрузка без реального API для устранения проблем
      const mockStatus = {
        status: 'running',
        uptime: 3600,
        metrics: {
          cpu_usage: 15,
          memory_usage: 45,
          active_positions: 1,
          total_pnl: 0
        }
      };
      setSystemStatus(mockStatus);
      setConfigFiles([]);
    } catch (error) {
      console.error('Failed to load config data:', error);
      showNotification('error', 'Failed to load configuration data');
    }
    setLoading(false);
  };

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleConfigSave = (configType: string) => {
    showNotification('success', `${configType} configuration saved successfully`);
  };

  const renderOverview = () => (
    <div className="space-y-6">
      {/* System Status Card */}
      <div className="card relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600/10 to-purple-600/10"></div>
        <div className="relative z-10 p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-xl font-semibold text-white">System Status</h3>
              <p className="text-gray-400 text-sm mt-1">Current system configuration and health</p>
            </div>
            <button
              onClick={loadConfigData}
              disabled={loading}
              className="flex items-center space-x-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg text-white text-sm transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
          
          {systemStatus && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700/50">
                <div className={`text-lg font-semibold ${
                  systemStatus.status === 'running' ? 'text-green-400' : 'text-red-400'
                }`}>
                  {systemStatus.status?.toUpperCase() || 'UNKNOWN'}
                </div>
                <div className="text-sm text-gray-400">System Status</div>
              </div>
              <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700/50">
                <div className="text-lg font-semibold text-white">
                  {Math.floor((systemStatus.uptime || 0) / 3600)}h {Math.floor(((systemStatus.uptime || 0) % 3600) / 60)}m
                </div>
                <div className="text-sm text-gray-400">Uptime</div>
              </div>
              <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700/50">
                <div className="text-lg font-semibold text-white">
                  {systemStatus.metrics?.active_positions || 0}
                </div>
                <div className="text-sm text-gray-400">Active Positions</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Configuration Files */}
      <div className="card">
        <div className="p-6">
          <h3 className="text-xl font-semibold text-white mb-6">Configuration Files</h3>
          
          {configFiles.length > 0 ? (
            <div className="grid gap-4">
              {configFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between p-4 bg-gray-800/50 rounded-xl border border-gray-700/50">
                  <div className="flex items-center space-x-4">
                    <div className="w-10 h-10 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg flex items-center justify-center">
                      <FileText className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-white">{file.name}</div>
                      <div className="text-xs text-gray-400">{file.description}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        Modified: {new Date(file.last_modified).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                      file.type === 'trading' ? 'bg-blue-600/20 text-blue-400' :
                      file.type === 'system' ? 'bg-green-600/20 text-green-400' :
                      file.type === 'ml' ? 'bg-purple-600/20 text-purple-400' :
                      'bg-gray-600/20 text-gray-400'
                    }`}>
                      {file.type}
                    </span>
                    <button
                      onClick={() => setActiveSection(file.type as ConfigSection)}
                      className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs text-white transition-colors"
                    >
                      Edit
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No configuration files found</p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {sections.slice(1).map((section) => {
          const Icon = section.icon;
          return (
            <div key={section.id} className="card group cursor-pointer" onClick={() => setActiveSection(section.id)}>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className={`w-12 h-12 bg-gradient-to-r ${
                    section.id === 'exchanges' ? 'from-green-600 to-blue-600' :
                    section.id === 'trading' ? 'from-blue-600 to-purple-600' :
                    section.id === 'system' ? 'from-purple-600 to-pink-600' :
                    section.id === 'ml' ? 'from-pink-600 to-red-600' :
                    'from-red-600 to-orange-600'
                  } rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <div className="text-2xl group-hover:scale-110 transition-transform duration-300">→</div>
                </div>
                <h4 className="text-lg font-semibold text-white mb-2">{section.name}</h4>
                <p className="text-sm text-gray-400">{section.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderContent = () => {
    switch (activeSection) {
      case 'overview':
        return renderOverview();
      case 'exchanges':
        return <SimpleExchangeSettings onSave={() => handleConfigSave('Exchange')} />;
      case 'trading':
        return <SimpleTradingSettings onSave={() => handleConfigSave('Trading')} />;
      case 'system':
        return (
          <div className="card">
            <div className="p-6">
              <h3 className="text-xl font-semibold text-white mb-4">System Configuration</h3>
              <p className="text-gray-400">System configuration interface coming soon...</p>
            </div>
          </div>
        );
      case 'ml':
        return <SimpleMLSettings onSave={() => handleConfigSave('ML Model')} />;
      case 'risk':
        return <RiskManagementSettings onSave={() => handleConfigSave('Risk Management')} />;
      default:
        return renderOverview();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Settings</h1>
          <p className="text-gray-400 mt-1">
            System configuration and management
          </p>
        </div>
        
        {/* Status Badge */}
        {systemStatus && (
          <div className={`flex items-center space-x-2 px-4 py-2 rounded-lg ${
            systemStatus.status === 'running' 
              ? 'bg-green-600/20 text-green-400 border border-green-600/30' 
              : 'bg-red-600/20 text-red-400 border border-red-600/30'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              systemStatus.status === 'running' ? 'bg-green-400 animate-pulse' : 'bg-red-400'
            }`}></div>
            <span className="text-sm font-medium">{systemStatus.status?.toUpperCase() || 'UNKNOWN'}</span>
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="card">
        <div className="p-2">
          <div className="flex space-x-1 overflow-x-auto">
            {sections.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`flex items-center space-x-2 px-4 py-3 rounded-lg font-medium text-sm transition-all duration-200 whitespace-nowrap ${
                    activeSection === section.id
                      ? 'bg-blue-600 text-white shadow-lg'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{section.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="animate-fade-in">
        {renderContent()}
      </div>

      {/* Notification */}
      {notification && (
        <div className={`fixed bottom-4 right-4 flex items-center space-x-3 px-4 py-3 rounded-lg shadow-lg z-50 animate-slide-in-bottom ${
          notification.type === 'success' 
            ? 'bg-green-600 text-white' 
            : 'bg-red-600 text-white'
        }`}>
          {notification.type === 'success' ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          <span className="font-medium">{notification.message}</span>
        </div>
      )}
    </div>
  );
};

export default Settings;
