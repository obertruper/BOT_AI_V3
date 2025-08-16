-- SQL запросы для дашбордов Metabase BOT_AI_V3

-- =====================================================
-- 1. ML PREDICTIONS DASHBOARD
-- =====================================================

-- 1.1 Общая статистика предсказаний
CREATE OR REPLACE VIEW v_ml_predictions_stats AS
SELECT
    DATE(datetime) AS date,
    COUNT(*) AS total_predictions,
    COUNT(DISTINCT symbol) AS unique_symbols,
    AVG(signal_confidence) AS avg_confidence,
    SUM(CASE WHEN signal_type = 'LONG' THEN 1 ELSE 0 END) AS long_signals,
    SUM(CASE WHEN signal_type = 'SHORT' THEN 1 ELSE 0 END) AS short_signals,
    SUM(CASE WHEN signal_type = 'NEUTRAL' THEN 1 ELSE 0 END) AS neutral_signals,
    AVG(inference_time_ms) AS avg_inference_time
FROM ml_predictions
GROUP BY DATE(datetime);

-- 1.2 Точность предсказаний по таймфреймам
CREATE OR REPLACE VIEW v_ml_accuracy_by_timeframe AS
SELECT 'Доступность добавить заполнение actual_return полей для анализа' AS notice;

-- Временная версия без actual данных
SELECT
    symbol,
    COUNT(*) AS predictions_count,
    AVG(direction_15m_confidence) AS avg_confidence_15m,
    AVG(direction_1h_confidence) AS avg_confidence_1h,
    AVG(direction_4h_confidence) AS avg_confidence_4h,
    AVG(direction_12h_confidence) AS avg_confidence_12h
FROM ml_predictions
WHERE datetime >= NOW() - INTERVAL '7 days'
GROUP BY symbol
ORDER BY predictions_count DESC;

-- 1.3 Распределение сигналов по символам
CREATE OR REPLACE VIEW v_signal_distribution AS
SELECT
    symbol,
    signal_type,
    COUNT(*) AS count,
    AVG(signal_confidence) AS avg_confidence,
    MIN(signal_confidence) AS min_confidence,
    MAX(signal_confidence) AS max_confidence
FROM ml_predictions
WHERE datetime >= NOW() - INTERVAL '24 hours'
GROUP BY symbol, signal_type
ORDER BY symbol ASC, count DESC;

-- 1.4 Риск метрики
CREATE OR REPLACE VIEW v_risk_metrics AS
SELECT
    symbol,
    AVG(risk_score) AS avg_risk_score,
    AVG(max_drawdown_predicted) AS avg_max_drawdown,
    AVG(max_rally_predicted) AS avg_max_rally,
    COUNT(*) AS predictions_count
FROM ml_predictions
WHERE datetime >= NOW() - INTERVAL '7 days'
GROUP BY symbol
HAVING COUNT(*) > 10
ORDER BY avg_risk_score DESC;

-- =====================================================
-- 2. TRADING PERFORMANCE DASHBOARD
-- =====================================================

-- 2.1 Производительность торговли
CREATE OR REPLACE VIEW v_trading_performance AS
SELECT
    DATE(created_at) AS date,
    COUNT(DISTINCT o.id) AS total_orders,
    COUNT(DISTINCT t.id) AS total_trades,
    SUM(t.profit) AS total_profit,
    AVG(t.profit) AS avg_profit,
    SUM(CASE WHEN t.profit > 0 THEN 1 ELSE 0 END) AS winning_trades,
    SUM(CASE WHEN t.profit < 0 THEN 1 ELSE 0 END) AS losing_trades,
    SUM(CASE WHEN t.profit > 0 THEN t.profit ELSE 0 END) AS gross_profit,
    SUM(CASE WHEN t.profit < 0 THEN t.profit ELSE 0 END) AS gross_loss
FROM orders AS o
LEFT JOIN trades AS t ON o.id = t.order_id
WHERE o.created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- 2.2 Эффективность по символам
CREATE OR REPLACE VIEW v_symbol_performance AS
SELECT
    symbol,
    COUNT(*) AS total_trades,
    SUM(profit) AS total_profit,
    AVG(profit) AS avg_profit,
    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) AS win_rate,
    MAX(profit) AS max_profit,
    MIN(profit) AS max_loss,
    STDDEV(profit) AS profit_std
FROM trades
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY symbol
HAVING COUNT(*) > 5
ORDER BY total_profit DESC;

-- 2.3 SL/TP эффективность
CREATE OR REPLACE VIEW v_sltp_effectiveness AS
SELECT
    o.symbol,
    o.side,
    COUNT(*) AS total_orders,
    SUM(CASE WHEN o.stop_loss IS NOT NULL THEN 1 ELSE 0 END) AS orders_with_sl,
    SUM(CASE WHEN o.take_profit IS NOT NULL THEN 1 ELSE 0 END) AS orders_with_tp,
    AVG(CASE
        WHEN o.side = 'BUY' AND o.stop_loss IS NOT NULL
            THEN (o.price - o.stop_loss) / o.price * 100
        WHEN o.side = 'SELL' AND o.stop_loss IS NOT NULL
            THEN (o.stop_loss - o.price) / o.price * 100
    END) AS avg_sl_percentage,
    AVG(CASE
        WHEN o.side = 'BUY' AND o.take_profit IS NOT NULL
            THEN (o.take_profit - o.price) / o.price * 100
        WHEN o.side = 'SELL' AND o.take_profit IS NOT NULL
            THEN (o.price - o.take_profit) / o.price * 100
    END) AS avg_tp_percentage
FROM orders AS o
WHERE o.created_at >= NOW() - INTERVAL '7 days'
GROUP BY o.symbol, o.side
ORDER BY total_orders DESC;

-- =====================================================
-- 3. SIGNAL QUALITY DASHBOARD
-- =====================================================

-- 3.1 Качество сигналов по стратегиям
CREATE OR REPLACE VIEW v_signal_quality AS
SELECT
    strategy_name,
    signal_type,
    COUNT(*) AS signal_count,
    AVG(strength) AS avg_strength,
    AVG(confidence) AS avg_confidence,
    MIN(confidence) AS min_confidence,
    MAX(confidence) AS max_confidence
FROM signals
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY strategy_name, signal_type
ORDER BY signal_count DESC;

-- 3.2 Конверсия сигналов в ордера
CREATE OR REPLACE VIEW v_signal_conversion AS
SELECT
    s.symbol,
    s.strategy_name,
    COUNT(DISTINCT s.id) AS total_signals,
    COUNT(DISTINCT o.id) AS converted_to_orders,
    COUNT(DISTINCT o.id)::FLOAT / NULLIF(COUNT(DISTINCT s.id), 0) AS conversion_rate
FROM signals AS s
LEFT JOIN orders AS o
    ON
        s.symbol = o.symbol
        AND o.created_at BETWEEN s.created_at AND s.created_at + INTERVAL '5 minutes'
WHERE s.created_at >= NOW() - INTERVAL '24 hours'
GROUP BY s.symbol, s.strategy_name
ORDER BY total_signals DESC;

-- =====================================================
-- 4. REAL-TIME MONITORING
-- =====================================================

-- 4.1 Активные позиции
CREATE OR REPLACE VIEW v_active_positions AS
SELECT
    symbol,
    side,
    quantity,
    price AS entry_price,
    stop_loss,
    take_profit,
    created_at,
    NOW() - created_at AS position_age
FROM orders
WHERE status IN ('OPEN', 'PARTIALLY_FILLED')
ORDER BY created_at DESC;

-- 4.2 Последние ML предсказания (реального времени)
CREATE OR REPLACE VIEW v_recent_ml_predictions AS
SELECT
    symbol,
    signal_type,
    signal_confidence,
    predicted_return_15m,
    direction_15m,
    direction_15m_confidence,
    risk_score,
    inference_time_ms,
    datetime
FROM ml_predictions
WHERE datetime >= NOW() - INTERVAL '1 hour'
ORDER BY datetime DESC
LIMIT 100;

-- 4.3 Производительность системы
CREATE OR REPLACE VIEW v_system_performance AS
SELECT
    DATE_TRUNC('minute', datetime) AS minute,
    COUNT(*) AS predictions_per_minute,
    AVG(inference_time_ms) AS avg_inference_time,
    MAX(inference_time_ms) AS max_inference_time,
    COUNT(DISTINCT symbol) AS unique_symbols
FROM ml_predictions
WHERE datetime >= NOW() - INTERVAL '1 hour'
GROUP BY DATE_TRUNC('minute', datetime)
ORDER BY minute DESC;

-- =====================================================
-- 5. FEATURE IMPORTANCE DASHBOARD
-- =====================================================

-- 5.1 Важность признаков
CREATE OR REPLACE VIEW v_feature_importance AS
SELECT
    feature_name,
    AVG(importance_score) AS avg_importance,
    AVG(importance_rank) AS avg_rank,
    COUNT(*) AS calculation_count,
    MAX(calculated_at) AS last_calculated
FROM ml_feature_importance
GROUP BY feature_name
ORDER BY avg_importance DESC
LIMIT 50;

-- =====================================================
-- 6. ERROR ANALYSIS
-- =====================================================

-- 6.1 Анализ ошибок SHORT позиций
CREATE OR REPLACE VIEW v_short_position_errors AS
SELECT
    o.symbol,
    o.created_at,
    o.price,
    o.stop_loss,
    o.take_profit,
    CASE
        WHEN o.side = 'SELL' AND o.stop_loss <= o.price
            THEN 'ERROR: SL должен быть выше цены'
        WHEN o.side = 'SELL' AND o.take_profit >= o.price
            THEN 'ERROR: TP должен быть ниже цены'
        ELSE 'OK'
    END AS sl_tp_validation
FROM orders AS o
WHERE
    o.side = 'SELL'
    AND o.created_at >= NOW() - INTERVAL '7 days'
    AND (o.stop_loss IS NOT NULL OR o.take_profit IS NOT NULL)
ORDER BY o.created_at DESC;

-- =====================================================
-- Создание индексов для оптимизации
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_ml_predictions_datetime ON ml_predictions (datetime);
CREATE INDEX IF NOT EXISTS idx_ml_predictions_symbol_datetime ON ml_predictions (symbol, datetime);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at);
CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades (created_at);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals (created_at);

COMMENT ON VIEW v_ml_predictions_stats IS 'Общая статистика ML предсказаний';
COMMENT ON VIEW v_trading_performance IS 'Производительность торговли по дням';
COMMENT ON VIEW v_symbol_performance IS 'Эффективность торговли по символам';
COMMENT ON VIEW v_signal_quality IS 'Качество торговых сигналов';
COMMENT ON VIEW v_active_positions IS 'Текущие открытые позиции';
COMMENT ON VIEW v_short_position_errors IS 'Проверка ошибок SL/TP для SHORT позиций';
