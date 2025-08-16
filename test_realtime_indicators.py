#!/usr/bin/env python3
"""
Тест исправленных индикаторов в real-time calculator
"""

import asyncio
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from core.logger import setup_logger
from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

logger = setup_logger(__name__)


def generate_realistic_ohlcv(n_samples=350):
    """Генерирует реалистичные OHLCV данные для тестирования"""
    # Начинаем с недавней даты
    start_time = datetime.now() - timedelta(days=2)
    dates = pd.date_range(start=start_time, periods=n_samples, freq="5T")

    # Реалистичная генерация цен для BTCUSDT
    np.random.seed(42)
    base_price = 42000  # Реалистичная цена BTC

    # Генерируем доходности с волатильностью как у BTC
    returns = np.random.normal(0, 0.008, n_samples)  # ~0.8% волатильность за 5 минут

    # Добавляем тренд и циклы
    trend = np.linspace(0, 0.02, n_samples)  # 2% рост за период
    cycle = 0.01 * np.sin(np.linspace(0, 4 * np.pi, n_samples))  # Цикличность

    returns = returns + trend + cycle

    # Генерируем цены
    prices = [base_price]
    for ret in returns[1:]:
        new_price = prices[-1] * (1 + ret)
        prices.append(new_price)

    prices = np.array(prices)

    # Создаем OHLCV с реалистичными spread-ами
    spread_pct = 0.001  # 0.1% спред

    df = pd.DataFrame(index=dates)
    df["open"] = prices
    df["high"] = prices * (1 + np.random.uniform(0, spread_pct * 2, n_samples))
    df["low"] = prices * (1 - np.random.uniform(0, spread_pct * 2, n_samples))
    df["close"] = prices
    df["volume"] = np.random.lognormal(
        mean=8, sigma=1, size=n_samples
    )  # Логнормальное распределение объема

    # Корректируем high/low чтобы они были логичными
    df["high"] = np.maximum(df["high"], np.maximum(df["open"], df["close"]))
    df["low"] = np.minimum(df["low"], np.minimum(df["open"], df["close"]))

    return df


async def test_realtime_calculator():
    """Тестирует RealTimeIndicatorCalculator с исправлениями"""
    logger.info("🧪 Начинаем тест RealTimeIndicatorCalculator...")

    # Генерируем реалистичные данные
    ohlcv_data = generate_realistic_ohlcv(350)
    logger.info(f"📊 Сгенерированы OHLCV данные: {len(ohlcv_data)} свечей")
    logger.info(f"   Период: {ohlcv_data.index[0]} - {ohlcv_data.index[-1]}")
    logger.info(
        f"   Цена: ${ohlcv_data['close'].iloc[0]:.0f} -> ${ohlcv_data['close'].iloc[-1]:.0f}"
    )

    # Создаем калькулятор
    config = {}
    calculator = RealTimeIndicatorCalculator(cache_ttl=300, config=config, use_inference_mode=True)

    # Тестируем расчет индикаторов
    logger.info("🔧 Рассчитываем индикаторы...")
    result = await calculator.calculate_indicators(
        symbol="BTCUSDT",
        ohlcv_df=ohlcv_data,
        save_to_db=False,  # Не сохраняем в БД при тесте
    )

    if not result:
        logger.error("❌ Расчет индикаторов не удался!")
        return False

    # Анализируем результаты
    metadata = result.get("metadata", {})
    ml_features = result.get("ml_features", {})
    technical_indicators = result.get("technical_indicators", {})
    microstructure_features = result.get("microstructure_features", {})

    logger.info("✅ Результаты расчета:")
    logger.info(f"   ML признаков: {len(ml_features)}")
    logger.info(f"   Технических индикаторов: {len(technical_indicators)}")
    logger.info(f"   Микроструктурных признаков: {len(microstructure_features)}")
    logger.info(f"   Время расчета: {metadata.get('calculation_time')}")

    # Проверяем ключевые индикаторы
    key_features = ["rsi_14", "sma_20", "ema_20", "macd_12_26", "atr_14", "bb_position_20"]
    missing_key = []
    present_key = []

    for feature in key_features:
        if feature in ml_features:
            value = ml_features[feature]
            present_key.append((feature, value))
        else:
            missing_key.append(feature)

    logger.info("📊 Проверка ключевых индикаторов:")
    for feature, value in present_key:
        logger.info(f"   ✅ {feature}: {value:.6f}")

    if missing_key:
        logger.warning(f"   ❌ Отсутствующие: {missing_key}")

    # Проверяем качество данных
    nan_count = sum(1 for v in ml_features.values() if pd.isna(v))
    inf_count = sum(1 for v in ml_features.values() if np.isinf(v))
    zero_count = sum(1 for v in ml_features.values() if v == 0)

    logger.info("🧪 Качество данных:")
    logger.info(f"   NaN значений: {nan_count}/{len(ml_features)}")
    logger.info(f"   Inf значений: {inf_count}/{len(ml_features)}")
    logger.info(f"   Нулевых значений: {zero_count}/{len(ml_features)}")

    # Тестируем get_features_for_ml
    logger.info("🔧 Тестируем get_features_for_ml...")
    features_array = await calculator.get_features_for_ml("BTCUSDT", ohlcv_data)

    if len(features_array) == 240:
        logger.info(f"✅ get_features_for_ml: {len(features_array)} признаков")

        # Проверяем дисперсию
        non_zero_variance = np.sum(np.var(features_array.reshape(1, -1), axis=0) > 1e-10)
        logger.info(f"   Признаков с ненулевой дисперсией: {non_zero_variance}/240")
    else:
        logger.error(f"❌ get_features_for_ml: получено {len(features_array)} вместо 240")

    # Тестируем prepare_ml_input
    logger.info("🔧 Тестируем prepare_ml_input...")
    try:
        ml_input, ml_metadata = await calculator.prepare_ml_input(
            "BTCUSDT", ohlcv_data, lookback=96
        )
        logger.info(f"✅ prepare_ml_input: {ml_input.shape}")
        logger.info(f"   Lookback: {ml_metadata['lookback']}")
        logger.info(f"   Features: {ml_metadata['features_count']}")
        logger.info(f"   Non-zero variance: {ml_metadata['non_zero_variance_features']}")
    except Exception as e:
        logger.error(f"❌ prepare_ml_input ошибка: {e}")

    return {
        "success": True,
        "ml_features_count": len(ml_features),
        "tech_indicators_count": len(technical_indicators),
        "nan_count": nan_count,
        "inf_count": inf_count,
        "key_features_present": len(present_key),
        "key_features_missing": len(missing_key),
    }


if __name__ == "__main__":
    result = asyncio.run(test_realtime_calculator())

    if result["success"]:
        print("\n" + "=" * 60)
        print("🎯 РЕЗУЛЬТАТЫ ТЕСТА REALTIME CALCULATOR")
        print("=" * 60)
        print(f"✅ ML признаков: {result['ml_features_count']}")
        print(f"✅ Технических индикаторов: {result['tech_indicators_count']}")
        print(f"🧪 NaN значений: {result['nan_count']}")
        print(f"🧪 Inf значений: {result['inf_count']}")
        print(f"🎯 Ключевых признаков найдено: {result['key_features_present']}")
        print(f"❌ Ключевых признаков отсутствует: {result['key_features_missing']}")

        if (
            result["nan_count"] == 0
            and result["inf_count"] == 0
            and result["key_features_missing"] == 0
        ):
            print("\n🎉 РЕАЛЬНАЯ СИСТЕМА ГОТОВА К РАБОТЕ!")
        else:
            print("\n⚠️ ТРЕБУЕТСЯ ДОПОЛНИТЕЛЬНАЯ НАСТРОЙКА")
    else:
        print("\n❌ ТЕСТ НЕ ПРОЙДЕН")
