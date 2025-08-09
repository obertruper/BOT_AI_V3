#!/usr/bin/env python3
"""
Отладочный скрипт для проверки уникальности предсказаний ML модели
"""

import asyncio

import numpy as np

from core.config.config_manager import ConfigManager
from data.data_loader import DataLoader
from ml.logic.feature_engineering import FeatureEngineer
from ml.ml_manager import MLManager


async def test_unique_predictions():
    """Тестирование уникальности предсказаний для разных монет"""
    print("=" * 80)
    print("ТЕСТ УНИКАЛЬНОСТИ ML ПРЕДСКАЗАНИЙ")
    print("=" * 80)

    # Инициализация компонентов
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # 1. Инициализация ML Manager
    print("\n1. Инициализация ML Manager...")
    ml_manager = MLManager(config)
    await ml_manager.initialize()
    print("✓ ML Manager инициализирован")

    # 2. Загрузка данных для разных монет
    print("\n2. Загрузка данных...")
    loader = DataLoader()
    await loader.initialize()

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    data_dict = {}

    for symbol in symbols:
        df = await loader.get_data_for_ml(symbol, limit=200)
        data_dict[symbol] = df
        print(
            f"✓ {symbol}: загружено {len(df)} записей, последняя цена: {df['close'].iloc[-1]}"
        )

    # 3. Генерация признаков
    print("\n3. Генерация признаков...")
    fe = FeatureEngineer()
    features_dict = {}

    for symbol, df in data_dict.items():
        features = fe.create_features(df)
        # Берем последние 96 временных точек
        if len(features) >= 96:
            features = features[-96:]
        features_dict[symbol] = features
        print(f"✓ {symbol}: сгенерировано {features.shape} признаков")
        print(f"  Среднее: {features.mean():.6f}, Std: {features.std():.6f}")

    # 4. Нормализация признаков
    print("\n4. Нормализация признаков...")
    normalized_dict = {}

    for symbol, features in features_dict.items():
        # Добавляем batch dimension
        features_batch = features.reshape(1, 96, -1).astype(np.float32)
        # Просто используем features как есть (ML Manager нормализует внутри predict)
        normalized_dict[symbol] = features_batch
        print(f"✓ {symbol}: подготовлено {features_batch.shape}")
        print(
            f"  Статистика - Среднее: {features_batch.mean():.6f}, Std: {features_batch.std():.6f}"
        )

    # 5. Проверка уникальности нормализованных данных
    print("\n5. Проверка уникальности нормализованных данных...")
    btc_norm = normalized_dict["BTCUSDT"]
    eth_norm = normalized_dict["ETHUSDT"]
    sol_norm = normalized_dict["SOLUSDT"]

    btc_eth_diff = np.abs(btc_norm - eth_norm).mean()
    btc_sol_diff = np.abs(btc_norm - sol_norm).mean()
    eth_sol_diff = np.abs(eth_norm - sol_norm).mean()

    print(f"Средняя разница BTC-ETH: {btc_eth_diff:.6f}")
    print(f"Средняя разница BTC-SOL: {btc_sol_diff:.6f}")
    print(f"Средняя разница ETH-SOL: {eth_sol_diff:.6f}")

    # 6. Получение предсказаний
    print("\n6. Получение ML предсказаний...")
    predictions = {}

    for symbol, features in normalized_dict.items():
        pred = await ml_manager.predict(features)
        predictions[symbol] = pred
        print(f"\n{symbol}:")
        print(f"  Signal type: {pred.get('signal_type')}")
        print(f"  Confidence: {pred.get('confidence'):.4f}")
        print(f"  Returns 15m: {pred.get('predictions', {}).get('returns_15m', 0):.6f}")
        print(f"  Returns 1h: {pred.get('predictions', {}).get('returns_1h', 0):.6f}")
        print(
            f"  Direction score: {pred.get('predictions', {}).get('direction_score', 0):.2f}"
        )

    # 7. Анализ уникальности предсказаний
    print("\n7. Анализ уникальности предсказаний...")
    btc_ret = predictions["BTCUSDT"]["predictions"]["returns_15m"]
    eth_ret = predictions["ETHUSDT"]["predictions"]["returns_15m"]
    sol_ret = predictions["SOLUSDT"]["predictions"]["returns_15m"]

    print("\nВозвраты 15м:")
    print(f"BTC: {btc_ret:.8f}")
    print(f"ETH: {eth_ret:.8f}")
    print(f"SOL: {sol_ret:.8f}")

    if btc_ret == eth_ret == sol_ret:
        print("\n❌ ПРОБЛЕМА: Все предсказания одинаковые!")
    else:
        print("\n✅ Предсказания уникальные!")

    # Cleanup
    await loader.cleanup()

    print("\n" + "=" * 80)
    print("ТЕСТ ЗАВЕРШЕН")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_unique_predictions())
