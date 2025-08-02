#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML Signal Processor для интеграции ML предсказаний с торговыми сигналами
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd

from core.logger import setup_logger
from ml.ml_manager import MLManager
from trading.signals.signal import Signal, SignalStrength, SignalType

logger = setup_logger("ml_signal_processor")


class MLSignalProcessor:
    """
    Процессор для преобразования ML предсказаний в торговые сигналы.
    Интегрирует ML модель с торговой системой.
    """

    def __init__(self, ml_manager: MLManager, config: Dict[str, Any]):
        """
        Инициализация ML Signal Processor.

        Args:
            ml_manager: Менеджер ML моделей
            config: Конфигурация системы
        """
        self.ml_manager = ml_manager
        self.config = config

        # Пороги для принятия решений
        ml_config = config.get("ml", {})
        self.min_confidence = ml_config.get("min_confidence", 0.65)
        self.min_signal_strength = ml_config.get("min_signal_strength", 0.3)
        self.risk_tolerance = ml_config.get("risk_tolerance", "MEDIUM")

        # Кэш для предсказаний
        self.prediction_cache = {}
        self.cache_ttl = 60  # секунд

        logger.info("MLSignalProcessor initialized")

    async def process_market_data(
        self,
        symbol: str,
        exchange: str,
        ohlcv_data: pd.DataFrame,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Signal]:
        """
        Обрабатывает рыночные данные и генерирует торговый сигнал.

        Args:
            symbol: Торговый символ
            exchange: Название биржи
            ohlcv_data: OHLCV данные
            additional_data: Дополнительные данные (индикаторы и т.д.)

        Returns:
            Signal объект или None
        """
        try:
            # Проверяем кэш
            cache_key = f"{exchange}:{symbol}"
            cached = self._get_cached_prediction(cache_key)
            if cached:
                logger.debug(f"Using cached prediction for {cache_key}")
                return self._create_signal_from_prediction(
                    cached, symbol, exchange, additional_data
                )

            # Получаем предсказание от ML модели
            prediction = await self.ml_manager.predict(ohlcv_data)

            # Кэшируем результат
            self._cache_prediction(cache_key, prediction)

            # Создаем сигнал на основе предсказания
            signal = self._create_signal_from_prediction(
                prediction, symbol, exchange, additional_data
            )

            return signal

        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {e}")
            return None

    def _create_signal_from_prediction(
        self,
        prediction: Dict[str, Any],
        symbol: str,
        exchange: str,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Signal]:
        """
        Создает торговый сигнал на основе ML предсказания.

        Args:
            prediction: Предсказание от ML модели
            symbol: Торговый символ
            exchange: Название биржи
            additional_data: Дополнительные данные

        Returns:
            Signal объект или None
        """
        # Проверяем уверенность модели
        confidence = prediction.get("confidence", 0)
        if confidence < self.min_confidence:
            logger.debug(
                f"Low confidence {confidence:.2f} < {self.min_confidence}, skipping signal"
            )
            return None

        # Проверяем силу сигнала
        signal_strength_value = prediction.get("signal_strength", 0)
        if signal_strength_value < self.min_signal_strength:
            logger.debug(
                f"Weak signal {signal_strength_value:.2f} < {self.min_signal_strength}, skipping"
            )
            return None

        # Проверяем уровень риска
        risk_level = prediction.get("risk_level", "HIGH")
        if not self._check_risk_tolerance(risk_level):
            logger.debug(
                f"Risk level {risk_level} exceeds tolerance {self.risk_tolerance}, skipping"
            )
            return None

        # Определяем тип сигнала
        ml_signal_type = prediction.get("signal_type", "NEUTRAL")
        if ml_signal_type == "NEUTRAL":
            return None

        # Мапим ML сигнал на торговый SignalType
        if ml_signal_type == "BUY":
            signal_type = SignalType.LONG
        elif ml_signal_type == "SELL":
            signal_type = SignalType.SHORT
        else:
            return None

        # Определяем силу сигнала
        if signal_strength_value >= 0.8:
            strength = SignalStrength.VERY_STRONG
        elif signal_strength_value >= 0.6:
            strength = SignalStrength.STRONG
        elif signal_strength_value >= 0.4:
            strength = SignalStrength.MEDIUM
        else:
            strength = SignalStrength.WEAK

        # Получаем текущую цену из дополнительных данных
        current_price = None
        if additional_data and "current_price" in additional_data:
            current_price = additional_data["current_price"]

        # Создаем сигнал
        signal = Signal(
            symbol=symbol,
            exchange=exchange,
            signal_type=signal_type,
            strength=strength.value,
            confidence=confidence,
            strategy_name="PatchTST_ML",
            suggested_price=current_price,
            suggested_stop_loss=prediction.get("stop_loss"),
            suggested_take_profit=prediction.get("take_profit"),
            indicators={
                "ml_predictions": prediction.get("predictions", {}),
                "risk_level": risk_level,
                "signal_strength": signal_strength_value,
            },
            extra_data={
                "ml_model": "UnifiedPatchTST",
                "prediction_timestamp": prediction.get("timestamp"),
                "additional_data": additional_data,
            },
        )

        logger.info(
            f"Generated {signal_type.value} signal for {symbol} "
            f"with confidence {confidence:.2f} and strength {strength.value}"
        )

        return signal

    def _check_risk_tolerance(self, risk_level: str) -> bool:
        """
        Проверяет, соответствует ли уровень риска настройкам.

        Args:
            risk_level: Уровень риска из предсказания

        Returns:
            True если риск приемлемый
        """
        risk_hierarchy = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}

        prediction_risk = risk_hierarchy.get(risk_level, 3)
        tolerance_risk = risk_hierarchy.get(self.risk_tolerance, 2)

        return prediction_risk <= tolerance_risk

    def _get_cached_prediction(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Получает закэшированное предсказание"""
        if cache_key not in self.prediction_cache:
            return None

        cached_data = self.prediction_cache[cache_key]
        cached_time = datetime.fromisoformat(cached_data["timestamp"])

        # Проверяем TTL
        if datetime.now() - cached_time > timedelta(seconds=self.cache_ttl):
            del self.prediction_cache[cache_key]
            return None

        return cached_data

    def _cache_prediction(self, cache_key: str, prediction: Dict[str, Any]):
        """Кэширует предсказание"""
        self.prediction_cache[cache_key] = prediction

        # Очищаем старые записи
        self._cleanup_cache()

    def _cleanup_cache(self):
        """Очищает устаревшие записи из кэша"""
        current_time = datetime.now()
        keys_to_remove = []

        for key, data in self.prediction_cache.items():
            cached_time = datetime.fromisoformat(data["timestamp"])
            if current_time - cached_time > timedelta(seconds=self.cache_ttl):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.prediction_cache[key]

    async def validate_signal(self, signal: Signal) -> bool:
        """
        Дополнительная валидация сигнала.

        Args:
            signal: Сигнал для валидации

        Returns:
            True если сигнал валиден
        """
        # Здесь можно добавить дополнительные проверки
        # Например, проверка на конфликт с другими сигналами,
        # проверка рыночных условий и т.д.

        return True

    def update_config(self, config: Dict[str, Any]):
        """Обновляет конфигурацию процессора"""
        ml_config = config.get("ml", {})
        self.min_confidence = ml_config.get("min_confidence", self.min_confidence)
        self.min_signal_strength = ml_config.get(
            "min_signal_strength", self.min_signal_strength
        )
        self.risk_tolerance = ml_config.get("risk_tolerance", self.risk_tolerance)

        logger.info(
            f"Config updated: confidence={self.min_confidence}, "
            f"strength={self.min_signal_strength}, risk={self.risk_tolerance}"
        )
