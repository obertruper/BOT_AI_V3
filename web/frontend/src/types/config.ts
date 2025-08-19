// Configuration types for settings management

export interface TradingConfig {
  trading_enabled: boolean;
  exchanges: {
    [key: string]: {
      enabled: boolean;
      api_key?: string;
      api_secret?: string;
      sandbox?: boolean;
      rate_limit?: number;
    };
  };
  risk_management: {
    max_position_size: number;
    max_daily_loss: number;
    max_drawdown: number;
    stop_loss_percentage: number;
    take_profit_percentage: number;
    leverage: number;
  };
  position_management: {
    max_open_positions: number;
    position_size_usd: number;
    min_balance_threshold: number;
  };
}

export interface SystemConfig {
  system_name: string;
  debug: boolean;
  log_level: string;
  database: {
    host: string;
    port: number;
    name: string;
    user: string;
  };
  api: {
    host: string;
    port: number;
    cors_origins: string[];
  };
  redis: {
    host: string;
    port: number;
    db: number;
  };
  monitoring: {
    prometheus_enabled: boolean;
    prometheus_port: number;
    grafana_enabled: boolean;
  };
}

export interface MLConfig {
  model: {
    name: string;
    version: string;
    input_features: number;
    prediction_horizon: number;
    confidence_threshold: number;
  };
  training: {
    batch_size: number;
    learning_rate: number;
    epochs: number;
    validation_split: number;
  };
  inference: {
    update_interval: number;
    cache_ttl: number;
    gpu_enabled: boolean;
  };
  features: {
    technical_indicators: number;
    market_features: number;
    sentiment_features: number;
  };
}

export interface RiskConfig {
  global_settings: {
    max_risk_per_trade: number;
    max_portfolio_risk: number;
    max_correlation: number;
    volatility_limit: number;
  };
  position_sizing: {
    kelly_criterion: boolean;
    fixed_percentage: number;
    dynamic_sizing: boolean;
  };
  stop_loss: {
    atr_multiplier: number;
    max_loss_percentage: number;
    trailing_stop: boolean;
  };
  take_profit: {
    risk_reward_ratio: number;
    partial_tp_levels: number[];
  };
}

export interface ExchangeConfig {
  name: string;
  enabled: boolean;
  display_name: string;
  api_key: string;
  api_secret: string;
  passphrase?: string;
  sandbox: boolean;
  rate_limit: number;
  supported_assets: string[];
  fees: {
    maker: number;
    taker: number;
  };
}

export interface TraderConfig {
  name: string;
  enabled: boolean;
  strategy: string;
  symbols: string[];
  timeframes: string[];
  parameters: {
    [key: string]: any;
  };
}

// API response types
export interface ConfigResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface ConfigFile {
  name: string;
  path: string;
  type: 'trading' | 'system' | 'ml' | 'risk' | 'exchange' | 'trader';
  description: string;
  last_modified: string;
  size: number;
  content: any;
}

export interface ConfigValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
}