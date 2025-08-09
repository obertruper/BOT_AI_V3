#!/usr/bin/env python3
"""
Отладка ML сигналов
"""

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def debug_ml():
    """Отладка ML сигналов"""
    from core.config.config_manager import get_global_config_manager
    from database.connections.postgres import AsyncPGPool
    from ml.ml_manager import MLManager

    print(f"\n🔍 ОТЛАДКА ML СИГНАЛОВ - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

    try:
        pool = await AsyncPGPool.get_pool()
        config_manager = get_global_config_manager()

        # 1. Проверяем количество данных
        print("\n📊 ПРОВЕРКА ДАННЫХ:")

        data_count = await pool.fetchrow(
            """
            SELECT
                COUNT(*) as total,
                MIN(datetime) as first,
                MAX(datetime) as last
            FROM raw_market_data
            WHERE symbol = 'BTCUSDT' AND interval_minutes = 15
        """
        )

        if data_count:
            print(f"   BTCUSDT: {data_count['total']} свечей")
            print(f"   Первая: {data_count['first']}")
            print(f"   Последняя: {data_count['last']}")

        # 2. Инициализируем ML Manager
        print("\n🤖 ИНИЦИАЛИЗАЦИЯ ML:")

        config = config_manager.get_config()
        ml_manager = MLManager(config)
        await ml_manager.initialize()
        print("   ✅ ML Manager инициализирован")

        # 3. Генерируем сигнал вручную
        print("\n📈 ГЕНЕРАЦИЯ ML СИГНАЛА:")

        symbols = ["BTCUSDT"]

        for symbol in symbols:
            try:
                signal = await ml_manager.generate_signal(symbol)

                if signal:
                    print(f"\n   ✅ Сигнал для {symbol}:")
                    print(f"      Направление: {signal.signal_type}")
                    print(f"      Уверенность: {signal.confidence:.2%}")
                    print(f"      Сила: {signal.strength:.4f}")
                    print(f"      Рекомендуемая цена: ${signal.suggested_price}")

                    # Сохраняем сигнал в БД
                    await pool.execute(
                        """
                        INSERT INTO signals
                        (symbol, signal_type, strength, confidence, suggested_price,
                         strategy_name, created_at, extra_data)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                        signal.symbol,
                        signal.signal_type,
                        signal.strength,
                        signal.confidence,
                        signal.suggested_price,
                        "ML_Debug",
                        datetime.now(),
                        "{}",
                    )
                    print("      ✅ Сигнал сохранен в БД")
                else:
                    print(f"   ❌ Нет сигнала для {symbol}")

            except Exception as e:
                print(f"   ❌ Ошибка генерации сигнала для {symbol}: {e}")
                import traceback

                traceback.print_exc()

        # 4. Проверяем сохраненные сигналы
        print("\n📊 ПОСЛЕДНИЕ СИГНАЛЫ В БД:")

        signals = await pool.fetch(
            """
            SELECT
                symbol,
                signal_type,
                strength,
                confidence,
                created_at
            FROM signals
            WHERE created_at > NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC
            LIMIT 5
        """
        )

        if signals:
            for sig in signals:
                print(
                    f"   {sig['symbol']} - {sig['signal_type']} "
                    f"(уверенность: {sig['confidence']:.0%}) "
                    f"в {sig['created_at'].strftime('%H:%M:%S')}"
                )
        else:
            print("   Нет сигналов за последний час")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(debug_ml())
