// Типы для торговой системы BOT_Trading v3.0

export interface Trader {
  id: string
  name: string
  status: TraderStatus
  exchange: string
  symbol: string
  balance: number
  equity: number
  pnl: number
  pnl_percentage: number
  position?: Position
  strategy: string
  created_at: string
  last_activity: string
  config: TraderConfig
}

export interface Position {
  id: string
  trader_id: string
  symbol: string
  side: 'long' | 'short'
  size: number
  entry_price: number
  current_price: number
  unrealized_pnl: number
  realized_pnl: number
  leverage: number
  margin: number
  stop_loss?: number
  take_profit?: number
  created_at: string
  updated_at: string
}

export interface Order {
  id: string
  trader_id: string
  symbol: string
  side: 'buy' | 'sell'
  type: 'market' | 'limit' | 'stop' | 'stop_limit'
  status: OrderStatus
  quantity: number
  price?: number
  filled_quantity: number
  average_price?: number
  created_at: string
  updated_at: string
}

export interface TradeSignal {
  id: string
  symbol: string
  action: 'buy' | 'sell'
  price: number
  quantity?: number
  confidence: number
  ml_prediction?: MLPrediction
  indicators: Record<string, any>
  timestamp: string
  source: string
}

export interface MLPrediction {
  buy_profit_probability: number
  buy_loss_probability: number
  sell_profit_probability: number
  sell_loss_probability: number
  confidence_score: number
  model_version: string
}

export interface TraderConfig {
  max_position_size: number
  max_daily_loss: number
  risk_percentage: number
  leverage: number
  stop_loss_percentage: number
  take_profit_percentage: number
  enable_partial_close: boolean
  trailing_stop: boolean
}

export enum TraderStatus {
  ACTIVE = 'active',
  PAUSED = 'paused',
  STOPPED = 'stopped',
  ERROR = 'error'
}

export enum OrderStatus {
  PENDING = 'pending',
  FILLED = 'filled',
  PARTIALLY_FILLED = 'partially_filled',
  CANCELLED = 'cancelled',
  REJECTED = 'rejected'
}

export interface SystemStatus {
  status: 'running' | 'paused' | 'error'
  uptime: number
  traders_count: number
  active_positions: number
  total_pnl: number
  system_metrics: {
    memory_usage: number
    cpu_usage: number
    open_connections: number
    api_calls_per_minute: number
  }
}

export interface ExchangeInfo {
  name: string
  status: 'connected' | 'disconnected' | 'error'
  last_ping: number
  supported_symbols: string[]
  rate_limits: {
    requests_per_minute: number
    orders_per_minute: number
  }
}

// WebSocket события
export interface WebSocketEvent<T = any> {
  type: string
  data: T
  timestamp: number
}

export interface PriceUpdateEvent {
  symbol: string
  price: number
  change_24h: number
  volume_24h: number
  timestamp: number
}

export interface PositionUpdateEvent {
  trader_id: string
  position: Position
  timestamp: number
}

export interface OrderUpdateEvent {
  trader_id: string
  order: Order
  timestamp: number
}

export interface TraderStatusEvent {
  trader_id: string
  status: TraderStatus
  message?: string
  timestamp: number
}

// API Response типы
export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  timestamp: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  has_next: boolean
  has_prev: boolean
}

// Торговая статистика
export interface TradingStats {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_pnl: number
  average_win: number
  average_loss: number
  profit_factor: number
  max_drawdown: number
  sharpe_ratio: number
  period_start: string
  period_end: string
}

// Настройки интерфейса
export interface UISettings {
  theme: 'light' | 'dark' | 'system'
  refresh_interval: number
  show_notifications: boolean
  default_timeframe: string
  auto_scroll_logs: boolean
  chart_settings: {
    show_volume: boolean
    show_indicators: boolean
    chart_type: 'candlestick' | 'line' | 'area'
  }
}
