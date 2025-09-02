# 📊 ML Trading Examples & Use Cases

## 🔍 Практические примеры использования ML сигналов

### Пример 1: Обработка реального LONG сигнала

```python
# Входные данные от модели (20 параметров)
model_output = torch.tensor([
    0.012,   # returns_15m: +1.2%
    0.018,   # returns_1h: +1.8%
    0.025,   # returns_4h: +2.5%
    0.020,   # returns_12h: +2.0%
    2.5, -0.8, -1.2,  # direction 15m: LONG (высокая уверенность)
    2.2, -0.6, -1.0,  # direction 1h: LONG
    2.8, -0.9, -1.5,  # direction 4h: LONG
    2.0, -0.5, -0.8,  # direction 12h: LONG
    0.018,   # max_drawdown_1h: 1.8%
    0.028,   # max_rally_1h: 2.8%
    0.022,   # max_drawdown_4h: 2.2%
    0.035    # max_rally_4h: 3.5%
])

# Расчет Expected Value
EV = 0.2 * 0.012 + 0.3 * 0.018 + 0.4 * 0.025 + 0.1 * 0.020
# EV = 0.0024 + 0.0054 + 0.0100 + 0.0020 = 0.0198 (1.98%)

# Проверка направления
directions = apply_softmax([[2.5, -0.8, -1.2], [2.2, -0.6, -1.0], 
                           [2.8, -0.9, -1.5], [2.0, -0.5, -0.8]])
# Все 4 таймфрейма указывают на LONG ✅

# Kelly Criterion
win_prob = 1/(1 + exp(-0.0198/0.02)) = 0.729
kelly = (0.729 * 0.028 - 0.271 * 0.018) / 0.028 = 0.554
safe_kelly = 0.554 * 0.25 = 0.139 (13.9% от Kelly)

# Размер позиции
capital = $500
volatility_adj = min(0.02/0.0265, 1.5) = 0.755
position = 500 * 0.0139 * 0.755 * 0.8 = $4.20

# Dynamic TP/SL
entry_price = $50,000 (BTC)
stop_loss = 50000 * (1 - 0.018 * 1.2) = $48,920 (-2.16%)
take_profit = 50000 * (1 + 0.035 * 0.9) = $51,575 (+3.15%)
risk_reward = 3.15 / 2.16 = 1.46

# Quality Score
quality = 0.25*0.80 + 0.25*0.75 + 0.25*(1.46/3) + 0.25*(0.0198/0.02)
quality = 0.200 + 0.188 + 0.122 + 0.248 = 0.758 ✅

# РЕЗУЛЬТАТ: Открываем LONG позицию $4.20
```

### Пример 2: Отклоненный SHORT сигнал

```python
# Входные данные от модели
model_output = torch.tensor([
    -0.003,  # returns_15m: -0.3%
    -0.005,  # returns_1h: -0.5%
    -0.008,  # returns_4h: -0.8%
    -0.006,  # returns_12h: -0.6%
    -0.5, 1.2, -0.3,  # direction 15m: SHORT (слабая уверенность)
    -0.8, 1.8, -0.5,  # direction 1h: SHORT
    0.2, 0.3, -0.1,   # direction 4h: NEUTRAL ⚠️
    -0.6, 1.4, -0.4,  # direction 12h: SHORT
    0.025,   # max_drawdown_1h: 2.5%
    0.020,   # max_rally_1h: 2.0%
    0.030,   # max_drawdown_4h: 3.0%
    0.025    # max_rally_4h: 2.5%
])

# Расчет Expected Value
EV = 0.2*(-0.003) + 0.3*(-0.005) + 0.4*(-0.008) + 0.1*(-0.006)
# EV = -0.0006 - 0.0015 - 0.0032 - 0.0006 = -0.0059 (-0.59%)

# Проверка направления
# 3 из 4 таймфреймов SHORT (4h - NEUTRAL) ⚠️
# Согласованность: 75%

# Quality Score
quality = 0.25*0.45 + 0.25*0.40 + 0.25*(0.8/3) + 0.25*(0.0059/0.02)
quality = 0.113 + 0.100 + 0.067 + 0.074 = 0.354 ❌

# РЕЗУЛЬТАТ: Сигнал отклонен (quality < 0.45)
```

### Пример 3: Корректировка по волатильности

```python
# Высокая волатильность
risk_metrics = {
    'max_drawdown_4h': 0.045,  # 4.5%
    'max_rally_4h': 0.052       # 5.2%
}

implied_volatility = (0.045 + 0.052) / 2 = 0.0485
target_volatility = 0.02
volatility_multiplier = 0.02 / 0.0485 = 0.412

# Базовый размер позиции: $10
# Скорректированный размер: $10 * 0.412 = $4.12

# При низкой волатильности
risk_metrics = {
    'max_drawdown_4h': 0.008,  # 0.8%
    'max_rally_4h': 0.012       # 1.2%
}

implied_volatility = (0.008 + 0.012) / 2 = 0.010
volatility_multiplier = min(0.02 / 0.010, 1.5) = 1.5

# Базовый размер: $10
# Скорректированный размер: $10 * 1.5 = $15
```

## 📈 Реальные торговые сценарии

### Сценарий 1: Бычий тренд с высокой уверенностью

```python
# Сильный восходящий тренд на BTC
market_conditions = {
    'trend': 'strong_bullish',
    'btc_price': 52000,
    'volume': 'high',
    'volatility': 'normal'
}

# ML предсказания
predictions = {
    'expected_value': 0.024,      # +2.4%
    'confidence': 0.85,
    'direction_agreement': 4/4,   # Все таймфреймы LONG
    'max_rally_4h': 0.038,        # +3.8%
    'max_drawdown_1h': 0.012      # -1.2%
}

# Торговые параметры
trade_params = {
    'entry': 52000,
    'stop_loss': 51376,           # -1.2% * 1.2 = -1.44%
    'take_profit_1': 52780,       # +1.5%
    'take_profit_2': 53300,       # +2.5%
    'take_profit_3': 53976,       # +3.8% * 0.9 = +3.42%
    'position_size': 15.50,       # Kelly optimal
    'risk_reward': 2.38
}

# Исполнение
execute_order(
    symbol='BTC/USDT',
    side='buy',
    amount=15.50/52000,
    sl=51376,
    tp_levels=[52780, 53300, 53976],
    tp_percentages=[40, 40, 20]
)
```

### Сценарий 2: Медвежий разворот

```python
# Признаки разворота на ETH
market_conditions = {
    'trend': 'weakening_bullish',
    'eth_price': 3200,
    'rsi': 78,                    # Перекупленность
    'volume': 'declining'
}

# ML предсказания
predictions = {
    'expected_value': -0.018,     # -1.8%
    'confidence': 0.72,
    'direction_agreement': 4/4,   # Все SHORT
    'max_drawdown_4h': 0.032,     # -3.2%
    'max_rally_1h': 0.015         # +1.5%
}

# Торговые параметры для SHORT
trade_params = {
    'entry': 3200,
    'stop_loss': 3258,            # +1.5% * 1.2 = +1.8%
    'take_profit_1': 3152,        # -1.5%
    'take_profit_2': 3120,        # -2.5%
    'take_profit_3': 3098,        # -3.2% * 0.9 = -2.88%
    'position_size': 8.75,
    'risk_reward': 1.60
}
```

### Сценарий 3: Боковик с фильтрацией

```python
# Боковое движение на SOL
market_conditions = {
    'trend': 'ranging',
    'sol_price': 120,
    'atr': 2.5,
    'bollinger_position': 'middle'
}

# ML предсказания (слабые)
predictions = {
    'expected_value': 0.006,      # +0.6%
    'confidence': 0.42,
    'direction_agreement': 2/4,   # Разногласия
    'quality_score': 0.38         # < 0.45
}

# РЕЗУЛЬТАТ: Сигнал отфильтрован
# - Low quality score (0.38 < 0.45)
# - Weak direction agreement (50%)
# - Low expected value (0.6% < 0.8%)
action = "NO_TRADE"
```

## 🔧 Отладка и диагностика

### Проверка компонентов Quality Score

```python
def diagnose_signal_quality(signal):
    """Диагностика причин низкого качества"""
    
    components = {
        'confidence': signal.confidence,
        'strength': signal.strength,
        'risk_reward': signal.risk_reward,
        'expected_value': signal.expected_value
    }
    
    print("Quality Score Components:")
    print(f"Confidence: {components['confidence']:.3f} (weight: 25%)")
    print(f"Strength: {components['strength']:.3f} (weight: 25%)")
    print(f"Risk/Reward: {components['risk_reward']:.2f} (weight: 25%)")
    print(f"Expected Value: {components['expected_value']:.3f} (weight: 25%)")
    
    # Identify weak components
    if components['confidence'] < 0.5:
        print("⚠️ Low confidence - check direction agreement")
    if components['strength'] < 0.4:
        print("⚠️ Weak signal strength - check feature values")
    if components['risk_reward'] < 1.5:
        print("⚠️ Poor risk/reward - adjust TP/SL levels")
    if components['expected_value'] < 0.008:
        print("⚠️ Low expected value - wait for better setup")

# Пример использования
signal = MLSignal(
    confidence=0.35,
    strength=0.45,
    risk_reward=1.2,
    expected_value=0.006
)
diagnose_signal_quality(signal)

# Output:
# Quality Score Components:
# Confidence: 0.350 (weight: 25%)
# Strength: 0.450 (weight: 25%)
# Risk/Reward: 1.20 (weight: 25%)
# Expected Value: 0.006 (weight: 25%)
# ⚠️ Low confidence - check direction agreement
# ⚠️ Poor risk/reward - adjust TP/SL levels
# ⚠️ Low expected value - wait for better setup
```

### Мониторинг Kelly Criterion

```python
def monitor_kelly_efficiency(trades_history):
    """Проверка эффективности Kelly sizing"""
    
    kelly_trades = []
    
    for trade in trades_history:
        kelly_fraction = trade['kelly_fraction']
        actual_return = trade['pnl_percent']
        expected_return = trade['expected_value']
        
        efficiency = actual_return / expected_return if expected_return != 0 else 0
        
        kelly_trades.append({
            'symbol': trade['symbol'],
            'kelly_f': kelly_fraction,
            'expected': expected_return,
            'actual': actual_return,
            'efficiency': efficiency
        })
    
    # Статистика
    avg_efficiency = np.mean([t['efficiency'] for t in kelly_trades])
    win_rate = len([t for t in kelly_trades if t['actual'] > 0]) / len(kelly_trades)
    
    print(f"Kelly Efficiency: {avg_efficiency:.2%}")
    print(f"Win Rate: {win_rate:.2%}")
    
    if avg_efficiency < 0.6:
        print("⚠️ Low Kelly efficiency - consider reducing fraction")
    if win_rate < 0.45:
        print("⚠️ Low win rate - review signal filtering")
```

## 📊 Формулы и расчеты

### Основные математические формулы

```python
# 1. Expected Value (EV)
def calculate_expected_value(returns, weights=[0.2, 0.3, 0.4, 0.1]):
    """
    EV = Σ(weight_i * return_i)
    where i ∈ {15m, 1h, 4h, 12h}
    """
    return sum(w * r for w, r in zip(weights, returns))

# 2. Kelly Criterion
def kelly_criterion(win_prob, avg_win, avg_loss):
    """
    f = (p*b - q)/b
    where:
    - f = optimal fraction
    - p = win probability
    - b = win/loss ratio
    - q = 1 - p
    """
    b = avg_win / avg_loss
    f = (win_prob * b - (1 - win_prob)) / b
    return max(0, min(f, 1))  # Clamp to [0, 1]

# 3. Win Probability from EV
def win_probability_from_ev(expected_value, sensitivity=0.02):
    """
    P(win) = 1 / (1 + e^(-EV/sensitivity))
    Sigmoid function for probability estimation
    """
    return 1 / (1 + np.exp(-expected_value / sensitivity))

# 4. Volatility Adjustment
def volatility_multiplier(implied_vol, target_vol=0.02):
    """
    multiplier = min(target_vol / implied_vol, 1.5)
    Reduces position size in high volatility
    """
    return min(target_vol / implied_vol, 1.5)

# 5. Risk-Adjusted Position Size
def calculate_position_size(capital, kelly_f, vol_mult, confidence):
    """
    size = capital * kelly_f * vol_mult * confidence
    Multi-factor position sizing
    """
    return capital * kelly_f * vol_mult * confidence

# 6. Dynamic Stop Loss
def dynamic_stop_loss(entry_price, max_drawdown, buffer=1.2):
    """
    SL = entry_price * (1 - max_drawdown * buffer)
    Adaptive SL based on historical drawdown
    """
    return entry_price * (1 - max_drawdown * buffer)

# 7. Quality Score
def quality_score(confidence, strength, risk_reward, expected_value):
    """
    QS = 0.25*conf + 0.25*str + 0.25*RR/3 + 0.25*EV/0.02
    Normalized weighted average
    """
    return (
        0.25 * confidence +
        0.25 * strength +
        0.25 * min(risk_reward / 3, 1) +
        0.25 * min(abs(expected_value) / 0.02, 1)
    )
```

## 🎯 Оптимальные параметры по инструментам

### BTC/USDT
```python
btc_params = {
    'min_expected_value': 0.008,   # 0.8%
    'min_confidence': 0.30,
    'kelly_fraction': 0.25,
    'max_position_pct': 0.025,     # 2.5%
    'sl_buffer': 1.2,
    'tp_aggressive': 0.9,
    'tp_conservative': 0.8
}
```

### ETH/USDT
```python
eth_params = {
    'min_expected_value': 0.010,   # 1.0%
    'min_confidence': 0.35,
    'kelly_fraction': 0.20,
    'max_position_pct': 0.020,     # 2.0%
    'sl_buffer': 1.3,
    'tp_aggressive': 0.85,
    'tp_conservative': 0.75
}
```

### Altcoins (SOL, MATIC, etc.)
```python
alt_params = {
    'min_expected_value': 0.012,   # 1.2%
    'min_confidence': 0.40,
    'kelly_fraction': 0.15,
    'max_position_pct': 0.015,     # 1.5%
    'sl_buffer': 1.5,
    'tp_aggressive': 0.8,
    'tp_conservative': 0.7
}
```

---

*Примеры обновлены: 24.08.2025*