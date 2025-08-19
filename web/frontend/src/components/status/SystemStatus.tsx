import React from 'react';
import { SystemStatus as SystemStatusType } from '../../services/apiService';

interface SystemStatusProps {
  status: SystemStatusType | null;
  isConnected: boolean;
}

export const SystemStatus: React.FC<SystemStatusProps> = ({ status, isConnected }) => {
  const getStatusColor = (systemStatus: string) => {
    switch (systemStatus) {
      case 'running':
        return 'text-green-500';
      case 'degraded':
        return 'text-yellow-500';
      case 'stopped':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusIcon = (systemStatus: string) => {
    switch (systemStatus) {
      case 'running':
        return '🟢';
      case 'degraded':
        return '🟡';
      case 'stopped':
        return '🔴';
      default:
        return '⚪';
    }
  };

  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  if (!status) {
    return (
      <div style={{
        backgroundColor: '#1a1a1a',
        borderRadius: '8px',
        padding: '24px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        color: 'white'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: 0 }}>System Status</h2>
          <div style={{ fontSize: '14px', color: isConnected ? '#4ade80' : '#ef4444' }}>
            {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </div>
        </div>
        <div style={{ textAlign: 'center', color: '#9ca3af' }}>
          Loading system status...
        </div>
      </div>
    );
  }

  return (
    <div style={{
      backgroundColor: '#1a1a1a',
      borderRadius: '8px',
      padding: '24px',
      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
      color: 'white'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: 0 }}>System Status</h2>
        <div style={{ fontSize: '14px', color: isConnected ? '#4ade80' : '#ef4444' }}>
          {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </div>
      </div>
      
      {/* Main Status */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '24px' }}>
        <span style={{ fontSize: '24px', marginRight: '12px' }}>{getStatusIcon(status.status)}</span>
        <div>
          <div style={{ fontSize: '18px', fontWeight: '600', color: getStatusColor(status.status) === 'text-green-500' ? '#10b981' : getStatusColor(status.status) === 'text-yellow-500' ? '#f59e0b' : '#ef4444' }}>
            {status.status.toUpperCase()}
          </div>
          <div style={{ fontSize: '14px', color: '#9ca3af' }}>
            Uptime: {formatUptime(status.uptime)}
          </div>
        </div>
      </div>

      {/* Components Status */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
        <div style={{ backgroundColor: '#374151', borderRadius: '6px', padding: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '14px', color: '#d1d5db' }}>Trading Engine</span>
            <span style={{ color: status.components?.trading_engine ? '#10b981' : '#ef4444' }}>
              {status.components?.trading_engine ? '✅' : '❌'}
            </span>
          </div>
        </div>
        
        <div style={{ backgroundColor: '#374151', borderRadius: '6px', padding: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '14px', color: '#d1d5db' }}>ML Manager</span>
            <span style={{ color: status.components?.ml_manager ? '#10b981' : '#ef4444' }}>
              {status.components?.ml_manager ? '✅' : '❌'}
            </span>
          </div>
        </div>
        
        <div style={{ backgroundColor: '#374151', borderRadius: '6px', padding: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '14px', color: '#d1d5db' }}>Exchanges</span>
            <span style={{ color: status.components?.exchanges ? '#10b981' : '#ef4444' }}>
              {status.components?.exchanges ? '✅' : '❌'}
            </span>
          </div>
        </div>
        
        <div style={{ backgroundColor: '#374151', borderRadius: '6px', padding: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '14px', color: '#d1d5db' }}>Risk Manager</span>
            <span style={{ color: status.components?.risk_manager ? '#10b981' : '#ef4444' }}>
              {status.components?.risk_manager ? '✅' : '❌'}
            </span>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#3b82f6' }}>{status.metrics?.active_positions || 0}</div>
          <div style={{ fontSize: '12px', color: '#9ca3af' }}>Active Positions</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: (status.metrics?.total_pnl || 0) >= 0 ? '#10b981' : '#ef4444' }}>
            ${(status.metrics?.total_pnl || 0).toFixed(2)}
          </div>
          <div style={{ fontSize: '12px', color: '#9ca3af' }}>Total PnL</div>
        </div>
      </div>
    </div>
  );
};

export default SystemStatus;
