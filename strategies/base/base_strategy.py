#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовый класс для всех торговых стратегий
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from database.models import Signal
from indicators.calculator.indicator_calculator import IndicatorCalculator


class BaseStrategy(ABC):
    """
    Базовый класс для всех торговых стратегий

    Предоставляет:
    - Общий интерфейс для всех стратегий
    - Управление жизненным циклом
    - Базовые методы для работы с индикаторами
    - Систему управления параметрами
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        exchange: str,
        timeframe: str = "5m",
        parameters: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Инициализация базовой стратегии

        Args:
            name: Имя стратегии
            symbol: Торговый символ (например, 'BTC/USDT')
            exchange: Название биржи
            timeframe: Временной интервал
            parameters: Параметры стратегии
            logger: Логгер
        """
        self.name = name
        self.symbol = symbol
        self.exchange = exchange
        self.timeframe = timeframe
        self.parameters = parameters or {}
        self.logger = logger or logging.getLogger(f"strategy.{name}")

        # Состояние стратегии
        self._is_active = False
        self._last_signal = None
        self._position_size = Decimal("0")
        self._entry_price = Decimal("0")

        # Калькулятор индикаторов
        self.indicator_calculator = IndicatorCalculator()

        # История данных
        self._price_history = []
        self._signal_history = []

        # Метрики производительности
        self._metrics = {
            "total_signals": 0,
            "profitable_signals": 0,
            "loss_signals": 0,
            "total_pnl": Decimal("0"),
            "win_rate": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
        }

    @abstractmethod
    async def analyze(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """
        Анализ рыночных данных и генерация торгового сигнала

        Args:
            market_data: Рыночные данные (OHLCV, стакан, сделки)

        Returns:
            Signal или None если нет сигнала
        """
        pass

    @abstractmethod
    async def calculate_position_size(
        self, signal: Signal, account_balance: Decimal
    ) -> Decimal:
        """
        Расчет размера позиции на основе сигнала и баланса

        Args:
            signal: Торговый сигнал
            account_balance: Доступный баланс

        Returns:
            Размер позиции
        """
        pass

    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """
        Получить список необходимых индикаторов

        Returns:
            Список имен индикаторов
        """
        pass

    async def start(self):
        """Запуск стратегии"""
        self._is_active = True
        self.logger.info(
            f"Стратегия {self.name} запущена для {self.symbol} на {self.exchange}"
        )
        await self.on_start()

    async def stop(self):
        """Остановка стратегии"""
        self._is_active = False
        await self.on_stop()
        self.logger.info(f"Стратегия {self.name} остановлена")

    async def update(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """
        Обновление стратегии с новыми рыночными данными

        Args:
            market_data: Новые рыночные данные

        Returns:
            Signal или None
        """
        if not self._is_active:
            return None

        try:
            # Обновляем историю цен
            self._update_price_history(market_data)

            # Анализируем рынок
            signal = await self.analyze(market_data)

            if signal:
                # Валидируем сигнал
                if self._validate_signal(signal):
                    # Добавляем в историю
                    self._signal_history.append(signal)
                    self._last_signal = signal
                    self._metrics["total_signals"] += 1

                    self.logger.info(
                        f"Сгенерирован сигнал: {signal.signal_type.value} "
                        f"для {signal.symbol} с силой {signal.strength}"
                    )

                    return signal
                else:
                    self.logger.warning(f"Сигнал не прошел валидацию: {signal}")

        except Exception as e:
            self.logger.error(f"Ошибка в update: {e}")

        return None

    def _validate_signal(self, signal: Signal) -> bool:
        """Валидация торгового сигнала"""
        # Проверяем базовые параметры
        if not signal.symbol or not signal.exchange:
            return False

        # Проверяем силу сигнала
        min_strength = self.parameters.get("min_signal_strength", 0.5)
        if signal.strength and signal.strength < min_strength:
            return False

        # Проверяем уверенность
        min_confidence = self.parameters.get("min_signal_confidence", 0.5)
        if signal.confidence and signal.confidence < min_confidence:
            return False

        # Проверяем не слишком ли частые сигналы
        if self._last_signal:
            time_diff = (
                datetime.utcnow() - self._last_signal.created_at
            ).total_seconds()
            min_signal_interval = self.parameters.get("min_signal_interval", 60)

            if time_diff < min_signal_interval:
                return False

        return True

    def _update_price_history(self, market_data: Dict[str, Any]):
        """Обновление истории цен"""
        if "candles" in market_data:
            # Добавляем последнюю свечу
            last_candle = market_data["candles"][-1] if market_data["candles"] else None
            if last_candle:
                self._price_history.append(
                    {
                        "timestamp": last_candle.get("timestamp"),
                        "open": last_candle.get("open"),
                        "high": last_candle.get("high"),
                        "low": last_candle.get("low"),
                        "close": last_candle.get("close"),
                        "volume": last_candle.get("volume"),
                    }
                )

                # Ограничиваем размер истории
                max_history = self.parameters.get("max_price_history", 1000)
                if len(self._price_history) > max_history:
                    self._price_history = self._price_history[-max_history:]

    def calculate_indicators(self, price_data: List[Dict]) -> Dict[str, Any]:
        """
        Расчет технических индикаторов

        Args:
            price_data: Исторические данные цен

        Returns:
            Словарь с рассчитанными индикаторами
        """
        indicators = {}

        # Получаем список необходимых индикаторов
        required_indicators = self.get_required_indicators()

        # Подготавливаем данные
        closes = [float(candle["close"]) for candle in price_data]
        highs = [float(candle["high"]) for candle in price_data]
        lows = [float(candle["low"]) for candle in price_data]
        volumes = [float(candle["volume"]) for candle in price_data]

        # Рассчитываем индикаторы
        for indicator_name in required_indicators:
            if indicator_name == "RSI":
                indicators["RSI"] = self.indicator_calculator.calculate_rsi(
                    closes, self.parameters.get("rsi_period", 14)
                )
            elif indicator_name == "MACD":
                indicators["MACD"] = self.indicator_calculator.calculate_macd(
                    closes,
                    self.parameters.get("macd_fast", 12),
                    self.parameters.get("macd_slow", 26),
                    self.parameters.get("macd_signal", 9),
                )
            elif indicator_name == "BB":
                indicators["BB"] = self.indicator_calculator.calculate_bollinger_bands(
                    closes,
                    self.parameters.get("bb_period", 20),
                    self.parameters.get("bb_std", 2),
                )
            elif indicator_name == "EMA":
                for period in self.parameters.get("ema_periods", [9, 21, 50]):
                    indicators[f"EMA_{period}"] = (
                        self.indicator_calculator.calculate_ema(closes, period)
                    )
            elif indicator_name == "ATR":
                indicators["ATR"] = self.indicator_calculator.calculate_atr(
                    highs, lows, closes, self.parameters.get("atr_period", 14)
                )
            elif indicator_name == "STOCH":
                indicators["STOCH"] = self.indicator_calculator.calculate_stochastic(
                    highs,
                    lows,
                    closes,
                    self.parameters.get("stoch_k_period", 14),
                    self.parameters.get("stoch_d_period", 3),
                )

        return indicators

    def calculate_stop_loss(self, entry_price: float, side: str, atr: float) -> float:
        """
        Расчет уровня stop-loss

        Args:
            entry_price: Цена входа
            side: 'long' или 'short'
            atr: Значение ATR

        Returns:
            Уровень stop-loss
        """
        atr_multiplier = self.parameters.get("stop_loss_atr_multiplier", 2.0)

        if side == "long":
            return entry_price - (atr * atr_multiplier)
        else:
            return entry_price + (atr * atr_multiplier)

    def calculate_take_profit(
        self, entry_price: float, side: str, stop_loss: float
    ) -> float:
        """
        Расчет уровня take-profit

        Args:
            entry_price: Цена входа
            side: 'long' или 'short'
            stop_loss: Уровень stop-loss

        Returns:
            Уровень take-profit
        """
        risk_reward_ratio = self.parameters.get("risk_reward_ratio", 2.0)
        risk = abs(entry_price - stop_loss)

        if side == "long":
            return entry_price + (risk * risk_reward_ratio)
        else:
            return entry_price - (risk * risk_reward_ratio)

    def get_parameters(self) -> Dict[str, Any]:
        """Получить текущие параметры стратегии"""
        return self.parameters.copy()

    def update_parameters(self, new_parameters: Dict[str, Any]):
        """Обновить параметры стратегии"""
        self.parameters.update(new_parameters)
        self.logger.info(f"Параметры стратегии {self.name} обновлены")

    def get_metrics(self) -> Dict[str, Any]:
        """Получить метрики производительности"""
        # Рассчитываем win rate
        if self._metrics["total_signals"] > 0:
            self._metrics["win_rate"] = (
                self._metrics["profitable_signals"] / self._metrics["total_signals"]
            )

        return self._metrics.copy()

    def update_metrics(self, pnl: Decimal, is_profitable: bool):
        """Обновить метрики производительности"""
        self._metrics["total_pnl"] += pnl

        if is_profitable:
            self._metrics["profitable_signals"] += 1
        else:
            self._metrics["loss_signals"] += 1

    async def on_start(self):
        """Callback при запуске стратегии (может быть переопределен)"""
        pass

    async def on_stop(self):
        """Callback при остановке стратегии (может быть переопределен)"""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.name}, symbol={self.symbol}, exchange={self.exchange})>"
