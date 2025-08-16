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
from database.connections.postgres import AsyncPGPool

logger = setup_logger("ml_prediction_logger")


class MLPredictionLogger:
    """
    Класс для детального логирования ML предсказаний и сохранения в БД
    """

    def __init__(self):
        """Инициализация логгера предсказаний"""
        self.model_version = "unified_patchtst_v1.0"
        self.batch_predictions = []
        self.batch_size = 10  # Сохраняем в БД пачками

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

        # Подготавливаем данные для БД
        prediction_record = {
            "symbol": symbol,
            "timestamp": int(time.time() * 1000),
            "datetime": datetime.now(UTC),
            # Input features summary
            "features_count": len(features),
            "features_hash": features_hash,
            "lookback_periods": 96,  # Стандартное значение
            # Key features
            **key_features,
            # Feature statistics
            **feature_stats,
            # Model outputs - raw predictions
            "predicted_return_15m": float(predictions["returns_15m"]),
            "predicted_return_1h": float(predictions["returns_1h"]),
            "predicted_return_4h": float(predictions["returns_4h"]),
            "predicted_return_12h": float(predictions["returns_12h"]),
            # Direction predictions
            "direction_15m": predictions["direction_15m"],
            "direction_15m_confidence": float(predictions["confidence_15m"]),
            "direction_1h": predictions["direction_1h"],
            "direction_1h_confidence": float(predictions["confidence_1h"]),
            "direction_4h": predictions["direction_4h"],
            "direction_4h_confidence": float(predictions["confidence_4h"]),
            "direction_12h": predictions["direction_12h"],
            "direction_12h_confidence": float(predictions["confidence_12h"]),
            # Risk metrics
            "risk_score": float(predictions.get("risk_score", 0)),
            "max_drawdown_predicted": float(predictions.get("max_drawdown", 0)),
            "max_rally_predicted": float(predictions.get("max_rally", 0)),
            # Final signal
            "signal_type": predictions["signal_type"],
            "signal_confidence": float(predictions["signal_confidence"]),
            "signal_timeframe": predictions.get("primary_timeframe", "15m"),
            # Model metadata
            "model_version": self.model_version,
            "inference_time_ms": (time.time() - start_time) * 1000,
            # Full arrays for detailed analysis
            "features_array": features.tolist() if features.size < 1000 else None,
            "model_outputs_raw": model_outputs.tolist() if model_outputs is not None else None,
        }

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
        else:
            key_features["close_price"] = 0
            key_features["volume"] = 0

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
        self, symbol: str, record: dict[str, Any], predictions: dict[str, Any]
    ) -> None:
        """Выводит детальные логи предсказания"""

        logger.info(
            f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    ML PREDICTION DETAILS - {symbol:^10}              ║
╠══════════════════════════════════════════════════════════════════════╣
║ 📊 INPUT FEATURES                                                     ║
║   • Feature Count: {record["features_count"]:<6} • Hash: {record["features_hash"]:016x}     ║
║   • NaN Count: {record["nan_count"]:<6} • Zero Variance: {record["zero_variance_count"]:<6}        ║
║   • Mean: {record["features_mean"]:>8.4f}  • Std: {record["features_std"]:>8.4f}            ║
║   • Min:  {record["features_min"]:>8.4f}  • Max: {record["features_max"]:>8.4f}            ║
╟──────────────────────────────────────────────────────────────────────╢
║ 🎯 KEY INDICATORS                                                     ║
║   • Close: ${record.get("close_price", 0):>10.2f}  • Volume: {record.get("volume", 0):>12.0f}  ║
║   • RSI: {record.get("rsi", 0):>6.2f}  • MACD: {record.get("macd", 0):>8.4f}                  ║
║   • BB Position: {record.get("bb_position", 0):>6.3f}  • ATR%: {record.get("atr_pct", 0):>6.3f}   ║
╟──────────────────────────────────────────────────────────────────────╢
║ 📈 PREDICTED RETURNS                                                  ║
║   • 15m: {record["predicted_return_15m"]:>7.4f} ({record["direction_15m"]:^7}) [{record["direction_15m_confidence"]:>5.2%}]  ║
║   • 1h:  {record["predicted_return_1h"]:>7.4f} ({record["direction_1h"]:^7}) [{record["direction_1h_confidence"]:>5.2%}]   ║
║   • 4h:  {record["predicted_return_4h"]:>7.4f} ({record["direction_4h"]:^7}) [{record["direction_4h_confidence"]:>5.2%}]   ║
║   • 12h: {record["predicted_return_12h"]:>7.4f} ({record["direction_12h"]:^7}) [{record["direction_12h_confidence"]:>5.2%}] ║
╟──────────────────────────────────────────────────────────────────────╢
║ ⚠️  RISK METRICS                                                      ║
║   • Risk Score: {record.get("risk_score", 0):>6.3f}                                       ║
║   • Max Drawdown: {record.get("max_drawdown_predicted", 0):>6.2%}                           ║
║   • Max Rally: {record.get("max_rally_predicted", 0):>6.2%}                              ║
╟──────────────────────────────────────────────────────────────────────╢
║ 🎯 FINAL SIGNAL                                                       ║
║   • Type: {record["signal_type"]:^10}  • Confidence: {record["signal_confidence"]:>5.2%}       ║
║   • Primary Timeframe: {record.get("signal_timeframe", "N/A"):^10}                      ║
║   • Inference Time: {record["inference_time_ms"]:>6.1f} ms                            ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        )

        # Логируем дополнительную информацию для отладки
        if predictions.get("debug_info"):
            logger.debug(f"Debug info for {symbol}: {predictions['debug_info']}")

    async def _save_batch_to_db(self) -> None:
        """Сохраняет батч предсказаний в БД"""
        if not self.batch_predictions:
            return

        try:
            # Подготавливаем SQL запрос для batch insert
            columns = list(self.batch_predictions[0].keys())
            placeholders = ", ".join([f"${i + 1}" for i in range(len(columns))])

            # Формируем запрос
            insert_query = f"""
                INSERT INTO ml_predictions ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT (symbol, timestamp) DO UPDATE SET
                    signal_confidence = EXCLUDED.signal_confidence,
                    updated_at = NOW()
            """

            # Выполняем batch insert
            for record in self.batch_predictions:
                values = [record[col] for col in columns]
                # Конвертируем None в NULL для PostgreSQL
                values = [json.dumps(v) if isinstance(v, (list, dict)) else v for v in values]

                await AsyncPGPool.execute(insert_query, *values)

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
            # Сортируем по важности
            sorted_indices = np.argsort(importance_scores)[::-1]

            # Подготавливаем данные для вставки
            insert_query = """
                INSERT INTO ml_feature_importance
                (feature_name, feature_index, importance_score, importance_rank,
                 model_version, calculated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """

            calculated_at = datetime.now(UTC)

            for rank, idx in enumerate(sorted_indices[:100], 1):  # Топ-100 признаков
                await AsyncPGPool.execute(
                    insert_query,
                    feature_names[idx],
                    int(idx),
                    float(importance_scores[idx]),
                    rank,
                    self.model_version,
                    calculated_at,
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
