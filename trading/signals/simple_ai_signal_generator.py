"""
Simple AI Signal Generator для BOT_AI_V3

Упрощенный генератор торговых сигналов без ML для тестирования.
Использует технический анализ для генерации сигналов каждую минуту.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from core.config.config_manager import ConfigManager
from strategies.base.strategy_abc import SignalStrength, SignalType, TradingSignal

logger = logging.getLogger(__name__)


@dataclass
class SimpleSignalScore:
    """Упрощенная оценка сигнала"""

    symbol: str
    timestamp: datetime
    direction: str  # BUY/SELL/NEUTRAL

    # Оценки индикаторов
    rsi_score: float = 0.0
    ema_score: float = 0.0
    volume_score: float = 0.0
    momentum_score: float = 0.0

    # Итоговые оценки
    total_score: float = 0.0
    signal_strength: SignalStrength = SignalStrength.WEAK
    should_trade: bool = False

    # Рекомендуемые уровни
    suggested_sl: Optional[float] = None
    suggested_tp: Optional[float] = None

    # Детали для логирования
    reasons: List[str] = field(default_factory=list)


class SimpleAISignalGenerator:
    """
    Упрощенный генератор торговых сигналов

    Функциональность:
    - Генерация сигналов для множественных символов
    - Технический анализ с индикаторами
    - Простые правила для SL/TP
    """

    def __init__(self, config_manager: ConfigManager, exchange_name: str = "bybit"):
        self.config_manager = config_manager
        self.exchange_name = exchange_name
        self.logger = logger

        # Компоненты системы
        self.exchange = None

        # Конфигурация
        self.symbols = []
        self.signal_interval = 60  # секунд
        self._load_config()

        # Состояние
        self._running = False
        self._signal_tasks: Dict[str, asyncio.Task] = {}
        self._last_signals: Dict[str, SimpleSignalScore] = {}
        self._candle_cache: Dict[str, pd.DataFrame] = {}

    def _load_config(self):
        """Загрузка конфигурации"""
        full_config = self.config_manager.get_config()

        # Получаем список символов из multi_crypto_10 трейдера
        traders = full_config.get("traders", [])
        for trader in traders:
            if trader.get("id") == "multi_crypto_10" and trader.get("enabled"):
                self.symbols = trader.get("symbols", [])
                strategy_config = trader.get("strategy_config", {})
                self.signal_interval = strategy_config.get("signal_interval", 60)
                break

        if not self.symbols:
            # Конфигурация по умолчанию
            self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

    async def initialize(self):
        """Инициализация генератора"""
        self.logger.info("🤖 Инициализация Simple AI Signal Generator")

        try:
            # Создаем exchange
            full_config = self.config_manager.get_config()
            bybit_config = full_config.get("exchanges", {}).get("bybit", {})

            exchange_config = {
                "api_key": os.getenv("BYBIT_API_KEY"),
                "api_secret": os.getenv("BYBIT_API_SECRET"),
                "testnet": bybit_config.get("testnet", False),
            }

            # Создаем фабрику и клиента
            from exchanges.factory import get_exchange_factory

            factory = get_exchange_factory()

            self.exchange = await factory.create_and_connect(
                exchange_type=self.exchange_name,
                api_key=exchange_config["api_key"],
                api_secret=exchange_config["api_secret"],
                sandbox=exchange_config["testnet"],
            )

            self.logger.info(
                f"📊 Настроено {len(self.symbols)} символов для отслеживания"
            )
            self.logger.info(
                f"⏱️ Интервал генерации сигналов: {self.signal_interval} сек"
            )

        except Exception as e:
            self.logger.error(f"Ошибка инициализации: {e}")
            raise

    async def start(self):
        """Запуск генерации сигналов"""
        self._running = True
        self.logger.info("🚀 Запуск генерации сигналов")

        # Запускаем задачу генерации для каждого символа
        for symbol in self.symbols:
            task = asyncio.create_task(self._signal_generation_loop(symbol))
            self._signal_tasks[symbol] = task

        # Запускаем общий цикл мониторинга
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
                await asyncio.sleep(self.signal_interval)

            except Exception as e:
                self.logger.error(f"❌ Ошибка генерации сигнала для {symbol}: {e}")
                await asyncio.sleep(self.signal_interval)

    async def _generate_and_score_signal(
        self, symbol: str
    ) -> Optional[SimpleSignalScore]:
        """Генерация и оценка сигнала для символа"""
        try:
            # Получаем свечные данные
            candles = await self._get_candles(symbol)
            if candles is None or len(candles) < 50:
                return None

            # Создаем базовый сигнал
            signal_score = SimpleSignalScore(symbol=symbol, timestamp=datetime.now())

            # 1. RSI анализ
            rsi = self._calculate_rsi(candles["close"])
            current_rsi = rsi.iloc[-1]

            if current_rsi < 30:
                signal_score.rsi_score = 0.8
                signal_score.direction = "BUY"
                signal_score.reasons.append(f"RSI перепродан: {current_rsi:.1f}")
            elif current_rsi > 70:
                signal_score.rsi_score = 0.8
                signal_score.direction = "SELL"
                signal_score.reasons.append(f"RSI перекуплен: {current_rsi:.1f}")
            else:
                signal_score.rsi_score = 0.2

            # 2. EMA анализ
            ema_9 = candles["close"].ewm(span=9).mean()
            ema_21 = candles["close"].ewm(span=21).mean()

            if ema_9.iloc[-1] > ema_21.iloc[-1] and ema_9.iloc[-2] <= ema_21.iloc[-2]:
                signal_score.ema_score = 0.7
                if signal_score.direction != "SELL":
                    signal_score.direction = "BUY"
                signal_score.reasons.append("EMA пересечение вверх")
            elif ema_9.iloc[-1] < ema_21.iloc[-1] and ema_9.iloc[-2] >= ema_21.iloc[-2]:
                signal_score.ema_score = 0.7
                if signal_score.direction != "BUY":
                    signal_score.direction = "SELL"
                signal_score.reasons.append("EMA пересечение вниз")

            # 3. Анализ объемов
            avg_volume = candles["volume"].rolling(20).mean().iloc[-1]
            current_volume = candles["volume"].iloc[-1]

            if current_volume > avg_volume * 1.5:
                signal_score.volume_score = 0.5
                signal_score.reasons.append(
                    f"Высокий объем: {current_volume / avg_volume:.1f}x"
                )
            elif current_volume > avg_volume:
                signal_score.volume_score = 0.3

            # 4. Анализ моментума
            price_change = (
                candles["close"].iloc[-1] / candles["close"].iloc[-5] - 1
            ) * 100

            if abs(price_change) > 2:
                signal_score.momentum_score = 0.4
                signal_score.reasons.append(f"Сильный моментум: {price_change:.1f}%")

            # 5. Расчет итоговой оценки
            signal_score.total_score = (
                signal_score.rsi_score * 0.3
                + signal_score.ema_score * 0.3
                + signal_score.volume_score * 0.2
                + signal_score.momentum_score * 0.2
            )

            # 6. Определение силы сигнала
            if signal_score.total_score >= 0.7:
                signal_score.signal_strength = SignalStrength.STRONG
            elif signal_score.total_score >= 0.5:
                signal_score.signal_strength = SignalStrength.MODERATE
            else:
                signal_score.signal_strength = SignalStrength.WEAK

            # 7. Решение о торговле
            signal_score.should_trade = (
                signal_score.total_score >= 0.5 and signal_score.direction != "NEUTRAL"
            )

            # 8. Расчет SL/TP
            if signal_score.should_trade:
                current_price = float(candles["close"].iloc[-1])

                if signal_score.direction == "BUY":
                    signal_score.suggested_sl = current_price * 0.98  # -2%
                    signal_score.suggested_tp = current_price * 1.058  # +5.8%
                else:
                    signal_score.suggested_sl = current_price * 1.02  # +2%
                    signal_score.suggested_tp = current_price * 0.942  # -5.8%

            # Логирование
            self._log_signal_score(signal_score)

            return signal_score

        except Exception as e:
            self.logger.error(f"Ошибка оценки сигнала {symbol}: {e}")
            return None

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Расчет RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _create_trading_signal(self, signal_score: SimpleSignalScore) -> TradingSignal:
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
            position_size=0.01,  # 1% от баланса по умолчанию
            strategy_name="SimpleAISignalGenerator",
            timeframe="15m",
            indicators_used=["RSI", "EMA", "Volume", "Momentum"],
        )

        return signal

    async def _emit_signal(self, signal: TradingSignal):
        """Отправка сигнала в систему"""
        self.logger.info(
            f"📡 Новый сигнал: {signal.symbol} {signal.signal_type.value} "
            f"(уверенность: {signal.confidence:.1f}%, цена: {signal.entry_price:.2f})"
        )

        # TODO: Интеграция с trading engine для обработки сигнала

    async def _get_candles(
        self, symbol: str, timeframe: str = "15m", limit: int = 100
    ) -> Optional[pd.DataFrame]:
        """Получение свечных данных"""
        try:
            # Проверяем кэш
            cache_key = f"{symbol}_{timeframe}"
            if cache_key in self._candle_cache:
                cached_data = self._candle_cache[cache_key]
                # Если данные не старше 1 минуты - используем кэш
                if len(cached_data) > 0 and (
                    datetime.now() - cached_data.index[-1]
                ) < timedelta(minutes=1):
                    return cached_data

            # Получаем свежие данные
            klines = await self.exchange.get_klines(symbol, timeframe, limit=limit)

            if klines:
                # Преобразуем klines в DataFrame
                candles_data = []
                for kline in klines:
                    candles_data.append(
                        {
                            "timestamp": kline.timestamp,
                            "open": float(kline.open),
                            "high": float(kline.high),
                            "low": float(kline.low),
                            "close": float(kline.close),
                            "volume": float(kline.volume),
                        }
                    )

                df = pd.DataFrame(candles_data)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df.set_index("timestamp", inplace=True)

                # Кэшируем
                self._candle_cache[cache_key] = df

                return df

        except Exception as e:
            self.logger.error(f"Ошибка получения свечей {symbol}: {e}")
            return None

    def _log_signal_score(self, signal_score: SimpleSignalScore):
        """Логирование оценки сигнала"""
        if signal_score.should_trade:
            self.logger.info(
                f"📊 Сигнал {signal_score.symbol} {signal_score.direction}:\n"
                f"   RSI: {signal_score.rsi_score:.2f}\n"
                f"   EMA: {signal_score.ema_score:.2f}\n"
                f"   Объем: {signal_score.volume_score:.2f}\n"
                f"   Моментум: {signal_score.momentum_score:.2f}\n"
                f"   Итого: {signal_score.total_score:.2f} ({signal_score.signal_strength.value})\n"
                f"   Причины: {', '.join(signal_score.reasons)}"
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
                    f"📊 Статистика генератора:\n"
                    f"   Отслеживается символов: {len(self.symbols)}\n"
                    f"   Активных сигналов: {active_signals}/{total_signals}"
                )

            except Exception as e:
                self.logger.error(f"Ошибка мониторинга: {e}")

    async def get_current_signals(self) -> Dict[str, SimpleSignalScore]:
        """Получение текущих сигналов"""
        return self._last_signals.copy()
