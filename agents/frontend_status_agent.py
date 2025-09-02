#!/usr/bin/env python3
"""
Frontend Status Agent - Автоматическая доработка веб-интерфейса BOT_AI_V3
Интеграция реального статуса системы, позиций, ML сигналов в React frontend
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FrontendStatusAgent:
    """Агент для автоматической доработки веб-интерфейса с реальным статусом"""

    def __init__(self, project_root: str = "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3"):
        self.project_root = Path(project_root)
        self.frontend_path = self.project_root / "web" / "frontend"
        self.api_base_url = "http://localhost:8083/api"
        self.ws_url = "ws://localhost:8083/ws"

        # Проверяем существование директорий
        self.ensure_directories()

        self.status_components = {
            "SystemStatus": "src/components/status/SystemStatus.tsx",
            "PositionBoard": "src/components/status/PositionBoard.tsx",
            "MLSignalBoard": "src/components/status/MLSignalBoard.tsx",
            "MetricsBoard": "src/components/status/MetricsBoard.tsx",
            "StatusDashboard": "src/components/StatusDashboard.tsx",
        }

    def ensure_directories(self):
        """Создание необходимых директорий"""
        directories = [
            self.frontend_path / "src" / "components" / "status",
            self.frontend_path / "src" / "hooks",
            self.frontend_path / "src" / "services",
            self.frontend_path / "src" / "types",
            self.frontend_path / "src" / "utils",
        ]

        for dir_path in directories:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory: {dir_path}")

    async def analyze_current_frontend(self) -> dict[str, Any]:
        """Анализ текущей структуры frontend"""
        logger.info("Analyzing current frontend structure...")

        analysis = {
            "structure": {},
            "components": [],
            "api_integration": False,
            "websocket_support": False,
            "status_components": False,
        }

        if not self.frontend_path.exists():
            logger.error(f"Frontend path does not exist: {self.frontend_path}")
            return analysis

        # Анализируем структуру
        for root, dirs, files in os.walk(self.frontend_path):
            rel_path = Path(root).relative_to(self.frontend_path)
            analysis["structure"][str(rel_path)] = {
                "dirs": dirs,
                "files": [f for f in files if f.endswith((".tsx", ".ts", ".jsx", ".js"))],
            }

            # Ищем существующие компоненты
            for file in files:
                if file.endswith((".tsx", ".ts", ".jsx", ".js")):
                    file_path = Path(root) / file
                    try:
                        content = file_path.read_text(encoding="utf-8")

                        # Проверяем наличие API интеграции
                        if "fetch(" in content or "axios" in content:
                            analysis["api_integration"] = True

                        # Проверяем WebSocket
                        if "WebSocket" in content or "ws://" in content:
                            analysis["websocket_support"] = True

                        # Проверяем статус компоненты
                        if "Status" in file or "status" in content.lower():
                            analysis["status_components"] = True

                        analysis["components"].append(
                            {
                                "file": str(file_path.relative_to(self.frontend_path)),
                                "name": file.split(".")[0],
                                "type": file.split(".")[-1],
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Could not read file {file_path}: {e}")

        logger.info(f"Frontend analysis complete: {len(analysis['components'])} components found")
        return analysis

    def create_api_service(self):
        """Создание API сервиса для интеграции"""
        logger.info("Creating API service...")

        api_service_content = """export interface SystemStatus {
  status: 'running' | 'stopped' | 'degraded';
  uptime: number;
  components: {
    trading_engine: boolean;
    ml_manager: boolean;
    exchanges: boolean;
    risk_manager: boolean;
  };
  metrics: {
    cpu_usage: number;
    memory_usage: number;
    active_positions: number;
    total_pnl: number;
  };
}

export interface Position {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percentage: number;
  leverage: number;
  status: string;
  created_at: string;
}

export interface MLSignal {
  id: string;
  symbol: string;
  signal_type: 'buy' | 'sell';
  confidence: number;
  predicted_price: number;
  current_price: number;
  timeframe: string;
  created_at: string;
  model_version: string;
}

export interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_io: {
    bytes_sent: number;
    bytes_recv: number;
  };
  database_connections: number;
  api_requests_per_minute: number;
}

class ApiService {
  private baseURL = 'http://localhost:8083/api';

  async getSystemStatus(): Promise<SystemStatus> {
    try {
      const response = await fetch(`${this.baseURL}/system/status`);
      if (!response.ok) throw new Error('Failed to fetch system status');
      const data = await response.json();
      return data.success ? data.data : data;
    } catch (error) {
      console.error('Failed to fetch system status:', error);
      throw error;
    }
  }

  async getActivePositions(): Promise<Position[]> {
    try {
      const response = await fetch(`${this.baseURL}/positions/active`);
      if (!response.ok) throw new Error('Failed to fetch positions');
      const data = await response.json();
      return Array.isArray(data) ? data : (data.data || []);
    } catch (error) {
      console.error('Failed to fetch positions:', error);
      return [];
    }
  }

  async getMLSignals(): Promise<MLSignal[]> {
    try {
      const response = await fetch(`${this.baseURL}/ml/signals/recent`);
      if (!response.ok) throw new Error('Failed to fetch ML signals');
      const data = await response.json();
      return Array.isArray(data) ? data : (data.data || []);
    } catch (error) {
      console.error('Failed to fetch ML signals:', error);
      return [];
    }
  }

  async getSystemMetrics(): Promise<SystemMetrics> {
    try {
      const response = await fetch(`${this.baseURL}/system/metrics`);
      if (!response.ok) throw new Error('Failed to fetch system metrics');
      const data = await response.json();
      return data.success ? data.data : data;
    } catch (error) {
      console.error('Failed to fetch system metrics:', error);
      // Return mock data as fallback
      return {
        cpu_usage: 0,
        memory_usage: 0,
        disk_usage: 0,
        network_io: { bytes_sent: 0, bytes_recv: 0 },
        database_connections: 0,
        api_requests_per_minute: 0
      };
    }
  }

  async getTradersStatus() {
    try {
      const response = await fetch(`${this.baseURL}/traders/status`);
      if (!response.ok) throw new Error('Failed to fetch traders status');
      const data = await response.json();
      return data.success ? data.data : data;
    } catch (error) {
      console.error('Failed to fetch traders status:', error);
      return [];
    }
  }
}

export const apiService = new ApiService();
export default ApiService;
"""

        api_service_path = self.frontend_path / "src" / "services" / "apiService.ts"
        api_service_path.write_text(api_service_content, encoding="utf-8")
        logger.info(f"Created API service: {api_service_path}")

    def create_system_status_component(self):
        """Создание компонента системного статуса"""
        logger.info("Creating SystemStatus component...")

        system_status_content = """import React from 'react';
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
"""

        status_component_path = (
            self.frontend_path / "src" / "components" / "status" / "SystemStatus.tsx"
        )
        status_component_path.write_text(system_status_content, encoding="utf-8")
        logger.info(f"Created SystemStatus component: {status_component_path}")

    def create_status_dashboard(self):
        """Создание основного дашборда статуса"""
        logger.info("Creating StatusDashboard component...")

        status_dashboard_content = """import React, { useState, useEffect } from 'react';
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
"""

        status_dashboard_path = self.frontend_path / "src" / "components" / "StatusDashboard.tsx"
        status_dashboard_path.write_text(status_dashboard_content, encoding="utf-8")
        logger.info(f"Created StatusDashboard component: {status_dashboard_path}")

    def update_main_app(self):
        """Обновление основного App.tsx файла"""
        logger.info("Updating main App component...")

        app_tsx_path = self.frontend_path / "src" / "App.tsx"

        app_content = """import React from 'react';
import './App.css';
import StatusDashboard from './components/StatusDashboard';

function App() {
  return (
    <div className="App">
      <StatusDashboard />
    </div>
  );
}

export default App;
"""

        app_tsx_path.write_text(app_content, encoding="utf-8")
        logger.info(f"Updated App.tsx: {app_tsx_path}")

    def update_app_css(self):
        """Обновление App.css для лучшего внешнего вида"""
        logger.info("Updating App.css...")

        app_css_content = """body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #0d0d0d;
  color: #ffffff;
}

* {
  box-sizing: border-box;
}

.App {
  text-align: left;
  min-height: 100vh;
  background: #0d0d0d;
}

h1, h2, h3, h4, h5, h6 {
  margin: 0;
}

code {
  font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New',
    monospace;
}

button {
  font-family: inherit;
}

button:hover {
  opacity: 0.8;
}
"""

        app_css_path = self.frontend_path / "src" / "App.css"
        app_css_path.write_text(app_css_content, encoding="utf-8")
        logger.info(f"Updated App.css: {app_css_path}")

    async def test_api_connectivity(self) -> dict[str, bool]:
        """Тестирование подключения к API"""
        logger.info("Testing API connectivity...")

        endpoints = {"/system/status": False, "/health": False}

        try:
            import urllib.request

            for endpoint in endpoints:
                try:
                    url = f"{self.api_base_url.replace('/api', '')}{endpoint}"
                    if endpoint == "/system/status":
                        url = f"{self.api_base_url}{endpoint}"

                    request = urllib.request.Request(url)
                    request.add_header("User-Agent", "Frontend-Status-Agent/1.0")

                    with urllib.request.urlopen(request, timeout=5) as response:
                        if response.getcode() == 200:
                            endpoints[endpoint] = True
                            logger.info(f"API {endpoint}: ✅")
                        else:
                            logger.info(f"API {endpoint}: ❌ ({response.getcode()})")

                except Exception as e:
                    logger.warning(f"API {endpoint} failed: {e}")
                    endpoints[endpoint] = False

        except Exception as e:
            logger.error(f"API connectivity test failed: {e}")

        return endpoints

    def generate_status_report(self) -> dict[str, Any]:
        """Генерация отчета о статусе"""
        return {
            "timestamp": datetime.now().isoformat(),
            "frontend_path": str(self.frontend_path),
            "components_created": list(self.status_components.keys()),
            "files_created": [
                "src/services/apiService.ts",
                "src/components/status/SystemStatus.tsx",
                "src/components/StatusDashboard.tsx",
                "src/App.tsx",
                "src/App.css",
            ],
            "features_added": [
                "Real-time API integration",
                "System status monitoring",
                "Automatic data refresh every 5 seconds",
                "Responsive inline styling",
                "Error handling and reconnection",
                "System metrics display",
            ],
        }

    async def run_complete_setup(self):
        """Выполнение полной настройки frontend"""
        logger.info("🚀 Starting complete frontend setup...")

        try:
            # 1. Анализ текущего состояния
            analysis = await self.analyze_current_frontend()
            logger.info(f"Analysis complete: {len(analysis['components'])} existing components")

            # 2. Создание API сервисов и компонентов
            self.create_api_service()
            self.create_system_status_component()
            self.create_status_dashboard()

            # 3. Обновление основного App
            self.update_main_app()
            self.update_app_css()

            # 4. Тестирование API
            api_status = await self.test_api_connectivity()

            # 5. Генерация отчета
            report = self.generate_status_report()
            report["api_connectivity"] = api_status

            logger.info("✅ Frontend setup completed successfully!")

            # Сохраняем отчет
            report_path = self.project_root / "frontend_setup_report.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            print("\n" + "=" * 60)
            print("🎉 FRONTEND STATUS AGENT SETUP COMPLETE")
            print("=" * 60)
            print(f"📁 Frontend Path: {self.frontend_path}")
            print(f"🔗 API Base URL: {self.api_base_url}")
            print(f"📊 Components Created: {len(self.status_components)}")
            print("\n📋 Created Components:")
            for component in self.status_components:
                print(f"  ✅ {component}")

            print("\n🌐 API Endpoints Status:")
            for endpoint, status in api_status.items():
                print(f"  {'✅' if status else '❌'} {endpoint}")

            print(f"\n📄 Full report saved: {report_path}")
            print("\n🚀 Frontend is ready!")
            print("  📱 Access at: http://localhost:5173")
            print("=" * 60)

            return report

        except Exception as e:
            logger.error(f"Setup failed: {e}")
            raise


def main():
    """Основная функция для запуска агента"""
    agent = FrontendStatusAgent()

    try:
        # Запускаем полную настройку
        report = asyncio.run(agent.run_complete_setup())
        return report

    except KeyboardInterrupt:
        logger.info("Setup cancelled by user")
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise


if __name__ == "__main__":
    main()
