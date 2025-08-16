# ML Logging and Visualization System

## Overview

Complete ML prediction logging and visualization system for BOT_AI_V3, providing detailed tracking of all ML model predictions and performance metrics.

## Components

### 1. ML Prediction Logger (`ml/ml_prediction_logger.py`)

Comprehensive logging system that captures:

- All 240 input features with statistics
- 20 raw model outputs
- Interpreted predictions (signal type, confidence, directions)
- Risk metrics
- Performance timing
- Feature importance tracking

### 2. Database Schema

Two main tables created via Alembic migration:

#### `ml_predictions` Table

- Stores complete prediction details
- Unique constraint on (symbol, timestamp)
- Indexes for fast querying by symbol, signal type, confidence
- JSONB fields for full feature arrays

#### `ml_feature_importance` Table

- Tracks feature importance scores
- Updates periodically with model retraining
- Used for feature selection optimization

### 3. Metabase Visualization

Docker-based Metabase setup with pre-configured dashboards:

- **ML Predictions Monitor** - Real-time prediction tracking
- **Trading Performance** - P&L analysis by symbol/strategy
- **Signal Quality** - Signal strength and conversion rates
- **Risk Analysis** - SL/TP effectiveness and risk metrics
- **Feature Importance** - Top contributing features

## Setup Instructions

### 1. Database Setup

```bash
# Apply migrations to create tables
alembic upgrade head

# Verify tables exist
psql -p 5555 -U obertruper -d bot_trading_v3 -c "\dt ml_*"
```

### 2. Metabase Installation

```bash
# Run setup script
chmod +x setup_metabase.sh
./setup_metabase.sh

# Access at http://localhost:3000
# Database connection:
#   Host: host.docker.internal
#   Port: 5555
#   Database: bot_trading_v3
#   Username: obertruper
#   Password: ilpnqw1234
```

### 3. Create SQL Views

```bash
# Import dashboard views
psql -p 5555 -U obertruper -d bot_trading_v3 < metabase_dashboards.sql
```

## Usage

### ML Prediction Logging

The system automatically logs every ML prediction when trading with ML mode:

```bash
# Start with ML predictions
python3 unified_launcher.py --mode=ml
```

Each prediction logs:

- Input features (all 240)
- Model outputs (all 20)
- Interpreted signals
- Risk metrics
- Execution time

### Viewing Logs

#### Console Output

Beautiful formatted tables showing:

```
╔══════════════════════════════════════════════════════════════════════╗
║                    ML PREDICTION DETAILS - BTCUSDT                   ║
╠══════════════════════════════════════════════════════════════════════╣
║ 📊 INPUT FEATURES                                                     ║
║   • Feature Count: 240    • Hash: 0x3f4a5b6c7d8e9f0a                 ║
║   • Mean: 0.0234  • Std: 1.2456                                     ║
╟──────────────────────────────────────────────────────────────────────╢
║ 🎯 FINAL SIGNAL                                                       ║
║   • Type: LONG      • Confidence: 85.00%                            ║
╚══════════════════════════════════════════════════════════════════════╝
```

#### Database Queries

```sql
-- Recent predictions
SELECT * FROM ml_predictions
WHERE created_at >= NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;

-- Performance by symbol
SELECT
    symbol,
    AVG(signal_confidence) as avg_confidence,
    COUNT(*) as predictions
FROM ml_predictions
GROUP BY symbol;
```

### Metabase Dashboards

1. Navigate to <http://localhost:3000>
2. Login with admin credentials
3. Go to Dashboards section
4. Select pre-built dashboards or create custom ones

## Testing

### Test ML Logging

```bash
# Direct test of logging system
python3 test_ml_logging_direct.py

# Test with real ML manager
python3 test_ml_logging.py
```

### Verify Data Flow

```bash
# Check if predictions are being saved
psql -p 5555 -U obertruper -d bot_trading_v3 -c "
SELECT COUNT(*) as total_predictions,
       COUNT(DISTINCT symbol) as symbols,
       MAX(created_at) as latest
FROM ml_predictions
WHERE created_at >= NOW() - INTERVAL '1 hour';
"
```

## Troubleshooting

### Issue: No predictions in database

1. Check migrations applied:

```bash
alembic current
```

2. Verify ML manager integration:

```bash
grep -n "ml_prediction_logger" ml/ml_manager.py
```

3. Check logs for errors:

```bash
tail -f data/logs/bot_trading_*.log | grep ml_prediction
```

### Issue: Metabase can't connect

1. Use correct host:
   - Docker: `host.docker.internal`
   - Linux: Host IP address

2. Verify PostgreSQL on port 5555:

```bash
lsof -i :5555
```

### Issue: Hash value out of range

Fixed in ml_prediction_logger.py - hash limited to 56 bits

## Performance Optimization

### Batch Processing

- Predictions saved in batches of 10
- Reduces database round trips
- Automatic flush on shutdown

### Indexing Strategy

- Primary key on (id)
- Unique on (symbol, timestamp)
- Indexes on frequently queried columns

### Data Retention

- Consider archiving old predictions
- Partition by month for large datasets

## API Integration

### Get Recent Predictions

```python
from database.connections.postgres import AsyncPGPool

async def get_recent_predictions(symbol: str, hours: int = 1):
    query = """
        SELECT * FROM ml_predictions
        WHERE symbol = $1
        AND created_at >= NOW() - INTERVAL '%s hours'
        ORDER BY created_at DESC
    """
    return await AsyncPGPool.fetch(query, symbol, hours)
```

### Feature Importance Analysis

```python
async def get_top_features(limit: int = 20):
    query = """
        SELECT feature_name, AVG(importance_score) as avg_score
        FROM ml_feature_importance
        GROUP BY feature_name
        ORDER BY avg_score DESC
        LIMIT $1
    """
    return await AsyncPGPool.fetch(query, limit)
```

## Security Considerations

1. **Database Credentials**: Store in .env, never commit
2. **Metabase Access**: Use strong admin password
3. **Data Privacy**: ML predictions contain trading signals
4. **Network Security**: Use HTTPS for production Metabase

## Future Enhancements

1. **Real-time Streaming**: WebSocket feed of predictions
2. **Model Comparison**: A/B testing different models
3. **Automated Alerts**: Slack/Telegram on anomalies
4. **Performance Metrics**: Prediction accuracy tracking
5. **Feature Evolution**: Track feature importance over time

---

*Last Updated: January 14, 2025*
*Version: 1.0.0*
