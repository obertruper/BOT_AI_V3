#!/usr/bin/env python3
"""
Полная диагностика ML pipeline
"""

import asyncio
import os
from datetime import datetime

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def diagnose_ml_pipeline():
    """Полная диагностика ML pipeline"""
    from core.config.config_manager import get_global_config_manager
    from database.connections.postgres import AsyncPGPool
    from ml.logic.feature_engineering import FeatureEngineer
    from ml.ml_manager import MLManager

    print(f"\n🔍 ДИАГНОСТИКА ML PIPELINE - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 80)

    try:
        pool = await AsyncPGPool.get_pool()
        config_manager = get_global_config_manager()
        config = config_manager.get_config()

        # 1. Проверка данных
        print("\n1️⃣ ПРОВЕРКА ДАННЫХ В БД:")

        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

        for symbol in symbols:
            data_info = await pool.fetchrow(
                """
                SELECT
                    COUNT(*) as count,
                    MIN(datetime) as first,
                    MAX(datetime) as last,
                    (MAX(datetime) - MIN(datetime)) as span
                FROM raw_market_data
                WHERE symbol = $1 AND interval_minutes = 15
            """,
                symbol,
            )

            if data_info and data_info["count"] > 0:
                lag = datetime.now() - data_info["last"].replace(tzinfo=None)
                print(
                    f"   {symbol}: {data_info['count']} свечей, "
                    f"последняя {int(lag.total_seconds() / 60)} мин назад"
                )
            else:
                print(f"   {symbol}: ❌ Нет данных!")

        # 2. Загрузка данных для ML
        print("\n2️⃣ ЗАГРУЗКА ДАННЫХ ДЛЯ ML:")

        symbol = "BTCUSDT"

        # Загружаем последние 200 свечей
        candles = await pool.fetch(
            """
            SELECT
                datetime,
                open,
                high,
                low,
                close,
                volume
            FROM raw_market_data
            WHERE symbol = $1 AND interval_minutes = 15
            ORDER BY datetime DESC
            LIMIT 200
        """,
            symbol,
        )

        if candles:
            print(f"   ✅ Загружено {len(candles)} свечей для {symbol}")

            # Преобразуем в DataFrame с правильными именами колонок
            df = pd.DataFrame(
                candles, columns=["datetime", "open", "high", "low", "close", "volume"]
            )
            print(f"   📋 Колонки: {list(df.columns)}")

            # Создаем timestamp колонку
            df["timestamp"] = pd.to_datetime(df["datetime"])
            df = df.sort_values("timestamp")
            df = df.reset_index(drop=True)

            # Конвертируем decimal в float
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            print(f"   📊 DataFrame shape: {df.shape}")
            print(f"   📅 Период: {df['timestamp'].min()} - {df['timestamp'].max()}")

            # 3. Feature Engineering
            print("\n3️⃣ FEATURE ENGINEERING:")

            try:
                feature_engineer = FeatureEngineer(config)

                # Создаем признаки
                features_array = feature_engineer.create_features(df)

                print(
                    f"   ✅ Создано признаков: {features_array.shape[1] if len(features_array.shape) > 1 else 1}"
                )
                print(f"   📊 Shape после FE: {features_array.shape}")

                # Проверяем NaN
                nan_count = np.isnan(features_array).sum()
                print(f"   ⚠️ NaN значений: {nan_count}")

                if nan_count > 0:
                    nan_mask = np.isnan(features_array).any(axis=0)
                    nan_indices = np.where(nan_mask)[0]
                    print(
                        f"   ⚠️ Индексы признаков с NaN: {nan_indices[:5].tolist()}..."
                    )

                # 4. Подготовка данных для модели
                print("\n4️⃣ ПОДГОТОВКА ДАННЫХ ДЛЯ МОДЕЛИ:")

                # Удаляем строки с NaN
                if nan_count > 0:
                    # Находим строки без NaN
                    valid_rows = ~np.isnan(features_array).any(axis=1)
                    features_clean = features_array[valid_rows]
                else:
                    features_clean = features_array

                print(f"   📊 Shape после удаления NaN: {features_clean.shape}")

                if features_clean.shape[0] >= 96:
                    # Берем последние 96 временных точек
                    features_for_model = features_clean[-96:]
                    print(f"   ✅ Данные для модели: {features_for_model.shape}")

                    # 5. Инициализация ML Manager
                    print("\n5️⃣ ИНИЦИАЛИЗАЦИЯ ML MANAGER:")

                    ml_manager = MLManager(config)
                    await ml_manager.initialize()
                    print("   ✅ ML Manager инициализирован")

                    # 6. Предсказание
                    print("\n6️⃣ ГЕНЕРАЦИЯ ПРЕДСКАЗАНИЯ:")

                    # Добавляем batch dimension
                    input_tensor = features_for_model[
                        np.newaxis, ...
                    ]  # (1, 96, features)
                    print(f"   📊 Input shape: {input_tensor.shape}")

                    prediction = await ml_manager.predict(input_tensor)

                    if prediction:
                        print("   ✅ Предсказание получено:")
                        print(f"      Direction: {prediction.get('direction')}")
                        print(
                            f"      Confidence: {prediction.get('confidence', 0):.2%}"
                        )
                        print(
                            f"      Predicted returns: {prediction.get('predicted_returns', [])}"
                        )

                        # 7. Проверка Signal Processor
                        print("\n7️⃣ ПРОВЕРКА SIGNAL PROCESSOR:")

                        from ml.ml_signal_processor import MLSignalProcessor

                        signal_processor = MLSignalProcessor(config)

                        # Получаем текущую цену
                        current_price = float(df["close"].iloc[-1])
                        print(f"   💲 Текущая цена: ${current_price:.2f}")

                        # Обрабатываем предсказание
                        signal = await signal_processor.process_ml_prediction(
                            symbol=symbol,
                            ml_output=prediction,
                            current_price=current_price,
                        )

                        if signal:
                            print("   ✅ Сигнал сгенерирован:")
                            print(f"      Type: {signal.signal_type}")
                            print(f"      Confidence: {signal.confidence:.2%}")
                            print(f"      Strength: {signal.strength:.4f}")
                        else:
                            print("   ❌ Сигнал не прошел фильтры")
                    else:
                        print("   ❌ Предсказание не получено")
                else:
                    print(f"   ❌ Недостаточно данных: {features_clean.shape[0]} < 96")

            except Exception as e:
                print(f"   ❌ Ошибка в Feature Engineering: {e}")
                import traceback

                traceback.print_exc()

        else:
            print(f"   ❌ Не удалось загрузить данные для {symbol}")

        # 8. Проверка конфигурации
        print("\n8️⃣ ПРОВЕРКА КОНФИГУРАЦИИ ML:")

        ml_config = config.get("ml", {})
        print(f"   Модель: {ml_config.get('model', {}).get('model_type', 'N/A')}")
        print(
            f"   Минимальная уверенность: {ml_config.get('trading', {}).get('min_confidence', 0.6):.0%}"
        )
        print(
            f"   Размер позиции: {ml_config.get('trading', {}).get('position_size', 0.01)}"
        )

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(diagnose_ml_pipeline())
