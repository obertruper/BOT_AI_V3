# 🎯 Детальный план разработки торговых стратегий BOT Trading v3

**Дата создания**: 13 июля 2025
**Фокус**: Спекулятивная торговля 1-7 дней
**Приоритет**: indicator_strategy → система скоринга → контроль доходности

---

## 📊 Текущее состояние

### ✅ Что готово

- **StrategyManager** (639 строк) - полностью реализован
- **Архитектура стратегий** - определена структура папок
- **AI Synthesized Scalping Strategy** - готовая стратегия скальпинга

### ❌ Что нужно создать

- Базовые компоненты (ABC, Registry, Factory)
- Все конкретные стратегии (только пустые папки)
- Система индикаторов и скоринга
- Конфигурации стратегий

---

## 🏗️ Этапы разработки

### ЭТАП 1: Критические базовые компоненты (1-2 дня)

#### 1.1 Базовый абстрактный класс

```python
# strategies/base/strategy_abc.py
class StrategyABC(ABC):
    """Базовый абстрактный класс для всех торговых стратегий"""

    @abstractmethod
    async def analyze(self, market_data: MarketData) -> Signal

    @abstractmethod
    async def generate_signals(self, timeframe: str) -> List[Signal]

    @abstractmethod
    def get_risk_parameters(self) -> RiskParameters
```

#### 1.2 Реестр стратегий

```python
# strategies/registry.py
class StrategyRegistry:
    """Централизованный реестр всех стратегий"""

    _strategies: Dict[str, Type[StrategyABC]] = {}

    @classmethod
    def register(cls, name: str, strategy_class: Type[StrategyABC])

    @classmethod
    def get_strategy(cls, name: str) -> Type[StrategyABC]
```

#### 1.3 Фабрика стратегий

```python
# strategies/factory.py
class StrategyFactory:
    """Фабрика для создания экземпляров стратегий"""

    @staticmethod
    def create_strategy(name: str, config: Dict) -> StrategyABC
```

### ЭТАП 2: Indicator Strategy Foundation (3-5 дней)

#### 2.1 Архитектура indicator_strategy/

```
indicator_strategy/
├── __init__.py
├── base_indicator_strategy.py      # Базовый класс индикаторных стратегий
├── indicators/                     # Модуль индикаторов
│   ├── __init__.py
│   ├── trend.py                   # Трендовые индикаторы (EMA, SMA, MACD)
│   ├── momentum.py                # Импульсные (RSI, Stochastic, Williams %R)
│   ├── volatility.py              # Волатильность (Bollinger Bands, ATR)
│   ├── volume.py                  # Объемные (VWAP, OBV, Volume Profile)
│   └── custom.py                  # Кастомные индикаторы
├── scoring/                       # Система скоринга
│   ├── __init__.py
│   ├── weight_manager.py          # Управление весами индикаторов
│   ├── score_calculator.py        # Расчет итогового скора
│   └── performance_tracker.py     # Отслеживание производительности
├── strategies/                    # Конкретные стратегии
│   ├── __init__.py
│   ├── multi_timeframe_strategy.py # Мульти-таймфрейм стратегия
│   ├── swing_trading_strategy.py   # Свинг-трейдинг (1-7 дней)
│   └── momentum_reversal_strategy.py # Импульс + разворот
└── configs/                       # Конфигурации
    ├── conservative_1d.yaml       # Консервативная на 1 день
    ├── aggressive_3d.yaml         # Агрессивная на 3 дня
    └── balanced_7d.yaml           # Сбалансированная на 7 дней
```

#### 2.2 Приоритетные индикаторы для краткосрочной торговли

##### **Категория 1: Трендовые (вес 30%)**

- **EMA 9/21/50** - определение тренда и динамическая поддержка/сопротивление
- **MACD (12,26,9)** - конвергенция/дивергенция для входов
- **Bollinger Bands (20,2)** - волатильность и границы тренда

##### **Категория 2: Импульсные (вес 25%)**

- **RSI (14)** - перекупленность/перепроданность
- **Stochastic (14,3,3)** - дополнительный импульс
- **Williams %R (14)** - обратный к RSI

##### **Категория 3: Объемные (вес 25%)**

- **VWAP** - средневзвешенная цена по объему
- **Volume Oscillator** - подтверждение движений
- **OBV** - накопление/распределение

##### **Категория 4: Волатильность (вес 20%)**

- **ATR (14)** - для расчета стоп-лоссов
- **Volatility Index** - оценка рыночного страха
- **Price Rate of Change** - скорость изменения цены

### ЭТАП 3: Система скоринга и весов (2-3 дня)

#### 3.1 Матрица скоринга

```python
class IndicatorScoringMatrix:
    """Матрица скоринга для комбинированной оценки индикаторов"""

    def __init__(self):
        self.weights = {
            'trend': 0.30,      # 30% - направление тренда
            'momentum': 0.25,   # 25% - импульс движения
            'volume': 0.25,     # 25% - подтверждение объемом
            'volatility': 0.20  # 20% - рыночная волатильность
        }

    def calculate_composite_score(self, indicators: Dict) -> float:
        """Расчет итогового скора (-100 до +100)"""
        score = 0
        for category, weight in self.weights.items():
            category_score = self._calculate_category_score(indicators[category])
            score += category_score * weight
        return score

    def adjust_weights_by_performance(self, performance_data: Dict):
        """Динамическая корректировка весов на основе производительности"""
        pass
```

#### 3.2 Алгоритм присвоения весов

##### **Статические веса (базовые):**

- **Тренд EMA**: 15% (основной тренд)
- **MACD**: 10% (сигналы входа)
- **RSI**: 12% (перекупленность)
- **VWAP**: 13% (справедливая цена)
- **Bollinger Bands**: 8% (границы)
- **Volume**: 12% (подтверждение)
- **ATR**: 10% (волатильность)
- **Остальные**: распределено по важности

##### **Динамические веса:**

```python
def adjust_weights_by_market_condition(self, market_condition: str):
    """Корректировка весов в зависимости от рыночных условий"""

    if market_condition == "trending":
        self.weights['trend'] += 0.10
        self.weights['momentum'] -= 0.05
        self.weights['volatility'] -= 0.05

    elif market_condition == "sideways":
        self.weights['momentum'] += 0.10
        self.weights['volatility'] += 0.05
        self.weights['trend'] -= 0.15
```

### ЭТАП 4: Датасет и исторические данные (1-2 дня)

#### 4.1 Структура датасета для бэктестинга

```python
class StrategyDataset:
    """Датасет для бэктестинга стратегий"""

    def __init__(self, symbol: str, timeframe: str, history_days: int = 365):
        self.symbol = symbol
        self.timeframe = timeframe
        self.history_days = history_days
        self.data = self._load_historical_data()
        self.indicators = self._calculate_all_indicators()

    def get_training_data(self, train_ratio: float = 0.7) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Разделение на обучающую и тестовую выборки"""
        pass

    def calculate_strategy_performance(self, signals: List[Signal]) -> PerformanceMetrics:
        """Расчет метрик производительности стратегии"""
        pass
```

#### 4.2 Минимальные требования к данным

- **Исторические данные**: минимум 365 дней для надежного бэктестинга
- **Временные фреймы**: 1h, 4h, 1d для мульти-таймфрейм анализа
- **Валидация**: out-of-sample тестирование на 30% данных
- **Symbols**: BTC/USDT, ETH/USDT, Top-10 альткоинов

### ЭТАП 5: Первая рабочая стратегия (3-4 дня)

#### 5.1 SwingTradingStrategy (1-7 дней)

```python
class SwingTradingStrategy(BaseIndicatorStrategy):
    """
    Спекулятивная стратегия для позиций 1-7 дней

    Логика:
    - Entry: Confluence 3+ индикаторов в одном направлении
    - Exit: Take Profit на 2-5% или Stop Loss на 1-2%
    - Position Size: 2-5% от портфеля в зависимости от конфиденса
    """

    def __init__(self, config: SwingTradingConfig):
        self.timeframes = ['4h', '1d']  # Основные таймфреймы
        self.target_hold_days = config.target_hold_days  # 1-7 дней
        self.min_confidence = 0.65  # Минимальный скор для входа

    async def analyze(self, market_data: MarketData) -> Signal:
        # 1. Анализ тренда на старшем таймфрейме (1d)
        daily_trend = self._analyze_daily_trend(market_data)

        # 2. Поиск точки входа на младшем таймфрейме (4h)
        entry_signal = self._find_entry_signal(market_data)

        # 3. Расчет риск/прибыль
        risk_reward = self._calculate_risk_reward(market_data)

        # 4. Итоговое решение
        return self._make_decision(daily_trend, entry_signal, risk_reward)
```

#### 5.2 Конфигурация для спекулятивной торговли

```yaml
# configs/swing_1_7_days.yaml
strategy_name: "SwingTrading1-7D"
timeframes: ["4h", "1d"]
target_hold_period:
  min_days: 1
  max_days: 7
  optimal_days: 3

indicators:
  trend:
    ema_fast: 9
    ema_slow: 21
    macd: [12, 26, 9]
  momentum:
    rsi_period: 14
    stochastic: [14, 3, 3]
  volume:
    vwap_period: 20
    volume_sma: 20
  volatility:
    bollinger_bands: [20, 2]
    atr_period: 14

risk_management:
  max_position_size: 0.05  # 5% портфеля
  stop_loss_pct: 0.015     # 1.5%
  take_profit_pct: 0.03    # 3%
  trailing_stop: true
  min_risk_reward: 2.0     # 1:2 минимум

entry_conditions:
  min_confidence: 0.65     # 65% скор
  required_confluence: 3   # Минимум 3 индикатора в одном направлении
  volume_confirmation: true
```

### ЭТАП 6: Тестирование и оптимизация (2-3 дня)

#### 6.1 Бэктестинг framework

```python
class StrategyBacktester:
    """Система бэктестинга стратегий"""

    def __init__(self, strategy: StrategyABC, dataset: StrategyDataset):
        self.strategy = strategy
        self.dataset = dataset

    def run_backtest(self, start_date: str, end_date: str) -> BacktestResults:
        """Запуск полного бэктестинга"""

    def calculate_metrics(self) -> PerformanceMetrics:
        """Расчет метрик производительности"""
        return PerformanceMetrics(
            total_return=self._calculate_total_return(),
            sharpe_ratio=self._calculate_sharpe_ratio(),
            max_drawdown=self._calculate_max_drawdown(),
            win_rate=self._calculate_win_rate(),
            avg_hold_time=self._calculate_avg_hold_time(),
            profit_factor=self._calculate_profit_factor()
        )
```

#### 6.2 Метрики для оценки стратегий

- **Sharpe Ratio** > 1.5 (риск-скорректированная доходность)
- **Maximum Drawdown** < 15% (максимальная просадка)
- **Win Rate** > 55% (процент прибыльных сделок)
- **Profit Factor** > 1.3 (соотношение прибыли к убыткам)
- **Average Hold Time** = 1-7 дней (соответствие стратегии)

---

## 🎯 Последовательность реализации

### Неделя 1: Базовая архитектура

- [ ] День 1-2: StrategyABC, Registry, Factory
- [ ] День 3-4: BaseIndicatorStrategy
- [ ] День 5-7: Система индикаторов (trend, momentum)

### Неделя 2: Система скоринга

- [ ] День 1-2: Weight Manager и Score Calculator
- [ ] День 3-4: Performance Tracker
- [ ] День 5-7: Матрица скоринга и тестирование

### Неделя 3: Первая стратегия

- [ ] День 1-2: SwingTradingStrategy implementation
- [ ] День 3-4: Конфигурация и риск-менеджмент
- [ ] День 5-7: Интеграция с существующим StrategyManager

### Неделя 4: Тестирование и оптимизация

- [ ] День 1-3: Бэктестинг на исторических данных
- [ ] День 4-5: Оптимизация параметров
- [ ] День 6-7: Paper trading и валидация

---

## 🔗 Интеграция с существующими компонентами

### StrategyManager integration

```python
# manager.py уже готов принимать стратегии через:
async def register_strategy(self, strategy_config: StrategyConfig) -> str:
    """Регистрация новой стратегии"""

async def start_strategy(self, strategy_id: str) -> bool:
    """Запуск стратегии"""
```

### Exchange integration

```python
# Стратегии будут использовать ExchangeRegistry:
exchange = await self.exchange_registry.get_exchange("binance")
market_data = await exchange.get_klines(symbol, timeframe)
```

### Risk Management integration

```python
# Интеграция с RiskManager (857 строк):
risk_check = await self.risk_manager.validate_signal(signal)
if risk_check.approved:
    await self.execute_signal(signal)
```

---

## 📋 Критерии успеха

### Технические

- [ ] Все базовые компоненты реализованы и протестированы
- [ ] Система скоринга работает корректно
- [ ] Первая стратегия проходит бэктестинг с положительными метриками
- [ ] Интеграция с StrategyManager без ошибок

### Бизнес

- [ ] Стратегия показывает стабильную прибыльность на исторических данных
- [ ] Drawdown не превышает 15%
- [ ] Sharpe ratio > 1.5
- [ ] Время удержания позиций соответствует 1-7 дням

### Архитектурные

- [ ] Код легко расширяется для добавления новых индикаторов
- [ ] Система конфигурации позволяет быстро настраивать стратегии
- [ ] Performance Tracker корректно отслеживает эффективность
- [ ] Готовность к добавлению ML компонентов в будущем

---

**Статус**: План готов к реализации
**Оценка времени**: 4 недели для полной реализации
**Первые результаты**: через 2 недели (базовая indicator_strategy)

*Этот план будет дополнен AI консультациями для уточнения деталей реализации*
