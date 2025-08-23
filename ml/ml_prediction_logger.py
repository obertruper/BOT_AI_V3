"""
ML Prediction Logger - детальное логирование и сохранение предсказаний в БД
"""

import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from core.logger import setup_logger
from database.db_manager import get_db
from database.repositories.ml_prediction_repository import MLPrediction

logger = setup_logger("ml_prediction_logger")


class MLPredictionLogger:
    """
    Класс для детального логирования ML предсказаний и сохранения в БД
    """

    def __init__(self):
        """Инициализация логгера предсказаний"""
        self.model_version = "unified_patchtst_v1.0"
        self.batch_predictions = []
        self.batch_size = 1  # Сохраняем сразу же для реального времени
        self._db_manager = None

    async def _get_db_manager(self):
        """Получает менеджер БД (ленивая инициализация)"""
        if self._db_manager is None:
            self._db_manager = await get_db()
        return self._db_manager

    async def log_prediction(
        self,
        symbol: str,
        features: np.ndarray,
        model_outputs: np.ndarray,
        predictions: dict[str, Any],
        market_data: pd.DataFrame | None = None,
    ) -> None:
        """
        Детальное логирование одного предсказания

        Args:
            symbol: Торговый символ
            features: Массив признаков (240 features)
            model_outputs: Сырые выходы модели (20 values)
            predictions: Интерпретированные предсказания
            market_data: Исходные рыночные данные
        """
        start_time = time.time()

        # Вычисляем хэш признаков для дедупликации
        features_hash = self._compute_features_hash(features)

        # Извлекаем ключевые признаки для анализа
        key_features = self._extract_key_features(features, market_data)

        # Вычисляем статистику признаков
        feature_stats = self._compute_feature_statistics(features)

        # Создаём объект MLPrediction
        prediction_record = MLPrediction(
            symbol=symbol,
            timestamp=int(time.time() * 1000),
            predicted_at=datetime.now(UTC),
            # Input features summary
            features_count=len(features),
            features_hash=features_hash,
            lookback_periods=96,  # Стандартное значение
            # Key features
            **key_features,
            # Feature statistics  
            **feature_stats,
            # Model outputs - raw predictions
            predicted_return_15m=float(predictions.get("returns_15m", 0)),
            predicted_return_1h=float(predictions.get("returns_1h", 0)),
            predicted_return_4h=float(predictions.get("returns_4h", 0)),
            predicted_return_12h=float(predictions.get("returns_12h", 0)),
            # Direction predictions
            direction_15m=predictions["direction_15m"],
            direction_15m_confidence=float(predictions["confidence_15m"]),
            direction_1h=predictions["direction_1h"],
            direction_1h_confidence=float(predictions["confidence_1h"]),
            direction_4h=predictions["direction_4h"],
            direction_4h_confidence=float(predictions["confidence_4h"]),
            direction_12h=predictions["direction_12h"],
            direction_12h_confidence=float(predictions["confidence_12h"]),
            # Risk metrics
            risk_score=float(predictions.get("risk_score", 0)),
            max_drawdown_predicted=float(predictions.get("max_drawdown", 0)),
            max_rally_predicted=float(predictions.get("max_rally", 0)),
            # Final signal
            signal_type=predictions["signal_type"],
            signal_confidence=float(predictions["signal_confidence"]),
            signal_timeframe=predictions.get("primary_timeframe", "15m"),
            # Model metadata
            model_version=self.model_version,
            inference_time_ms=(time.time() - start_time) * 1000,
            # Full arrays for detailed analysis
            features_array=features.tolist() if features.size < 1000 else None,
            model_outputs_raw=model_outputs.tolist() if model_outputs is not None else None,
        )

        # Детальное логирование
        self._log_prediction_details(symbol, prediction_record, predictions)

        # Добавляем в батч для сохранения
        self.batch_predictions.append(prediction_record)

        # Сохраняем в БД если набрался батч
        if len(self.batch_predictions) >= self.batch_size:
            await self._save_batch_to_db()

    def _compute_features_hash(self, features: np.ndarray) -> int:
        """Вычисляет хэш массива признаков для дедупликации"""
        # Конвертируем в bytes и вычисляем хэш
        features_bytes = features.astype(np.float32).tobytes()
        hash_obj = hashlib.md5(features_bytes)
        # Берем первые 8 байт хэша и ограничиваем до int64 range
        # PostgreSQL int64 range: -9223372036854775808 to 9223372036854775807
        hash_int = int(
            hash_obj.hexdigest()[:15], 16
        )  # 15 hex chars = ~56 bits, safely within int64
        return hash_int

    def _extract_key_features(
        self, features: np.ndarray, market_data: pd.DataFrame | None
    ) -> dict[str, float]:
        """Извлекает ключевые признаки для анализа"""
        key_features = {}

        # Предполагаемые индексы ключевых признаков
        # (нужно синхронизировать с feature_engineering_v2.py)
        feature_indices = {
            "rsi": 14,  # Примерный индекс
            "macd": 20,
            "bb_position": 30,
            "atr_pct": 40,
            "volume_ratio": 7,
            "trend_strength": 50,
        }

        # Извлекаем по индексам если возможно
        for name, idx in feature_indices.items():
            if idx < len(features):
                key_features[name] = float(features[idx])
            else:
                key_features[name] = None

        # Если есть market_data, берем текущие цену и объем
        if market_data is not None and not market_data.empty:
            last_row = market_data.iloc[-1]
            key_features["close_price"] = float(last_row.get("close", 0))
            key_features["volume"] = float(last_row.get("volume", 0))
            # DEBUG: логируем что получили из market_data
            logger.debug(
                f"DEBUG market_data last row: close={last_row.get('close')}, volume={last_row.get('volume')}"
            )
        else:
            key_features["close_price"] = 0
            key_features["volume"] = 0
            logger.debug("DEBUG: market_data is None or empty")

        return key_features

    def _compute_feature_statistics(self, features: np.ndarray) -> dict[str, float]:
        """Вычисляет статистику по признакам"""
        # Фильтруем только валидные числа
        valid_features = features[~np.isnan(features)]

        stats = {
            "features_mean": float(np.mean(valid_features)) if len(valid_features) > 0 else 0,
            "features_std": float(np.std(valid_features)) if len(valid_features) > 0 else 0,
            "features_min": float(np.min(valid_features)) if len(valid_features) > 0 else 0,
            "features_max": float(np.max(valid_features)) if len(valid_features) > 0 else 0,
            "zero_variance_count": int(np.sum(np.var(features.reshape(-1, 1), axis=0) < 1e-10)),
            "nan_count": int(np.sum(np.isnan(features))),
        }

        return stats

    def _log_prediction_details(
        self, symbol: str, record: MLPrediction, predictions: dict[str, Any]
    ) -> None:
        """Выводит детальные логи предсказания"""

        # DEBUG: Проверяем, что реально передается
        logger.debug(
            f"DEBUG predictions content: returns_15m={predictions.get('returns_15m')}, "
            f"returns_1h={predictions.get('returns_1h')}, "
            f"returns_4h={predictions.get('returns_4h')}, "
            f"returns_12h={predictions.get('returns_12h')}"
        )

        # Собираем всю таблицу в одну строку, чтобы она выводилась целиком
        table_lines = []
        table_lines.append(
            "╔══════════════════════════════════════════════════════════════════════╗"
        )
        table_lines.append(
            f"║                    ML PREDICTION DETAILS - {symbol:^10}              ║"
        )
        table_lines.append(
            "╠══════════════════════════════════════════════════════════════════════╣"
        )
        table_lines.append(
            "║ 📊 INPUT FEATURES                                                     ║"
        )
        table_lines.append(
            f"║   • Feature Count: {record.features_count:<6} • Hash: {record.features_hash:016x}     ║"
        )
        table_lines.append(
            f"║   • NaN Count: {record.nan_count:<6} • Zero Variance: {record.zero_variance_count:<6}        ║"
        )
        table_lines.append(
            f"║   • Mean: {record.features_mean:>8.4f}  • Std: {record.features_std:>8.4f}            ║"
        )
        table_lines.append(
            f"║   • Min:  {record.features_min:>8.4f}  • Max: {record.features_max:>8.4f}            ║"
        )
        table_lines.append(
            "╟──────────────────────────────────────────────────────────────────────╢"
        )
        table_lines.append(
            "║ 🎯 KEY INDICATORS                                                     ║"
        )
        table_lines.append(
            f"║   • Close: ${getattr(record, 'close_price', 0):>10.2f}  • Volume: {getattr(record, 'volume', 0):>12.0f}  ║"
        )
        table_lines.append(
            f"║   • RSI: {getattr(record, 'rsi', 0):>6.2f}  • MACD: {getattr(record, 'macd', 0):>8.4f}                  ║"
        )
        table_lines.append(
            f"║   • BB Position: {getattr(record, 'bb_position', 0):>6.3f}  • ATR%: {getattr(record, 'atr_pct', 0):>6.3f}   ║"
        )
        table_lines.append(
            "╟──────────────────────────────────────────────────────────────────────╢"
        )
        table_lines.append(
            "║ 📈 PREDICTED RETURNS                                                  ║"
        )
        table_lines.append(
            f"║   • 15m: {record.predicted_return_15m:>7.4f} ({record.direction_15m:^7}) [{record.direction_15m_confidence:>5.2%}]  ║"
        )
        table_lines.append(
            f"║   • 1h:  {record.predicted_return_1h:>7.4f} ({record.direction_1h:^7}) [{record.direction_1h_confidence:>5.2%}]   ║"
        )
        table_lines.append(
            f"║   • 4h:  {record.predicted_return_4h:>7.4f} ({record.direction_4h:^7}) [{record.direction_4h_confidence:>5.2%}]   ║"
        )
        table_lines.append(
            f"║   • 12h: {record.predicted_return_12h:>7.4f} ({record.direction_12h:^7}) [{record.direction_12h_confidence:>5.2%}] ║"
        )
        table_lines.append(
            "╟──────────────────────────────────────────────────────────────────────╢"
        )
        table_lines.append(
            "║ ⚠️  RISK METRICS                                                      ║"
        )
        table_lines.append(
            f"║   • Risk Score: {getattr(record, 'risk_score', 0):>6.3f}                                       ║"
        )
        table_lines.append(
            f"║   • Max Drawdown: {getattr(record, 'max_drawdown_predicted', 0):>6.2%}                           ║"
        )
        table_lines.append(
            f"║   • Max Rally: {getattr(record, 'max_rally_predicted', 0):>6.2%}                              ║"
        )
        table_lines.append(
            "╟──────────────────────────────────────────────────────────────────────╢"
        )
        table_lines.append(
            "║ 🎯 FINAL SIGNAL                                                       ║"
        )
        table_lines.append(
            f"║   • Type: {record.signal_type:^10}  • Confidence: {record.signal_confidence:>5.2%}       ║"
        )
        table_lines.append(
            f"║   • Primary Timeframe: {getattr(record, 'signal_timeframe', 'N/A'):^10}                      ║"
        )
        table_lines.append(
            f"║   • Inference Time: {record.inference_time_ms:>6.1f} ms                            ║"
        )
        table_lines.append(
            "╚══════════════════════════════════════════════════════════════════════╝"
        )

        # Выводим всю таблицу одним вызовом logger.info
        logger.info("\n" + "\n".join(table_lines))

        # Логируем дополнительную информацию для отладки
        if predictions.get("debug_info"):
            logger.debug(f"Debug info for {symbol}: {predictions['debug_info']}")

    async def _save_batch_to_db(self) -> None:
        """Сохраняет батч предсказаний в БД"""
        if not self.batch_predictions:
            return

        try:
            # Получаем менеджер БД и репозиторий
            db_manager = await self._get_db_manager()
            ml_repo = db_manager.get_ml_prediction_repository()

            # Используем bulk_insert для высокой производительности
            if len(self.batch_predictions) == 1:
                # Одиночное сохранение
                await ml_repo.create_prediction(self.batch_predictions[0])
            else:
                # Массовое сохранение
                await ml_repo.bulk_insert(self.batch_predictions)

            logger.info(f"✅ Сохранено {len(self.batch_predictions)} предсказаний в БД")

            # Очищаем батч
            self.batch_predictions.clear()

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения предсказаний в БД: {e}")
            # Не очищаем батч при ошибке, попробуем в следующий раз

    async def save_feature_importance(
        self, feature_names: list[str], importance_scores: np.ndarray
    ) -> None:
        """
        Сохраняет важность признаков в БД

        Args:
            feature_names: Названия признаков
            importance_scores: Оценки важности
        """
        try:
            # Получаем менеджер БД и репозиторий
            db_manager = await self._get_db_manager()
            ml_repo = db_manager.get_ml_prediction_repository()

            # Сохраняем через репозиторий
            await ml_repo.save_feature_importance(
                feature_names, importance_scores, self.model_version
            )

            logger.info("✅ Сохранена важность топ-100 признаков в БД")

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения важности признаков: {e}")

    async def flush(self) -> None:
        """Принудительно сохраняет все накопленные предсказания"""
        if self.batch_predictions:
            await self._save_batch_to_db()


# Глобальный экземпляр логгера
ml_prediction_logger = MLPredictionLogger()
