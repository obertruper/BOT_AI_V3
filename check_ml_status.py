#!/usr/bin/env python3
"""
Проверка статуса ML предсказаний с актуальными данными
"""

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def check_ml_status():
    """Проверка работы ML с обновленными данными"""
    print("🤖 Проверка ML системы с актуальными данными...\n")

    from core.config.config_manager import get_global_config_manager
    from database.connections.postgres import AsyncPGPool
    from ml.ml_manager import MLManager

    try:
        # Инициализация
        config_manager = get_global_config_manager()
        ml_manager = MLManager(config_manager.get_ml_config())

        print("1️⃣ Инициализация ML Manager...")
        await ml_manager.initialize()
        print("   ✅ ML Manager инициализирован")

        # Проверка данных
        print("\n2️⃣ Проверка актуальности данных...")

        pool = await AsyncPGPool.get_pool()

        # Получаем последние данные для основных символов
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

        for symbol in symbols:
            result = await pool.fetchrow(
                """
                SELECT
                    COUNT(*) as count,
                    MAX(datetime) as latest,
                    MIN(datetime) as earliest
                FROM raw_market_data
                WHERE symbol = $1
                AND interval_minutes = 15
                AND datetime > NOW() - INTERVAL '24 hours'
            """,
                symbol,
            )

            if result:
                print(f"\n   📊 {symbol}:")
                print(f"      - Свечей за последние 24ч: {result['count']}")
                print(f"      - Последние данные: {result['latest']}")

                # Проверяем актуальность
                if result["latest"]:
                    time_diff = (
                        datetime.now(result["latest"].tzinfo) - result["latest"]
                    ).total_seconds() / 60
                    print(
                        f"      - Отставание от текущего времени: {time_diff:.0f} минут"
                    )

                    if time_diff < 60:
                        print("      - ✅ Данные актуальны!")
                    else:
                        print("      - ⚠️ Данные устарели")

        # Генерация ML предсказаний
        print("\n3️⃣ Генерация ML предсказаний...")

        # Получаем предсказания для BTCUSDT
        symbol = "BTCUSDT"

        # Проверяем, есть ли достаточно данных
        candle_count = await pool.fetchval(
            """
            SELECT COUNT(*) FROM raw_market_data
            WHERE symbol = $1 AND interval_minutes = 15
        """,
            symbol,
        )

        print(f"\n   Всего свечей для {symbol}: {candle_count}")

        if candle_count >= 96:
            print("   ✅ Достаточно данных для ML предсказаний")

            # Получаем последние 96 свечей
            candles = await pool.fetch(
                """
                SELECT datetime, open, high, low, close, volume
                FROM raw_market_data
                WHERE symbol = $1 AND interval_minutes = 15
                ORDER BY datetime DESC
                LIMIT 96
            """,
                symbol,
            )

            # Конвертируем в DataFrame
            import pandas as pd

            df = pd.DataFrame(
                [
                    {
                        "datetime": c["datetime"],
                        "open": float(c["open"]),
                        "high": float(c["high"]),
                        "low": float(c["low"]),
                        "close": float(c["close"]),
                        "volume": float(c["volume"]),
                    }
                    for c in candles
                ]
            )

            # Сортируем по времени (от старых к новым)
            df = df.sort_values("datetime").reset_index(drop=True)

            # Получаем предсказание
            prediction = await ml_manager.predict(df)

            if prediction:
                print(f"\n   🎯 ML предсказание для {symbol}:")

                # Основные метрики
                if "signal" in prediction:
                    signal = prediction["signal"]
                    print(f"      - Направление: {signal}")

                if "confidence" in prediction:
                    print(f"      - Уверенность: {prediction['confidence']:.2%}")

                if "predicted_returns" in prediction:
                    returns = prediction["predicted_returns"]
                    print("\n   📈 Предсказанные доходности:")
                    print(f"      - 15м: {returns.get('15m', 0):.4f}")
                    print(f"      - 1ч: {returns.get('1h', 0):.4f}")
                    print(f"      - 4ч: {returns.get('4h', 0):.4f}")

                if "predicted_directions" in prediction:
                    directions = prediction["predicted_directions"]
                    print("\n   🎯 Предсказанные направления:")
                    print(
                        f"      - 15м: {'▲ LONG' if directions.get('15m', 0) > 0 else '▼ SHORT'}"
                    )
                    print(
                        f"      - 1ч: {'▲ LONG' if directions.get('1h', 0) > 0 else '▼ SHORT'}"
                    )
                    print(
                        f"      - 4ч: {'▲ LONG' if directions.get('4h', 0) > 0 else '▼ SHORT'}"
                    )

                if "volatility" in prediction:
                    print(f"\n   📊 Волатильность: {prediction['volatility']:.4f}")

                if "risk_metrics" in prediction:
                    risk = prediction["risk_metrics"]
                    print("\n   ⚠️ Риск-метрики:")
                    for key, value in risk.items():
                        if isinstance(value, float):
                            print(f"      - {key}: {value:.4f}")
            else:
                print("   ❌ Не удалось получить ML предсказание")
        else:
            print(f"   ❌ Недостаточно данных: {candle_count} < 96")

        print("\n✅ Проверка завершена!")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Закрываем пул соединений
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(check_ml_status())
