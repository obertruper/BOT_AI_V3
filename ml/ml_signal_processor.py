#!/usr/bin/env python3
"""
ML Signal Processor для интеграции ML предсказаний с торговыми сигналами
"""

import asyncio
import heapq
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from database.db_manager import get_db
from database.models.base_models import SignalType
from database.models.signal import Signal
from ml.ml_manager import MLManager
from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator
from production_features_config import REAL_FEATURES_240 as REQUIRED_FEATURES_240

# Импорт UnifiedPrediction для поддержки нового формата
try:
    from ml.adapters import UnifiedPrediction

    UNIFIED_PREDICTION_AVAILABLE = True
except ImportError:
    UNIFIED_PREDICTION_AVAILABLE = False

logger = setup_logger("ml_signal_processor")


class MLSignalProcessor:
    """
    Процессор для преобразования ML предсказаний в торговые сигналы.
    Интегрирует ML модель с торговой системой.
    """

    def __init__(
        self,
        ml_manager: MLManager,
        config: dict[str, Any],
        config_manager: ConfigManager | None = None,
    ):
        """
        Инициализация ML Signal Processor.

        Args:
            ml_manager: Менеджер ML моделей
            config: Конфигурация системы
            config_manager: Менеджер конфигурации
        """
        self.ml_manager = ml_manager
        self.config = config
        self.config_manager = config_manager

        # Пороги для принятия решений из конфигурации (читаем из ml.filters)
        # Поддержка и Pydantic и dict конфигурации
        if hasattr(config, "ml"):
            ml_config = config.ml
            if hasattr(ml_config, "model_dump"):
                ml_config = ml_config.model_dump()
            elif hasattr(ml_config, "dict"):
                ml_config = ml_config.dict()
            else:
                ml_config = dict(ml_config)
        else:
            ml_config = config.get("ml", {})

        filters_cfg = {}
        if isinstance(ml_config, dict):
            filters_cfg = ml_config.get("filters", {}) or {}

        # «Мягкие» значения по умолчанию
        self.min_confidence = filters_cfg.get(
            "min_confidence", ml_config.get("min_confidence", 0.30)
        )
        # Порог уверенности по типам сигналов (кастомизируемые)
        self.min_confidence_long = filters_cfg.get("min_confidence_long", self.min_confidence)
        self.min_confidence_short = filters_cfg.get("min_confidence_short", self.min_confidence)
        self.neutral_min_confidence = filters_cfg.get("neutral_min_confidence", 0.80)
        self.min_signal_strength = filters_cfg.get(
            "min_signal_strength", ml_config.get("min_signal_strength", 0.30)
        )
        self.risk_tolerance = ml_config.get("risk_tolerance", "MEDIUM")

        # Пороговые метрики качества (configurable)
        self.min_quality_score = filters_cfg.get("min_quality_score", 0.30)
        self.min_expected_value = filters_cfg.get("min_expected_value", 0.0015)
        self.min_risk_reward = filters_cfg.get("min_risk_reward", 1.10)

        # Кэш для предсказаний с коротким TTL
        self.prediction_cache = {}
        self.cache_ttl = 60  # 60 секунд - более частые обновления для свежести сигналов

        # Инициализируем калькулятор индикаторов с увеличенным TTL
        self.indicator_calculator = RealTimeIndicatorCalculator(
            cache_ttl=self.cache_ttl, config=config
        )

        # Data loader для получения OHLCV
        self.data_loader = None

        # Список активных задач
        self._pending_tasks = set()

        # Статистика разнообразия сигналов
        self.signal_stats = {
            "total_signals": 0,
            "long_signals": 0,
            "short_signals": 0,
            "last_warning_time": None,
        }

        logger.info("MLSignalProcessor initialized")

        # Статистика кэша для мониторинга
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "unique_symbols": set(),
            "last_cleanup": datetime.utcnow(),
        }

    async def process_market_data(
        self,
        symbol: str,
        exchange: str,
        ohlcv_data: pd.DataFrame,
        additional_data: dict[str, Any] | None = None,
    ) -> Signal | None:
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
            # УЛУЧШЕННОЕ КЭШИРОВАНИЕ: используем хэш последней свечи для уникальности
            import hashlib
            from datetime import datetime

            # Создаем хеш последней свечи для уникальности
            if ohlcv_data is not None and len(ohlcv_data) > 0:
                # Используем OHLCV последней свечи для создания уникального хэша
                last_candle = ohlcv_data.iloc[-1]
                candle_str = f"{last_candle.get('open', 0):.8f}_{last_candle.get('high', 0):.8f}_{last_candle.get('low', 0):.8f}_{last_candle.get('close', 0):.8f}_{last_candle.get('volume', 0):.2f}"
                data_hash = hashlib.md5(candle_str.encode()).hexdigest()[:12]

                # Временная метка с округлением до минуты для группировки близких запросов
                time_bucket = datetime.utcnow().strftime("%Y%m%d%H%M")
            else:
                data_hash = "no_data"
                time_bucket = datetime.utcnow().strftime("%Y%m%d%H%M")

            # Ключ кэша: биржа:символ:временной_бакет:хэш_свечи
            cache_key = f"{exchange}:{symbol}:{time_bucket}:{data_hash}"

            logger.debug(f"🔑 Уникальный cache key для {symbol}: {cache_key}")

            cached = self._get_cached_prediction(cache_key)
            if cached:
                self.cache_stats["hits"] += 1
                logger.debug(f"✅ Cache HIT для {symbol}: {cache_key}")
                return self._create_signal_from_prediction(
                    cached, symbol, exchange, additional_data
                )

            # Получаем предсказание от ML модели
            self.cache_stats["misses"] += 1
            self.cache_stats["unique_symbols"].add(symbol)
            logger.info(f"🔄 Cache MISS для {symbol} - генерируем НОВОЕ предсказание")
            prediction = await self.ml_manager.predict(ohlcv_data)

            # ДОБАВЛЕНО: Логируем уникальность предсказания
            if prediction and "signal_type" in prediction:
                signal_type = prediction.get("signal_type", "UNKNOWN")
                confidence = prediction.get("confidence", 0)
                logger.info(
                    f"🎯 Новое предсказание для {symbol}: {signal_type} "
                    f"(уверенность: {confidence:.2%})"
                )

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

    def _create_signal_from_unified(
        self,
        prediction: "UnifiedPrediction",
        symbol: str,
        exchange: str,
        additional_data: dict[str, Any] | None = None,
    ) -> Signal | None:
        """
        Создает торговый сигнал на основе UnifiedPrediction.

        Args:
            prediction: UnifiedPrediction от адаптера
            symbol: Торговый символ
            exchange: Название биржи
            additional_data: Дополнительные данные

        Returns:
            Signal объект или None
        """
        # Проверяем уверенность модели
        if prediction.confidence < self.min_confidence:
            logger.debug(
                f"Low confidence {prediction.confidence:.2f} < {self.min_confidence}, skipping signal"
            )
            return None

        # Проверяем силу сигнала
        if prediction.signal_strength < self.min_signal_strength:
            logger.debug(
                f"Weak signal {prediction.signal_strength:.2f} < {self.min_signal_strength}, skipping"
            )
            return None

        # Проверяем уровень риска
        risk_level = prediction.risk_metrics.risk_level if prediction.risk_metrics else "HIGH"
        if not self._check_risk_tolerance(risk_level):
            logger.debug(
                f"Risk level {risk_level} exceeds tolerance {self.risk_tolerance}, skipping"
            )
            return None

        # Определяем тип сигнала
        ml_signal_type = prediction.signal_type

        # Обработка NEUTRAL сигналов
        if ml_signal_type == "NEUTRAL":
            if prediction.confidence < self.neutral_min_confidence:
                logger.debug(
                    f"🎯 NEUTRAL сигнал с уверенностью {prediction.confidence:.1%} < {self.neutral_min_confidence:.0%}, пропускаем"
                )
                return None

        # Мапим ML сигнал на торговый SignalType
        if ml_signal_type == "LONG":
            signal_type = SignalType.LONG
        elif ml_signal_type == "SHORT":
            signal_type = SignalType.SHORT
        elif ml_signal_type == "NEUTRAL":
            signal_type = SignalType.NEUTRAL
        else:
            logger.warning(f"Unknown signal type: {ml_signal_type}")
            return None

        # Получаем текущую цену
        entry_price = (additional_data.get("current_price") if additional_data else None) or 0.0

        # Создаем сигнал с явным указанием временных меток
        from datetime import UTC, datetime

        current_time = datetime.now(UTC)

        signal = Signal(
            strategy_name="UnifiedMLStrategy",
            symbol=symbol,
            signal_type=signal_type,
            entry_price=entry_price,
            stop_loss_pct=prediction.stop_loss_pct,
            take_profit_pct=prediction.take_profit_pct,
            confidence=prediction.confidence,
            strength=prediction.signal_strength,
            exchange=exchange,
            created_at=current_time,
            updated_at=current_time,
            metadata={
                "risk_level": risk_level,
                "quality_score": (
                    prediction.quality_score if hasattr(prediction, "quality_score") else None
                ),
                "timeframe_consensus": self._calculate_timeframe_consensus(prediction),
                "source": "unified_adapter",
            },
        )

        logger.info(
            f"✅ Created UnifiedPrediction signal: {signal_type.value} for {symbol} "
            f"(confidence: {prediction.confidence:.2%}, strength: {prediction.signal_strength:.2f})"
        )

        return signal

    def _calculate_timeframe_consensus(self, prediction: "UnifiedPrediction") -> float:
        """Рассчитывает консенсус между таймфреймами"""
        if not prediction.timeframe_predictions:
            return 0.0

        confidences = [tf.confidence for tf in prediction.timeframe_predictions.values()]
        return sum(confidences) / len(confidences) if confidences else 0.0

    def _create_signal_from_prediction(
        self,
        prediction: dict[str, Any],
        symbol: str,
        exchange: str,
        additional_data: dict[str, Any] | None = None,
    ) -> Signal | None:
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
        # Проверяем, это UnifiedPrediction или dict
        if UNIFIED_PREDICTION_AVAILABLE and isinstance(prediction, UnifiedPrediction):
            return self._create_signal_from_unified(prediction, symbol, exchange, additional_data)
        # Логируем полное предсказание для отладки
        logger.info(f"🔍 Предсказание для {symbol}:")
        logger.info(f"   Сырое: {prediction}")

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

        # Обработка NEUTRAL сигналов
        # NEUTRAL (класс 2) означает отсутствие четкого направления
        if ml_signal_type == "NEUTRAL":
            # NEUTRAL сигналы обрабатываем только при очень высокой уверенности (>80%)
            # Это соответствует логике обучения где NEUTRAL = нет торговли
            if confidence < 0.8:
                logger.debug(
                    f"🎯 NEUTRAL сигнал с уверенностью {confidence:.1%} < 80%, пропускаем (правильно!)"
                )
                return None
            logger.info(
                f"🎯 NEUTRAL сигнал с очень высокой уверенностью {confidence:.1%}, обрабатываем как исключение"
            )

        # Мапим ML сигнал на торговый SignalType
        # Модель возвращает "LONG"/"SHORT"/"NEUTRAL"
        if ml_signal_type == "LONG":
            signal_type = SignalType.LONG
        elif ml_signal_type == "SHORT":
            signal_type = SignalType.SHORT
        elif ml_signal_type == "NEUTRAL":
            signal_type = SignalType.NEUTRAL
        else:
            logger.warning(f"Unknown signal type: {ml_signal_type}")
            return None

        # Определяем силу сигнала (используем числовое значение 0.0-1.0)
        strength = signal_strength_value

        # Получаем текущую цену из дополнительных данных
        current_price = None
        if additional_data and "current_price" in additional_data:
            current_price = additional_data["current_price"]

        # ВАЖНО: Рассчитываем правильный размер позиции в единицах актива
        # Используем конфигурацию: fixed_balance * risk_per_trade * leverage
        fixed_balance = 100.0  # Из config/trading.yaml
        risk_per_trade = 0.02  # 2% риска
        leverage = 5.0  # 5x плечо

        # Расчет размера позиции в USD
        position_size_usd = fixed_balance * risk_per_trade * leverage  # $100 * 0.02 * 5 = $10

        # Конвертация в единицы актива
        suggested_quantity = position_size_usd / current_price if current_price > 0 else 0.01

        logger.info(
            f"💰 Размер позиции: ${position_size_usd:.2f} USD = {suggested_quantity:.6f} {symbol} "
            f"(цена: ${current_price:.2f})"
        )

        # Подготовим EV на основе SL/TP, если они рассчитаны
        ev_from_sltp = 0.0
        try:
            if (
                locals().get("stop_loss") is not None
                and locals().get("take_profit") is not None
                and current_price
                and current_price > 0
            ):
                risk_pct = abs(current_price - locals().get("stop_loss")) / current_price
                reward_pct = abs(locals().get("take_profit") - current_price) / current_price
                ev_from_sltp = reward_pct * confidence - risk_pct * (1 - confidence)
        except Exception:
            ev_from_sltp = 0.0

        # Создаем сигнал с явным указанием временных меток
        # ВАЖНО: если выше рассчитали SL/TP (по pct или дефолтным), используем их,
        # чтобы downstream-логика (EV, RR) работала корректно
        current_time = datetime.now(UTC)

        signal = Signal(
            symbol=symbol,
            exchange=exchange,
            signal_type=signal_type,
            strength=strength,  # Точное значение без округления
            confidence=confidence,  # Точное значение без округления
            strategy_name="PatchTST_ML",
            suggested_price=current_price,
            suggested_stop_loss=locals().get("stop_loss"),
            suggested_take_profit=locals().get("take_profit"),
            suggested_quantity=suggested_quantity,  # ДОБАВЛЕНО: правильный размер в единицах
            suggested_position_size=position_size_usd,  # ДОБАВЛЕНО: размер в USD для signal_processor
            created_at=current_time,
            updated_at=current_time,
            indicators={
                "ml_predictions": prediction.get("predictions", {}),
                "risk_level": risk_level,
                "signal_strength": signal_strength_value,
                "success_probability": prediction.get("success_probability", 0.5),  # Добавлено!
                "expected_value": ev_from_sltp,
            },
            extra_data={
                "ml_model": "UnifiedPatchTST",
                "prediction_timestamp": prediction.get("timestamp"),
                "additional_data": additional_data,
                "raw_prediction": prediction,  # Сохраняем полное предсказание для анализа
            },
        )

        logger.info(
            f"Generated {signal_type.value} signal for {symbol} "
            f"with confidence {confidence:.2f} and strength {strength}"
        )

        # Обновляем статистику и проверяем разнообразие сигналов
        self._update_signal_diversity_stats(signal_type)

        return signal

    def _update_signal_diversity_stats(self, signal_type):
        """
        Обновляет статистику разнообразия сигналов и предупреждает о дисбалансе.

        Args:
            signal_type: Тип сигнала (SignalType.LONG или SignalType.SHORT)
        """
        from database.models.base_models import SignalType

        # Обновляем счетчики
        self.signal_stats["total_signals"] += 1
        if signal_type == SignalType.LONG:
            self.signal_stats["long_signals"] += 1
        elif signal_type == SignalType.SHORT:
            self.signal_stats["short_signals"] += 1
        elif signal_type == SignalType.NEUTRAL:
            self.signal_stats["neutral_signals"] = self.signal_stats.get("neutral_signals", 0) + 1

        # Проверяем разнообразие каждые 10 сигналов
        if self.signal_stats["total_signals"] % 10 == 0:
            total = self.signal_stats["total_signals"]
            long_pct = (self.signal_stats["long_signals"] / total) * 100
            short_pct = (self.signal_stats["short_signals"] / total) * 100
            neutral_pct = (self.signal_stats.get("neutral_signals", 0) / total) * 100

            # Предупреждение если более 70% сигналов в одном направлении (уменьшили с 80%)
            if long_pct > 70 or short_pct > 70:
                logger.warning(
                    f"⚠️ ДИСБАЛАНС СИГНАЛОВ: {long_pct:.1f}% LONG, {short_pct:.1f}% SHORT, {neutral_pct:.1f}% NEUTRAL! "
                    f"Проверьте пороги weighted_direction или калибровку модели."
                )
            else:
                logger.info(
                    f"📊 Разнообразие сигналов: {long_pct:.1f}% LONG, {short_pct:.1f}% SHORT, {neutral_pct:.1f}% NEUTRAL"
                )

            # Критическое предупреждение если 100% в одном направлении
            if long_pct == 100 or short_pct == 100:
                logger.critical(
                    f"🚨 КРИТИЧЕСКИЙ ДИСБАЛАНС: ВСЕ {total} сигналов в одном направлении! "
                    f"Рекомендуется остановить торговлю и проверить модель."
                )
                # Сбрасываем статистику после критического предупреждения
                self.signal_stats["long_signals"] = 0
                self.signal_stats["short_signals"] = 0
                self.signal_stats["total_signals"] = 0

            # Логируем текущий баланс
            logger.info(
                f"📊 Баланс сигналов (последние {total}): "
                f"LONG: {long_pct:.1f}%, SHORT: {short_pct:.1f}%"
            )

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

    def _get_cached_prediction(self, cache_key: str) -> dict[str, Any] | None:
        """Получает закэшированное предсказание"""
        if cache_key not in self.prediction_cache:
            return None

        cached_data = self.prediction_cache[cache_key]
        cached_time = datetime.fromisoformat(cached_data["timestamp"])

        # Проверяем TTL
        if datetime.now(UTC) - cached_time > timedelta(seconds=self.cache_ttl):
            del self.prediction_cache[cache_key]
            return None

        return cached_data

    def _cache_prediction(self, cache_key: str, prediction: dict[str, Any]):
        """Кэширует предсказание"""
        self.prediction_cache[cache_key] = prediction

        # Очищаем старые записи
        self._cleanup_cache()

    def _cleanup_cache(self):
        """
        Очищает устаревшие записи из кэша с расширенной логикой
        Поддерживает как новый, так и старый формат ключей кэша
        """
        current_time = datetime.now(UTC)
        keys_to_remove = []

        cache_size_before = len(self.prediction_cache)

        for key, data in self.prediction_cache.items():
            try:
                # Проверяем TTL на основе timestamp в данных
                if isinstance(data, dict) and "timestamp" in data:
                    cached_time = datetime.fromisoformat(data["timestamp"])
                    if current_time - cached_time > timedelta(seconds=self.cache_ttl):
                        keys_to_remove.append(key)
                else:
                    # Если нет timestamp, удаляем запись (некорректные данные)
                    keys_to_remove.append(key)
            except (ValueError, TypeError) as e:
                # Если не можем распарсить timestamp, удаляем запись
                logger.debug(f"Удаляем некорректную запись кэша {key}: {e}")
                keys_to_remove.append(key)

        # Удаляем устаревшие записи
        for key in keys_to_remove:
            del self.prediction_cache[key]

        # Дополнительная очистка по размеру кэша (защита от переполнения)
        max_cache_size = 1000  # Максимум 1000 записей
        if len(self.prediction_cache) > max_cache_size:
            # Сортируем по времени и удаляем самые старые
            sorted_items = sorted(
                self.prediction_cache.items(),
                key=lambda x: x[1].get("timestamp", "1970-01-01T00:00:00"),
            )

            items_to_remove = len(self.prediction_cache) - max_cache_size
            for i in range(items_to_remove):
                key_to_remove = sorted_items[i][0]
                del self.prediction_cache[key_to_remove]
                keys_to_remove.append(key_to_remove)

        cache_size_after = len(self.prediction_cache)
        if keys_to_remove:
            self.cache_stats["last_cleanup"] = current_time
            logger.debug(
                f"🧹 Очистка кэша: удалено {len(keys_to_remove)} записей "
                f"(было: {cache_size_before}, стало: {cache_size_after})"
            )

    async def validate_signal(self, signal: Signal) -> bool:
        """
        Улучшенная валидация сигнала с quality score и Expected Value.

        Args:
            signal: Сигнал для валидации

        Returns:
            True если сигнал валиден
        """
        # Расчет quality score
        ev = self._extract_expected_value(signal)
        # Подстраховка: если EV не найден (0.0), пересчитаем из SL/TP
        if (
            abs(ev) < 1e-9
            and signal.suggested_stop_loss
            and signal.suggested_take_profit
            and signal.suggested_price
        ):
            try:
                risk = (
                    abs(signal.suggested_price - signal.suggested_stop_loss)
                    / signal.suggested_price
                )
                reward = (
                    abs(signal.suggested_take_profit - signal.suggested_price)
                    / signal.suggested_price
                )
                ev = reward * signal.confidence - risk * (1 - signal.confidence)
            except Exception:
                ev = 0.0

        quality_components = {
            "confidence": signal.confidence,
            "strength": signal.strength,
            "risk_reward": self._calculate_risk_reward_ratio(signal),
            "expected_value": ev,
        }

        # Комплексный quality score
        quality_score = (
            quality_components["confidence"] * 0.25
            + quality_components["strength"] * 0.25
            + min(quality_components["risk_reward"] / 3.0, 1.0) * 0.25
            + min(abs(quality_components["expected_value"]) / 0.02, 1.0) * 0.25
        )

        # Логирование для анализа
        if signal.signal_type == SignalType.SHORT:
            logger.info(
                f"🔴 Валидация SHORT {signal.symbol}: quality={quality_score:.2f}, "
                f"conf={signal.confidence:.2f}, EV={quality_components['expected_value']:.4f}, "
                f"RR={quality_components['risk_reward']:.2f}"
            )

        # Доп. правило: нейтральные сигналы принимаем только при высокой уверенности (конфигурируемо)
        if signal.signal_type == SignalType.NEUTRAL and signal.confidence is not None:
            if signal.confidence < self.neutral_min_confidence:
                # Near-miss логирование (10% от порога)
                if signal.confidence >= 0.9 * self.neutral_min_confidence:
                    logger.info(
                        f"🟨 Почти прошёл NEUTRAL {signal.symbol}: confidence={signal.confidence:.2f} ~> min {self.neutral_min_confidence:.2f}"
                    )
                # Убираем WARNING для нейтральных отклонений, логируем как INFO
                logger.info(
                    f"❌ NEUTRAL сигнал {signal.symbol} отклонен: уверенность {signal.confidence:.2f} < {self.neutral_min_confidence}"
                )
                return False

        # Минимальный quality score (из конфигурации)
        min_quality_score = self.min_quality_score
        if quality_score < min_quality_score:
            # Near-miss логирование (10% от порога)
            if quality_score >= 0.9 * min_quality_score:
                logger.info(
                    f"🟨 Почти прошёл {signal.symbol}: quality={quality_score:.2f} ~> min {min_quality_score:.2f}"
                )
            logger.warning(
                f"❌ Сигнал {signal.symbol} отклонен: quality score "
                f"{quality_score:.2f} < {min_quality_score}"
            )
            return False

        # Проверяем минимальную уверенность (персигнальный порог)
        eff_min_conf = self.min_confidence
        if signal.signal_type == SignalType.LONG:
            eff_min_conf = self.min_confidence_long
        elif signal.signal_type == SignalType.SHORT:
            eff_min_conf = self.min_confidence_short
        elif signal.signal_type == SignalType.NEUTRAL:
            eff_min_conf = self.neutral_min_confidence

        if signal.confidence < eff_min_conf:
            # Near-miss логирование (10% от порога)
            if signal.confidence >= 0.9 * eff_min_conf:
                logger.info(
                    f"🟨 Почти прошёл {signal.symbol}: confidence={signal.confidence:.2f} ~> min {eff_min_conf:.2f}"
                )
            # Для NEUTRAL уже выше логируем как INFO; для остальных оставляем WARNING
            if signal.signal_type == SignalType.NEUTRAL:
                logger.info(
                    f"❌ Сигнал {signal.symbol} отклонен: уверенность {signal.confidence:.2f} < {eff_min_conf}"
                )
            else:
                logger.warning(
                    f"❌ Сигнал {signal.symbol} отклонен: уверенность {signal.confidence:.2f} < {eff_min_conf}"
                )
            return False

        # Проверяем минимальную силу сигнала
        if signal.strength < self.min_signal_strength:
            # Near-miss логирование (10% от порога)
            if signal.strength >= 0.9 * self.min_signal_strength:
                logger.info(
                    f"🟨 Почти прошёл {signal.symbol}: strength={signal.strength:.2f} ~> min {self.min_signal_strength:.2f}"
                )
            logger.warning(
                f"❌ Сигнал {signal.symbol} отклонен: сила "
                f"{signal.strength:.2f} < {self.min_signal_strength}"
            )
            return False

        # Проверка минимального Expected Value (из конфигурации)
        # ВАЖНО: для LONG и для SHORT требуем положительный EV и не ниже порога
        min_expected_value = self.min_expected_value
        ev_val = quality_components["expected_value"]
        if ev_val < min_expected_value:
            # Near-miss логирование (10% от порога) — только если EV положительный и близок к порогу
            if ev_val >= 0 and ev_val >= 0.9 * min_expected_value:
                logger.info(
                    f"🟨 Почти прошёл {signal.symbol}: EV={ev_val:.4f} ~> min {min_expected_value:.4f}"
                )
            logger.warning(
                f"❌ Сигнал {signal.symbol} отклонен: Expected Value "
                f"{ev_val:.4f} < {min_expected_value}"
            )
            return False

        # Проверка Risk/Reward (из конфигурации)
        min_risk_reward = self.min_risk_reward
        rr_val = quality_components["risk_reward"]
        if rr_val < min_risk_reward:
            # Near-miss логирование (10% от порога)
            if rr_val >= 0.9 * min_risk_reward:
                logger.info(
                    f"🟨 Почти прошёл {signal.symbol}: RR={rr_val:.2f} ~> min {min_risk_reward:.2f}"
                )
            logger.warning(
                f"❌ Сигнал {signal.symbol} отклонен: Risk/Reward {rr_val:.2f} < {min_risk_reward}"
            )
            return False

        logger.info(
            f"✅ {signal.signal_type.value} сигнал {signal.symbol} прошел валидацию! "
            f"Quality: {quality_score:.2f}, EV: {quality_components['expected_value']:.3%}"
        )

        return True

    def _calculate_risk_reward_ratio(self, signal: Signal) -> float:
        """Расчет соотношения риск/прибыль"""
        if not signal.suggested_stop_loss or not signal.suggested_take_profit:
            return 0.0

        risk = abs(signal.suggested_price - signal.suggested_stop_loss)
        reward = abs(signal.suggested_take_profit - signal.suggested_price)

        if risk == 0:
            return 0.0

        return reward / risk

    def _extract_expected_value(self, signal: Signal) -> float:
        """Извлекает Expected Value из сигнала"""
        # Пытаемся найти expected_value в разных местах
        if hasattr(signal, "expected_value"):
            return signal.expected_value

        if hasattr(signal, "indicators") and signal.indicators:
            if "expected_value" in signal.indicators:
                return signal.indicators["expected_value"]
            elif "ml_predictions" in signal.indicators:
                ml_pred = signal.indicators["ml_predictions"]
                if isinstance(ml_pred, dict):
                    if "expected_value" in ml_pred:
                        return ml_pred["expected_value"]
                    # Пытаемся вычислить из future_returns
                    if "future_returns" in ml_pred:
                        returns = ml_pred["future_returns"]
                        if isinstance(returns, (list, np.ndarray)) and len(returns) >= 3:
                            # Взвешенный расчет
                            return 0.2 * returns[0] + 0.3 * returns[1] + 0.4 * returns[2]

        # Fallback: оцениваем по TP/SL
        if signal.suggested_stop_loss and signal.suggested_take_profit:
            risk = abs(signal.suggested_price - signal.suggested_stop_loss) / signal.suggested_price
            reward = (
                abs(signal.suggested_take_profit - signal.suggested_price) / signal.suggested_price
            )
            # Простая оценка: EV = reward * confidence - risk * (1 - confidence)
            return reward * signal.confidence - risk * (1 - signal.confidence)

        return 0.0

    def update_config(self, config: dict[str, Any]):
        """Обновляет конфигурацию процессора"""
        ml_config = config.get("ml", {})
        filters_cfg = ml_config.get("filters", {}) if isinstance(ml_config, dict) else {}
        self.min_confidence = filters_cfg.get(
            "min_confidence", ml_config.get("min_confidence", self.min_confidence)
        )
        self.min_signal_strength = filters_cfg.get(
            "min_signal_strength", ml_config.get("min_signal_strength", self.min_signal_strength)
        )
        self.risk_tolerance = ml_config.get("risk_tolerance", self.risk_tolerance)
        self.min_quality_score = filters_cfg.get("min_quality_score", self.min_quality_score)
        self.min_expected_value = filters_cfg.get("min_expected_value", self.min_expected_value)
        self.min_risk_reward = filters_cfg.get("min_risk_reward", self.min_risk_reward)

        logger.info(
            f"Config updated: confidence={self.min_confidence}, strength={self.min_signal_strength}, "
            f"risk={self.risk_tolerance}, qmin={self.min_quality_score}, evmin={self.min_expected_value}, rrmin={self.min_risk_reward}"
        )

    async def initialize(self):
        """Асинхронная инициализация компонента"""
        try:
            logger.info("🔄 Инициализация ML Signal Processor...")

            # Проверяем что ML Manager инициализирован
            if not self.ml_manager:
                raise ValueError("ML Manager не передан в конструктор")

            # Инициализируем data loader если нужно
            if not self.data_loader:
                self.data_loader = DataLoader(self.config_manager)

            # Инициализируем статистику
            self._stats = {
                "total_signals_processed": 0,
                "valid_signals_generated": 0,
                "signals_saved": 0,
                "processing_errors": 0,
            }

            # Отмечаем как инициализированный
            self._initialized = True

            logger.info("✅ ML Signal Processor инициализирован")

        except Exception as e:
            logger.error(f"Ошибка инициализации ML Signal Processor: {e}")
            raise

    async def process_signal(
        self, symbol: str, features: np.ndarray, current_price: float
    ) -> Signal | None:
        """
        Обрабатывает один сигнал.

        Args:
            symbol: Торговый символ
            features: Массив признаков для предсказания
            current_price: Текущая цена

        Returns:
            Signal или None
        """
        try:
            # Получаем предсказание от модели
            predictions = await self.ml_manager.predict(features)

            # Конвертируем в сигнал
            signal = await self._convert_predictions_to_signal(
                symbol=symbol, predictions=predictions, current_price=current_price
            )

            if signal and await self.validate_signal(signal):
                self._stats["valid_signals_generated"] += 1
                return signal

            return None

        except Exception as e:
            logger.error(f"Error processing signal for {symbol}: {e}")
            self._stats["processing_errors"] += 1
            return None
        finally:
            self._stats["total_signals_processed"] += 1

    async def process_batch(self, batch_data: list[dict[str, Any]]) -> list[Signal]:
        """
        Обрабатывает пакет сигналов.

        Args:
            batch_data: Список данных для обработки

        Returns:
            Список валидных сигналов
        """
        signals = []

        for data in batch_data:
            signal = await self.process_signal(
                symbol=data["symbol"],
                features=data["features"],
                current_price=data["current_price"],
            )
            if signal:
                signals.append(signal)

        return signals

    async def _convert_predictions_to_signal(
        self,
        symbol: str,
        predictions: np.ndarray | dict[str, Any],
        current_price: float,
    ) -> Signal | None:
        """
        Конвертирует предсказания модели в сигнал.

        Args:
            symbol: Торговый символ
            predictions: Предсказания модели
            current_price: Текущая цена

        Returns:
            Signal или None
        """
        # Если predictions это numpy array, конвертируем в dict (старый формат)
        if isinstance(predictions, np.ndarray):
            # ВАЖНО: Модель выдает 20 значений, НЕ directions в позициях 4-8!
            # Структура: [0-3]: returns, [4-15]: direction logits, [16-19]: risk metrics
            pred_dict = {
                "future_returns": predictions[0:4].tolist(),
                "direction_logits": predictions[4:16].tolist(),  # 12 логитов для softmax
                "risk_metrics": predictions[16:20].tolist(),
            }
            logger.warning(
                "⚠️ Получен numpy array вместо dict - используем старый формат интерпретации"
            )
        else:
            pred_dict = predictions

        # НОВАЯ ЛОГИКА: Проверяем формат от ml_manager
        if "signal_type" in pred_dict:
            # Используем новый формат от ml_manager
            ml_signal_type = pred_dict.get("signal_type", "NEUTRAL")

            logger.info(f"🎯 ML signal_type: {ml_signal_type}")

            # Конвертируем ML сигнал в торговый SignalType
            if ml_signal_type == "LONG":
                signal_type = SignalType.LONG
            elif ml_signal_type == "SHORT":
                signal_type = SignalType.SHORT
            else:  # NEUTRAL
                logger.info("🎯 Нейтральный сигнал обрабатываем (старый формат)")
                signal_type = SignalType.NEUTRAL

            # Используем готовые значения от ml_manager
            confidence = pred_dict.get("confidence", 0.5)
            strength = pred_dict.get("signal_strength", 0.5)

            # Получаем expected_value из новых полей
            expected_value = pred_dict.get("expected_return", 0.0)
            if expected_value == 0.0 and "primary_returns" in pred_dict:
                # Вычисляем из primary_returns
                returns = pred_dict["primary_returns"]
                if isinstance(returns, dict):
                    expected_value = (
                        0.2 * returns.get("15m", 0.0)
                        + 0.3 * returns.get("1h", 0.0)
                        + 0.4 * returns.get("4h", 0.0)
                        + 0.1 * returns.get("12h", 0.0)
                    )

            # Получаем дополнительные параметры для расчетов
            risk_metrics = pred_dict.get("risk_metrics", {})
            if isinstance(risk_metrics, dict):
                max_drawdown_1h = risk_metrics.get("max_drawdown_1h", 0.02)
                max_drawdown_4h = risk_metrics.get("max_drawdown_4h", 0.02)
                implied_volatility = risk_metrics.get("volatility", 0.02)
            else:
                max_drawdown_1h = 0.02
                max_drawdown_4h = 0.02
                implied_volatility = 0.02

            # Получаем future_returns для indicators
            future_returns = pred_dict.get("primary_returns", {})
            if isinstance(future_returns, dict):
                future_returns = [
                    future_returns.get("15m", 0.0),
                    future_returns.get("1h", 0.0),
                    future_returns.get("4h", 0.0),
                    future_returns.get("12h", 0.0),
                ]

            # ВАЖНО: Теперь ml_manager возвращает проценты, не абсолютные цены!
            stop_loss_pct = pred_dict.get("stop_loss_pct")
            take_profit_pct = pred_dict.get("take_profit_pct")

            # Рассчитываем абсолютные цены на основе процентов
            if stop_loss_pct is not None and take_profit_pct is not None:
                if signal_type == SignalType.LONG:
                    # LONG: SL ниже цены входа, TP выше цены входа
                    stop_loss = current_price * (1 - stop_loss_pct)
                    take_profit = current_price * (1 + take_profit_pct)
                    logger.info(
                        f"📈 LONG {symbol}: entry={current_price:.6f}, SL={stop_loss:.6f} ({stop_loss_pct:.1%} ниже), TP={take_profit:.6f} ({take_profit_pct:.1%} выше)"
                    )
                elif signal_type == SignalType.SHORT:
                    # SHORT: SL выше цены входа, TP ниже цены входа
                    stop_loss = current_price * (1 + stop_loss_pct)
                    take_profit = current_price * (1 - take_profit_pct)
                    logger.info(
                        f"📉 SHORT {symbol}: entry={current_price:.6f}, SL={stop_loss:.6f} ({stop_loss_pct:.1%} выше), TP={take_profit:.6f} ({take_profit_pct:.1%} ниже)"
                    )
                else:  # NEUTRAL - не устанавливаем SL/TP
                    stop_loss = None
                    take_profit = None
                    logger.info(
                        f"🔵 NEUTRAL {symbol}: entry={current_price:.6f}, SL/TP не установлены"
                    )
            else:
                # Если проценты не определены, используем значения из enhanced_sltp
                enhanced_sltp = self.config.get("enhanced_sltp", {})
                initial_sltp = enhanced_sltp.get("initial", {})
                stop_loss_pct = initial_sltp.get("stop_loss_percent_min", 1.5) / 100  # 1.5%
                take_profit_pct = initial_sltp.get("take_profit_percent_min", 4.0) / 100  # 4%

                if signal_type == SignalType.LONG:
                    stop_loss = current_price * (1 - stop_loss_pct)
                    take_profit = current_price * (1 + take_profit_pct)
                else:
                    stop_loss = current_price * (1 + stop_loss_pct)
                    take_profit = current_price * (1 - take_profit_pct)

            risk_level = pred_dict.get("risk_level", "MEDIUM")

            # Вычисляем Kelly fraction и другие параметры для consistency
            win_probability = 1 / (1 + np.exp(-expected_value / 0.02))
            avg_win = abs(expected_value) if expected_value > 0 else 0.015
            avg_loss = max_drawdown_1h if signal_type == SignalType.LONG else max_drawdown_4h
            kelly_fraction = (
                (win_probability * avg_win - (1 - win_probability) * avg_loss) / avg_win
                if avg_win > 0
                else 0.01
            )
            kelly_fraction = max(0, min(kelly_fraction * 0.25, 0.02))

        else:
            # СТАРАЯ ЛОГИКА - обрабатываем direction_logits если они есть
            if "direction_logits" in pred_dict:
                # Преобразуем логиты в направления через softmax
                logits = np.array(pred_dict["direction_logits"]).reshape(
                    4, 3
                )  # 4 таймфрейма × 3 класса
                directions = []
                for tf_logits in logits:
                    exp_logits = np.exp(tf_logits - np.max(tf_logits))
                    probs = exp_logits / exp_logits.sum()
                    directions.append(np.argmax(probs))
                directions = np.array(directions)
                logger.info(f"🎯 Направления из логитов: {directions} (0=LONG, 1=SHORT, 2=NEUTRAL)")
            else:
                # Fallback на дефолтные значения
                directions = np.array(pred_dict.get("directions", [2, 2, 2, 2]))
                logger.warning(f"⚠️ Нет direction_logits, используем fallback: {directions}")

            signal_type = await self._determine_signal_type(directions)
            logger.info(f"🎯 Определенный тип сигнала: {signal_type}")

            if signal_type is None:
                logger.info("🎯 Сигнал не определен (слишком много FLAT)")
                return None

            # Вычисляем уверенность на основе логитов или используем дефолтные значения
            if "direction_logits" in pred_dict:
                # Рассчитываем вероятности из логитов
                logits = np.array(pred_dict["direction_logits"]).reshape(4, 3)
                all_probs = []
                for tf_logits in logits:
                    exp_logits = np.exp(tf_logits - np.max(tf_logits))
                    probs = exp_logits / exp_logits.sum()
                    all_probs.append(probs)
                # Берем вероятности для LONG (0) и SHORT (1)
                long_probs = [p[0] for p in all_probs]
                short_probs = [p[1] for p in all_probs]
            else:
                # Используем profit_probabilities если есть, иначе дефолтные
                long_probs = pred_dict.get("profit_probabilities", {}).get("long", [0.5] * 4)
                short_probs = pred_dict.get("profit_probabilities", {}).get("short", [0.5] * 4)

            # ВАЖНО: Рассчитываем Expected Value из future returns
            future_returns = np.array(pred_dict.get("future_returns", [0.0] * 4))
            # Взвешенный расчет ожидаемой доходности
            expected_value = (
                0.2 * future_returns[0]  # 15m - краткосрочный
                + 0.3 * future_returns[1]  # 1h - среднесрочный
                + 0.4 * future_returns[2]  # 4h - основной
                + 0.1 * future_returns[3]  # 12h - долгосрочный
            )

            # Фильтрация по Expected Value
            min_expected_value = 0.005  # Минимум 0.5% ожидаемой прибыли
            # ВАЖНО: требуем положительную ожидаемую доходность и не ниже порога
            if expected_value < min_expected_value:
                logger.warning(
                    f"⚠️ Сигнал отклонен: низкая ожидаемая доходность {expected_value:.4f} < {min_expected_value}"
                )
                return None

            if signal_type == SignalType.LONG:
                confidence = np.mean(long_probs)
            else:
                confidence = np.mean(short_probs)

            # Согласованность направлений
            direction_agreement = np.sum(
                directions == (0 if signal_type == SignalType.LONG else 1)
            ) / len(directions)

            # Риск метрики для динамических уровней
            risk_metrics = np.array(pred_dict.get("risk_metrics", [0.02] * 4))
            max_drawdown_1h = risk_metrics[0] if len(risk_metrics) > 0 else 0.02
            max_rally_1h = risk_metrics[1] if len(risk_metrics) > 1 else 0.02
            max_drawdown_4h = risk_metrics[2] if len(risk_metrics) > 2 else 0.02
            max_rally_4h = risk_metrics[3] if len(risk_metrics) > 3 else 0.02

            # Оценка волатильности из risk metrics
            implied_volatility = (max_rally_4h + max_drawdown_4h) / 2
            risk_level_num = np.mean(risk_metrics)

            # Вычисляем силу сигнала с учетом Expected Value
            strength = await self._calculate_signal_strength_enhanced(
                confidence=confidence,
                direction_agreement=direction_agreement,
                expected_value=expected_value,
                risk_level=risk_level_num,
                implied_volatility=implied_volatility,
            )

            # Вычисляем уровни риска
            stop_loss, take_profit = await self._calculate_risk_levels(
                signal_type=signal_type,
                current_price=current_price,
                risk_metrics=risk_metrics,
                profit_probabilities=long_probs if signal_type == SignalType.LONG else short_probs,
            )

            # Конвертируем числовой риск в текстовый
            if risk_level_num < 0.3:
                risk_level = "LOW"
            elif risk_level_num < 0.7:
                risk_level = "MEDIUM"
            else:
                risk_level = "HIGH"

        # Kelly Criterion для оптимального размера позиции
        win_probability = 1 / (1 + np.exp(-expected_value / 0.02))  # Sigmoid нормализация
        avg_win = abs(expected_value) if expected_value > 0 else 0.015
        avg_loss = max_drawdown_1h if signal_type == SignalType.LONG else max_drawdown_4h

        # Формула Келли с 25% фракцией для безопасности
        kelly_fraction = (
            (win_probability * avg_win - (1 - win_probability) * avg_loss) / avg_win
            if avg_win > 0
            else 0.01
        )
        kelly_fraction = max(0, min(kelly_fraction * 0.25, 0.02))  # 25% Келли, макс 2% капитала

        # Корректировка по волатильности
        target_volatility = 0.02  # 2% целевая волатильность
        volatility_multiplier = (
            min(target_volatility / implied_volatility, 1.5) if implied_volatility > 0 else 1.0
        )

        # Финальный размер позиции
        base_capital = 500.0  # Базовый капитал
        position_size_usd = base_capital * kelly_fraction * volatility_multiplier * confidence
        position_size_usd = max(5.0, min(position_size_usd, 50.0))  # От $5 до $50
        suggested_quantity = position_size_usd / current_price if current_price > 0 else 0.01

        # Создаем сигнал с явным указанием временных меток
        current_time = datetime.now(UTC)

        signal = Signal(
            symbol=symbol,
            exchange="bybit",  # Будет переопределено при необходимости
            signal_type=signal_type,
            confidence=confidence,
            strength=strength,
            suggested_stop_loss=stop_loss,
            suggested_take_profit=take_profit,
            suggested_price=current_price,
            suggested_quantity=suggested_quantity,  # Оптимальный размер по Kelly
            strategy_name="PatchTST_ML",
            created_at=current_time,
            updated_at=current_time,
            indicators={
                "ml_predictions": pred_dict.get("predictions", pred_dict),
                "risk_level": risk_level,
                "success_probability": win_probability,
                "expected_value": expected_value,  # Добавлено для валидации
                "kelly_fraction": kelly_fraction,  # Для анализа
                "implied_volatility": implied_volatility,  # Для мониторинга
                "quality_score": strength,  # Предварительная оценка качества
                "future_returns": (
                    future_returns.tolist()
                    if isinstance(future_returns, np.ndarray)
                    else future_returns
                ),
            },
        )

        # Специальное логирование для SHORT сигналов
        if signal_type == SignalType.SHORT:
            logger.warning(
                f"✅🔴 Создан SHORT сигнал для {symbol}: "
                f"confidence={confidence:.2f}, strength={strength:.2f}"
            )
        else:
            logger.info(
                f"✅ Создан {signal_type.value} сигнал для {symbol}: "
                f"confidence={confidence:.2f}, strength={strength:.2f}"
            )

        return signal

    async def _calculate_signal_strength(
        self,
        confidence: float,
        direction_agreement: float,
        profit_probability: float,
        risk_level: float,
    ) -> float:
        """
        Вычисляет силу сигнала.

        Args:
            confidence: Уверенность модели
            direction_agreement: Согласованность направлений
            profit_probability: Вероятность прибыли
            risk_level: Уровень риска

        Returns:
            Сила сигнала (0.0-1.0)
        """
        # Базовая формула с весами
        weights = {"confidence": 0.3, "direction": 0.3, "profit": 0.3, "risk": 0.1}

        # Инвертируем риск (низкий риск = высокий вклад)
        risk_contribution = 1.0 - min(risk_level * 10, 1.0)

        strength = (
            weights["confidence"] * confidence
            + weights["direction"] * direction_agreement
            + weights["profit"] * profit_probability
            + weights["risk"] * risk_contribution
        )

        return min(max(strength, 0.0), 1.0)

    async def _calculate_signal_strength_enhanced(
        self,
        confidence: float,
        direction_agreement: float,
        expected_value: float,
        risk_level: float,
        implied_volatility: float,
    ) -> float:
        """
        Улучшенный расчет силы сигнала с учетом Expected Value.

        Args:
            confidence: Уверенность модели
            direction_agreement: Согласованность направлений
            expected_value: Ожидаемая доходность
            risk_level: Уровень риска
            implied_volatility: Подразумеваемая волатильность

        Returns:
            Сила сигнала (0.0-1.0)
        """
        # Нормализуем Expected Value (2% = отличный сигнал)
        ev_score = min(abs(expected_value) / 0.02, 1.0)

        # Инвертируем риск (низкий риск = высокий вклад)
        risk_contribution = 1.0 - min(risk_level * 10, 1.0)

        # Волатильность score (оптимальная волатильность = 2%)
        vol_score = 1.0 - abs(implied_volatility - 0.02) / 0.02
        vol_score = max(0, min(vol_score, 1.0))

        # Веса для улучшенной формулы
        weights = {
            "expected_value": 0.35,  # Больший вес на доходность
            "confidence": 0.25,
            "direction": 0.20,
            "risk": 0.10,
            "volatility": 0.10,
        }

        strength = (
            weights["expected_value"] * ev_score
            + weights["confidence"] * confidence
            + weights["direction"] * direction_agreement
            + weights["risk"] * risk_contribution
            + weights["volatility"] * vol_score
        )

        return min(max(strength, 0.0), 1.0)

    async def _determine_signal_type(self, directions: np.ndarray) -> SignalType | None:
        """
        Определяет тип сигнала на основе направлений.

        Args:
            directions: Массив направлений (0=LONG, 1=SHORT, 2=FLAT)

        Returns:
            SignalType или None
        """
        # Подсчитываем голоса
        long_count = np.sum(directions == 0)
        short_count = np.sum(directions == 1)
        flat_count = np.sum(directions == 2)

        # Если большинство FLAT - нет сигнала
        if flat_count >= len(directions) / 2:
            return None

        # Определяем победителя
        if long_count > short_count:
            return SignalType.LONG
        elif short_count > long_count:
            return SignalType.SHORT
        else:
            return None

    async def _calculate_risk_levels(
        self,
        signal_type: SignalType,
        current_price: float,
        risk_metrics: np.ndarray,
        profit_probabilities: list[float] | np.ndarray,
    ) -> tuple:
        """
        Динамический расчет уровней stop loss и take profit на основе risk metrics.

        Args:
            signal_type: Тип сигнала
            current_price: Текущая цена
            risk_metrics: Метрики риска [max_drawdown_1h, max_rally_1h, max_drawdown_4h, max_rally_4h]
            profit_probabilities: Вероятности прибыли

        Returns:
            (stop_loss, take_profit)
        """
        # Извлекаем конкретные метрики
        max_drawdown_1h = risk_metrics[0] if len(risk_metrics) > 0 else 0.02
        max_rally_1h = risk_metrics[1] if len(risk_metrics) > 1 else 0.02
        max_drawdown_4h = risk_metrics[2] if len(risk_metrics) > 2 else 0.02
        max_rally_4h = risk_metrics[3] if len(risk_metrics) > 3 else 0.02

        # Получаем правильные уровни из enhanced_sltp конфигурации
        enhanced_sltp = self.config.get("enhanced_sltp", {})
        initial_sltp = enhanced_sltp.get("initial", {})

        # Используем правильные диапазоны из конфигурации
        sl_min = initial_sltp.get("stop_loss_percent_min", 1.0) / 100  # 1% -> 0.01
        sl_max = initial_sltp.get("stop_loss_percent_max", 2.0) / 100  # 2% -> 0.02
        tp_min = initial_sltp.get("take_profit_percent_min", 3.6) / 100  # 3.6% -> 0.036
        tp_max = initial_sltp.get("take_profit_percent_max", 6.0) / 100  # 6% -> 0.06

        # Базовые уровни для обратной совместимости
        base_risk = self.config.get("trading", {}).get("default_stop_loss_pct", 0.015)
        base_profit = self.config.get("trading", {}).get("default_take_profit_pct", 0.045)
        risk_reward_ratio = self.config.get("trading", {}).get("risk_reward_ratio", 3.0)

        if signal_type == SignalType.LONG:
            # Для LONG: адаптивный SL на основе волатильности, но в пределах 1-2%
            adaptive_sl = max_drawdown_1h * 1.2
            stop_loss_pct = max(sl_min, min(adaptive_sl, sl_max))  # Ограничиваем 1-2%

            # TP адаптивный на основе потенциала роста, но в пределах 3.6-6%
            # Используем вероятности для выбора между минимальным и максимальным TP
            avg_profit_prob = np.mean(profit_probabilities)

            if avg_profit_prob > 0.7:
                # Высокая вероятность - используем более амбициозный TP
                take_profit_pct = tp_min + (tp_max - tp_min) * 0.8  # ~5.5%
            elif avg_profit_prob > 0.5:
                # Средняя вероятность - средний TP
                take_profit_pct = tp_min + (tp_max - tp_min) * 0.5  # ~4.8%
            else:
                # Низкая вероятность - консервативный TP
                take_profit_pct = tp_min + (tp_max - tp_min) * 0.2  # ~4%

            # Учитываем потенциал движения
            potential_tp = max_rally_4h * 0.9
            if potential_tp > tp_min and potential_tp < tp_max:
                # Если потенциал в правильном диапазоне, используем его
                take_profit_pct = potential_tp
            elif potential_tp < tp_min:
                # Если потенциал слишком мал, используем минимум
                take_profit_pct = tp_min
            else:
                # Если потенциал слишком велик, ограничиваем максимумом
                take_profit_pct = min(potential_tp, tp_max)

            # Финальные уровни
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + take_profit_pct)

        else:  # SHORT
            # Для SHORT: аналогичная логика с инверсией
            adaptive_sl = max_rally_1h * 1.2
            stop_loss_pct = max(sl_min, min(adaptive_sl, sl_max))  # Ограничиваем 1-2%

            # TP для SHORT
            avg_profit_prob = np.mean(profit_probabilities)

            if avg_profit_prob > 0.7:
                take_profit_pct = tp_min + (tp_max - tp_min) * 0.8  # ~5.5%
            elif avg_profit_prob > 0.5:
                take_profit_pct = tp_min + (tp_max - tp_min) * 0.5  # ~4.8%
            else:
                take_profit_pct = tp_min + (tp_max - tp_min) * 0.2  # ~4%

            # Учитываем потенциал падения
            potential_tp = max_drawdown_4h * 0.9
            if potential_tp > tp_min and potential_tp < tp_max:
                take_profit_pct = potential_tp
            elif potential_tp < tp_min:
                take_profit_pct = tp_min
            else:
                take_profit_pct = min(potential_tp, tp_max)

            # Финальные уровни для SHORT
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - take_profit_pct)

        # Проверка минимального Risk/Reward
        actual_risk = abs(current_price - stop_loss) / current_price
        actual_reward = abs(take_profit - current_price) / current_price

        if actual_reward / actual_risk < 1.5:  # Минимум 1.5:1
            # Корректируем TP для достижения минимального RR
            if signal_type == SignalType.LONG:
                take_profit = current_price * (1 + actual_risk * 1.5)
            else:
                take_profit = current_price * (1 - actual_risk * 1.5)

        return stop_loss, take_profit

    async def _calculate_expiry(self, signal: Signal) -> datetime:
        """
        Вычисляет время истечения сигнала.

        Args:
            signal: Сигнал

        Returns:
            Время истечения
        """
        expiry_minutes = self.config.get("ml", {}).get("signal_expiry_minutes", 15)
        return signal.created_at + timedelta(minutes=expiry_minutes)

    async def save_signal(self, signal: Signal) -> bool:
        """
        Сохраняет сигнал в базу данных.

        Args:
            signal: Сигнал для сохранения

        Returns:
            True если успешно
        """
        try:
            # Не сохраняем NEUTRAL, если БД может не поддерживать это значение enum
            if signal.signal_type == SignalType.NEUTRAL:
                logger.info(
                    f"ℹ️ Пропуск сохранения NEUTRAL сигнала для {signal.symbol} (бессделочный сигнал)"
                )
                return False

            # Дополнительное логирование для SHORT сигналов
            if signal.signal_type == SignalType.SHORT:
                logger.warning(
                    f"🔴 Попытка сохранить SHORT сигнал для {signal.symbol}: "
                    f"strength={signal.strength:.2f}, confidence={signal.confidence:.2f}"
                )

            # Используем единый DBManager с asyncpg-репозиторием сигналов
            db_manager = await get_db()
            if not getattr(db_manager, "signals", None):
                logger.error("SignalRepository не инициализирован в DBManager")
                return False

            # Сохранение через репозиторий (обеспечивает корректные типы для asyncpg)
            await db_manager.signals.save_signal(signal)

            self._stats["signals_saved"] += 1

            if signal.signal_type == SignalType.SHORT:
                logger.warning(f"✅🔴 SHORT сигнал УСПЕШНО сохранен для {signal.symbol}")
            else:
                logger.info(f"✅ Signal saved for {signal.symbol}")

            # Отправляем сигнал в TradingEngine после успешного сохранения
            try:
                from core.shared_context import shared_context

                orchestrator = shared_context.get_orchestrator()
                if (
                    orchestrator
                    and hasattr(orchestrator, "trading_engine")
                    and orchestrator.trading_engine
                ):
                    logger.info(f"📤 Отправка сохраненного сигнала {signal.symbol} в TradingEngine")
                    await orchestrator.trading_engine.receive_trading_signal(signal)
                    logger.info(
                        f"✅ Сохраненный сигнал {signal.symbol} успешно отправлен в TradingEngine"
                    )
                else:
                    logger.warning("⚠️ TradingEngine не доступен для отправки сохраненного сигнала")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки сохраненного сигнала в TradingEngine: {e}")

            return True
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            return False

    async def filter_signals(self, signals: list[Signal]) -> list[Signal]:
        """
        Фильтрует слабые сигналы.

        Args:
            signals: Список сигналов

        Returns:
            Отфильтрованный список
        """
        filtered = []
        for signal in signals:
            if await self.validate_signal(signal):
                filtered.append(signal)
        return filtered

    async def aggregate_signals(self, signals: list[dict[str, Any]]) -> dict[str, Any] | None:
        """
        Агрегирует множественные сигналы.

        Args:
            signals: Список сигналов для агрегации

        Returns:
            Агрегированный сигнал или None
        """
        if not signals:
            return None

        # Группируем по символу
        symbol = signals[0]["symbol"]

        # Агрегируем метрики
        confidences = [s.get("confidence", 0) for s in signals]
        strengths = [s.get("strength", 0) for s in signals]

        aggregated = {
            "symbol": symbol,
            "aggregated_confidence": np.mean(confidences),
            "aggregated_strength": np.mean(strengths),
            "signal_count": len(signals),
            "signals": signals,
        }

        return aggregated

    async def get_metrics(self) -> dict[str, Any]:
        """
        Возвращает метрики производительности.

        Returns:
            Словарь с метриками
        """
        total = self._stats["total_signals_processed"]
        if total == 0:
            return {
                "total_processed": 0,
                "success_rate": 0.0,
                "save_rate": 0.0,
                "error_rate": 0.0,
                "cache_metrics": self.get_cache_metrics(),
            }

        return {
            "total_processed": total,
            "success_rate": self._stats["valid_signals_generated"] / total,
            "save_rate": self._stats["signals_saved"] / total,
            "error_rate": self._stats["processing_errors"] / total,
            "cache_metrics": self.get_cache_metrics(),
        }

    def get_cache_metrics(self) -> dict[str, Any]:
        """
        Возвращает детальные метрики кэша для мониторинга уникальности предсказаний

        Returns:
            Словарь с метриками кэша
        """
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = self.cache_stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            "cache_hits": self.cache_stats["hits"],
            "cache_misses": self.cache_stats["misses"],
            "cache_hit_rate": hit_rate,
            "cache_size": len(self.prediction_cache),
            "unique_symbols_processed": len(self.cache_stats["unique_symbols"]),
            "symbols_list": list(self.cache_stats["unique_symbols"]),
            "cache_ttl_seconds": self.cache_ttl,
            "last_cleanup": self.cache_stats["last_cleanup"].isoformat(),
        }

    async def queue_signal(self, signal_data: dict[str, Any]):
        """
        Добавляет сигнал в приоритетную очередь.

        Args:
            signal_data: Данные сигнала
        """
        # Приоритет: high=0, medium=1, low=2
        priority_map = {"high": 0, "medium": 1, "low": 2}
        priority = priority_map.get(signal_data.get("priority", "medium"), 1)

        # Используем отрицательную уверенность для max heap
        confidence = -signal_data.get("confidence", 0)

        # Добавляем в кучу (приоритет, уверенность, данные)
        heapq.heappush(self._signal_queue, (priority, confidence, signal_data))

    async def process_queue(self) -> list[dict[str, Any]]:
        """
        Обрабатывает очередь сигналов.

        Returns:
            Список обработанных сигналов
        """
        processed = []

        while self._signal_queue:
            _, _, signal_data = heapq.heappop(self._signal_queue)
            processed.append(signal_data)

        return processed

    async def get_or_generate_signal(self, symbol: str, data: dict[str, Any]) -> Signal | None:
        """
        Получает сигнал из кеша или генерирует новый.

        Args:
            symbol: Торговый символ
            data: Данные для генерации

        Returns:
            Signal или None
        """
        # Проверяем кеш
        cache_key = f"signal:{symbol}"

        if self._enable_cache and cache_key in self.prediction_cache:
            cached = self.prediction_cache[cache_key]
            if isinstance(cached, Signal):
                # Проверяем TTL
                if (datetime.utcnow() - cached.created_at).total_seconds() < self.cache_ttl:
                    return cached

        # Генерируем новый сигнал
        signal = await self._generate_signal(symbol, data)

        # Кешируем
        if self._enable_cache and signal:
            self.prediction_cache[cache_key] = signal

        return signal

    async def _generate_signal(self, symbol: str, data: dict[str, Any]) -> Signal | None:
        """
        Генерирует новый сигнал.

        Args:
            symbol: Торговый символ
            data: Данные для генерации

        Returns:
            Signal или None
        """
        # Заглушка для тестов
        return Signal(symbol=symbol, confidence=0.8)

    async def process_realtime_signal(
        self,
        symbol: str,
        exchange: str = "bybit",
        lookback_minutes: int = 7200,  # 480 свечей * 15 минут (5 дней)
    ) -> Signal | None:
        """
        Генерирует сигнал в реальном времени с расчетом индикаторов on-demand

        Args:
            symbol: Торговый символ
            exchange: Биржа
            lookback_minutes: Сколько минут истории загрузить

        Returns:
            Signal или None
        """
        try:
            logger.info(f"🔄 Real-time обработка сигнала для {symbol}")

            # 1. Получаем последние OHLCV данные из БД
            ohlcv_df = await self._fetch_latest_ohlcv(symbol, exchange, lookback_minutes)

            if ohlcv_df is None or len(ohlcv_df) < 96:
                logger.warning(
                    f"Недостаточно данных для {symbol}: "
                    f"{len(ohlcv_df) if ohlcv_df is not None else 0} < 96"
                )
                return None

            # 2. Сначала рассчитываем и сохраняем индикаторы в БД
            indicators = await self.indicator_calculator.calculate_indicators(
                symbol=symbol,
                ohlcv_df=ohlcv_df,
                save_to_db=True,  # ВКЛЮЧАЕМ сохранение в processed_market_data
            )

            # 3. Затем готовим ML input
            features_array, metadata = await self.indicator_calculator.prepare_ml_input(
                symbol=symbol,
                ohlcv_df=ohlcv_df,
                lookback=96,  # Стандартный lookback для модели
            )

            logger.info(f"📊 Рассчитано {metadata['features_count']} признаков для {symbol}")

            # 3. Получаем предсказание от модели
            logger.info(f"📊 Отправляем на предсказание массив формы: {features_array.shape}")
            prediction = await self.ml_manager.predict(
                features_array, symbol=symbol, current_price=metadata["last_price"]
            )  # Передаем symbol и текущую цену
            logger.info(f"📊 Получили предсказание: {type(prediction)}")

            # 🎨 КРАСИВАЯ ВИЗУАЛИЗАЦИЯ ML ВХОДНЫХ ДАННЫХ И ПРЕДСКАЗАНИЙ
            await self._display_ml_visualization(symbol, features_array, prediction)

            # 4. Конвертируем предсказание в сигнал
            signal = await self._convert_predictions_to_signal(
                symbol=symbol,
                predictions=prediction,
                current_price=metadata["last_price"],
            )

            logger.info(f"📊 Результат конвертации в сигнал: {signal is not None}")

            if signal:
                # Добавляем дополнительные данные
                signal.exchange = exchange
                signal.strategy_name = "PatchTST_RealTime"

                # Валидируем сигнал
                if await self.validate_signal(signal):
                    self._stats["valid_signals_generated"] += 1

                    # Сохраняем в БД если нужно
                    if self.config.get("ml", {}).get("save_signals", True):
                        # Специальное логирование для SHORT
                        if signal.signal_type == SignalType.SHORT:
                            logger.warning(f"🔴 Вызываем save_signal для SHORT сигнала {symbol}")

                        saved = await self.save_signal(signal)

                        if not saved:
                            if signal.signal_type == SignalType.SHORT:
                                logger.error(f"❌🔴 SHORT сигнал для {symbol} НЕ БЫЛ сохранен!")
                            else:
                                logger.warning(f"❌ Сигнал для {symbol} не был сохранен")

                    # Отправляем сигнал в TradingEngine
                    try:
                        from core.shared_context import shared_context

                        orchestrator = shared_context.get_orchestrator()
                        if (
                            orchestrator
                            and hasattr(orchestrator, "trading_engine")
                            and orchestrator.trading_engine
                        ):
                            logger.info(f"📤 Отправка сигнала {signal.symbol} в TradingEngine")
                            await orchestrator.trading_engine.receive_trading_signal(signal)
                            logger.info(
                                f"✅ Сигнал {signal.symbol} успешно отправлен в TradingEngine"
                            )
                        else:
                            logger.warning("⚠️ TradingEngine не доступен для отправки сигнала")
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки сигнала в TradingEngine: {e}")

                    logger.info(
                        f"✅ Сгенерирован {signal.signal_type.value} сигнал для {symbol} "
                        f"с уверенностью {signal.confidence:.2f}"
                    )

                    return signal
                else:
                    logger.debug(f"Сигнал для {symbol} не прошел валидацию")

            return None

        except Exception as e:
            logger.error(f"Ошибка real-time обработки для {symbol}: {e}")
            self._stats["processing_errors"] += 1
            return None
        finally:
            self._stats["total_signals_processed"] += 1

    async def _fetch_latest_ohlcv(
        self, symbol: str, exchange: str, lookback_minutes: int
    ) -> pd.DataFrame | None:
        """
        Получает последние OHLCV данные из БД с retry логикой

        Args:
            symbol: Символ
            exchange: Биржа
            lookback_minutes: Количество минут истории

        Returns:
            DataFrame с OHLCV данными или None
        """
        max_retries = 3
        retry_delay = 1.0
        last_error = None

        for attempt in range(max_retries):
            try:
                # Сначала пробуем получить из БД
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(minutes=lookback_minutes)

                db_manager = await get_db()

                # Добавляем таймаут для транзакции
                async with asyncio.timeout(10):
                    async with db_manager.transaction() as conn:
                        # Используем raw SQL вместо SQLAlchemy ORM
                        query = """
                            SELECT * FROM raw_market_data
                            WHERE symbol = $1
                              AND exchange = $2
                              AND datetime >= $3
                              AND interval_minutes = 15
                            ORDER BY timestamp
                        """

                        rows = await conn.fetch(query, symbol, exchange, start_date)
                        data = [dict(row) for row in rows]

                        if not data or len(data) < 240:
                            # Если данных мало - обновляем через data loader
                            logger.info(
                                f"Обновление данных для {symbol}: в БД только {len(data)} записей"
                            )

                            # Обновляем данные
                            await self.data_loader.update_latest_data(
                                symbols=[symbol], interval_minutes=15, exchange=exchange
                            )

                            # Повторно запрашиваем
                            rows = await conn.fetch(query, symbol, exchange, start_date)
                            data = [dict(row) for row in rows]

                        if data:
                            # Добавляем колонку symbol для правильной генерации признаков
                            df = pd.DataFrame(
                                [
                                    {
                                        "timestamp": d["timestamp"],
                                        "datetime": d["datetime"],
                                        "open": float(d["open"]),
                                        "high": float(d["high"]),
                                        "low": float(d["low"]),
                                        "close": float(d["close"]),
                                        "volume": float(d["volume"]),
                                        "turnover": (
                                            float(d.get("turnover", 0)) if d.get("turnover") else 0
                                        ),
                                        "symbol": symbol,  # Добавляем symbol для уникальных признаков
                                    }
                                    for d in data
                                ]
                            )

                            df.set_index("datetime", inplace=True)
                            df = df.sort_index()

                            logger.info(
                                f"Загружено {len(df)} свечей для {symbol} с колонкой symbol"
                            )
                            return df

                        return None

            except asyncio.TimeoutError:
                last_error = f"Timeout getting OHLCV data for {symbol}"
                logger.warning(f"Attempt {attempt + 1}/{max_retries}: {last_error}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue

            except Exception as e:
                last_error = str(e)
                # Не логируем ошибку rollback, просто предупреждаем
                if "rollback" in str(e).lower() and "connection" in str(e).lower():
                    logger.warning(f"Connection issue for {symbol}: {e}")
                else:
                    logger.error(f"Error getting OHLCV for {symbol}: {e}")

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue

        # Все попытки исчерпаны
        logger.error(f"Failed to get OHLCV for {symbol} after {max_retries} attempts: {last_error}")
        return None

    async def generate_signals_for_symbols(
        self, symbols: list[str], exchange: str = "bybit"
    ) -> list[Signal]:
        """
        Генерирует сигналы для списка символов

        Args:
            symbols: Список символов
            exchange: Биржа

        Returns:
            Список сгенерированных сигналов
        """
        signals = []

        # Параллельная генерация для всех символов
        tasks = []
        for symbol in symbols:
            task = self.process_realtime_signal(symbol, exchange)
            tasks.append(task)

        # Ждем завершения всех задач
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка генерации для {symbols[i]}: {result}")
            elif result is not None:
                signals.append(result)

        logger.info(f"📈 Сгенерировано {len(signals)} сигналов из {len(symbols)} символов")

        return signals

    async def shutdown(self):
        """Корректное завершение работы процессора"""
        self._initialized = False

        # Отменяем все незавершенные задачи
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()

        # Ждем завершения
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)

        # Закрываем data loader
        if self.data_loader:
            await self.data_loader.cleanup()

        logger.info("MLSignalProcessor shutdown complete")

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Получение статистики кэша для API эндпоинтов

        Returns:
            Словарь с метриками кэша
        """
        # Получаем уникальные символы из кэша
        symbols_in_cache = set()
        for key in self.prediction_cache:
            # Ключ кэша имеет формат: {exchange}:{symbol}:{time}:{data_hash}
            parts = key.split(":")
            if len(parts) >= 2:
                symbols_in_cache.add(parts[1])

        return {
            "cache_hits": self.cache_stats.get("cache_hits", 0),
            "cache_misses": self.cache_stats.get("cache_misses", 0),
            "cache_size": len(self.prediction_cache),
            "symbols": symbols_in_cache,
            "ttl_seconds": 300,  # Из конфигурации
            "last_cleanup": self.cache_stats.get("last_cleanup", datetime.now(UTC).isoformat()),
        }

    async def _display_ml_visualization(
        self, symbol: str, features_array: np.ndarray, prediction: np.ndarray | dict
    ) -> None:
        """
        🎨 КРАСИВАЯ ВИЗУАЛИЗАЦИЯ ML ВХОДНЫХ ДАННЫХ И ПРЕДСКАЗАНИЙ
        Отображает детальную информацию о входных признаках и предсказаниях модели
        """
        try:
            if features_array is None or features_array.size == 0:
                logger.debug("⚠️ Нет данных для визуализации")
                return

            # Получаем последнюю строку признаков для анализа (последние 96 свечей)
            if len(features_array.shape) == 3:
                # Формат (batch, sequence, features)
                features_to_show = features_array[0, -1, :]  # Последняя свеча
                context_data = features_array[0]  # Весь контекст
            elif len(features_array.shape) == 2:
                features_to_show = features_array[-1, :]  # Последняя строка
                context_data = features_array
            else:
                logger.warning("⚠️ Неизвестный формат features_array")
                return

            # ════════════════════════════════════════════════════════════════════
            # 🎯 ВХОДНЫЕ ПАРАМЕТРЫ МОДЕЛИ - КРАСИВАЯ ТАБЛИЦА
            # ════════════════════════════════════════════════════════════════════
            logger.info("")
            logger.info("╔══════════════════════════════════════════════════════════════════════╗")
            logger.info(
                f"║            ВХОДНЫЕ ПАРАМЕТРЫ МОДЕЛИ - {features_array.shape[-1]} ПРИЗНАКОВ             ║"
            )
            logger.info("╠══════════════════════════════════════════════════════════════════════╣")
            logger.info("║ 🎯 ОБЗОР ПРИЗНАКОВ (без имен):                                     ║")
            # Показываем первые 4 и последние 4 значения признаков как ориентир
            if len(features_to_show) >= 8:
                head_vals = ", ".join([f"{v:>+0.4f}" for v in features_to_show[:4]])
                tail_vals = ", ".join([f"{v:>+0.4f}" for v in features_to_show[-4:]])
                logger.info(f"║   • head: {head_vals:<48} ║")
                logger.info(f"║   • tail: {tail_vals:<48} ║")
            else:
                seq_vals = ", ".join([f"{v:>+0.4f}" for v in features_to_show])
                logger.info(f"║   • vals: {seq_vals:<48} ║")

            # Дополнительно: Топ‑8 признаков по абсолютному значению с реальными именами
            try:
                if len(features_to_show) == len(REQUIRED_FEATURES_240):
                    abs_vals = np.abs(features_to_show)
                    top_k = min(8, len(abs_vals))
                    top_idx = np.argsort(-abs_vals)[:top_k]
                    logger.info(
                        "╟──────────────────────────────────────────────────────────────────────╢"
                    )
                    logger.info(
                        "║ 🔎 ТОП ПРИЗНАКОВ (по |значению|):                                   ║"
                    )
                    for idx in top_idx:
                        name = REQUIRED_FEATURES_240[idx]
                        val = features_to_show[idx]
                        logger.info(f"║   • {idx:3d} {name:<32}: {val:>+12.6f}                 ║")
            except Exception:
                # Визуализация не должна ломать основной поток
                pass

            # Статистика признаков
            nan_count = np.isnan(features_to_show).sum()
            zero_count = (features_to_show == 0).sum()
            mean_val = np.nanmean(features_to_show)
            std_val = np.nanstd(features_to_show)

            logger.info("╟──────────────────────────────────────────────────────────────────────╢")
            logger.info("║ 📊 СТАТИСТИКА ПРИЗНАКОВ:                                            ║")
            logger.info(
                f"║   • Всего признаков: {len(features_to_show):<4}    • NaN: {nan_count:<6} • Zeros: {zero_count:<8}             ║"
            )
            logger.info(
                f"║   • Mean: {mean_val:<12.4f}  • Std: {std_val:<12.4f}                           ║"
            )
            logger.info("╚══════════════════════════════════════════════════════════════════════╝")

            # ════════════════════════════════════════════════════════════════════
            # 🤖 ML MODEL PREDICTION ANALYSIS - КРАСИВАЯ ТАБЛИЦА
            # ════════════════════════════════════════════════════════════════════
            if prediction is not None:
                logger.info("")
                logger.info(
                    "╔══════════════════════════════════════════════════════════════════════╗"
                )
                logger.info(
                    "║                    🤖 ML MODEL PREDICTION ANALYSIS                   ║"
                )
                logger.info(
                    "╠══════════════════════════════════════════════════════════════════════╣"
                )

                if isinstance(prediction, np.ndarray) and len(prediction) >= 20:
                    logger.info(
                        "║ 📊 RAW MODEL OUTPUTS (20 parameters):                                ║"
                    )

                    # Показываем в группах по 5
                    for i in range(0, min(20, len(prediction)), 5):
                        values = [
                            f"{prediction[j]:.4f}" for j in range(i, min(i + 5, len(prediction)))
                        ]
                        range_str = f"[{i}-{min(i + 4, len(prediction) - 1)}]"
                        logger.info(f"║  {range_str:>6}:  {', '.join(values):<50} ║")

                    logger.info(
                        "╠══════════════════════════════════════════════════════════════════════╣"
                    )
                    logger.info(
                        "║ 🔮 ИНТЕРПРЕТАЦИЯ ПРЕДСКАЗАНИЙ:                                      ║"
                    )

                    # Показываем интерпретацию основных предсказаний
                    interpretations = [
                        ("15m return", prediction[0] if len(prediction) > 0 else 0),
                        ("1h return", prediction[1] if len(prediction) > 1 else 0),
                        ("4h return", prediction[2] if len(prediction) > 2 else 0),
                        ("12h return", prediction[3] if len(prediction) > 3 else 0),
                        ("Max Drawdown 1h", prediction[16] if len(prediction) > 16 else 0),
                        ("Max Rally 1h", prediction[17] if len(prediction) > 17 else 0),
                        ("Max Drawdown 4h", prediction[18] if len(prediction) > 18 else 0),
                        ("Max Rally 4h", prediction[19] if len(prediction) > 19 else 0),
                    ]

                    for desc, value in interpretations:
                        logger.info(f"║   • {desc:<20}: {value:>+8.6f}                         ║")

                logger.info(
                    "╚══════════════════════════════════════════════════════════════════════╝"
                )

        except Exception as e:
            logger.error(f"Ошибка визуализации ML данных для {symbol}: {e}")
            # Не прерываем основной процесс из-за ошибки визуализации
