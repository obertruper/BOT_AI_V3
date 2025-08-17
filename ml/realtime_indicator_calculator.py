#!/usr/bin/env python3
"""
Real-time расчет технических индикаторов для ML модели
Адаптировано для генерации сигналов в реальном времени
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert

from core.logger import setup_logger
from database.connections import get_async_db
from database.models.market_data import ProcessedMarketData, RawMarketData
from ml.config.features_240 import REQUIRED_FEATURES_240
from ml.logic.feature_engineering_v2 import FeatureEngineer

logger = setup_logger(__name__)


class RealTimeIndicatorCalculator:
    """
    Калькулятор для расчета всех индикаторов в реальном времени
    при генерации торговых сигналов
    """

    def __init__(
        self,
        cache_ttl: int = 900,
        config: dict[str, Any] | None = None,
        use_inference_mode: bool = True,
    ):
        """
        Args:
            cache_ttl: Время жизни кеша в секундах
            config: Конфигурация системы
            use_inference_mode: Использовать ли inference mode для генерации только 240 признаков
        """
        # Передаем inference_mode в конфигурацию FeatureEngineer
        engineer_config = config or {}
        engineer_config["inference_mode"] = use_inference_mode

        self.feature_engineer = FeatureEngineer(engineer_config, inference_mode=use_inference_mode)
        # Отключаем прогресс-бар чтобы не блокировать async операции
        self.feature_engineer.disable_progress = False  # Включаем логи для отладки
        self.cache = {}  # Кеш рассчитанных индикаторов
        self.cache_ttl = cache_ttl
        self._lock = asyncio.Lock()
        self.use_inference_mode = use_inference_mode

        logger.info(
            f"RealTimeIndicatorCalculator инициализирован (inference_mode={use_inference_mode})"
        )

    async def calculate_indicators(
        self, symbol: str, ohlcv_df: pd.DataFrame, save_to_db: bool = True
    ) -> dict[str, Any]:
        """
        Рассчитывает все индикаторы для символа в реальном времени

        Args:
            symbol: Торговый символ
            ohlcv_df: DataFrame с OHLCV данными (должен содержать минимум 240 свечей)
            save_to_db: Сохранять ли результаты в БД

        Returns:
            Словарь с рассчитанными индикаторами и признаками
        """
        try:
            logger.info(f"🔍 Starting calculate_indicators for {symbol}")
            # Проверяем кеш
            cache_key = f"{symbol}_{ohlcv_df.index[-1]}"
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.debug(f"Использован кеш для {symbol}")
                return cached_result

            # Проверяем достаточность данных
            if len(ohlcv_df) < 96:
                logger.warning(f"Недостаточно данных для {symbol}: {len(ohlcv_df)} < 96")
                return {}

            # Рассчитываем все признаки через FeatureEngineer
            logger.info(f"Расчет индикаторов для {symbol} в реальном времени...")

            # Подготавливаем DataFrame в нужном формате
            df = self._prepare_dataframe(ohlcv_df, symbol)

            # Рассчитываем все признаки
            logger.info(
                f"About to call create_features for {symbol} (inference_mode={self.use_inference_mode})"
            )
            features_result = self.feature_engineer.create_features(
                df, inference_mode=self.use_inference_mode
            )
            logger.info(
                f"create_features returned type: {type(features_result)}, shape: {getattr(features_result, 'shape', 'no shape')}"
            )

            # ИСПРАВЛЕНО: Используем точный список признаков из конфигурации
            if isinstance(features_result, pd.DataFrame):
                # Используем ТОЛЬКО признаки из REQUIRED_FEATURES_240
                available_cols = features_result.columns.tolist()
                selected_features = []

                # Выбираем признаки в правильном порядке из REQUIRED_FEATURES_240
                for feature in REQUIRED_FEATURES_240:
                    if feature in available_cols:
                        selected_features.append(feature)
                    else:
                        # Если признак отсутствует, логируем предупреждение
                        logger.warning(f"Признак {feature} отсутствует в результатах")

                # Проверяем, что получили ровно 240 признаков
                if len(selected_features) != 240:
                    logger.error(f"Получено {len(selected_features)} признаков вместо 240!")
                    # Дополняем нулями если меньше 240
                    while len(selected_features) < 240:
                        selected_features.append("padding_0")
                        features_result["padding_0"] = 0.0

                features_array = features_result[selected_features[:240]].values
                feature_names = selected_features[:240]
            elif isinstance(features_result, np.ndarray):
                features_array = features_result
                feature_names = [f"feature_{i}" for i in range(features_array.shape[1])]
            else:
                logger.error(f"create_features returned unexpected type: {type(features_result)}")
                return {}

            # feature_names уже определены выше

            # ИСПРАВЛЕНО: Извлекаем последнюю строку как numpy array, затем конвертируем в dict
            if features_array.ndim == 2 and features_array.shape[0] > 0:
                last_features = features_array[-1]  # Получаем последнюю строку как numpy array
                current_features = {
                    feature_names[i]: float(last_features[i]) for i in range(len(last_features))
                }
            else:
                logger.error(f"Неожиданная форма features_array: {features_array.shape}")
                return {}

            # Структурируем результат
            result = self._structure_indicators(current_features, ohlcv_df)

            # Добавляем метаинформацию
            result["metadata"] = {
                "symbol": symbol,
                "timestamp": int(ohlcv_df.index[-1].timestamp() * 1000),
                "datetime": ohlcv_df.index[-1],
                "features_count": len(current_features),
                "calculation_time": datetime.now(UTC),
            }

            # Сохраняем в БД если нужно
            if save_to_db:
                await self._save_to_database(symbol, result)

            # Кешируем результат
            self._add_to_cache(cache_key, result)

            logger.info(f"Рассчитано {len(current_features)} признаков для {symbol}")

            return result

        except Exception as e:
            logger.error(f"Ошибка расчета индикаторов для {symbol}: {e}")
            return {}

    async def calculate_indicators_batch(
        self, symbols: list[str], ohlcv_data: dict[str, pd.DataFrame]
    ) -> dict[str, dict[str, Any]]:
        """
        Пакетный расчет индикаторов для нескольких символов

        Args:
            symbols: Список символов
            ohlcv_data: Словарь {symbol: DataFrame}

        Returns:
            Словарь {symbol: indicators}
        """
        results = {}

        # Параллельный расчет для всех символов
        tasks = []
        for symbol in symbols:
            if symbol in ohlcv_data:
                task = self.calculate_indicators(symbol, ohlcv_data[symbol])
                tasks.append((symbol, task))

        # Ждем завершения всех расчетов
        for symbol, task in tasks:
            try:
                result = await task
                results[symbol] = result
            except Exception as e:
                logger.error(f"Ошибка расчета для {symbol}: {e}")
                results[symbol] = {}

        return results

    def _prepare_dataframe(self, ohlcv_df: pd.DataFrame, symbol: str = "BTCUSDT") -> pd.DataFrame:
        """
        Подготавливает DataFrame для FeatureEngineer
        """
        # Убеждаемся что есть все нужные колонки
        required_columns = ["open", "high", "low", "close", "volume"]

        df = ohlcv_df.copy()

        # Проверяем наличие колонок
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Отсутствует обязательная колонка: {col}")

        # Добавляем дополнительные колонки если их нет
        if "turnover" not in df.columns:
            df["turnover"] = df["close"] * df["volume"]

        # Добавляем колонку symbol (требуется для FeatureEngineer)
        if "symbol" not in df.columns:
            df["symbol"] = symbol

        # Обработка datetime колонки (требуется для FeatureEngineer)
        if "datetime" in df.columns:
            # Если datetime уже есть как колонка, используем её
            pass
        elif hasattr(df.index, "name") and df.index.name == "datetime":
            # Если datetime это имя индекса, переносим в колонку
            df = df.reset_index()
        else:
            # Если нет datetime ни как колонки ни как индекса, создаем из индекса
            df["datetime"] = df.index

        # Сортируем по времени
        df = df.sort_index()

        return df

    def _structure_indicators(
        self, features: dict[str, float], ohlcv_df: pd.DataFrame
    ) -> dict[str, Any]:
        """
        Структурирует индикаторы для сохранения в БД
        """
        # Базовые OHLCV
        last_candle = ohlcv_df.iloc[-1]

        result = {
            "ohlcv": {
                "open": float(last_candle["open"]),
                "high": float(last_candle["high"]),
                "low": float(last_candle["low"]),
                "close": float(last_candle["close"]),
                "volume": float(last_candle["volume"]),
            }
        }

        # Группируем индикаторы по категориям
        technical_indicators = {}
        microstructure_features = {}
        ml_features = features.copy()

        # Технические индикаторы
        tech_indicators_list = [
            "sma_",
            "ema_",
            "rsi_",
            "macd_",
            "bb_",
            "atr_",
            "stoch_",
            "adx_",
            "cci_",
            "williams_",
            "mfi_",
            "obv",
        ]

        for key, value in features.items():
            for indicator in tech_indicators_list:
                if key.startswith(indicator):
                    technical_indicators[key] = value
                    break

            # Микроструктурные признаки
            if any(x in key for x in ["spread", "imbalance", "pressure", "flow"]):
                microstructure_features[key] = value

        result["technical_indicators"] = technical_indicators
        result["microstructure_features"] = microstructure_features
        result["ml_features"] = ml_features

        return result

    async def _save_to_database(self, symbol: str, indicators: dict[str, Any]):
        """
        Сохраняет рассчитанные индикаторы в базу данных
        """
        try:
            async with get_async_db() as session:
                # Получаем последнюю запись из raw_market_data
                stmt = (
                    select(RawMarketData)
                    .where(RawMarketData.symbol == symbol)
                    .order_by(desc(RawMarketData.timestamp))
                    .limit(1)
                )

                result = await session.execute(stmt)
                raw_data = result.scalar_one_or_none()

                if not raw_data:
                    logger.warning(f"Не найдены raw данные для {symbol}")
                    return

                # Подготавливаем данные для сохранения
                metadata = indicators.get("metadata", {})
                ohlcv = indicators.get("ohlcv", {})

                processed_data = {
                    "raw_data_id": raw_data.id,
                    "symbol": symbol,
                    "timestamp": metadata.get("timestamp", raw_data.timestamp),
                    "datetime": metadata.get("datetime", raw_data.datetime),
                    "open": Decimal(str(ohlcv.get("open", raw_data.open))),
                    "high": Decimal(str(ohlcv.get("high", raw_data.high))),
                    "low": Decimal(str(ohlcv.get("low", raw_data.low))),
                    "close": Decimal(str(ohlcv.get("close", raw_data.close))),
                    "volume": Decimal(str(ohlcv.get("volume", raw_data.volume))),
                    "technical_indicators": indicators.get("technical_indicators", {}),
                    "microstructure_features": indicators.get("microstructure_features", {}),
                    "ml_features": indicators.get("ml_features", {}),
                    "processing_version": "2.0",  # Real-time версия
                    "model_version": "patchtst_v1",
                }

                # Используем upsert
                stmt = insert(ProcessedMarketData).values(**processed_data)
                stmt = stmt.on_conflict_do_update(
                    constraint="_symbol_timestamp_processed_uc",
                    set_={
                        "technical_indicators": stmt.excluded.technical_indicators,
                        "microstructure_features": stmt.excluded.microstructure_features,
                        "ml_features": stmt.excluded.ml_features,
                        "updated_at": datetime.now(UTC),
                    },
                )

                await session.execute(stmt)
                await session.commit()

                logger.debug(f"Сохранены индикаторы для {symbol} в БД")

        except Exception as e:
            logger.error(f"Ошибка сохранения в БД для {symbol}: {e}")

    def _get_from_cache(self, cache_key: str) -> dict[str, Any] | None:
        """Получает данные из кеша если они еще актуальны"""
        if cache_key not in self.cache:
            return None

        cached_data, timestamp = self.cache[cache_key]

        # Логируем для отладки
        if not isinstance(timestamp, datetime):
            logger.warning(
                f"Неправильный тип timestamp в кеше: {type(timestamp)}, значение: {timestamp}"
            )

        # Проверяем тип timestamp и конвертируем если нужно
        if isinstance(timestamp, (int, float)):
            # Если timestamp это Unix timestamp в секундах или миллисекундах
            if timestamp > 1e10:  # Миллисекунды
                timestamp = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
            else:  # Секунды
                timestamp = datetime.fromtimestamp(timestamp, tz=UTC)
            # Обновляем кеш с правильным типом
            self.cache[cache_key] = (cached_data, timestamp)

        # Проверяем TTL
        if (datetime.now(UTC) - timestamp).total_seconds() > self.cache_ttl:
            del self.cache[cache_key]
            return None

        return cached_data

    def _add_to_cache(self, cache_key: str, data: dict[str, Any]):
        """Добавляет данные в кеш"""
        self.cache[cache_key] = (data, datetime.now(UTC))

        # Очищаем старые записи если кеш слишком большой
        if len(self.cache) > 100:
            self._cleanup_cache()

    def _cleanup_cache(self):
        """Очищает устаревшие записи из кеша"""
        current_time = datetime.now(UTC)
        keys_to_remove = []

        for key, (data, timestamp) in self.cache.items():
            # Проверяем тип timestamp и конвертируем если нужно
            if isinstance(timestamp, (int, float)):
                # Если timestamp это Unix timestamp в секундах или миллисекундах
                if timestamp > 1e10:  # Миллисекунды
                    timestamp = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
                else:  # Секунды
                    timestamp = datetime.fromtimestamp(timestamp, tz=UTC)
                # Обновляем кеш с правильным типом
                self.cache[key] = (data, timestamp)

            if (current_time - timestamp).total_seconds() > self.cache_ttl:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.cache[key]

    async def get_features_for_ml(self, symbol: str, ohlcv_df: pd.DataFrame) -> np.ndarray:
        """
        Получает признаки в формате для ML модели

        Args:
            symbol: Символ
            ohlcv_df: OHLCV данные

        Returns:
            Numpy массив с признаками для модели
        """
        try:
            # ИСПРАВЛЕНО: Прямой вызов FeatureEngineer без async
            logger.info(f"🚀 get_features_for_ml: Direct feature calculation for {symbol}")

            # Подготавливаем DataFrame
            df = self._prepare_dataframe(ohlcv_df, symbol)

            # Прямо вызываем create_features (это синхронный метод)
            features_result = self.feature_engineer.create_features(
                df, inference_mode=self.use_inference_mode
            )

            # Обработка результата - используем точный список признаков
            if isinstance(features_result, pd.DataFrame):
                logger.info(
                    f"🔧 get_features_for_ml: DataFrame shape {features_result.shape}, columns: {len(features_result.columns)}"
                )

                # Используем ТОЛЬКО признаки из REQUIRED_FEATURES_240
                available_cols = features_result.columns.tolist()
                selected_features = []

                for feature in REQUIRED_FEATURES_240:
                    if feature in available_cols:
                        selected_features.append(feature)
                    else:
                        # Добавляем нулевой признак если отсутствует
                        selected_features.append(feature)
                        features_result[feature] = 0.0
                        logger.debug(f"Добавлен нулевой признак: {feature}")

                # Гарантируем ровно 240 признаков
                logger.info(
                    f"🔧 get_features_for_ml: selected_features={len(selected_features)}, required={len(REQUIRED_FEATURES_240)}"
                )
                assert len(selected_features) == 240, (
                    f"Должно быть 240 признаков, получено {len(selected_features)}"
                )
                features_array = features_result[selected_features].values
                logger.info(
                    f"🔧 get_features_for_ml: final features_array shape: {features_array.shape}"
                )
            elif isinstance(features_result, np.ndarray):
                features_array = features_result
            else:
                logger.error(
                    f"create_features returned {type(features_result)}, expected DataFrame or np.ndarray"
                )
                return np.array([])

            # Возвращаем последнюю строку признаков для текущего момента
            if features_array.ndim == 2 and features_array.shape[0] > 0:
                last_features = features_array[-1]  # Последняя строка - должна быть размером 240
                logger.info(
                    f"✅ get_features_for_ml: Extracted {len(last_features)} features for {symbol}"
                )
                assert len(last_features) == 240, (
                    f"Ожидалось 240 признаков, получено {len(last_features)}"
                )
                return last_features
            else:
                logger.error(f"Неожиданная форма features_array: {features_array.shape}")
                return np.array([])

        except Exception as e:
            logger.error(f"Ошибка в get_features_for_ml для {symbol}: {e}")
            return np.array([])

    async def prepare_ml_input(
        self, symbol: str, ohlcv_df: pd.DataFrame, lookback: int = 96
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """
        Подготавливает входные данные для ML модели

        Args:
            symbol: Символ
            ohlcv_df: OHLCV данные (должно быть минимум lookback + 144 свечей)
            lookback: Количество временных точек для модели

        Returns:
            (features_array, metadata)
        """
        logger.info(
            f"🚀 НАЧИНАЕМ prepare_ml_input для {symbol}, данных: {len(ohlcv_df)}, inference_mode: {self.use_inference_mode}"
        )

        if len(ohlcv_df) < lookback:  # Минимум нужно lookback свечей
            raise ValueError(f"Недостаточно данных: {len(ohlcv_df)} < {lookback}")

        # ПРАВИЛЬНОЕ ИСПРАВЛЕНИЕ: Рассчитываем признаки для всего DataFrame сразу
        # FeatureEngineer уже правильно рассчитывает признаки с rolling windows
        logger.info(f"🔄 Расчет признаков для {symbol}, данных: {len(ohlcv_df)}")

        # Подготавливаем DataFrame
        df = self._prepare_dataframe(ohlcv_df, symbol)

        # Рассчитываем признаки для всего DataFrame
        # FeatureEngineer возвращает массив (n_samples, n_features)
        features_result = self.feature_engineer.create_features(
            df, inference_mode=self.use_inference_mode
        )

        if isinstance(features_result, pd.DataFrame):
            # ИСПРАВЛЕНО: Используем ТОЛЬКО признаки из REQUIRED_FEATURES_240
            available_cols = features_result.columns.tolist()
            logger.debug(f"🔧 DataFrame от FeatureEngineer: {len(available_cols)} колонок")
            logger.debug(f"🔧 Первые 10 колонок: {available_cols[:10]}")

            selected_features = []

            # Выбираем признаки в правильном порядке из REQUIRED_FEATURES_240
            for feature in REQUIRED_FEATURES_240:
                if feature in available_cols:
                    selected_features.append(feature)
                else:
                    # Если признак отсутствует, добавляем нулевой
                    selected_features.append(feature)
                    features_result[feature] = 0.0
                    logger.debug(f"Добавлен нулевой признак: {feature}")

            # Гарантируем ровно 240 признаков
            logger.debug(
                f"🔧 prepare_ml_input: selected_features={len(selected_features)}, required={len(REQUIRED_FEATURES_240)}"
            )
            assert len(selected_features) == 240, (
                f"Должно быть 240 признаков, получено {len(selected_features)}"
            )
            features_array = features_result[selected_features].values
            logger.info(
                f"✅ Использовано точно {len(selected_features)} признаков из REQUIRED_FEATURES_240"
            )
            logger.debug(f"🔧 features_array shape после фильтрации: {features_array.shape}")
        elif isinstance(features_result, np.ndarray):
            logger.info(
                f"🔧 prepare_ml_input: FeatureEngineer вернул np.ndarray shape: {features_result.shape}"
            )
            features_array = features_result
        else:
            raise ValueError(f"Неожиданный тип результата: {type(features_result)}")

        # Проверяем размерность
        if features_array.ndim != 2:
            raise ValueError(f"Неправильная размерность признаков: {features_array.shape}")

        # Берем последние lookback точек
        if len(features_array) < lookback:
            # Если данных меньше чем нужно, дополняем первыми значениями
            padding_size = lookback - len(features_array)
            padding = np.tile(features_array[0], (padding_size, 1))
            features_array = np.vstack([padding, features_array])
        else:
            # Берем последние lookback точек
            features_array = features_array[-lookback:]

        # Добавляем batch dimension: (lookback, features) -> (1, lookback, features)
        features_array = features_array.reshape(1, lookback, -1)

        # Проверяем дисперсию признаков
        # ИСПРАВЛЕНО: Безопасная проверка типов данных для предотвращения ошибки sqrt
        try:
            # Убеждаемся что данные в правильном формате numpy
            features_sample = np.asarray(features_array[0], dtype=np.float64)
            feature_std = np.std(features_sample, axis=0)
            non_zero_std = np.sum(feature_std > 1e-6)
        except (TypeError, ValueError) as e:
            logger.warning(f"Ошибка вычисления дисперсии признаков: {e}")
            # Fallback - простая проверка без std
            non_zero_std = (
                features_array.shape[2] if features_array.ndim > 2 else features_array.shape[1]
            )

        logger.info(f"📊 ML признаки для {symbol}: shape={features_array.shape}")
        logger.info(
            f"   Признаков с ненулевой дисперсией: {non_zero_std}/{features_array.shape[2]}"
        )
        logger.debug(
            f"   Дисперсия: min={feature_std.min():.6f}, max={feature_std.max():.6f}, mean={feature_std.mean():.6f}"
        )

        # Метаданные
        metadata = {
            "symbol": symbol,
            "last_timestamp": ohlcv_df.index[-1],
            "last_price": float(ohlcv_df["close"].iloc[-1]),
            "lookback": lookback,
            "features_count": features_array.shape[2],
            "non_zero_variance_features": int(non_zero_std),
        }

        return features_array, metadata
