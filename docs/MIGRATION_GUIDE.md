# Migration Guide - Feature Engineering v2.0

## Overview

This guide helps migrate from the old configuration-dependent feature engineering to the new v2.0 system.

## What Changed

### Old System (v1.0)

- Features created only if config exists
- Variable feature count (200-300)
- Config-dependent parameters
- Manual feature selection

### New System (v2.0)

- **Always creates 273 features** (240 ML + 33 targets)
- **No configuration dependency**
- **Automatic trimming to 240** for ML
- **100% compatibility** with original code

## Migration Steps

### 1. Update Imports

```python
# Old
from ml.logic.feature_engineering import FeatureEngineer

# New
from ml.logic.feature_engineering_v2 import FeatureEngineer
```

### 2. Remove Config Dependencies

```python
# Old - Config required
fe = FeatureEngineer(config)
if config.get('features', {}).get('technical'):
    features = fe.create_features(df)

# New - Works without config
fe = FeatureEngineer({})  # Empty config is fine
features = fe.create_features(df)  # Always creates features
```

### 3. Update Feature Count Expectations

```python
# Old - Variable count
assert len(features.columns) >= 200  # Could be anything

# New - Fixed count
numeric_cols = features.select_dtypes(include=[np.number]).columns
assert len(numeric_cols) == 273  # Always 273 (including targets)

# For ML - automatically trimmed
ml_features = numeric_cols[:240]  # First 240 for model
```

### 4. Handle Target Variables

```python
# New system clearly separates features and targets
feature_cols = [col for col in numeric_cols if 'target' not in col.lower()]
target_cols = [col for col in numeric_cols if 'target' in col.lower()]

# Or use built-in filtering
feature_cols = [col for col in numeric_cols if not any(
    pattern in col for pattern in [
        'future_', 'direction_', 'will_reach_',
        'max_drawdown_', 'max_rally_', 'expected_value'
    ]
)]
```

## Default Parameters

All indicators now use fixed default parameters:

```python
# Technical Indicators - Always Created
SMA_PERIODS = [20, 50]
EMA_PERIODS = [12, 26]
RSI_PERIOD = 14
MACD_SLOW = 26
MACD_FAST = 12
MACD_SIGNAL = 9
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2
ATR_PERIOD = 14
STOCHASTIC_WINDOW = 14
ADX_WINDOW = 14
```

## Feature List Changes

### Always Created (New)

These features are now ALWAYS created, regardless of configuration:

1. **Basic Features** (12)
   - returns, returns_5, returns_10, returns_20
   - high_low_ratio, close_open_ratio, close_position
   - volume_ratio, turnover_ratio
   - vwap, close_vwap_ratio, vwap_extreme_deviation

2. **Technical Indicators** (52)
   - SMA (20, 50) with ratios
   - EMA (12, 26) with ratios
   - RSI with oversold/overbought
   - MACD (normalized) with signal and diff
   - Bollinger Bands with width, position, breakouts
   - ATR with percentage
   - Stochastic K/D
   - ADX with directional indicators
   - And many more...

3. **Advanced Indicators** (23)
   - Ichimoku Cloud (tenkan, kijun, span_a, span_b)
   - Keltner Channels (upper_20, middle_20, lower_20)
   - Donchian Channels (upper_20, middle_20, lower_20)
   - MFI, CCI, Williams %R, OBV

### Removed/Changed Features

None - all original features are preserved.

## Testing Your Migration

### 1. Check Feature Count

```bash
python check_feature_count.py
# Should show: 273 total, 240 after filtering
```

### 2. Test with ML Model

```bash
python test_ml_uniqueness.py
# Should run without shape errors
```

### 3. Validate Specific Features

```python
# Test script
from ml.logic.feature_engineering_v2 import FeatureEngineer
import pandas as pd
import numpy as np

# Create test data
df = pd.DataFrame({
    'datetime': pd.date_range('2024-01-01', periods=500, freq='15min'),
    'symbol': 'BTCUSDT',
    'open': np.random.randn(500) * 100 + 50000,
    'high': np.random.randn(500) * 100 + 50100,
    'low': np.random.randn(500) * 100 + 49900,
    'close': np.random.randn(500) * 100 + 50000,
    'volume': np.random.randn(500) * 1000 + 10000,
    'turnover': np.random.randn(500) * 10000 + 100000
})

# Create features
fe = FeatureEngineer({})
features = fe.create_features(df)

# Check critical features exist
assert 'rsi' in features.columns
assert 'macd' in features.columns
assert 'bb_position' in features.columns
assert 'ichimoku_tenkan' in features.columns
assert 'obv' in features.columns
print("✅ All critical features present!")
```

## Troubleshooting

### Issue: Different feature count

**Solution**: Check that you're using feature_engineering_v2.py, not the old version.

### Issue: Missing indicators

**Solution**: All indicators are now created by default. Check for typos in feature names.

### Issue: Config errors

**Solution**: Pass empty dict `{}` if no config available. System uses defaults.

### Issue: ML shape mismatch

**Solution**: RealTimeIndicatorCalculator automatically trims to 240. Check it's updated.

## Rollback Plan

If you need to rollback:

```bash
# Keep backup of old file
cp ml/logic/feature_engineering.py ml/logic/feature_engineering_backup.py

# To rollback
cp ml/logic/feature_engineering_backup.py ml/logic/feature_engineering.py
```

## Performance Impact

- **Memory**: +10MB (more features stored)
- **CPU**: +50ms (more calculations)
- **Benefits**: Consistent features, no config issues

## Support

For migration issues:

1. Check logs: `grep "feature" data/logs/bot_trading_*.log`
2. Run tests: `pytest tests/unit/test_feature_engineering.py`
3. Review docs: [FEATURE_ENGINEERING.md](FEATURE_ENGINEERING.md)

---

*Migration Guide v1.0*
*Last Updated: January 14, 2025*
