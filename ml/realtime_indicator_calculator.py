#!/usr/bin/env python3
"""
Real-time расчет технических индикаторов для ML модели
Адаптировано для генерации сигналов в реальном времени
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from core.logger import setup_logger
from database.db_manager import get_db
from ml.logic.feature_engineering_production import ProductionFeatureEngineer as FeatureEngineer
from production_features_config import REAL_FEATURES_240 as REQUIRED_FEATURES_240

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
            use_inference_mode: Использовать ли inference mode для генерации только 231 признаков
        """
        # Передаем inference_mode в конфигурацию FeatureEngineer
        # ProductionFeatureEngineer работает без конфигурации
        # Передаем пустую конфигурацию, код адаптирован под это
        engineer_config = {}

        self.feature_engineer = FeatureEngineer(engineer_config)
        # Отключаем прогресс-бар чтобы не блокировать async операции
        self.feature_engineer.disable_progress = False  # Включаем логи для отладки
        self.cache = {}  # Кеш рассчитанных индикаторов
        self.cache_ttl = cache_ttl
        self._lock = asyncio.Lock()
        self.use_inference_mode = use_inference_mode
        # Ограничение конкуренции при сохранении в БД
        self._db_semaphore = asyncio.Semaphore(4)

        logger.info(
            f"RealTimeIndicatorCalculator инициализирован (inference_mode={use_inference_mode})"
        )

    async def calculate_indicators(
        self, symbol: str, ohlcv_df: pd.DataFrame, save_to_db: bool = True, use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Рассчитывает все индикаторы для символа в реальном времени

        Args:
            symbol: Торговый символ
            ohlcv_df: DataFrame с OHLCV данными (должен содержать минимум 150 свечей)
            save_to_db: Сохранять ли результаты в БД
            use_cache: Использовать ли кеш (отключаем для последнего таймфрейма)

        Returns:
            Словарь с рассчитанными индикаторами и признаками
        """
        try:
            logger.info(f"🔍 Starting calculate_indicators for {symbol}")
            # Проверяем кеш только если разрешено
            cache_key = f"{symbol}_{ohlcv_df.index[-1]}"
            if use_cache:
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
            logger.info(f"About to call create_features for {symbol}")
            # ProductionFeatureEngineer не принимает inference_mode
            # Отключаем enhanced_features - модуль не существует
            features_result = self.feature_engineer.create_features(df, use_enhanced_features=False)
            logger.info(
                f"create_features returned type: {type(features_result)}, shape: {getattr(features_result, 'shape', 'no shape')}"
            )

            # Используем точный список признаков из конфигурации
            if isinstance(features_result, pd.DataFrame):
                # Используем ТОЛЬКО признаки из REQUIRED_FEATURES_231
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

                # ИСПРАВЛЕНО: Фильтруем только числовые колонки перед созданием массива
                numeric_features = []
                for feature in selected_features[:240]:
                    if feature in features_result.columns:
                        # Проверяем что колонка содержит числовые данные
                        if pd.api.types.is_numeric_dtype(features_result[feature]):
                            numeric_features.append(feature)
                        else:
                            logger.debug(f"Пропускаем не-числовую колонку: {feature}")
                            # Заменяем на заглушку
                            features_result[f"{feature}_numeric"] = 0.0
                            numeric_features.append(f"{feature}_numeric")
                    else:
                        # Если колонки нет, создаем заглушку
                        features_result[f"{feature}_missing"] = 0.0
                        numeric_features.append(f"{feature}_missing")

                features_array = features_result[numeric_features].values
                feature_names = numeric_features
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
            
            # Добавляем все признаки для совместимости
            result["features"] = current_features

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

            # Кешируем результат только если разрешено
            if use_cache:
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

        # Сортируем по времени по колонке 'datetime' если доступна; иначе по индексу
        if "datetime" in df.columns:
            df = df.sort_values("datetime")
        else:
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
        # ИСПРАВЛЕНО: Фильтруем только числовые признаки
        ml_features = {
            k: v
            for k, v in features.items()
            if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, str)
        }

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
            # Используем простой execute вместо transaction для более стабильной работы
            db = await get_db()

            # Получаем последнюю запись из raw_market_data - используем упрощенный подход
            query = """
                SELECT id, timestamp, datetime, open, high, low, close, volume
                FROM raw_market_data
                WHERE symbol = $1
                ORDER BY timestamp DESC
                LIMIT 1
            """
            raw_data_row = (
                await db.fetch_one(query, symbol)
                if hasattr(db, "fetch_one")
                else await db.pool.fetchrow(query, symbol)
            )

            if not raw_data_row:
                logger.warning(f"Не найдены raw данные для {symbol}")
                return

            # Подготавливаем данные для сохранения
            metadata = indicators.get("metadata", {})
            ohlcv = indicators.get("ohlcv", {})

            # Используем простой INSERT или UPDATE вместо upsert для надежности
            insert_query = """
                INSERT INTO processed_market_data (
                    raw_data_id, symbol, timestamp, datetime,
                    open, high, low, close, volume,
                    technical_indicators, microstructure_features, ml_features,
                    processing_version, model_version, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (symbol, timestamp)
                DO UPDATE SET
                    technical_indicators = EXCLUDED.technical_indicators,
                    microstructure_features = EXCLUDED.microstructure_features,
                    ml_features = EXCLUDED.ml_features,
                    updated_at = EXCLUDED.updated_at
            """

            import json

            now = datetime.now(UTC)

            # Используем pool напрямую для выполнения запроса, ограничивая конкуренцию
            async with self._db_semaphore:
                async with db.pool.acquire() as conn:
                    await conn.execute(
                        insert_query,
                        raw_data_row["id"],
                        symbol,
                        metadata.get("timestamp", raw_data_row["timestamp"]),
                        metadata.get("datetime", raw_data_row["datetime"]),
                        (
                            float(ohlcv.get("open", raw_data_row["open"]))
                            if ohlcv.get("open") is not None
                            else float(raw_data_row["open"])
                        ),
                        (
                            float(ohlcv.get("high", raw_data_row["high"]))
                            if ohlcv.get("high") is not None
                            else float(raw_data_row["high"])
                        ),
                        (
                            float(ohlcv.get("low", raw_data_row["low"]))
                            if ohlcv.get("low") is not None
                            else float(raw_data_row["low"])
                        ),
                        (
                            float(ohlcv.get("close", raw_data_row["close"]))
                            if ohlcv.get("close") is not None
                            else float(raw_data_row["close"])
                        ),
                        (
                            float(ohlcv.get("volume", raw_data_row["volume"]))
                            if ohlcv.get("volume") is not None
                            else float(raw_data_row["volume"])
                        ),
                        json.dumps(indicators.get("technical_indicators", {})),
                        json.dumps(indicators.get("microstructure_features", {})),
                        json.dumps(indicators.get("ml_features", {})),
                        "2.0",  # processing_version
                        "patchtst_v1",  # model_version
                        now,
                        now,
                    )

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
            # Отключаем enhanced_features - модуль не существует
            features_result = self.feature_engineer.create_features(df, use_enhanced_features=False)

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
        # ProductionFeatureEngineer не принимает inference_mode
        # Отключаем enhanced_features - модуль не существует
        features_result = self.feature_engineer.create_features(df, use_enhanced_features=False)

        if isinstance(features_result, pd.DataFrame):
            # ИСПРАВЛЕНО: Жестко формируем 240 признаков строго в порядке обучения
            available_cols = features_result.columns.tolist()
            logger.info(f"🔧 DataFrame от FeatureEngineer: {len(available_cols)} колонок")

            # Служебные и временные колонки, которые НЕЛЬЗЯ включать в признаки
            # ВНИМАНИЕ: базовые OHLCV НЕ считаем служебными — если они есть в списке обучения,
            # их нужно включать как есть. Исключаем только явные служебные/временные.
            service_cols = {
                "datetime",
                "symbol",
                "id",
                "sector",
                "timestamp",
                "ts",
                "ts_ms",
                "time",
                "date",
                "index",
            }

            # Целевые и вспомогательные паттерны, которые исключаем
            target_patterns = ("direction_", "future_return_", "target_tp_", "target_sl_")

            selected_features: list[str] = []
            for feature in REQUIRED_FEATURES_240:
                if feature in service_cols or any(tp in feature for tp in target_patterns):
                    # Если список обучения по ошибке содержит служебную/целевую колонку — заменим заглушкой
                    feat_name = f"{feature}_numeric"
                    if feat_name not in features_result:
                        features_result[feat_name] = 0.0
                    selected_features.append(feat_name)
                    continue

                if feature in features_result.columns:
                    # Если колонка существует, но не числовая — создаем числовую заглушку
                    if not pd.api.types.is_numeric_dtype(features_result[feature]):
                        num_name = f"{feature}_numeric"
                        if num_name not in features_result:
                            features_result[num_name] = 0.0
                        selected_features.append(num_name)
                    else:
                        selected_features.append(feature)
                else:
                    # Отсутствует — создаем заглушку
                    miss_name = f"{feature}_missing"
                    if miss_name not in features_result:
                        features_result[miss_name] = 0.0
                    selected_features.append(miss_name)

            # Гарантируем ровно 240 признаков
            if len(selected_features) > 240:
                selected_features = selected_features[:240]
            elif len(selected_features) < 240:
                # Дополняем padding-колонками
                pad_needed = 240 - len(selected_features)
                for i in range(pad_needed):
                    pad_col = f"padding_{i}"
                    if pad_col not in features_result:
                        features_result[pad_col] = 0.0
                    selected_features.append(pad_col)

            features_array = features_result[selected_features].values
            logger.info("✅ Использовано 240 признаков для ML модели")
            logger.info(f"🔧 features_array shape: {features_array.shape}")
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
            # Убеждаемся что данные в правильном формате numpy - только числовые данные
            features_sample = features_array[0]
            if features_sample.dtype.kind not in ["i", "u", "f"]:  # integer, unsigned, float
                logger.debug("Массив содержит не-числовые данные, пропускаем проверку дисперсии")
                non_zero_std = (
                    features_array.shape[2] if features_array.ndim > 2 else features_array.shape[1]
                )
                feature_std = None
            else:
                feature_std = np.std(features_sample, axis=0)
                non_zero_std = np.sum(feature_std > 1e-6)
                logger.debug(
                    f"🔧 Расчет дисперсии для {symbol}: feature_std shape={feature_std.shape}, non_zero={non_zero_std}"
                )
        except (TypeError, ValueError) as e:
            logger.warning(f"Ошибка вычисления дисперсии признаков: {e}")
            # Fallback - простая проверка без std
            non_zero_std = (
                features_array.shape[2] if features_array.ndim > 2 else features_array.shape[1]
            )
            feature_std = None

        logger.info(f"📊 ML признаки для {symbol}: shape={features_array.shape}")
        logger.info(
            f"   Признаков с ненулевой дисперсией: {non_zero_std}/{features_array.shape[2]}"
        )

        # Детальное логирование zero variance признаков
        if feature_std is not None:
            zero_variance_mask = feature_std <= 1e-6
            zero_count = np.sum(zero_variance_mask)

            if zero_count > 0:
                logger.warning(
                    f"🔴 Найдено {zero_count} признаков с нулевой дисперсией для {symbol}:"
                )
                zero_indices = np.where(zero_variance_mask)[0]

                # Показываем первые 10 проблемных признаков
                for i, idx in enumerate(zero_indices[:10]):
                    feature_name = (
                        REQUIRED_FEATURES_240[idx]
                        if idx < len(REQUIRED_FEATURES_240)
                        else f"feature_{idx}"
                    )
                    logger.warning(f"   [{idx:3d}] {feature_name}: std={feature_std[idx]:.8f}")

                if len(zero_indices) > 10:
                    logger.warning(f"   ... и еще {len(zero_indices) - 10} признаков")

            logger.debug(
                f"   Дисперсия: min={feature_std.min():.6f}, max={feature_std.max():.6f}, mean={feature_std.mean():.6f}"
            )
        else:
            logger.debug("   Дисперсия: не вычислена (не-числовые данные)")

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
