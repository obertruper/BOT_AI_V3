-- Создание таблиц для истории SL/TP операций

-- Таблица истории частичных закрытий
CREATE TABLE IF NOT EXISTS partial_tp_history (
    id SERIAL PRIMARY KEY,
    trade_id INTEGER,
    position_id VARCHAR(100),
    symbol VARCHAR(50),
    side VARCHAR(10),
    level_percent DECIMAL(10,2),
    close_ratio DECIMAL(10,4),
    quantity DECIMAL(20,8),
    price DECIMAL(20,8),
    order_id VARCHAR(100),
    status VARCHAR(50),
    error_message TEXT,
    executed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_partial_tp_trade_id ON partial_tp_history(trade_id);
CREATE INDEX IF NOT EXISTS idx_partial_tp_position_id ON partial_tp_history(position_id);
CREATE INDEX IF NOT EXISTS idx_partial_tp_symbol ON partial_tp_history(symbol);
CREATE INDEX IF NOT EXISTS idx_partial_tp_status ON partial_tp_history(status);

-- Таблица истории обновлений SL/TP
CREATE TABLE IF NOT EXISTS sltp_updates (
    id SERIAL PRIMARY KEY,
    position_id VARCHAR(100),
    trade_id INTEGER,
    symbol VARCHAR(50),
    update_type VARCHAR(50), -- trailing/breakeven/partial/protection
    old_sl DECIMAL(20,8),
    new_sl DECIMAL(20,8),
    old_tp DECIMAL(20,8),
    new_tp DECIMAL(20,8),
    current_price DECIMAL(20,8),
    profit_percent DECIMAL(10,4),
    reason TEXT,
    status VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_sltp_updates_position_id ON sltp_updates(position_id);
CREATE INDEX IF NOT EXISTS idx_sltp_updates_trade_id ON sltp_updates(trade_id);
CREATE INDEX IF NOT EXISTS idx_sltp_updates_type ON sltp_updates(update_type);
CREATE INDEX IF NOT EXISTS idx_sltp_updates_created ON sltp_updates(created_at);

-- Таблица настроек SL/TP для активных позиций
CREATE TABLE IF NOT EXISTS position_sltp_settings (
    id SERIAL PRIMARY KEY,
    position_id VARCHAR(100) UNIQUE,
    trade_id INTEGER,
    symbol VARCHAR(50),
    side VARCHAR(10),
    entry_price DECIMAL(20,8),
    current_sl DECIMAL(20,8),
    current_tp DECIMAL(20,8),
    initial_sl DECIMAL(20,8),
    initial_tp DECIMAL(20,8),
    breakeven_triggered BOOLEAN DEFAULT FALSE,
    breakeven_price DECIMAL(20,8),
    trailing_activated BOOLEAN DEFAULT FALSE,
    trailing_distance DECIMAL(10,4),
    partial_levels_executed JSONB DEFAULT '[]'::jsonb,
    profit_protection_level INTEGER DEFAULT 0,
    last_update_type VARCHAR(50),
    last_update_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_position_sltp_position_id ON position_sltp_settings(position_id);
CREATE INDEX IF NOT EXISTS idx_position_sltp_trade_id ON position_sltp_settings(trade_id);
CREATE INDEX IF NOT EXISTS idx_position_sltp_symbol ON position_sltp_settings(symbol);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для автоматического обновления updated_at
CREATE TRIGGER update_partial_tp_history_updated_at BEFORE UPDATE
    ON partial_tp_history FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_position_sltp_settings_updated_at BEFORE UPDATE
    ON position_sltp_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Комментарии к таблицам
COMMENT ON TABLE partial_tp_history IS 'История частичных закрытий позиций';
COMMENT ON TABLE sltp_updates IS 'История всех изменений SL/TP';
COMMENT ON TABLE position_sltp_settings IS 'Текущие настройки SL/TP для активных позиций';