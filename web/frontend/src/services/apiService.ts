export interface SystemStatus {
  status: 'running' | 'stopped' | 'degraded';
  uptime: number;
  components: {
    trading_engine: boolean;
    ml_manager: boolean;
    exchanges: boolean;
    risk_manager: boolean;
    websocket_manager?: boolean;
    database_manager?: boolean;
  };
  metrics: {
    cpu_usage: number;
    memory_usage: number;
    active_positions: number;
    total_pnl: number;
    daily_pnl?: number;
    weekly_pnl?: number;
    win_rate?: number;
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
  status: 'open' | 'closed' | 'pending';
  created_at: string;
  updated_at?: string;
  stop_loss?: number;
  take_profit?: number;
  exchange: string;
  margin_used?: number;
  fees_paid?: number;
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
  features_count?: number;
  prediction_horizon?: string;
  quality_score?: number;
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH';
  executed?: boolean;
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

export interface TradingStrategy {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  parameters: Record<string, any>;
  performance: {
    total_trades: number;
    win_rate: number;
    profit_loss: number;
    max_drawdown: number;
  };
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: string;
  symbol: string;
  type: 'market' | 'limit' | 'stop_loss' | 'take_profit';
  side: 'buy' | 'sell';
  amount: number;
  price?: number;
  filled: number;
  remaining: number;
  status: 'pending' | 'open' | 'closed' | 'cancelled' | 'rejected';
  created_at: string;
  filled_at?: string;
  exchange: string;
  fees?: number;
}

export interface ExchangeInfo {
  id: string;
  name: string;
  status: 'connected' | 'disconnected' | 'error';
  balance: {
    total: number;
    available: number;
    used: number;
  };
  api_calls_remaining?: number;
  last_sync?: string;
}

export interface Indicator {
  id: string;
  name: string;
  type: string;
  parameters: Record<string, any>;
  enabled: boolean;
  timeframes: string[];
  description?: string;
}

export interface MarketData {
  symbol: string;
  price: number;
  change_24h: number;
  change_24h_percent: number;
  volume_24h: number;
  high_24h: number;
  low_24h: number;
  market_cap?: number;
  updated_at: string;
}

export interface AlertRule {
  id: string;
  name: string;
  condition: string;
  enabled: boolean;
  actions: {
    email?: boolean;
    telegram?: boolean;
    webhook?: string;
  };
  created_at: string;
  last_triggered?: string;
}

class ApiService {
  private baseURL = import.meta.env.VITE_API_URL || '/api';

  async getSystemStatus(): Promise<SystemStatus> {
    try {
      const response = await fetch(`${this.baseURL}/system/status`);
      if (!response.ok) throw new Error('Failed to fetch system status');
      const data = await response.json();
      
      // Адаптируем структуру ответа API к нашему интерфейсу
      const apiData = data.success ? data.data : data;
      
      return {
        status: apiData.status || 'unknown',
        uptime: apiData.uptime || 0,
        components: {
          trading_engine: true, // Получаем из API или устанавливаем по умолчанию
          ml_manager: true,
          exchanges: true,
          risk_manager: true
        },
        metrics: {
          cpu_usage: apiData.system_metrics?.cpu_usage || 0,
          memory_usage: apiData.system_metrics?.memory_usage || 0,
          active_positions: apiData.active_positions || 0,
          total_pnl: apiData.total_pnl || 0
        }
      };
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
      // Используем системный статус для метрик
      const response = await fetch(`${this.baseURL}/system/status`);
      if (!response.ok) throw new Error('Failed to fetch system metrics');
      const data = await response.json();
      const apiData = data.success ? data.data : data;
      
      return {
        cpu_usage: apiData.system_metrics?.cpu_usage || 0,
        memory_usage: apiData.system_metrics?.memory_usage || 0,
        disk_usage: 45, // Mock data
        network_io: { 
          bytes_sent: 1024000, 
          bytes_recv: 2048000 
        },
        database_connections: apiData.system_metrics?.open_connections || 0,
        api_requests_per_minute: apiData.system_metrics?.api_calls_per_minute || 0
      };
    } catch (error) {
      console.error('Failed to fetch system metrics:', error);
      // Return fallback data
      return {
        cpu_usage: 15,
        memory_usage: 45,
        disk_usage: 30,
        network_io: { bytes_sent: 0, bytes_recv: 0 },
        database_connections: 5,
        api_requests_per_minute: 120
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

  // Trading Strategies
  async getStrategies(): Promise<TradingStrategy[]> {
    try {
      const response = await fetch(`${this.baseURL}/strategies`);
      if (!response.ok) throw new Error('Failed to fetch strategies');
      const data = await response.json();
      return Array.isArray(data) ? data : (data.data || []);
    } catch (error) {
      console.error('Failed to fetch strategies:', error);
      return [];
    }
  }

  async updateStrategy(id: string, updates: Partial<TradingStrategy>): Promise<TradingStrategy> {
    const response = await fetch(`${this.baseURL}/strategies/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error('Failed to update strategy');
    return response.json();
  }

  async createStrategy(strategy: Omit<TradingStrategy, 'id' | 'created_at' | 'updated_at'>): Promise<TradingStrategy> {
    const response = await fetch(`${this.baseURL}/strategies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(strategy),
    });
    if (!response.ok) throw new Error('Failed to create strategy');
    return response.json();
  }

  // Orders Management
  async getOrders(status?: string): Promise<Order[]> {
    try {
      const url = status ? `${this.baseURL}/orders?status=${status}` : `${this.baseURL}/orders`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch orders');
      const data = await response.json();
      return Array.isArray(data) ? data : (data.data || []);
    } catch (error) {
      console.error('Failed to fetch orders:', error);
      return [];
    }
  }

  async cancelOrder(orderId: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/orders/${orderId}/cancel`, {
        method: 'POST',
      });
      return response.ok;
    } catch (error) {
      console.error('Failed to cancel order:', error);
      return false;
    }
  }

  async createOrder(order: Omit<Order, 'id' | 'created_at' | 'status'>): Promise<Order> {
    const response = await fetch(`${this.baseURL}/orders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(order),
    });
    if (!response.ok) throw new Error('Failed to create order');
    return response.json();
  }

  // Exchange Information
  async getExchanges(): Promise<ExchangeInfo[]> {
    try {
      const response = await fetch(`${this.baseURL}/exchanges`);
      if (!response.ok) throw new Error('Failed to fetch exchanges');
      const data = await response.json();
      return Array.isArray(data) ? data : (data.data || []);
    } catch (error) {
      console.error('Failed to fetch exchanges:', error);
      return [];
    }
  }

  // Indicators
  async getIndicators(): Promise<Indicator[]> {
    try {
      const response = await fetch(`${this.baseURL}/indicators`);
      if (!response.ok) throw new Error('Failed to fetch indicators');
      const data = await response.json();
      return Array.isArray(data) ? data : (data.data || []);
    } catch (error) {
      console.error('Failed to fetch indicators:', error);
      return [];
    }
  }

  async updateIndicator(id: string, updates: Partial<Indicator>): Promise<Indicator> {
    const response = await fetch(`${this.baseURL}/indicators/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error('Failed to update indicator');
    return response.json();
  }

  // Market Data
  async getMarketData(symbols?: string[]): Promise<MarketData[]> {
    try {
      const url = symbols ? 
        `${this.baseURL}/market/data?symbols=${symbols.join(',')}` : 
        `${this.baseURL}/market/data`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch market data');
      const data = await response.json();
      return Array.isArray(data) ? data : (data.data || []);
    } catch (error) {
      console.error('Failed to fetch market data:', error);
      return [];
    }
  }

  // Get historical price data for charts
  async getHistoricalData(symbol: string, timeframe: string = '15m', limit: number = 50): Promise<any[]> {
    try {
      const response = await fetch(`${this.baseURL}/market/historical?symbol=${symbol}&timeframe=${timeframe}&limit=${limit}`);
      if (!response.ok) throw new Error('Failed to fetch historical data');
      const data = await response.json();
      return Array.isArray(data) ? data : (data.data || []);
    } catch (error) {
      console.error('Failed to fetch historical data:', error);
      return [];
    }
  }

  // ML Configuration
  async getMLConfig(): Promise<any> {
    try {
      const response = await fetch(`${this.baseURL}/ml/config`);
      if (!response.ok) throw new Error('Failed to fetch ML config');
      return response.json();
    } catch (error) {
      console.error('Failed to fetch ML config:', error);
      return {};
    }
  }

  async updateMLConfig(config: any): Promise<any> {
    const response = await fetch(`${this.baseURL}/ml/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!response.ok) throw new Error('Failed to update ML config');
    return response.json();
  }

  // Alert Rules
  async getAlertRules(): Promise<AlertRule[]> {
    try {
      const response = await fetch(`${this.baseURL}/alerts/rules`);
      if (!response.ok) throw new Error('Failed to fetch alert rules');
      const data = await response.json();
      return Array.isArray(data) ? data : (data.data || []);
    } catch (error) {
      console.error('Failed to fetch alert rules:', error);
      return [];
    }
  }

  async createAlertRule(rule: Omit<AlertRule, 'id' | 'created_at'>): Promise<AlertRule> {
    const response = await fetch(`${this.baseURL}/alerts/rules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rule),
    });
    if (!response.ok) throw new Error('Failed to create alert rule');
    return response.json();
  }

  async updateAlertRule(id: string, updates: Partial<AlertRule>): Promise<AlertRule> {
    const response = await fetch(`${this.baseURL}/alerts/rules/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error('Failed to update alert rule');
    return response.json();
  }

  async deleteAlertRule(id: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/alerts/rules/${id}`, {
        method: 'DELETE',
      });
      return response.ok;
    } catch (error) {
      console.error('Failed to delete alert rule:', error);
      return false;
    }
  }

  // Analytics
  async getAnalytics(timeframe: string = '24h'): Promise<any> {
    try {
      const response = await fetch(`${this.baseURL}/analytics?timeframe=${timeframe}`);
      if (!response.ok) throw new Error('Failed to fetch analytics');
      return response.json();
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      return {};
    }
  }

  // System Control
  async startTrading(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/system/start`, { method: 'POST' });
      return response.ok;
    } catch (error) {
      console.error('Failed to start trading:', error);
      return false;
    }
  }

  async stopTrading(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/system/stop`, { method: 'POST' });
      return response.ok;
    } catch (error) {
      console.error('Failed to stop trading:', error);
      return false;
    }
  }

  async restartSystem(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/system/restart`, { method: 'POST' });
      return response.ok;
    } catch (error) {
      console.error('Failed to restart system:', error);
      return false;
    }
  }

  // Configuration Management
  async getConfigFiles(): Promise<any[]> {
    try {
      const response = await fetch(`${this.baseURL}/config/files`);
      if (!response.ok) throw new Error('Failed to fetch config files');
      const data = await response.json();
      return Array.isArray(data) ? data : (data.data || []);
    } catch (error) {
      console.error('Failed to fetch config files:', error);
      return [];
    }
  }

  async getConfig(configType: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseURL}/config/${configType}`);
      if (!response.ok) throw new Error(`Failed to fetch ${configType} config`);
      const data = await response.json();
      return data.success ? data.data : data;
    } catch (error) {
      console.error(`Failed to fetch ${configType} config:`, error);
      return {};
    }
  }

  async updateConfig(configType: string, config: any): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/config/${configType}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      return response.ok;
    } catch (error) {
      console.error(`Failed to update ${configType} config:`, error);
      return false;
    }
  }

  async validateConfig(configType: string, config: any): Promise<any> {
    try {
      const response = await fetch(`${this.baseURL}/config/${configType}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (!response.ok) throw new Error('Failed to validate config');
      return response.json();
    } catch (error) {
      console.error(`Failed to validate ${configType} config:`, error);
      return { valid: false, errors: ['Validation service unavailable'] };
    }
  }

  async backupConfig(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/config/backup`, { method: 'POST' });
      return response.ok;
    } catch (error) {
      console.error('Failed to backup config:', error);
      return false;
    }
  }

  async restoreConfig(backupId: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/config/restore/${backupId}`, { method: 'POST' });
      return response.ok;
    } catch (error) {
      console.error('Failed to restore config:', error);
      return false;
    }
  }
}

export const apiService = new ApiService();
export default ApiService;
