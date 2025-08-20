import React, { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';
import SystemStatus from './status/SystemStatus';
import type { SystemStatus as SystemStatusType, SystemMetrics } from '../services/apiService';

export const StatusDashboard: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatusType | null>(null);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Загружаем данные каждые 5 секунд
  useEffect(() => {
    const fetchAllData = async () => {
      try {
        setError(null);
        
        // Загружаем системный статус
        const statusData = await apiService.getSystemStatus();
        setSystemStatus(statusData);
        
        // Загружаем метрики
        const metricsData = await apiService.getSystemMetrics();
        setMetrics(metricsData);
        
        setLastUpdate(new Date());
        setIsConnected(true);
      } catch (err) {
        console.error('Failed to fetch data:', err);
        setError('Failed to connect to API');
        setIsConnected(false);
      }
    };

    fetchAllData(); // Загружаем сразу
    const interval = setInterval(fetchAllData, 5000); // Каждые 5 секунд

    return () => clearInterval(interval);
  }, []);

  const reconnect = () => {
    setError(null);
    setIsConnected(false);
    // Данные обновятся автоматически через useEffect
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      backgroundColor: '#0d0d0d', 
      padding: '16px',
      color: 'white',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h1 style={{ fontSize: '30px', fontWeight: 'bold', margin: 0 }}>BOT_AI_V3 Status Dashboard</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ fontSize: '14px', color: '#9ca3af' }}>
              Last update: {lastUpdate.toLocaleTimeString()}
            </div>
            {error && (
              <button
                onClick={reconnect}
                style={{
                  padding: '4px 12px',
                  backgroundColor: '#dc2626',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  fontSize: '14px',
                  cursor: 'pointer'
                }}
              >
                Reconnect
              </button>
            )}
          </div>
        </div>
        {error && (
          <div style={{
            marginTop: '8px',
            padding: '12px',
            backgroundColor: '#7f1d1d',
            color: '#fca5a5',
            borderRadius: '6px'
          }}>
            ⚠️ {error}
          </div>
        )}
      </div>

      {/* Main Content */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '24px' }}>
        {/* System Status */}
        <SystemStatus status={systemStatus} isConnected={isConnected} />

        {/* Metrics Board */}
        <div style={{
          backgroundColor: '#1a1a1a',
          borderRadius: '8px',
          padding: '24px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
        }}>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '16px', margin: 0 }}>📊 System Metrics</h2>
          
          {metrics ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* CPU Usage */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '14px', color: '#d1d5db' }}>CPU Usage</span>
                  <span style={{ fontWeight: '600' }}>{metrics.cpu_usage.toFixed(1)}%</span>
                </div>
                <div style={{ width: '100%', backgroundColor: '#374151', borderRadius: '9999px', height: '8px' }}>
                  <div
                    style={{
                      height: '8px',
                      borderRadius: '9999px',
                      backgroundColor: metrics.cpu_usage >= 80 ? '#ef4444' : metrics.cpu_usage >= 60 ? '#f59e0b' : '#10b981',
                      width: `${metrics.cpu_usage}%`,
                      transition: 'all 0.3s'
                    }}
                  />
                </div>
              </div>

              {/* Memory Usage */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '14px', color: '#d1d5db' }}>Memory Usage</span>
                  <span style={{ fontWeight: '600' }}>{metrics.memory_usage.toFixed(1)}%</span>
                </div>
                <div style={{ width: '100%', backgroundColor: '#374151', borderRadius: '9999px', height: '8px' }}>
                  <div
                    style={{
                      height: '8px',
                      borderRadius: '9999px',
                      backgroundColor: metrics.memory_usage >= 80 ? '#ef4444' : metrics.memory_usage >= 60 ? '#f59e0b' : '#10b981',
                      width: `${metrics.memory_usage}%`,
                      transition: 'all 0.3s'
                    }}
                  />
                </div>
              </div>

              {/* Additional Stats */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '16px' }}>
                <div style={{ backgroundColor: '#374151', borderRadius: '6px', padding: '12px', textAlign: 'center' }}>
                  <div style={{ color: '#a855f7', fontWeight: 'bold', fontSize: '18px' }}>
                    {metrics.database_connections}
                  </div>
                  <div style={{ fontSize: '12px', color: '#9ca3af' }}>DB Connections</div>
                </div>
                <div style={{ backgroundColor: '#374151', borderRadius: '6px', padding: '12px', textAlign: 'center' }}>
                  <div style={{ color: '#f97316', fontWeight: 'bold', fontSize: '18px' }}>
                    {metrics.api_requests_per_minute}
                  </div>
                  <div style={{ fontSize: '12px', color: '#9ca3af' }}>API Req/Min</div>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: '#9ca3af' }}>
              Loading metrics...
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={{ marginTop: '32px', textAlign: 'center', color: '#6b7280', fontSize: '14px' }}>
        <p>BOT_AI_V3 Trading System • Real-time Status Monitor</p>
        <p style={{ marginTop: '4px' }}>
          {isConnected ? '🟢 Live Data' : '🔴 Cached Data'} • 
          Auto-refresh: 5s
        </p>
      </div>
    </div>
  );
};

export default StatusDashboard;
