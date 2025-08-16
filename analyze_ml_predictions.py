#!/usr/bin/env python3
"""
Скрипт анализа ML предсказаний из базы данных
Показывает статистику точности, доходности и другие метрики
"""

import asyncio
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger("ml_predictions_analyzer")


class MLPredictionsAnalyzer:
    """Анализатор ML предсказаний из БД"""

    def __init__(self):
        self.predictions_df = None

    async def load_predictions(self, days_back: int = 7, symbol: str | None = None) -> pd.DataFrame:
        """
        Загружает предсказания из БД за указанный период

        Args:
            days_back: Количество дней назад
            symbol: Фильтр по символу (опционально)
        """
        try:
            query = """
                SELECT *
                FROM ml_predictions
                WHERE datetime >= $1
            """
            params = [datetime.now(UTC) - timedelta(days=days_back)]

            if symbol:
                query += " AND symbol = $2"
                params.append(symbol)

            query += " ORDER BY datetime DESC"

            rows = await AsyncPGPool.fetch(query, *params)

            if not rows:
                logger.warning("Нет предсказаний в БД за указанный период")
                return pd.DataFrame()

            # Конвертируем в DataFrame
            self.predictions_df = pd.DataFrame([dict(row) for row in rows])
            logger.info(f"Загружено {len(self.predictions_df)} предсказаний")

            return self.predictions_df

        except Exception as e:
            logger.error(f"Ошибка загрузки предсказаний: {e}")
            return pd.DataFrame()

    async def calculate_accuracy_metrics(self) -> dict:
        """Рассчитывает метрики точности предсказаний"""
        if self.predictions_df is None or self.predictions_df.empty:
            return {}

        df = self.predictions_df
        metrics = {}

        # Для каждого таймфрейма
        for timeframe in ["15m", "1h", "4h", "12h"]:
            # Фильтруем записи где есть актуальные результаты
            mask = df[f"actual_direction_{timeframe}"].notna()
            valid_df = df[mask]

            if valid_df.empty:
                continue

            # Точность направления
            correct = (
                valid_df[f"direction_{timeframe}"] == valid_df[f"actual_direction_{timeframe}"]
            ).sum()
            total = len(valid_df)
            accuracy = correct / total if total > 0 else 0

            # Средняя ошибка доходности
            if f"actual_return_{timeframe}" in valid_df.columns:
                return_errors = (
                    valid_df[f"predicted_return_{timeframe}"]
                    - valid_df[f"actual_return_{timeframe}"]
                ).abs()
                mae = return_errors.mean()
                rmse = np.sqrt((return_errors**2).mean())
            else:
                mae = rmse = None

            metrics[timeframe] = {
                "accuracy": accuracy,
                "total_predictions": total,
                "correct_predictions": correct,
                "mae": mae,
                "rmse": rmse,
                "avg_confidence": valid_df[f"direction_{timeframe}_confidence"].mean(),
            }

        return metrics

    async def analyze_by_confidence(self) -> pd.DataFrame:
        """Анализирует точность по уровням уверенности"""
        if self.predictions_df is None or self.predictions_df.empty:
            return pd.DataFrame()

        df = self.predictions_df
        results = []

        # Группы уверенности
        confidence_bins = [(0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.0)]

        for low, high in confidence_bins:
            mask = (df["signal_confidence"] >= low) & (df["signal_confidence"] < high)
            group_df = df[mask]

            if group_df.empty:
                continue

            # Считаем статистику для группы
            results.append(
                {
                    "confidence_range": f"{low:.0%}-{high:.0%}",
                    "count": len(group_df),
                    "avg_confidence": group_df["signal_confidence"].mean(),
                    "long_ratio": (group_df["signal_type"] == "LONG").mean(),
                    "short_ratio": (group_df["signal_type"] == "SHORT").mean(),
                    "neutral_ratio": (group_df["signal_type"] == "NEUTRAL").mean(),
                }
            )

        return pd.DataFrame(results)

    async def analyze_by_symbol(self) -> pd.DataFrame:
        """Анализирует статистику по символам"""
        if self.predictions_df is None or self.predictions_df.empty:
            return pd.DataFrame()

        df = self.predictions_df

        # Группируем по символам
        symbol_stats = df.groupby("symbol").agg(
            {
                "signal_confidence": ["mean", "std"],
                "signal_type": lambda x: (x == "LONG").sum(),
                "predicted_return_15m": "mean",
                "predicted_return_1h": "mean",
                "risk_score": "mean",
            }
        )

        symbol_stats.columns = ["_".join(col).strip() for col in symbol_stats.columns]
        symbol_stats["total_predictions"] = df.groupby("symbol").size()

        return symbol_stats.sort_values("total_predictions", ascending=False)

    async def analyze_feature_statistics(self) -> dict:
        """Анализирует статистику входных признаков"""
        if self.predictions_df is None or self.predictions_df.empty:
            return {}

        df = self.predictions_df

        return {
            "avg_features_count": df["features_count"].mean(),
            "avg_nan_count": df["nan_count"].mean(),
            "avg_zero_variance_count": df["zero_variance_count"].mean(),
            "features_mean": {
                "avg": df["features_mean"].mean(),
                "std": df["features_mean"].std(),
                "min": df["features_mean"].min(),
                "max": df["features_mean"].max(),
            },
            "features_std": {
                "avg": df["features_std"].mean(),
                "std": df["features_std"].std(),
                "min": df["features_std"].min(),
                "max": df["features_std"].max(),
            },
        }

    async def print_analysis_report(self):
        """Выводит полный отчет анализа"""
        print("\n" + "=" * 80)
        print(" ML PREDICTIONS ANALYSIS REPORT ".center(80, "="))
        print("=" * 80 + "\n")

        if self.predictions_df is None or self.predictions_df.empty:
            print("❌ Нет данных для анализа")
            return

        # Общая статистика
        print("📊 ОБЩАЯ СТАТИСТИКА")
        print("-" * 40)
        print(f"Всего предсказаний: {len(self.predictions_df)}")
        print(
            f"Период: {self.predictions_df['datetime'].min()} - {self.predictions_df['datetime'].max()}"
        )
        print(f"Уникальных символов: {self.predictions_df['symbol'].nunique()}")
        print(f"Средняя уверенность: {self.predictions_df['signal_confidence'].mean():.2%}")
        print()

        # Распределение сигналов
        signal_dist = self.predictions_df["signal_type"].value_counts()
        print("📈 РАСПРЕДЕЛЕНИЕ СИГНАЛОВ")
        print("-" * 40)
        for signal_type, count in signal_dist.items():
            print(f"{signal_type}: {count} ({count / len(self.predictions_df):.1%})")
        print()

        # Метрики точности
        accuracy_metrics = await self.calculate_accuracy_metrics()
        if accuracy_metrics:
            print("🎯 МЕТРИКИ ТОЧНОСТИ")
            print("-" * 40)
            for timeframe, metrics in accuracy_metrics.items():
                if metrics["total_predictions"] > 0:
                    print(f"\n{timeframe.upper()}:")
                    print(f"  Точность: {metrics['accuracy']:.2%}")
                    print(f"  Предсказаний: {metrics['total_predictions']}")
                    print(f"  Правильных: {metrics['correct_predictions']}")
                    print(f"  Средняя уверенность: {metrics['avg_confidence']:.2%}")
                    if metrics["mae"] is not None:
                        print(f"  MAE доходности: {metrics['mae']:.4f}")
                        print(f"  RMSE доходности: {metrics['rmse']:.4f}")

        # Анализ по уверенности
        confidence_analysis = await self.analyze_by_confidence()
        if not confidence_analysis.empty:
            print("\n💎 АНАЛИЗ ПО УВЕРЕННОСТИ")
            print("-" * 40)
            print(confidence_analysis.to_string(index=False))

        # Анализ по символам
        symbol_analysis = await self.analyze_by_symbol()
        if not symbol_analysis.empty:
            print("\n📊 ТОП-10 СИМВОЛОВ")
            print("-" * 40)
            print(symbol_analysis.head(10).to_string())

        # Статистика признаков
        feature_stats = await self.analyze_feature_statistics()
        if feature_stats:
            print("\n🔬 СТАТИСТИКА ПРИЗНАКОВ")
            print("-" * 40)
            print(f"Среднее количество признаков: {feature_stats['avg_features_count']:.0f}")
            print(f"Среднее количество NaN: {feature_stats['avg_nan_count']:.1f}")
            print(
                f"Среднее количество zero variance: {feature_stats['avg_zero_variance_count']:.1f}"
            )
            print(f"Features mean - avg: {feature_stats['features_mean']['avg']:.4f}")
            print(f"Features std - avg: {feature_stats['features_std']['avg']:.4f}")

        # Производительность
        if "inference_time_ms" in self.predictions_df.columns:
            print("\n⚡ ПРОИЗВОДИТЕЛЬНОСТЬ")
            print("-" * 40)
            print(
                f"Среднее время inference: {self.predictions_df['inference_time_ms'].mean():.1f} ms"
            )
            print(f"Медиана: {self.predictions_df['inference_time_ms'].median():.1f} ms")
            print(
                f"95 percentile: {self.predictions_df['inference_time_ms'].quantile(0.95):.1f} ms"
            )

        print("\n" + "=" * 80)


async def main():
    """Главная функция"""
    analyzer = MLPredictionsAnalyzer()

    # Загружаем данные за последние 7 дней
    await analyzer.load_predictions(days_back=7)

    # Выводим отчет
    await analyzer.print_analysis_report()

    # Опционально: сохраняем в файл
    try:
        if analyzer.predictions_df is not None and not analyzer.predictions_df.empty:
            analyzer.predictions_df.to_csv(
                f"ml_predictions_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                index=False,
            )
            print("\n✅ Данные сохранены в CSV файл")
    except Exception as e:
        logger.error(f"Ошибка сохранения в CSV: {e}")


if __name__ == "__main__":
    asyncio.run(main())
