# Database Migration Guide: BOT Trading v2 to v3

## Executive Summary

This document provides a comprehensive analysis of database schema differences between BOT Trading v2 and v3, along with specific migration steps and SQL commands.

## Schema Differences Analysis

### 1. Conceptual Changes

#### v2 Trade Model → v3 Order + Trade Models

- **v2**: `Trade` represents a position/order lifecycle
- **v3**: Split into:
  - `Order`: Represents pending/active orders
  - `Trade`: Represents executed trades only

#### Field Naming Conventions

- **v2**: Mixed naming (e.g., `order_id`, `close_order_id`)
- **v3**: Consistent naming with enums

### 2. Table Mapping

| v2 Table | v3 Equivalent | Notes |
|----------|---------------|-------|
| trades | orders + trades | Split concept |
| orders | orders | Different structure |
| sltp_orders | (none) | Merged into orders |
| signals | signals | Similar structure |
| (none) | balances | New in v3 |
| (none) | performance | New in v3 |

### 3. Missing Fields in v3

#### Orders Table

```sql
-- v2 fields missing in v3
trigger_by VARCHAR(50)
sl_trigger_price FLOAT
tp_trigger_price FLOAT
sl_order_id VARCHAR(100)
tp_order_id VARCHAR(100)
is_sltp BOOLEAN
parent_order_id VARCHAR(100)
reduce_only BOOLEAN
time_in_force VARCHAR(50)
position_idx INTEGER
```

#### Trades Table (for v2 compatibility)

```sql
-- ML fields from v2
model_name VARCHAR(100)
model_score FLOAT
profit_probability FLOAT
loss_probability FLOAT
confidence FLOAT
session_id VARCHAR(100)
ml_data TEXT
signal_id INTEGER
user_id INTEGER
```

#### Signals Table

```sql
-- Additional v2 fields
indicators JSONB
ml_predictions JSONB
processing_time FLOAT
model_name VARCHAR(100)
score INTEGER
raw_data JSONB
status VARCHAR(50)
error_message TEXT
```

### 4. New v2-specific Tables Needed

```sql
-- SLTP Orders (Stop Loss/Take Profit management)
CREATE TABLE sltp_orders (
    id SERIAL PRIMARY KEY,
    trade_id INTEGER NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,
    stop_loss_price FLOAT,
    take_profit_price FLOAT,
    sl_order_id VARCHAR(100),
    tp_order_id VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    attempts INTEGER DEFAULT 0,
    sl_trigger_by VARCHAR(50) DEFAULT 'LastPrice',
    tp_trigger_by VARCHAR(50) DEFAULT 'LastPrice',
    trailing_stop BOOLEAN DEFAULT FALSE,
    trailing_stop_price FLOAT,
    trailing_stop_activation_price FLOAT,
    trailing_callback FLOAT,
    is_breakeven BOOLEAN DEFAULT FALSE,
    partial_close_ratio FLOAT,
    partial_close_trigger FLOAT,
    original_stop_loss FLOAT,
    original_take_profit FLOAT,
    error_message TEXT,
    extra_data JSONB,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE
);

-- Bybit-specific tables
CREATE TABLE bybit_trade_history (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    order_id VARCHAR(100) NOT NULL UNIQUE,
    order_link_id VARCHAR(100),
    side VARCHAR(10) NOT NULL,
    price FLOAT NOT NULL,
    qty FLOAT NOT NULL,
    fee FLOAT DEFAULT 0.0,
    fee_currency VARCHAR(20),
    order_type VARCHAR(50),
    stop_order_type VARCHAR(50),
    created_time TIMESTAMP NOT NULL,
    updated_time TIMESTAMP,
    is_maker BOOLEAN DEFAULT FALSE,
    reduce_only BOOLEAN DEFAULT FALSE,
    close_on_trigger BOOLEAN DEFAULT FALSE,
    cum_exec_qty FLOAT,
    cum_exec_value FLOAT,
    cum_exec_fee FLOAT,
    trigger_price FLOAT,
    trigger_by VARCHAR(50),
    imported_at TIMESTAMP DEFAULT NOW()
);

-- Trading sessions
CREATE TABLE trading_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL UNIQUE,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    total_trades INTEGER DEFAULT 0,
    profitable_trades INTEGER DEFAULT 0,
    total_pnl FLOAT DEFAULT 0.0,
    max_drawdown FLOAT DEFAULT 0.0,
    win_rate FLOAT,
    config_snapshot JSONB,
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    metadata JSONB
);
```

## Migration Steps

### Step 1: Fix Alembic Migration Tree

```bash
# Update the migration revision tree
# Already fixed in 001_import_v2_structures.py
# down_revision = '3dcf72ea81e3'
```

### Step 2: Apply Compatibility Migration

```bash
# Run the v2 compatibility migration
alembic upgrade 001_import_v2
```

### Step 3: Data Migration SQL Scripts

#### 3.1 Migrate v2 Trades to v3 Orders

```sql
-- Insert v2 trades as orders in v3
INSERT INTO orders (
    exchange,
    symbol,
    order_id,
    side,
    order_type,
    status,
    price,
    quantity,
    filled_quantity,
    stop_loss,
    take_profit,
    created_at,
    updated_at,
    strategy_name,
    trader_id,
    extra_data
)
SELECT
    'bybit' as exchange,  -- Default exchange
    symbol,
    order_id,
    CASE
        WHEN side = 'Buy' THEN 'buy'::orderside
        WHEN side = 'Sell' THEN 'sell'::orderside
    END as side,
    'market'::ordertype as order_type,  -- Default to market
    CASE
        WHEN status = 'OPEN' THEN 'open'::orderstatus
        WHEN status = 'CLOSE' THEN 'filled'::orderstatus
        WHEN status = 'CANCELED' THEN 'cancelled'::orderstatus
        ELSE 'rejected'::orderstatus
    END as status,
    entry_price as price,
    quantity,
    CASE
        WHEN status = 'CLOSE' THEN quantity
        ELSE 0
    END as filled_quantity,
    stop_loss,
    take_profit,
    created_at::timestamp with time zone,
    COALESCE(closed_at, created_at)::timestamp with time zone as updated_at,
    model_name as strategy_name,
    NULL as trader_id,  -- Will need to map separately
    jsonb_build_object(
        'v2_trade_id', id,
        'leverage', leverage,
        'signal_id', signal_id,
        'model_score', model_score,
        'ml_data', ml_data
    ) as extra_data
FROM v2_trades  -- Assuming v2 data is imported
WHERE order_id IS NOT NULL;
```

#### 3.2 Create Trades for Closed Positions

```sql
-- Create trade records for closed v2 trades
INSERT INTO trades (
    exchange,
    symbol,
    trade_id,
    order_id,
    side,
    price,
    quantity,
    commission,
    realized_pnl,
    executed_at,
    created_at,
    strategy_name,
    trader_id
)
SELECT
    'bybit' as exchange,
    symbol,
    COALESCE(close_order_id, order_id || '_close') as trade_id,
    order_id,
    CASE
        WHEN side = 'Buy' THEN 'buy'::orderside
        WHEN side = 'Sell' THEN 'sell'::orderside
    END as side,
    COALESCE(close_price, entry_price) as price,
    quantity,
    0 as commission,  -- Will need to calculate
    pnl as realized_pnl,
    closed_at::timestamp with time zone as executed_at,
    NOW() as created_at,
    model_name as strategy_name,
    NULL as trader_id
FROM v2_trades
WHERE status = 'CLOSE' AND closed_at IS NOT NULL;
```

#### 3.3 Migrate SLTP Orders

```sql
-- Migrate v2 SLTP orders
INSERT INTO sltp_orders (
    trade_id,
    symbol,
    side,
    stop_loss_price,
    take_profit_price,
    sl_order_id,
    tp_order_id,
    status,
    created_at,
    updated_at,
    attempts,
    sl_trigger_by,
    tp_trigger_by,
    trailing_stop,
    trailing_stop_price,
    trailing_stop_activation_price,
    trailing_callback,
    is_breakeven,
    partial_close_ratio,
    partial_close_trigger,
    original_stop_loss,
    original_take_profit,
    error_message,
    extra_data
)
SELECT * FROM v2_sltp_orders;  -- Direct migration if structure matches
```

#### 3.4 Migrate Signals

```sql
-- Update signals table with v2 data
UPDATE signals s
SET
    indicators = v2s.indicators::jsonb,
    ml_predictions = v2s.predictions::jsonb,
    processing_time = EXTRACT(EPOCH FROM (v2s.processed_at::timestamp - v2s.created_at::timestamp)),
    extra_data = jsonb_build_object(
        'v2_signal_id', v2s.id,
        'model_name', v2s.model_name,
        'score', v2s.score,
        'raw_data', v2s.raw_data,
        'status', v2s.status,
        'error_message', v2s.error_message
    )
FROM v2_signals v2s
WHERE s.created_at = v2s.created_at::timestamp with time zone
  AND s.symbol = v2s.symbol;
```

### Step 4: Create Missing Indexes

```sql
-- Performance indexes
CREATE INDEX idx_orders_session_id ON orders((extra_data->>'v2_trade_id'));
CREATE INDEX idx_trades_session_id ON trades((extra_data->>'v2_trade_id'));
CREATE INDEX idx_sltp_orders_trade_id ON sltp_orders(trade_id);
CREATE INDEX idx_sltp_orders_symbol ON sltp_orders(symbol);
CREATE INDEX idx_bybit_trade_order_id ON bybit_trade_history(order_id);
CREATE INDEX idx_bybit_trade_symbol_time ON bybit_trade_history(symbol, created_time);
CREATE INDEX idx_trading_sessions_id ON trading_sessions(session_id);
```

### Step 5: Data Validation Queries

```sql
-- Validate migration completeness
SELECT
    'v2_trades' as source,
    COUNT(*) as count
FROM v2_trades
UNION ALL
SELECT
    'v3_orders' as source,
    COUNT(*) as count
FROM orders
WHERE extra_data->>'v2_trade_id' IS NOT NULL
UNION ALL
SELECT
    'v3_trades' as source,
    COUNT(*) as count
FROM trades;

-- Check for orphaned records
SELECT t.id, t.symbol, t.order_id
FROM v2_trades t
LEFT JOIN orders o ON o.order_id = t.order_id
WHERE o.id IS NULL AND t.order_id IS NOT NULL;
```

## Compatibility Issues and Solutions

### 1. Enum Type Differences

**Issue**: v2 uses string values, v3 uses enums
**Solution**: Create casting functions or use CASE statements in migrations

### 2. Trade vs Order+Trade Split

**Issue**: v2 Trade encompasses full lifecycle, v3 splits it
**Solution**:

- Map open v2 trades → v3 orders
- Map closed v2 trades → v3 orders + trades
- Store v2 trade ID in extra_data for reference

### 3. Missing ML Fields

**Issue**: v3 base models don't include ML fields
**Solution**: Added via migration, stored in extra_data where appropriate

### 4. SLTP Management

**Issue**: v3 doesn't have separate SLTP table
**Solution**: Created sltp_orders table to maintain v2 compatibility

## Rollback Plan

```sql
-- Rollback migration
alembic downgrade 3dcf72ea81e3

-- Emergency data recovery
-- All v2 data preserved in extra_data fields
SELECT
    extra_data->>'v2_trade_id' as original_id,
    *
FROM orders
WHERE extra_data->>'v2_trade_id' IS NOT NULL;
```

## Post-Migration Verification

1. **Record Count Validation**

   ```bash
   python scripts/validate_migration.py
   ```

2. **Data Integrity Checks**

   ```sql
   -- Check for data consistency
   SELECT COUNT(*) FROM orders WHERE symbol IS NULL OR symbol = '';
   SELECT COUNT(*) FROM trades WHERE price <= 0;
   ```

3. **Application Testing**
   - Test v2 API endpoints with migrated data
   - Verify ML model compatibility
   - Check SLTP order processing

## Notes

- Always backup database before migration
- Test migration on staging environment first
- Monitor application logs during first 24 hours post-migration
- Keep v2 tables for 30 days as backup
