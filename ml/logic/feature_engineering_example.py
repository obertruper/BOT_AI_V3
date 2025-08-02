"""
Пример использования FeatureEngineer для генерации признаков
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List

import numpy as np
import pandas as pd

from ml.logic.feature_engineering import FeatureConfig, FeatureEngineer

logger = logging.getLogger(__name__)


async def fetch_ohlcv_data(
    symbol: str, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    """
    Получение OHLCV данных из базы данных

    Args:
        symbol: Торговый символ (например, 'BTCUSDT')
        start_date: Начальная дата
        end_date: Конечная дата

    Returns:
        DataFrame с OHLCV данными
    """
    # Здесь должен быть реальный запрос к БД
    # Для примера генерируем синтетические данные

    periods = int(
        (end_date - start_date).total_seconds() / (15 * 60)
    )  # 15-минутные свечи
    dates = pd.date_range(start=start_date, end=end_date, freq="15min")[:periods]

    # Генерируем реалистичные данные
    base_price = 50000 if symbol == "BTCUSDT" else 3000
    trend = np.cumsum(np.random.normal(0, base_price * 0.001, len(dates)))

    close_prices = base_price + trend

    data = {
        "datetime": dates,
        "symbol": symbol,
        "open": close_prices * (1 + np.random.normal(0, 0.001, len(dates))),
        "high": close_prices * (1 + np.abs(np.random.normal(0.002, 0.001, len(dates)))),
        "low": close_prices * (1 - np.abs(np.random.normal(0.002, 0.001, len(dates)))),
        "close": close_prices,
        "volume": np.random.lognormal(10, 1, len(dates)),
    }

    df = pd.DataFrame(data)

    # Корректируем OHLC
    df["high"] = df[["open", "close", "high"]].max(axis=1)
    df["low"] = df[["open", "close", "low"]].min(axis=1)

    # Добавляем turnover
    df["turnover"] = df["close"] * df["volume"]

    return df


async def prepare_features_for_training(
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    config: FeatureConfig = None,
) -> pd.DataFrame:
    """
    Подготовка признаков для обучения модели

    Args:
        symbols: Список торговых символов
        start_date: Начальная дата
        end_date: Конечная дата
        config: Конфигурация признаков

    Returns:
        DataFrame с признаками и целевыми переменными
    """
    logger.info(
        "Начало подготовки данных",
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )

    # Загружаем данные для всех символов
    all_data = []
    for symbol in symbols:
        data = await fetch_ohlcv_data(symbol, start_date, end_date)
        all_data.append(data)

    # Объединяем данные
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values(["symbol", "datetime"])

    # Создаем экземпляр FeatureEngineer
    feature_engineer = FeatureEngineer(config)

    # Генерируем признаки
    features_df = feature_engineer.create_features(combined_df)

    # Создаем целевые переменные
    features_df = feature_engineer.create_target_variables(features_df)

    # Получаем список признаков
    feature_names = feature_engineer.get_feature_names()
    logger.info(f"Создано {len(feature_names)} признаков")

    # Выводим топ-10 признаков для примера
    logger.info(f"Примеры признаков: {feature_names[:10]}")

    # Статистика по целевым переменным
    for period in ["15m", "1h", "4h", "12h"]:
        if f"direction_{period}" in features_df.columns:
            dist = features_df[f"direction_{period}"].value_counts(normalize=True)
            logger.info(
                f"Распределение direction_{period}",
                up=dist.get("UP", 0),
                down=dist.get("DOWN", 0),
                flat=dist.get("FLAT", 0),
            )

    return features_df, feature_names


async def prepare_features_for_prediction(
    symbol: str,
    data: pd.DataFrame,
    feature_names: List[str],
    config: FeatureConfig = None,
) -> pd.DataFrame:
    """
    Подготовка признаков для предсказания в реальном времени

    Args:
        symbol: Торговый символ
        data: DataFrame с последними OHLCV данными (минимум 100 свечей)
        feature_names: Список признаков из обученной модели
        config: Конфигурация признаков (должна совпадать с обучением)

    Returns:
        DataFrame с признаками для последней свечи
    """
    # Добавляем symbol если его нет
    if "symbol" not in data.columns:
        data["symbol"] = symbol

    # Создаем экземпляр FeatureEngineer с той же конфигурацией
    feature_engineer = FeatureEngineer(config)

    # Генерируем признаки
    features_df = feature_engineer.create_features(data)

    # Берем только последнюю строку
    last_row = features_df.iloc[-1:].copy()

    # Выбираем только нужные признаки
    prediction_features = last_row[feature_names]

    return prediction_features


def analyze_feature_importance(
    features_df: pd.DataFrame, target_col: str = "direction_1h"
):
    """
    Анализ важности признаков с помощью взаимной информации

    Args:
        features_df: DataFrame с признаками
        target_col: Целевая переменная для анализа
    """
    from sklearn.feature_selection import mutual_info_classif
    from sklearn.preprocessing import LabelEncoder

    # Подготавливаем данные
    feature_cols = [
        col
        for col in features_df.columns
        if not any(
            pattern in col
            for pattern in [
                "future_",
                "direction_",
                "will_reach_",
                "max_drawdown_",
                "max_rally_",
            ]
        )
    ]

    # Удаляем нечисловые колонки
    feature_cols = [
        col for col in feature_cols if col not in ["datetime", "symbol", "sector"]
    ]

    # Подготавливаем X и y
    X = features_df[feature_cols].fillna(0)

    # Кодируем целевую переменную
    le = LabelEncoder()
    y = le.fit_transform(features_df[target_col].fillna("FLAT"))

    # Вычисляем взаимную информацию
    mi_scores = mutual_info_classif(X, y, random_state=42)

    # Создаем DataFrame с результатами
    importance_df = pd.DataFrame(
        {"feature": feature_cols, "importance": mi_scores}
    ).sort_values("importance", ascending=False)

    # Выводим топ-20 признаков
    logger.info(f"\nТоп-20 важных признаков для {target_col}:")
    for idx, row in importance_df.head(20).iterrows():
        logger.info(f"{row['feature']}: {row['importance']:.4f}")

    return importance_df


async def main():
    """Основная функция для демонстрации"""
    # Конфигурация признаков
    config = FeatureConfig(
        sma_periods=[10, 20, 50],
        ema_periods=[10, 20, 50],
        rsi_period=14,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        bb_period=20,
        bb_std=2.0,
        atr_period=14,
        volatility_periods=[5, 10, 20],
        volume_periods=[5, 10, 20],
    )

    # Параметры для загрузки данных
    symbols = ["BTCUSDT", "ETHUSDT"]
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # 1. Подготовка данных для обучения
    logger.info("=== Подготовка данных для обучения ===")
    features_df, feature_names = await prepare_features_for_training(
        symbols=symbols, start_date=start_date, end_date=end_date, config=config
    )

    logger.info(f"Размер данных: {features_df.shape}")
    logger.info(f"Количество признаков: {len(feature_names)}")

    # 2. Анализ важности признаков
    logger.info("\n=== Анализ важности признаков ===")
    importance_df = analyze_feature_importance(features_df, "direction_1h")

    # 3. Подготовка данных для предсказания
    logger.info("\n=== Подготовка данных для предсказания ===")

    # Получаем последние 100 свечей для предсказания
    recent_data = await fetch_ohlcv_data(
        "BTCUSDT",
        end_date - timedelta(hours=25),
        end_date,  # 100 свечей по 15 минут
    )

    prediction_features = await prepare_features_for_prediction(
        symbol="BTCUSDT", data=recent_data, feature_names=feature_names, config=config
    )

    logger.info(f"Признаки для предсказания подготовлены: {prediction_features.shape}")

    # 4. Статистика по признакам
    logger.info("\n=== Статистика по признакам ===")

    # Примеры значений некоторых ключевых признаков
    key_features = ["returns", "rsi", "volume_ratio_5", "bb_position", "momentum_1h"]
    for feature in key_features:
        if feature in features_df.columns:
            stats = features_df[feature].describe()
            logger.info(f"\n{feature}:")
            logger.info(f"  Mean: {stats['mean']:.4f}")
            logger.info(f"  Std: {stats['std']:.4f}")
            logger.info(f"  Min: {stats['min']:.4f}")
            logger.info(f"  Max: {stats['max']:.4f}")


if __name__ == "__main__":
    # Запускаем пример
    asyncio.run(main())
