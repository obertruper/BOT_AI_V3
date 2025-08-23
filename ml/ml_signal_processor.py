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
from sqlalchemy import and_, select

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from database.db_manager import get_db
from database.models.base_models import SignalType
from database.models.market_data import RawMarketData
from database.models.signal import Signal
from ml.ml_manager import MLManager
from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

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

        # Пороги для принятия решений из конфигурации
        # Поддержка и Pydantic и dict конфигурации
        if hasattr(config, "ml"):
            ml_config = config.ml
            # Конвертируем Pydantic в dict
            if hasattr(ml_config, "model_dump"):
                ml_config = ml_config.model_dump()
            elif hasattr(ml_config, "dict"):
                ml_config = ml_config.dict()
            else:
                # Fallback на прямой доступ к атрибутам
                ml_config = {
                    "min_confidence": getattr(ml_config, "min_confidence", 0.3),
                    "min_signal_strength": getattr(ml_config, "min_signal_strength", 0.25),
                    "risk_tolerance": getattr(ml_config, "risk_tolerance", "MEDIUM"),
                }
        else:
            ml_config = config.get("ml", {})
        # Используем правильные пороги из ml_config.yaml
        self.min_confidence = ml_config.get(
            "min_confidence", 0.3
        )  # Из конфига confidence_threshold: 0.3
        self.min_signal_strength = ml_config.get("min_signal_strength", 0.25)  # Базовое значение
        self.risk_tolerance = ml_config.get("risk_tolerance", "MEDIUM")  # Консервативный подход

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
            if prediction.confidence < 0.8:
                logger.debug(
                    f"🎯 NEUTRAL сигнал с уверенностью {prediction.confidence:.1%} < 80%, пропускаем"
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

        # Создаем сигнал
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

        # Создаем сигнал
        signal = Signal(
            symbol=symbol,
            exchange=exchange,
            signal_type=signal_type,
            strength=strength,  # Точное значение без округления
            confidence=confidence,  # Точное значение без округления
            strategy_name="PatchTST_ML",
            suggested_price=current_price,
            suggested_stop_loss=prediction.get("stop_loss"),
            suggested_take_profit=prediction.get("take_profit"),
            suggested_quantity=suggested_quantity,  # ДОБАВЛЕНО: правильный размер в единицах
            suggested_position_size=position_size_usd,  # ДОБАВЛЕНО: размер в USD для signal_processor
            indicators={
                "ml_predictions": prediction.get("predictions", {}),
                "risk_level": risk_level,
                "signal_strength": signal_strength_value,
                "success_probability": prediction.get("success_probability", 0.5),  # Добавлено!
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
        Дополнительная валидация сигнала.

        Args:
            signal: Сигнал для валидации

        Returns:
            True если сигнал валиден
        """
        # Специальное логирование для SHORT сигналов
        if signal.signal_type == SignalType.SHORT:
            logger.warning(
                f"🔴 Валидация SHORT сигнала {signal.symbol}: "
                f"conf={signal.confidence:.2f} (min={self.min_confidence}), "
                f"strength={signal.strength:.2f} (min={self.min_signal_strength})"
            )

        # Проверяем минимальную уверенность
        if signal.confidence < self.min_confidence:
            if signal.signal_type == SignalType.SHORT:
                logger.error(
                    f"❌🔴 SHORT сигнал {signal.symbol} отклонен: низкая уверенность "
                    f"{signal.confidence:.2f} < {self.min_confidence}"
                )
            return False

        # Проверяем минимальную силу сигнала
        if signal.strength < self.min_signal_strength:
            if signal.signal_type == SignalType.SHORT:
                logger.error(
                    f"❌🔴 SHORT сигнал {signal.symbol} отклонен: низкая сила "
                    f"{signal.strength:.2f} < {self.min_signal_strength}"
                )
            return False

        # Здесь можно добавить дополнительные проверки
        # Например, проверка на конфликт с другими сигналами,
        # проверка рыночных условий и т.д.

        if signal.signal_type == SignalType.SHORT:
            logger.warning(f"✅🔴 SHORT сигнал {signal.symbol} прошел валидацию!")

        return True

    def update_config(self, config: dict[str, Any]):
        """Обновляет конфигурацию процессора"""
        ml_config = config.get("ml", {})
        self.min_confidence = ml_config.get("min_confidence", self.min_confidence)
        self.min_signal_strength = ml_config.get("min_signal_strength", self.min_signal_strength)
        self.risk_tolerance = ml_config.get("risk_tolerance", self.risk_tolerance)

        logger.info(
            f"Config updated: confidence={self.min_confidence}, "
            f"strength={self.min_signal_strength}, risk={self.risk_tolerance}"
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
            pred_dict = {
                "future_returns": predictions[0:4].tolist(),
                "directions": predictions[4:8].tolist(),
                "profit_probabilities": {
                    "long": predictions[8:12].tolist(),
                    "short": predictions[12:16].tolist(),
                },
                "risk_metrics": predictions[16:20].tolist(),
            }
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
                # Если проценты не определены, используем дефолтные значения
                stop_loss_pct = 0.02  # 2%
                take_profit_pct = 0.05  # 5%

                if signal_type == SignalType.LONG:
                    stop_loss = current_price * (1 - stop_loss_pct)
                    take_profit = current_price * (1 + take_profit_pct)
                else:
                    stop_loss = current_price * (1 + stop_loss_pct)
                    take_profit = current_price * (1 - take_profit_pct)

            risk_level = pred_dict.get("risk_level", "MEDIUM")

        else:
            # СТАРАЯ ЛОГИКА для обратной совместимости
            directions = np.array(pred_dict.get("directions", [2, 2, 2, 2]))
            logger.info(f"🎯 Направления (старый формат): {directions}")
            signal_type = await self._determine_signal_type(directions)
            logger.info(f"🎯 Определенный тип сигнала: {signal_type}")

            if signal_type is None:
                logger.info("🎯 Сигнал не определен (слишком много FLAT)")
                return None

            # Вычисляем уверенность и силу сигнала
            long_probs = pred_dict.get("profit_probabilities", {}).get("long", [0.5] * 4)
            short_probs = pred_dict.get("profit_probabilities", {}).get("short", [0.5] * 4)

            if signal_type == SignalType.LONG:
                confidence = np.mean(long_probs)
            else:
                confidence = np.mean(short_probs)

            # Согласованность направлений
            direction_agreement = np.sum(
                directions == (0 if signal_type == SignalType.LONG else 1)
            ) / len(directions)

            # Риск
            risk_metrics = np.array(pred_dict.get("risk_metrics", [0.02] * 4))
            risk_level_num = np.mean(risk_metrics)

            # Вычисляем силу сигнала
            strength = await self._calculate_signal_strength(
                confidence=confidence,
                direction_agreement=direction_agreement,
                profit_probability=confidence,
                risk_level=risk_level_num,
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

        # ВАЖНО: Рассчитываем правильный размер позиции в единицах актива
        position_size_usd = 10.0  # $10 на позицию (2% от $500 с плечом 5x)
        suggested_quantity = position_size_usd / current_price if current_price > 0 else 0.01

        # Создаем сигнал
        signal = Signal(
            symbol=symbol,
            exchange="bybit",  # Будет переопределено при необходимости
            signal_type=signal_type,
            confidence=confidence,
            strength=strength,
            suggested_stop_loss=stop_loss,
            suggested_take_profit=take_profit,
            suggested_price=current_price,
            suggested_quantity=suggested_quantity,  # ДОБАВЛЕНО: правильный размер в единицах
            strategy_name="PatchTST_ML",
            indicators={
                "ml_predictions": pred_dict.get("predictions", pred_dict),
                "risk_level": risk_level,
                "success_probability": pred_dict.get("success_probability", 0.5),
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
        Вычисляет уровни stop loss и take profit.

        Args:
            signal_type: Тип сигнала
            current_price: Текущая цена
            risk_metrics: Метрики риска
            profit_probabilities: Вероятности прибыли

        Returns:
            (stop_loss, take_profit)
        """
        # Базовый риск из конфигурации
        base_risk = self.config.get("trading", {}).get("default_stop_loss_pct", 0.02)
        base_profit = self.config.get("trading", {}).get("default_take_profit_pct", 0.04)
        risk_reward_ratio = self.config.get("trading", {}).get("risk_reward_ratio", 2.0)

        # Адаптивный риск на основе предсказаний
        avg_risk = np.mean(risk_metrics)
        risk_multiplier = 1.0 + avg_risk

        # Адаптивная прибыль на основе вероятностей
        avg_profit_prob = np.mean(profit_probabilities)
        profit_multiplier = avg_profit_prob * 1.5

        # Вычисляем уровни
        stop_loss_pct = base_risk * risk_multiplier
        take_profit_pct = max(stop_loss_pct * risk_reward_ratio, base_profit * profit_multiplier)

        if signal_type == SignalType.LONG:
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + take_profit_pct)
        else:  # SHORT
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - take_profit_pct)

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
            # Добавляем специальное логирование для SHORT сигналов
            if signal.signal_type == SignalType.SHORT:
                logger.warning(
                    f"🔴 Попытка сохранить SHORT сигнал для {signal.symbol}: "
                    f"strength={signal.strength:.2f}, confidence={signal.confidence:.2f}"
                )

            db_manager = await get_db()
            async with db_manager.transaction() as db:
                # Проверяем, существует ли уже такой сигнал
                existing = await db.execute(
                    select(Signal).where(
                        and_(
                            Signal.symbol == signal.symbol,
                            Signal.signal_type == signal.signal_type,
                            Signal.strength == signal.strength,
                            Signal.confidence == signal.confidence,
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    logger.debug(f"Signal already exists for {signal.symbol}, skipping")
                    if signal.signal_type == SignalType.SHORT:
                        logger.warning(f"🔴 SHORT сигнал для {signal.symbol} уже существует в БД!")
                    return False

                db.add(signal)
                await db.commit()
                self._stats["signals_saved"] += 1

                # Особое логирование для SHORT сигналов
                if signal.signal_type == SignalType.SHORT:
                    logger.warning(f"✅🔴 SHORT сигнал УСПЕШНО сохранен для {signal.symbol}")
                else:
                    logger.info(f"✅ Signal saved for {signal.symbol}")
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
                features_array, symbol=symbol
            )  # Передаем symbol
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
        Получает последние OHLCV данные из БД

        Args:
            symbol: Символ
            exchange: Биржа
            lookback_minutes: Количество минут истории

        Returns:
            DataFrame с OHLCV данными или None
        """
        try:
            # Сначала пробуем получить из БД
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(minutes=lookback_minutes)

            db_manager = await get_db()
            async with db_manager.transaction() as session:
                stmt = (
                    select(RawMarketData)
                    .where(
                        and_(
                            RawMarketData.symbol == symbol,
                            RawMarketData.exchange == exchange,
                            RawMarketData.datetime >= start_date,
                            RawMarketData.interval_minutes == 15,  # 15-минутные свечи
                        )
                    )
                    .order_by(RawMarketData.timestamp)
                )

                result = await session.execute(stmt)
                data = result.scalars().all()

                if not data or len(data) < 240:
                    # Если данных мало - обновляем через data loader
                    logger.info(f"Обновление данных для {symbol}: в БД только {len(data)} записей")

                    # Обновляем данные
                    await self.data_loader.update_latest_data(
                        symbols=[symbol], interval_minutes=15, exchange=exchange
                    )

                    # Повторно запрашиваем
                    result = await session.execute(stmt)
                    data = result.scalars().all()

                if data:
                    # Добавляем колонку symbol для правильной генерации признаков
                    df = pd.DataFrame(
                        [
                            {
                                "timestamp": d.timestamp,
                                "datetime": d.datetime,
                                "open": float(d.open),
                                "high": float(d.high),
                                "low": float(d.low),
                                "close": float(d.close),
                                "volume": float(d.volume),
                                "turnover": float(d.turnover) if d.turnover else 0,
                                "symbol": symbol,  # Добавляем symbol для уникальных признаков
                            }
                            for d in data
                        ]
                    )

                    df.set_index("datetime", inplace=True)
                    df = df.sort_index()

                    logger.info(f"Загружено {len(df)} свечей для {symbol} с колонкой symbol")
                    return df

                return None

        except Exception as e:
            logger.error(f"Ошибка получения OHLCV для {symbol}: {e}")
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
        for key in self.prediction_cache.keys():
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
            logger.info("║ 🎯 КЛЮЧЕВЫЕ ИНДИКАТОРЫ:                                             ║")

            # Отображаем ключевые признаки в красивом формате
            feature_names = [
                "returns",
                "macd",
                "atr_pct",
                "adx",
                "obv_trend",
                "trend_1h",
                "rsi",
                "bb_position",
                "stoch_k",
                "volume_ratio",
                "momentum_1h",
                "signal_strength",
            ]

            for i in range(0, len(feature_names), 2):
                left_name = feature_names[i] if i < len(feature_names) else ""
                right_name = feature_names[i + 1] if i + 1 < len(feature_names) else ""

                left_val = features_to_show[i % len(features_to_show)] if left_name else 0
                right_val = features_to_show[(i + 1) % len(features_to_show)] if right_name else 0

                logger.info(
                    f"║   • {left_name:<15}: {left_val:>10.4f}  │  {right_name:<15}: {right_val:>8.4f}  ║"
                )

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
                        range_str = f"[{i}-{min(i+4, len(prediction)-1)}]"
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
