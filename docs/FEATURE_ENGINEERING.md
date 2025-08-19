# Feature Engineering Documentation - BOT_AI_V3

## Overview

Feature engineering system for cryptocurrency trading ML model with 240+ technical indicators, microstructure features, and ML-optimized signals.

## Architecture

```
feature_engineering_v2.py (Core)
    ├── Basic Features (OHLCV-based)
    ├── Technical Indicators (TA-lib)
    ├── Microstructure Features (Market dynamics)
    ├── Rally Detection Features (Volume patterns)
    ├── Signal Quality Features (Indicator consensus)
    ├── Futures-Specific Features (Leverage, liquidation)
    ├── ML-Optimized Features (Hurst, Fractal, Entropy)
    └── Target Variables (Without data leakage)
```

## Feature Categories

### 1. Basic Features (12 features)

- **Returns**: log returns for different periods (5, 10, 20)
- **Price Ratios**: high_low_ratio, close_open_ratio
- **Volume Metrics**: volume_ratio, turnover_ratio
- **VWAP**: Volume-weighted average price and ratios

### 2. Technical Indicators (52 features)

#### Moving Averages

- **SMA**: Periods [20, 50] with price ratios
- **EMA**: Periods [12, 26] with price ratios

#### Momentum Indicators

- **RSI**: Period 14, oversold/overbought signals
- **MACD**: Fast 12, Slow 26, Signal 9 (normalized)
- **Stochastic**: K and D lines
- **Williams %R**: Period 14
- **Ultimate Oscillator**: Combined periods 7/14/28

#### Volatility Indicators

- **Bollinger Bands**: Period 20, Std 2
  - Width, position, breakout signals
- **ATR**: Period 14, percentage of price
- **Keltner Channels**: Period 20, ATR 10
- **Donchian Channels**: Period 20, breakout detection

#### Trend Indicators

- **ADX**: Average Directional Index with +DI/-DI
- **Parabolic SAR**: Trend direction and distance
- **Ichimoku Cloud**: Tenkan, Kijun, Span A/B
- **Aroon**: Up/Down/Oscillator

#### Volume Indicators

- **OBV**: On Balance Volume with trend
- **MFI**: Money Flow Index, overbought/oversold
- **CMF**: Chaikin Money Flow
- **A/D Line**: Accumulation/Distribution

### 3. Microstructure Features (15 features)

- **Spread Metrics**: hl_spread, hl_spread_ma
- **Order Flow**: volume_imbalance, directed_volume
- **Price Impact**: Regular and log-scaled
- **Liquidity Measures**:
  - Amihud illiquidity
  - Kyle's lambda
  - VPIN (Volume-synchronized PIN)
- **Toxicity**: Flow toxicity measure
- **Volatility**: Realized vol (1h, daily, annual)

### 4. Rally Detection Features (42 features)

- **Volume Accumulation**: 4h, 8h, 12h, 24h periods
- **Volume Spikes**: Z-score based detection
- **Support/Resistance**: Local highs/lows for [20, 50, 100] periods
- **Volatility Squeeze**: BB vs Keltner comparison
- **Divergences**: RSI/MACD vs price divergences
- **Momentum**: 1h, 4h, 24h momentum with acceleration
- **Pattern Detection**: Spring pattern for breakouts

### 5. Signal Quality Features (21 features)

- **Indicator Consensus**: Agreement between RSI, MACD, BB, Stoch, ADX, MA
- **Trend Strength**: On 1h and 4h timeframes
- **Daily Position**: Position in daily range, near extremes
- **Market Structure**: Higher highs/lows detection
- **Liquidity Score**: Based on spread and volume
- **Signal Strength**: Combined metric without data leakage

### 6. Futures-Specific Features (15 features)

- **Liquidation Prices**: Long/short liquidation levels
- **Liquidation Distance**: Percentage to liquidation
- **Dynamic Leverage**: Volatility-adjusted leverage (3x-10x)
- **Liquidation Risk**: Historical probability
- **Optimal Leverage**: Based on daily volatility
- **Funding Rate**: Proxy and holding costs
- **Risk Metrics**: VaR, recommended position size

### 7. ML-Optimized Features (30+ features)

- **Hurst Exponent**: Market persistence measure
- **Fractal Dimension**: Price complexity
- **Market Efficiency Ratio**: Trend efficiency
- **Shannon Entropy**: Returns distribution entropy
- **Autocorrelation**: Lags 1, 5, 10, 20
- **Jump Detection**: Price jumps and intensity
- **Volatility Clustering**: Vol of vol metrics
- **Microstructure Noise**: Market noise estimation
- **HP Filter**: Trend-cycle decomposition

### 8. Temporal Features (16 features)

- **Time Components**: Hour, minute, day, month
- **Cyclic Encoding**: Sin/cos for hour, day, month
- **Trading Sessions**: Asian, European, American
- **Session Overlap**: Multiple session activity
- **Weekend Indicator**: Binary weekend flag

### 9. Cross-Asset Features (5 features, when multiple symbols)

- **BTC Correlation**: Rolling correlation with Bitcoin
- **Relative Strength**: vs BTC and sector
- **Sector Returns**: Sector-based classification
- **Returns Rank**: Cross-sectional ranking
- **Momentum Leadership**: Top momentum indicators

## Target Variables (20 features, excluded from ML)

### Future Returns (4)

- `future_return_15m`, `future_return_1h`, `future_return_4h`, `future_return_12h`

### Direction Labels (4)

- `direction_15m`, `direction_1h`, `direction_4h`, `direction_12h`
- Categories: UP (>threshold), DOWN (<-threshold), FLAT (between)

### Profit Targets (8)

- Long targets: 1% (4h), 2% (4h), 3% (12h), 5% (12h)
- Short targets: Same levels for short positions

### Risk Metrics (4)

- `max_drawdown_1h`, `max_drawdown_4h`
- `max_rally_1h`, `max_rally_4h`

## Implementation Details

### Feature Count Management

```python
# Total features generated: 273
# After excluding targets: 273 - 33 = 240
# Automatic trimming in realtime_indicator_calculator.py
if len(numeric_cols) > 240:
    numeric_cols = numeric_cols[:240]
```

### Safe Division Helper

```python
@staticmethod
def safe_divide(numerator, denominator, fill_value=0.0, max_value=1000.0):
    """Prevents division by zero and extreme values"""
    # Handles small denominators
    # Clips results to reasonable range
    # Replaces inf/nan with fill_value
```

### Walk-Forward Validation

- No future data leakage
- Scalers trained only on historical data
- Target variables use shift(-n) for future values

## Configuration

### Default Parameters (No Config Dependency)

```python
# Technical Indicators - Always Created
SMA_PERIODS = [20, 50]
EMA_PERIODS = [12, 26]
RSI_PERIOD = 14
MACD_PARAMS = {"slow": 26, "fast": 12, "signal": 9}
BB_PARAMS = {"period": 20, "std": 2}
ATR_PERIOD = 14
```

### Normalization

- Uses `RobustScaler` for outlier resistance
- Symbol-specific scaling
- Walk-forward approach for production

## Usage Examples

### Basic Feature Creation

```python
from ml.logic.archive_old_versions.feature_engineering_v2 import FeatureEngineer

# Initialize
fe = FeatureEngineer({})

# Create features for DataFrame
features_df = fe.create_features(ohlcv_df)

# Result: DataFrame with 273 columns (240 features + 33 targets)
```

### Real-time Feature Calculation

```python
from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

# Initialize calculator
calculator = RealTimeIndicatorCalculator()

# Calculate for trading
indicators = await calculator.calculate_indicators(
    symbol="BTCUSDT",
    ohlcv_df=market_data,
    save_to_db=True
)

# Prepare for ML model (auto-trims to 240)
features_array, metadata = await calculator.prepare_ml_input(
    symbol="BTCUSDT",
    ohlcv_df=market_data,
    lookback=96
)
```

### Feature Selection for ML

```python
# Automatic filtering in realtime_indicator_calculator.py
numeric_cols = features_df.select_dtypes(include=[np.number]).columns
# Exclude targets
feature_cols = [col for col in numeric_cols if 'target' not in col.lower()]
# Limit to 240
if len(feature_cols) > 240:
    feature_cols = feature_cols[:240]
```

## Performance Considerations

### Memory Usage

- ~273 features per row
- Float64 precision: 273 * 8 bytes = 2.2KB per row
- For 96 lookback: 96 * 2.2KB = 211KB per prediction

### Computation Time

- Feature creation: ~100ms per symbol (500 rows)
- Real-time calculation: ~50ms per symbol
- ML inference: ~20ms per batch

### Optimization Tips

1. Use `disable_progress=True` for production
2. Pre-calculate static features
3. Cache frequently used indicators
4. Batch multiple symbols together

## Quality Assurance

### Feature Validation

```python
# Check for NaN values
assert features_df.isna().sum().sum() == 0

# Check feature count
numeric_cols = features_df.select_dtypes(include=[np.number])
assert len(numeric_cols) == 273  # Including targets

# Check for infinite values
assert not np.isinf(features_df.select_dtypes(include=[np.number])).any().any()
```

### Testing Scripts

- `check_feature_count.py`: Validates feature generation
- `check_final_features.py`: Checks ML-ready features
- `test_ml_uniqueness.py`: Tests with real ML model

## Common Issues and Solutions

### Issue: Too Many Features (>240)

**Solution**: Automatic trimming in `realtime_indicator_calculator.py`

### Issue: NaN Values in Features

**Solution**:

- Use `_handle_missing_values()` method
- Forward fill for technical indicators
- Zero fill for others

### Issue: Extreme Values

**Solution**:

- `safe_divide()` helper with max_value parameter
- Clipping in normalization
- RobustScaler instead of StandardScaler

### Issue: Data Leakage

**Solution**:

- All future values use `shift(-n)`
- Walk-forward validation
- Separate scalers per symbol

## Version History

### v2.0 (Current)

- 240 ML features + 33 target variables
- No configuration dependency
- Automatic feature trimming
- Full compatibility with UnifiedPatchTST model

### v1.0 (Legacy)

- Config-dependent indicators
- Variable feature count
- Manual feature selection

## References

- Technical Analysis Library: [TA-Lib](https://github.com/mrjbq7/ta-lib)
- Market Microstructure: Kyle (1985), Amihud (2002)
- ML Features: Hurst (1951), Higuchi (1988)
- Trading Indicators: Murphy (1999), Pring (2002)
