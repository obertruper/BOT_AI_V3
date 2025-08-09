#!/usr/bin/env python3
"""
Тестовый генератор ML сигналов
"""

import asyncio
import os
import random
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def generate_test_signals():
    """Генерация тестовых ML сигналов"""
    from database.connections.postgres import AsyncPGPool

    pool = await AsyncPGPool.get_pool()

    print(f"\n🤖 ТЕСТОВЫЙ ML ГЕНЕРАТОР ЗАПУЩЕН - {datetime.now().strftime('%H:%M:%S')}")
    print("Нажмите Ctrl+C для остановки\n")

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    try:
        while True:
            # Генерируем сигнал для случайного символа
            symbol = random.choice(symbols)

            # Случайное направление (больше нейтральных для реалистичности)
            rand = random.random()
            if rand < 0.2:  # 20% LONG
                signal_type = "LONG"
                confidence = random.uniform(0.35, 0.7)
                strength = random.uniform(0.02, 0.05)
            elif rand < 0.4:  # 20% SHORT
                signal_type = "SHORT"
                confidence = random.uniform(0.35, 0.7)
                strength = random.uniform(0.02, 0.05)
            else:  # 60% NEUTRAL
                signal_type = "NEUTRAL"
                confidence = random.uniform(0.25, 0.4)
                strength = random.uniform(0.001, 0.02)

            # Получаем текущую цену
            price_data = await pool.fetchrow(
                """
                SELECT close
                FROM raw_market_data
                WHERE symbol = $1 AND interval_minutes = 15
                ORDER BY datetime DESC
                LIMIT 1
            """,
                symbol,
            )

            if price_data:
                current_price = float(price_data["close"])

                # Сохраняем сигнал
                await pool.execute(
                    """
                    INSERT INTO signals
                    (symbol, exchange, signal_type, strength, confidence, suggested_price,
                     strategy_name, created_at, extra_data)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), $8)
                """,
                    symbol,
                    "bybit",
                    signal_type,
                    strength,
                    confidence,
                    current_price,
                    "ML_Test_Generator",
                    '{"test": true}',
                )

                if signal_type != "NEUTRAL":
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] "
                        f"{'🟢' if signal_type == 'LONG' else '🔴'} "
                        f"{symbol}: {signal_type} (уверенность: {confidence:.0%})"
                    )

            # Ждем перед следующим сигналом
            await asyncio.sleep(random.uniform(10, 30))

    except KeyboardInterrupt:
        print("\n⏹️ Генератор остановлен")
    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(generate_test_signals())
