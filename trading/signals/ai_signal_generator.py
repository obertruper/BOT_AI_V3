"""
AI Signal Generator для BOT_AI_V3

Генератор торговых сигналов с использованием ML моделей для оценки.
Поддерживает множественные криптовалюты и генерацию сигналов по расписанию.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from core.config.config_manager import ConfigManager
from exchanges.factory import ExchangeFactory
from indicators.calculator.indicator_calculator import IndicatorCalculator
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor
from strategies.base.strategy_abc import SignalStrength, SignalType, TradingSignal


@dataclass
class AISignalConfig:
    """Конфигурация для AI генератора сигналов"""

    symbols: List[str] = field(default_factory=list)
    signal_interval: int = 60  # секунд
    min_confidence: float = 0.6  # минимальная уверенность
    min_profit_probability: float = 0.65  # минимальная вероятность прибыли
    max_risk: float = 0.03  # максимальный риск 3%

    # ML параметры
    use_ml_scoring: bool = True
    ml_model_path: Optional[str] = None
    feature_lookback: int = 96  # свечей для ML модели

    # Индикаторы для базового анализа
    indicators: List[Dict[str, Any]] = field(default_factory=list)

    # Пороги для принятия решений
    thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "buy_profit": 0.65,
            "buy_loss": 0.35,
            "sell_profit": 0.65,
            "sell_loss": 0.35,
        }
    )


@dataclass
class SignalScore:
    """Оценка сигнала от AI системы"""

    symbol: str
    timestamp: datetime
    direction: str  # BUY/SELL

    # ML оценки
    ml_confidence: float = 0.0
    ml_profit_probability: float = 0.0
    ml_expected_return: float = 0.0
    ml_risk_score: float = 0.0

    # Технический анализ
    technical_score: float = 0.0
    volume_score: float = 0.0
    momentum_score: float = 0.0

    # Итоговые оценки
    total_score: float = 0.0
    signal_strength: SignalStrength = SignalStrength.WEAK
    should_trade: bool = False

    # Рекомендуемые уровни
    suggested_sl: Optional[float] = None
    suggested_tp: Optional[float] = None
    suggested_size: Optional[float] = None

    # Детали для логирования
    reasons: List[str] = field(default_factory=list)
    ml_predictions: Optional[Dict[str, float]] = None


class AISignalGenerator:
    """
    Генератор торговых сигналов с AI/ML оценкой

    Функциональность:
    - Генерация сигналов для множественных символов
    - ML оценка каждого сигнала
    - Технический анализ с индикаторами
    - Адаптивные SL/TP на основе ML предсказаний
    - Оценка рисков и размера позиции
    """

    def __init__(self, config_manager: ConfigManager, exchange_name: str = "bybit"):
        self.config_manager = config_manager
        self.exchange_name = exchange_name
        self.logger = logging.getLogger(__name__)

        # Компоненты системы
        self.ml_manager: Optional[MLManager] = None
        self.ml_processor: Optional[MLSignalProcessor] = None
        self.indicator_calculator = IndicatorCalculator()
        self.exchange = None

        # Конфигурация
        self.config = self._load_config()

        # Состояние
        self._running = False
        self._signal_tasks: Dict[str, asyncio.Task] = {}
        self._last_signals: Dict[str, SignalScore] = {}
        self._candle_cache: Dict[str, pd.DataFrame] = {}

    def _load_config(self) -> AISignalConfig:
        """Загрузка конфигурации из config manager"""
        full_config = self.config_manager.get_config()
        system_config = self.config_manager.get_system_config()

        # Получаем конфигурацию трейдеров
        traders = full_config.get("traders", [])
        multi_crypto_trader = None

        for trader in traders:
            if trader.get("id") == "multi_crypto_10" and trader.get("enabled"):
                multi_crypto_trader = trader
                break

        if not multi_crypto_trader:
            # Конфигурация по умолчанию
            return AISignalConfig(
                symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"], signal_interval=60
            )

        # Создаем конфигурацию из настроек трейдера
        strategy_config = multi_crypto_trader.get("strategy_config", {})

        config = AISignalConfig(
            symbols=multi_crypto_trader.get("symbols", []),
            signal_interval=strategy_config.get("signal_interval", 60),
            indicators=strategy_config.get("indicators", []),
            use_ml_scoring=True,
            ml_model_path=full_config.get("ml_models", {})
            .get("patchtst", {})
            .get("model_path"),
        )

        # ML пороги
        ml_config = full_config.get("ml_models", {})
        config.thresholds = {
            "buy_profit": ml_config.get("threshold_buy_profit", 0.65),
            "buy_loss": ml_config.get("threshold_buy_loss", 0.35),
            "sell_profit": ml_config.get("threshold_sell_profit", 0.65),
            "sell_loss": ml_config.get("threshold_sell_loss", 0.35),
        }

        return config

    async def initialize(self):
        """Инициализация генератора"""
        self.logger.info("🤖 Инициализация AI Signal Generator")

        # Создаем exchange
        exchange_config = {
            "api_key": self.config_manager.get_exchange_config("bybit").get("api_key"),
            "api_secret": self.config_manager.get_exchange_config("bybit").get(
                "api_secret"
            ),
            "testnet": self.config_manager.get_exchange_config("bybit").get(
                "testnet", False
            ),
        }

        self.exchange = await ExchangeFactory.create_exchange(
            self.exchange_name, exchange_config
        )
        await self.exchange.initialize()

        # Инициализируем ML компоненты если включены
        if self.config.use_ml_scoring and self.config.ml_model_path:
            try:
                self.ml_manager = MLManager()
                await self.ml_manager.initialize()

                self.ml_processor = MLSignalProcessor(
                    ml_manager=self.ml_manager,
                    config=self.config_manager.get_system_config(),
                )

                self.logger.info("✅ ML система инициализирована")
            except Exception as e:
                self.logger.warning(f"⚠️ ML система недоступна: {e}")
                self.config.use_ml_scoring = False

        self.logger.info(
            f"📊 Настроено {len(self.config.symbols)} символов для отслеживания"
        )
        self.logger.info(
            f"⏱️ Интервал генерации сигналов: {self.config.signal_interval} сек"
        )

    async def start(self):
        """Запуск генерации сигналов"""
        self._running = True
        self.logger.info("🚀 Запуск генерации AI сигналов")

        # Запускаем задачу генерации для каждого символа
        for symbol in self.config.symbols:
            task = asyncio.create_task(self._signal_generation_loop(symbol))
            self._signal_tasks[symbol] = task

        # Также запускаем общий цикл мониторинга
        asyncio.create_task(self._monitoring_loop())

    async def stop(self):
        """Остановка генерации"""
        self._running = False

        # Отменяем все задачи
        for task in self._signal_tasks.values():
            task.cancel()

        # Ждем завершения
        await asyncio.gather(*self._signal_tasks.values(), return_exceptions=True)

        self._signal_tasks.clear()
        self.logger.info("✅ Генерация сигналов остановлена")

    async def _signal_generation_loop(self, symbol: str):
        """Цикл генерации сигналов для одного символа"""
        while self._running:
            try:
                # Генерируем и оцениваем сигнал
                signal_score = await self._generate_and_score_signal(symbol)

                if signal_score:
                    self._last_signals[symbol] = signal_score

                    # Если сигнал достаточно сильный - создаем торговый сигнал
                    if signal_score.should_trade:
                        trading_signal = self._create_trading_signal(signal_score)
                        await self._emit_signal(trading_signal)

                # Ждем до следующего цикла
                await asyncio.sleep(self.config.signal_interval)

            except Exception as e:
                self.logger.error(f"❌ Ошибка генерации сигнала для {symbol}: {e}")
                await asyncio.sleep(self.config.signal_interval)

    async def _generate_and_score_signal(self, symbol: str) -> Optional[SignalScore]:
        """Генерация и оценка сигнала для символа"""
        try:
            # Получаем свечные данные
            candles = await self._get_candles(symbol)
            if candles is None or len(candles) < self.config.feature_lookback:
                return None

            # Создаем базовый сигнал
            signal_score = SignalScore(symbol=symbol, timestamp=datetime.now())

            # 1. Технический анализ
            technical_signals = await self._analyze_technical(symbol, candles)
            signal_score.technical_score = technical_signals["score"]
            signal_score.direction = technical_signals["direction"]

            # 2. Анализ объемов
            volume_signals = await self._analyze_volume(symbol, candles)
            signal_score.volume_score = volume_signals["score"]

            # 3. Анализ моментума
            momentum_signals = await self._analyze_momentum(symbol, candles)
            signal_score.momentum_score = momentum_signals["score"]

            # 4. ML оценка (если доступна)
            if self.config.use_ml_scoring and self.ml_processor:
                ml_evaluation = await self._evaluate_with_ml(
                    symbol, candles, signal_score.direction
                )

                signal_score.ml_confidence = ml_evaluation["confidence"]
                signal_score.ml_profit_probability = ml_evaluation["profit_probability"]
                signal_score.ml_expected_return = ml_evaluation["expected_return"]
                signal_score.ml_risk_score = ml_evaluation["risk_score"]
                signal_score.ml_predictions = ml_evaluation["predictions"]

                # Рекомендуемые уровни от ML
                signal_score.suggested_sl = ml_evaluation.get("suggested_sl")
                signal_score.suggested_tp = ml_evaluation.get("suggested_tp")
                signal_score.suggested_size = ml_evaluation.get("suggested_size")

            # 5. Расчет итоговой оценки
            signal_score.total_score = self._calculate_total_score(signal_score)

            # 6. Определение силы сигнала
            signal_score.signal_strength = self._determine_signal_strength(
                signal_score.total_score
            )

            # 7. Решение о торговле
            signal_score.should_trade = self._should_trade(signal_score)

            # Логирование
            self._log_signal_score(signal_score)

            return signal_score

        except Exception as e:
            self.logger.error(f"Ошибка оценки сигнала {symbol}: {e}")
            return None

    async def _analyze_technical(self, symbol: str, candles: pd.DataFrame) -> Dict:
        """Технический анализ с индикаторами"""
        results = {"score": 0.0, "direction": "NEUTRAL", "signals": {}}

        try:
            # Рассчитываем индикаторы
            for indicator_config in self.config.indicators:
                indicator_type = indicator_config.get("type")

                if indicator_type == "RSI":
                    rsi = self.indicator_calculator.calculate_rsi(
                        candles["close"], period=indicator_config.get("period", 14)
                    )

                    current_rsi = rsi.iloc[-1]
                    results["signals"]["rsi"] = current_rsi

                    if current_rsi < indicator_config.get("oversold", 30):
                        results["score"] += 0.3
                        results["direction"] = "BUY"
                    elif current_rsi > indicator_config.get("overbought", 70):
                        results["score"] += 0.3
                        results["direction"] = "SELL"

                elif indicator_type == "EMA":
                    ema_short = (
                        candles["close"]
                        .ewm(span=indicator_config.get("short_period", 9))
                        .mean()
                    )
                    ema_long = (
                        candles["close"]
                        .ewm(span=indicator_config.get("long_period", 21))
                        .mean()
                    )

                    # Проверка пересечения
                    if (
                        ema_short.iloc[-1] > ema_long.iloc[-1]
                        and ema_short.iloc[-2] <= ema_long.iloc[-2]
                    ):
                        results["score"] += 0.4
                        if results["direction"] == "NEUTRAL":
                            results["direction"] = "BUY"
                    elif (
                        ema_short.iloc[-1] < ema_long.iloc[-1]
                        and ema_short.iloc[-2] >= ema_long.iloc[-2]
                    ):
                        results["score"] += 0.4
                        if results["direction"] == "NEUTRAL":
                            results["direction"] = "SELL"

                # Добавьте другие индикаторы по необходимости

        except Exception as e:
            self.logger.error(f"Ошибка технического анализа: {e}")

        return results

    async def _analyze_volume(self, symbol: str, candles: pd.DataFrame) -> Dict:
        """Анализ объемов"""
        results = {"score": 0.0, "signals": {}}

        try:
            # Средний объем за последние 20 свечей
            avg_volume = candles["volume"].rolling(20).mean().iloc[-1]
            current_volume = candles["volume"].iloc[-1]

            # Объем выше среднего - сильный сигнал
            if current_volume > avg_volume * 1.5:
                results["score"] = 0.3
            elif current_volume > avg_volume:
                results["score"] = 0.1

            results["signals"]["volume_ratio"] = current_volume / avg_volume

        except Exception as e:
            self.logger.error(f"Ошибка анализа объемов: {e}")

        return results

    async def _analyze_momentum(self, symbol: str, candles: pd.DataFrame) -> Dict:
        """Анализ моментума"""
        results = {"score": 0.0, "signals": {}}

        try:
            # Изменение цены за последние N свечей
            price_change_5 = (
                candles["close"].iloc[-1] / candles["close"].iloc[-5] - 1
            ) * 100
            price_change_10 = (
                candles["close"].iloc[-1] / candles["close"].iloc[-10] - 1
            ) * 100

            # Сильный моментум
            if abs(price_change_5) > 2:
                results["score"] = 0.2
            if abs(price_change_10) > 5:
                results["score"] += 0.1

            results["signals"]["momentum_5"] = price_change_5
            results["signals"]["momentum_10"] = price_change_10

        except Exception as e:
            self.logger.error(f"Ошибка анализа моментума: {e}")

        return results

    async def _evaluate_with_ml(
        self, symbol: str, candles: pd.DataFrame, direction: str
    ) -> Dict:
        """Оценка сигнала с помощью ML модели"""
        evaluation = {
            "confidence": 0.0,
            "profit_probability": 0.0,
            "expected_return": 0.0,
            "risk_score": 0.0,
            "predictions": {},
        }

        try:
            # Получаем предсказания от ML модели
            ml_signal = await self.ml_processor.process_candles(
                symbol=symbol,
                candles=candles,
                strategy_context={"direction": direction},
            )

            if ml_signal and ml_signal.ml_predictions:
                predictions = ml_signal.ml_predictions

                # Извлекаем ключевые метрики
                evaluation["confidence"] = predictions.get("confidence", 0.0)
                evaluation["profit_probability"] = predictions.get(
                    "profit_probability", 0.0
                )
                evaluation["expected_return"] = predictions.get("expected_return", 0.0)
                evaluation["risk_score"] = predictions.get("risk_metrics", {}).get(
                    "max_risk", 0.0
                )
                evaluation["predictions"] = predictions

                # Рекомендуемые уровни
                if predictions.get("suggested_levels"):
                    levels = predictions["suggested_levels"]
                    evaluation["suggested_sl"] = levels.get("stop_loss")
                    evaluation["suggested_tp"] = levels.get("take_profit")

                # Размер позиции на основе Kelly Criterion
                if predictions.get("position_sizing"):
                    evaluation["suggested_size"] = predictions["position_sizing"].get(
                        "kelly_fraction", 0.02
                    )

        except Exception as e:
            self.logger.error(f"Ошибка ML оценки: {e}")

        return evaluation

    def _calculate_total_score(self, signal_score: SignalScore) -> float:
        """Расчет итоговой оценки сигнала"""
        weights = {
            "technical": 0.25,
            "volume": 0.15,
            "momentum": 0.10,
            "ml_confidence": 0.20,
            "ml_profit": 0.20,
            "ml_risk": 0.10,  # инвертированный
        }

        total = 0.0

        # Базовые оценки
        total += signal_score.technical_score * weights["technical"]
        total += signal_score.volume_score * weights["volume"]
        total += signal_score.momentum_score * weights["momentum"]

        # ML оценки (если есть)
        if self.config.use_ml_scoring:
            total += signal_score.ml_confidence * weights["ml_confidence"]
            total += signal_score.ml_profit_probability * weights["ml_profit"]
            total += (1 - signal_score.ml_risk_score) * weights["ml_risk"]

        return min(total, 1.0)  # Ограничиваем максимум 1.0

    def _determine_signal_strength(self, total_score: float) -> SignalStrength:
        """Определение силы сигнала"""
        if total_score >= 0.8:
            return SignalStrength.VERY_STRONG
        elif total_score >= 0.65:
            return SignalStrength.STRONG
        elif total_score >= 0.5:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK

    def _should_trade(self, signal_score: SignalScore) -> bool:
        """Решение о торговле на основе оценок"""
        # Базовые проверки
        if signal_score.total_score < 0.5:
            signal_score.reasons.append("Низкая общая оценка")
            return False

        # ML проверки (если включены)
        if self.config.use_ml_scoring:
            # Проверка уверенности
            if signal_score.ml_confidence < self.config.min_confidence:
                signal_score.reasons.append(
                    f"Низкая ML уверенность: {signal_score.ml_confidence:.2%}"
                )
                return False

            # Проверка вероятности прибыли
            if signal_score.ml_profit_probability < self.config.min_profit_probability:
                signal_score.reasons.append(
                    f"Низкая вероятность прибыли: {signal_score.ml_profit_probability:.2%}"
                )
                return False

            # Проверка риска
            if signal_score.ml_risk_score > self.config.max_risk:
                signal_score.reasons.append(
                    f"Высокий риск: {signal_score.ml_risk_score:.2%}"
                )
                return False

        signal_score.reasons.append("✅ Все проверки пройдены")
        return True

    def _create_trading_signal(self, signal_score: SignalScore) -> TradingSignal:
        """Создание торгового сигнала из оценки"""
        signal_type = (
            SignalType.BUY if signal_score.direction == "BUY" else SignalType.SELL
        )

        # Получаем текущую цену из кэша
        candles = self._candle_cache.get(f"{signal_score.symbol}_15m")
        current_price = float(candles["close"].iloc[-1]) if candles is not None else 0

        signal = TradingSignal(
            timestamp=signal_score.timestamp,
            symbol=signal_score.symbol,
            signal_type=signal_type,
            confidence=signal_score.total_score * 100,  # Конвертируем в 0-100
            entry_price=current_price,
            stop_loss=signal_score.suggested_sl or current_price * 0.98,
            take_profit=signal_score.suggested_tp or current_price * 1.058,
            position_size=signal_score.suggested_size
            or 0.02,  # 2% от баланса по умолчанию
            strategy_name="AISignalGenerator_ML",
            timeframe="15m",
            indicators_used=["ML_PatchTST", "RSI", "EMA", "MACD", "Volume"],
        )

        return signal

    async def _emit_signal(self, signal: TradingSignal):
        """Отправка сигнала в систему"""
        self.logger.info(
            f"📡 Новый AI сигнал: {signal.symbol} {signal.signal_type.value} "
            f"(уверенность: {signal.confidence:.1f}%, цена: {signal.entry_price:.2f})"
        )

        # TODO: Интеграция с trading engine для обработки сигнала
        # Пока просто логируем

    async def _get_candles(
        self, symbol: str, timeframe: str = "15m", limit: int = 200
    ) -> Optional[pd.DataFrame]:
        """Получение свечных данных"""
        try:
            # Проверяем кэш
            cache_key = f"{symbol}_{timeframe}"
            if cache_key in self._candle_cache:
                cached_data = self._candle_cache[cache_key]
                # Если данные не старше 1 минуты - используем кэш
                if (datetime.now() - cached_data.index[-1]) < timedelta(minutes=1):
                    return cached_data

            # Получаем свежие данные
            candles = await self.exchange.get_candles(symbol, timeframe, limit)

            if candles:
                df = pd.DataFrame(candles)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df.set_index("timestamp", inplace=True)

                # Кэшируем
                self._candle_cache[cache_key] = df

                return df

        except Exception as e:
            self.logger.error(f"Ошибка получения свечей {symbol}: {e}")
            return None

    def _log_signal_score(self, signal_score: SignalScore):
        """Логирование оценки сигнала"""
        self.logger.debug(
            f"📊 Оценка {signal_score.symbol} {signal_score.direction}:\n"
            f"   Техническая: {signal_score.technical_score:.2f}\n"
            f"   Объемная: {signal_score.volume_score:.2f}\n"
            f"   Моментум: {signal_score.momentum_score:.2f}\n"
            f"   ML уверенность: {signal_score.ml_confidence:.2%}\n"
            f"   ML прибыль: {signal_score.ml_profit_probability:.2%}\n"
            f"   ML риск: {signal_score.ml_risk_score:.2%}\n"
            f"   Итого: {signal_score.total_score:.2f} ({signal_score.signal_strength.value})\n"
            f"   Торговать: {'ДА' if signal_score.should_trade else 'НЕТ'}"
        )

    async def _monitoring_loop(self):
        """Цикл мониторинга состояния генератора"""
        while self._running:
            try:
                # Выводим статистику каждые 5 минут
                await asyncio.sleep(300)

                active_signals = len(
                    [s for s in self._last_signals.values() if s.should_trade]
                )
                total_signals = len(self._last_signals)

                self.logger.info(
                    f"📊 Статистика AI генератора:\n"
                    f"   Отслеживается символов: {len(self.config.symbols)}\n"
                    f"   Активных сигналов: {active_signals}/{total_signals}\n"
                    f"   ML система: {'✅ Активна' if self.config.use_ml_scoring else '❌ Отключена'}"
                )

            except Exception as e:
                self.logger.error(f"Ошибка мониторинга: {e}")

    async def get_current_signals(self) -> Dict[str, SignalScore]:
        """Получение текущих сигналов"""
        return self._last_signals.copy()
