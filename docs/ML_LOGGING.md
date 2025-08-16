# ML Predictions Logging System

## Overview

Comprehensive logging and tracking system for ML model predictions in BOT_AI_V3.

## Components

### 1. Database Schema

Two main tables for tracking ML predictions:

#### ml_predictions

Stores detailed information about each prediction:

- **Input Features**: Count, hash, statistics (mean, std, min, max)
- **Key Indicators**: RSI, MACD, BB position, ATR%, volume ratio
- **Model Outputs**: Returns and directions for 15m, 1h, 4h, 12h
- **Signal Details**: Type (LONG/SHORT/NEUTRAL), confidence, timeframe
- **Performance Tracking**: Actual vs predicted for later analysis
- **Metadata**: Model version, inference time, timestamps

#### ml_feature_importance

Tracks feature importance over time:

- Feature names and indices
- Importance scores and rankings
- Correlation with returns
- Usage statistics

### 2. MLPredictionLogger (`ml/ml_prediction_logger.py`)

Main logging class with features:

- **Batch Processing**: Saves predictions in batches for efficiency
- **Feature Hashing**: Detects duplicate predictions
- **Detailed Logging**: Beautiful console output with tables
- **Async Operations**: Non-blocking database saves
- **Statistics Calculation**: Real-time feature statistics

### 3. Integration with MLManager

Automatic logging on every prediction:

```python
# In ml_manager.py
predictions = self._interpret_predictions(outputs)
await ml_prediction_logger.log_prediction(
    symbol=symbol,
    features=features_scaled[-1],
    model_outputs=outputs_np,
    predictions=predictions,
    market_data=input_data
)
```

## Usage

### Running ML with Logging

```bash
# Start system with ML mode
python unified_launcher.py --mode=ml

# Predictions are automatically logged to database
```

### Testing Logging System

```bash
# Test logging functionality
python test_ml_logging.py

# Output shows:
# - Detailed prediction tables
# - Database save confirmation
# - Performance metrics
```

### Analyzing Predictions

```bash
# Analyze last 7 days of predictions
python analyze_ml_predictions.py

# Analyze specific symbol
python analyze_ml_predictions.py --symbol BTCUSDT --days 30
```

## Log Output Format

Each prediction generates detailed console output:

```
╔══════════════════════════════════════════════════════════════════════╗
║                    ML PREDICTION DETAILS - BTCUSDT                   ║
╠══════════════════════════════════════════════════════════════════════╣
║ 📊 INPUT FEATURES                                                     ║
║   • Feature Count: 240    • Hash: a3f2b1c4d5e6f7a8                   ║
║   • NaN Count: 0      • Zero Variance: 3                            ║
║   • Mean:   0.0234  • Std:   1.2456                                 ║
╟──────────────────────────────────────────────────────────────────────╢
║ 🎯 KEY INDICATORS                                                     ║
║   • Close: $50234.50  • Volume:   123456789                         ║
║   • RSI:  45.23  • MACD:  -0.0234                                   ║
║   • BB Position:  0.234  • ATR%:  1.234                             ║
╟──────────────────────────────────────────────────────────────────────╢
║ 📈 PREDICTED RETURNS                                                  ║
║   • 15m:  0.0012 (LONG)  [72.3%]                                    ║
║   • 1h:   0.0034 (LONG)  [68.5%]                                    ║
║   • 4h:   0.0089 (LONG)  [65.2%]                                    ║
║   • 12h: -0.0023 (SHORT) [61.8%]                                    ║
╟──────────────────────────────────────────────────────────────────────╢
║ ⚠️  RISK METRICS                                                      ║
║   • Risk Score:  0.234                                              ║
║   • Max Drawdown: -2.34%                                            ║
║   • Max Rally:    3.45%                                             ║
╟──────────────────────────────────────────────────────────────────────╢
║ 🎯 FINAL SIGNAL                                                       ║
║   • Type: LONG       • Confidence: 68.5%                            ║
║   • Primary Timeframe: 15m                                          ║
║   • Inference Time:   23.4 ms                                       ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Database Queries

### Recent Predictions

```sql
SELECT * FROM ml_predictions
WHERE datetime >= NOW() - INTERVAL '1 hour'
ORDER BY datetime DESC;
```

### Accuracy by Symbol

```sql
SELECT
    symbol,
    COUNT(*) as total,
    AVG(CASE WHEN accuracy_15m THEN 1 ELSE 0 END) as accuracy_15m,
    AVG(signal_confidence) as avg_confidence
FROM ml_predictions
WHERE actual_direction_15m IS NOT NULL
GROUP BY symbol
ORDER BY total DESC;
```

### High Confidence Signals

```sql
SELECT * FROM ml_predictions
WHERE signal_confidence > 0.8
  AND signal_type != 'NEUTRAL'
ORDER BY datetime DESC
LIMIT 100;
```

## Configuration

### Batch Size

In `ml_prediction_logger.py`:

```python
self.batch_size = 10  # Adjust based on prediction frequency
```

### Logging Level

Control verbosity:

```bash
export LOG_LEVEL=DEBUG  # Show all details
export LOG_LEVEL=INFO   # Normal operation
```

## Performance

- **Logging Overhead**: <5ms per prediction
- **Batch Save Time**: <50ms for 10 predictions
- **Storage**: ~2KB per prediction (without full feature array)
- **Query Performance**: Indexed for fast retrieval

## Troubleshooting

### Predictions Not Saving

1. Check database connection: `psql -p 5555 -U obertruper -d bot_trading_v3`
2. Verify table exists: `\dt ml_predictions`
3. Check batch size and flush frequency
4. Look for errors in logs: `grep "ml_prediction_logger" logs/*.log`

### High Memory Usage

- Reduce batch size
- Disable full feature array storage
- Implement periodic cleanup of old predictions

### Slow Queries

- Ensure indexes are created
- Vacuum and analyze tables regularly
- Archive old predictions

## Future Enhancements

1. **Real-time Dashboard**: Web interface for live prediction monitoring
2. **Automated Analysis**: Periodic reports on model performance
3. **A/B Testing**: Compare multiple model versions
4. **Feature Attribution**: SHAP values for explainability
5. **Drift Detection**: Alert when model performance degrades

---

*Last Updated: January 14, 2025*
*Version: 1.0.0*
