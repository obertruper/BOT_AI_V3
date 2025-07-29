# Документация indicator_strategy для BOT Trading v3

## Общая концепция

**indicator_strategy** - это модульная торговая стратегия, основанная на анализе технических индикаторов для криптовалютного трейдинга с горизонтом 1-7 дней. Стратегия использует комплексную систему скоринга для принятия торговых решений.

## Архитектура системы

### 1. Структура классов

```
indicator_strategy/
├── __init__.py                 # Точка входа
├── core/                       # Основные компоненты
│   ├── strategy.py            # Главный класс стратегии
│   ├── scoring_engine.py      # Система скоринга
│   └── signal_processor.py    # Обработка сигналов
├── indicators/                 # Технические индикаторы
│   ├── trend/                 # Трендовые индикаторы
│   │   ├── ema.py            # Exponential Moving Average
│   │   ├── sma.py            # Simple Moving Average
│   │   └── macd.py           # MACD
│   ├── momentum/              # Индикаторы импульса
│   │   ├── rsi.py            # Relative Strength Index
│   │   ├── stochastic.py     # Stochastic Oscillator
│   │   └── williams_r.py     # Williams %R
│   ├── volume/                # Объёмные индикаторы
│   │   ├── obv.py            # On-Balance Volume
│   │   ├── vwap.py           # Volume Weighted Average Price
│   │   └── volume_profile.py  # Volume Profile
│   └── volatility/           # Индикаторы волатильности
│       ├── bollinger.py      # Bollinger Bands
│       ├── atr.py            # Average True Range
│       └── vix_crypto.py     # Crypto Volatility Index
├── risk_management/           # Управление рисками
│   ├── position_sizing.py    # Расчёт размера позиции
│   ├── stop_loss.py          # Stop Loss логика
│   └── take_profit.py        # Take Profit логика
├── backtesting/              # Бэктестинг
│   ├── data_handler.py       # Обработка данных
│   ├── metrics.py            # Метрики производительности
│   └── validator.py          # Валидация стратегии
└── config/                   # Конфигурация
    ├── indicators.yaml       # Настройки индикаторов
    ├── scoring.yaml          # Система весов
    └── risk_params.yaml      # Параметры рисков
```

### 2. Ключевые принципы архитектуры

1. **Модульность**: Каждый индикатор - отдельный класс
2. **Масштабируемость**: Легко добавлять новые индикаторы
3. **Конфигурируемость**: Все параметры через YAML файлы
4. **Тестируемость**: Каждый компонент покрыт unit-тестами
5. **Асинхронность**: Поддержка async/await для высокой производительности

## Система скоринга и весов

### Структура весов (общий вес = 100%)

```yaml
# config/scoring.yaml
scoring_weights:
  trend:        30%    # Трендовые индикаторы
  momentum:     25%    # Индикаторы импульса
  volume:       25%    # Объёмные индикаторы
  volatility:   20%    # Индикаторы волатильности

# Детализация по индикаторам в каждой категории
trend_indicators:
  ema_crossover:    40%    # 12% от общего веса
  macd:            35%    # 10.5% от общего веса
  sma_trend:       25%    # 7.5% от общего веса

momentum_indicators:
  rsi:             40%    # 10% от общего веса
  stochastic:      35%    # 8.75% от общего веса
  williams_r:      25%    # 6.25% от общего веса

volume_indicators:
  obv:             40%    # 10% от общего веса
  vwap:            35%    # 8.75% от общего веса
  volume_profile:  25%    # 6.25% от общего веса

volatility_indicators:
  bollinger:       50%    # 10% от общего веса
  atr:             30%    # 6% от общего веса
  vix_crypto:      20%    # 4% от общего веса
```

### Алгоритм скоринга

```python
class ScoringEngine:
    def calculate_signal_strength(self, indicators_data: Dict) -> float:
        """
        Расчёт силы сигнала от -100 до +100

        -100 до -50: Сильный медвежий сигнал
        -50 до -20:  Слабый медвежий сигнал
        -20 до +20:  Нейтральная зона
        +20 до +50:  Слабый бычий сигнал
        +50 до +100: Сильный бычий сигнал
        """
        total_score = 0.0

        # Трендовые индикаторы (30%)
        trend_score = self._calculate_trend_score(indicators_data['trend'])
        total_score += trend_score * 0.30

        # Импульсные индикаторы (25%)
        momentum_score = self._calculate_momentum_score(indicators_data['momentum'])
        total_score += momentum_score * 0.25

        # Объёмные индикаторы (25%)
        volume_score = self._calculate_volume_score(indicators_data['volume'])
        total_score += volume_score * 0.25

        # Индикаторы волатильности (20%)
        volatility_score = self._calculate_volatility_score(indicators_data['volatility'])
        total_score += volatility_score * 0.20

        return min(max(total_score, -100), 100)
```

## Технические индикаторы и формулы

### 1. Трендовые индикаторы

#### EMA (Exponential Moving Average)

```python
# Формула EMA
# EMA[today] = (Price[today] * multiplier) + (EMA[yesterday] * (1 - multiplier))
# multiplier = 2 / (period + 1)

class EMAIndicator:
    def __init__(self, fast_period: int = 12, slow_period: int = 26):
        self.fast_period = fast_period
        self.slow_period = slow_period

    def calculate(self, prices: List[float]) -> Dict[str, float]:
        fast_ema = self._ema(prices, self.fast_period)
        slow_ema = self._ema(prices, self.slow_period)

        # Сигнал: пересечение быстрой и медленной EMA
        signal = 1 if fast_ema > slow_ema else -1
        strength = abs(fast_ema - slow_ema) / slow_ema * 100

        return {
            'signal': signal,
            'strength': min(strength, 100),
            'fast_ema': fast_ema,
            'slow_ema': slow_ema
        }
```

#### MACD (Moving Average Convergence Divergence)

```python
# MACD = EMA12 - EMA26
# Signal Line = EMA9 of MACD
# Histogram = MACD - Signal Line

class MACDIndicator:
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def calculate(self, prices: List[float]) -> Dict[str, float]:
        ema_fast = self._ema(prices, self.fast)
        ema_slow = self._ema(prices, self.slow)

        macd = ema_fast - ema_slow
        signal_line = self._ema([macd], self.signal)
        histogram = macd - signal_line

        # Сигнал на основе пересечения MACD и сигнальной линии
        signal = 1 if macd > signal_line else -1
        strength = abs(histogram) / abs(macd) * 100 if macd != 0 else 0

        return {
            'signal': signal,
            'strength': min(strength, 100),
            'macd': macd,
            'signal_line': signal_line,
            'histogram': histogram
        }
```

### 2. Индикаторы импульса

#### RSI (Relative Strength Index)

```python
# RSI = 100 - (100 / (1 + RS))
# RS = Average Gain / Average Loss

class RSIIndicator:
    def __init__(self, period: int = 14):
        self.period = period

    def calculate(self, prices: List[float]) -> Dict[str, float]:
        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))

        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # Сигналы RSI для криптовалют (адаптированные уровни)
        if rsi > 75:      # Перекупленность
            signal = -1
            strength = min((rsi - 75) * 4, 100)
        elif rsi < 25:    # Перепроданность
            signal = 1
            strength = min((25 - rsi) * 4, 100)
        else:             # Нейтральная зона
            signal = 0
            strength = 0

        return {
            'signal': signal,
            'strength': strength,
            'rsi': rsi
        }
```

### 3. Объёмные индикаторы

#### OBV (On-Balance Volume)

```python
class OBVIndicator:
    def calculate(self, prices: List[float], volumes: List[float]) -> Dict[str, float]:
        obv = [volumes[0]]

        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif prices[i] < prices[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])

        # Анализ тренда OBV
        obv_trend = self._calculate_trend(obv[-20:])  # Последние 20 периодов

        return {
            'signal': 1 if obv_trend > 0 else -1,
            'strength': min(abs(obv_trend) * 10, 100),
            'obv': obv[-1]
        }
```

### 4. Индикаторы волатильности

#### Bollinger Bands

```python
class BollingerBandsIndicator:
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev

    def calculate(self, prices: List[float]) -> Dict[str, float]:
        sma = sum(prices[-self.period:]) / self.period
        variance = sum([(x - sma) ** 2 for x in prices[-self.period:]]) / self.period
        std = variance ** 0.5

        upper_band = sma + (std * self.std_dev)
        lower_band = sma - (std * self.std_dev)
        current_price = prices[-1]

        # Позиция цены относительно полос
        band_width = upper_band - lower_band
        position = (current_price - lower_band) / band_width

        # Сигналы на основе позиции
        if position > 0.8:        # Близко к верхней границе
            signal = -1
            strength = min((position - 0.8) * 500, 100)
        elif position < 0.2:      # Близко к нижней границе
            signal = 1
            strength = min((0.2 - position) * 500, 100)
        else:
            signal = 0
            strength = 0

        return {
            'signal': signal,
            'strength': strength,
            'upper_band': upper_band,
            'middle_band': sma,
            'lower_band': lower_band,
            'position': position
        }
```

#### ATR (Average True Range)

```python
class ATRIndicator:
    def __init__(self, period: int = 14):
        self.period = period

    def calculate(self, highs: List[float], lows: List[float],
                 closes: List[float]) -> Dict[str, float]:
        true_ranges = []

        for i in range(1, len(closes)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            true_ranges.append(max(tr1, tr2, tr3))

        atr = sum(true_ranges[-self.period:]) / self.period
        current_price = closes[-1]

        # Волатильность как процент от цены
        volatility_pct = (atr / current_price) * 100

        # Адаптивные уровни для криптовалют
        if volatility_pct > 8:        # Высокая волатильность
            signal = -1  # Осторожность
            strength = min((volatility_pct - 8) * 10, 100)
        elif volatility_pct < 2:      # Низкая волатильность
            signal = 1   # Возможный прорыв
            strength = min((2 - volatility_pct) * 50, 100)
        else:
            signal = 0
            strength = 0

        return {
            'signal': signal,
            'strength': strength,
            'atr': atr,
            'volatility_pct': volatility_pct
        }
```

## Управление рисками

### Параметры для позиций 1-7 дней

```yaml
# config/risk_params.yaml
risk_management:
  position_sizing:
    max_position_size: 5%      # Максимум 5% депозита на позицию
    volatility_adjustment: true # Уменьшение при высокой волатильности
    min_position_size: 0.5%    # Минимальный размер позиции

  stop_loss:
    fixed_percent: 3%          # Фиксированный SL 3%
    atr_multiplier: 2.0        # Динамический SL на основе ATR
    trailing_activation: 2%    # Активация трейлинг-стопа
    trailing_distance: 1%      # Расстояние трейлинг-стопа

  take_profit:
    target_multiplier: 2.0     # TP = SL * 2 (соотношение 1:2)
    partial_close: 50%         # Частичное закрытие при достижении 1:1
    scale_out_levels:          # Уровни фиксации прибыли
      - level: 1.0, percent: 25%
      - level: 1.5, percent: 25%
      - level: 2.0, percent: 50%

  max_correlation: 0.7       # Максимальная корреляция между позициями
  max_daily_risk: 2%         # Максимальный дневной риск
  max_drawdown: 10%          # Максимальная просадка
```

### Расчёт размера позиции

```python
class PositionSizing:
    def calculate_position_size(self,
                              account_balance: float,
                              entry_price: float,
                              stop_loss: float,
                              volatility: float,
                              signal_strength: float) -> float:
        """
        Расчёт размера позиции с учётом:
        - Риска на сделку (% от депозита)
        - Волатильности актива
        - Силы сигнала
        """
        # Базовый риск
        base_risk = account_balance * 0.02  # 2% от депозита

        # Корректировка на волатильность
        if volatility > 8:
            volatility_multiplier = 0.5
        elif volatility < 2:
            volatility_multiplier = 1.2
        else:
            volatility_multiplier = 1.0

        # Корректировка на силу сигнала
        signal_multiplier = 0.5 + (signal_strength / 100) * 0.5

        # Расчёт размера позиции
        risk_per_share = abs(entry_price - stop_loss)
        position_size = (base_risk * volatility_multiplier * signal_multiplier) / risk_per_share

        # Ограничения
        max_position = account_balance * 0.05  # Максимум 5%
        min_position = account_balance * 0.005 # Минимум 0.5%

        return min(max(position_size, min_position), max_position)
```

## Структура данных для бэктестинга

### Формат исторических данных

```python
@dataclass
class MarketData:
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    # Дополнительные поля для криптовалют
    quote_volume: float = None
    trades_count: int = None
    buy_volume: float = None
    sell_volume: float = None

@dataclass
class IndicatorResult:
    timestamp: datetime
    symbol: str
    indicator_name: str
    signal: int           # -1, 0, 1
    strength: float       # 0-100
    raw_values: Dict      # Сырые значения индикатора

@dataclass
class TradingSignal:
    timestamp: datetime
    symbol: str
    signal_type: str      # 'BUY', 'SELL', 'HOLD'
    confidence: float     # 0-100
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    indicators_used: List[str]
    reasoning: str
```

### Метрики производительности

```python
class PerformanceMetrics:
    def calculate_metrics(self, trades: List[Trade]) -> Dict[str, float]:
        """Расчёт ключевых метрик для валидации стратегии"""

        returns = [trade.pnl_pct for trade in trades]

        # Базовые метрики
        total_return = sum(returns)
        win_rate = len([r for r in returns if r > 0]) / len(returns)
        avg_win = np.mean([r for r in returns if r > 0])
        avg_loss = np.mean([r for r in returns if r < 0])

        # Риск-метрики
        sharpe_ratio = self._calculate_sharpe(returns)
        max_drawdown = self._calculate_max_drawdown(returns)
        sortino_ratio = self._calculate_sortino(returns)

        # Специфичные для криптовалют
        volatility = np.std(returns) * np.sqrt(365)  # Годовая волатильность
        calmar_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0

        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'calmar_ratio': calmar_ratio,
            'trades_count': len(trades),
            'avg_trade_duration': np.mean([t.duration_hours for t in trades])
        }
```

## Требования к данным

### Минимальный объём для бэктестинга

- **Период**: 2 года исторических данных (730 дней)
- **Таймфрейм**: 1-часовые свечи (17,520 свечей)
- **Валидация**: 20% данных для out-of-sample тестирования
- **Walk-forward**: Скользящее окно 6 месяцев

### Качество данных

- Отсутствие пропусков > 2 часов подряд
- Корректировка на сплиты и дивиденды (для традиционных активов)
- Фильтрация аномальных объёмов и цен
- Синхронизация данных между различными биржами

## Кросс-верификация с тремя AI системами

✅ **ЗАВЕРШЕНА**: Экспертные консультации от ChatGPT o3-pro, Grok v4, Claude Opus 4
📊 **Детальный анализ**: `docs/AI_VERIFICATION_REPORTS/INDICATOR_STRATEGY_CROSS_VERIFICATION.md`

### Синтезированные рекомендации от трех AI систем

#### Финальные параметры (консенсус)

```python
RECOMMENDED_PARAMETERS = {
    'indicators': {
        'rsi': {'period': 14, 'levels': [25, 75]},  # Claude (крипто-адаптация)
        'macd': {'fast': 12, 'slow': 26, 'signal': 9},  # ChatGPT+Grok консенсус
        'ema': {'periods': [12, 26, 50, 200]},  # Объединение всех подходов
        'bb': {'period': 20, 'std': 2.0, 'squeeze_detection': True},  # Claude
        'atr': {'period': 14}  # Единогласно
    },
    'scoring': {
        'method': 'dynamic_weights',  # Claude (продвинутый)
        'base_weights': {'rsi': 0.25, 'macd': 0.30, 'ema': 0.20, 'bb': 0.15, 'atr': 0.10},
        'regime_multipliers': {  # Адаптивность Claude
            'trending': {'macd': 1.3, 'ema': 1.5},
            'ranging': {'rsi': 1.4, 'bb': 1.4},
            'high_vol': {'atr': 1.5, 'ema': 1.2}
        }
    },
    'risk_management': {
        'position_sizing': 'kelly_limited',  # Claude (математически оптимальный)
        'max_risk_per_trade': 0.02,  # 2% консенсус
        'sl_multiplier': 2.0,  # Среднее из всех рекомендаций
        'tp_strategy': 'multi_level',  # Claude (более эффективный)
        'tp_levels': [1.5, 3.0, 5.0]
    }
}
```

## Следующие шаги

1. ✅ **ЗАВЕРШЕНО**: Получение экспертных мнений от 3 AI систем
2. ✅ **ЗАВЕРШЕНО**: Кросс-верификационный анализ и синтез рекомендаций
3. **[ПРИОРИТЕТ]** Создание базовых классов с синтезированной архитектурой
4. **[ПЛАНИРУЕТСЯ]** Реализация индикаторов с консенсус-параметрами
5. **[ПЛАНИРУЕТСЯ]** Интеграция динамической системы скоринга Claude
6. **[ПЛАНИРУЕТСЯ]** Comprehensive бэктестинг на исторических данных

---

**Статус документа**: ✅ ЗАВЕРШЕН (базовая документация + AI кросс-верификация)
**Последнее обновление**: 13 июля 2025, 15:00
**Версия**: 2.0-verified
**AI Консультации**: ✅ ChatGPT o3-pro, ✅ Grok v4, ✅ Claude Opus 4 (все завершены)
**Кросс-верификация**: ✅ Полная, с синтезированными рекомендациями
