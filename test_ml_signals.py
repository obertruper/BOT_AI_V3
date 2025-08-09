#!/usr/bin/env python3
"""
Простой тест ML сигналов
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


async def test_signals():
    """Тестирование генерации сигналов"""
    from core.config.config_manager import get_global_config_manager
    from database.connections.postgres import AsyncPGPool
    from trading.signals.ai_signal_generator import AISignalGenerator

    print(f"\n🧪 ТЕСТ ML СИГНАЛОВ - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

    try:
        # Инициализация
        config_manager = get_global_config_manager()
        config = config_manager.get_config()
        pool = await AsyncPGPool.get_pool()

        # Создаем генератор сигналов
        print("\n1️⃣ СОЗДАНИЕ AI SIGNAL GENERATOR:")

        signal_generator = AISignalGenerator(config_manager)
        await signal_generator.initialize()
        print("   ✅ AI Signal Generator инициализирован")

        # Проверяем ML Manager
        if signal_generator.ml_manager:
            print("   ✅ ML Manager активен")
        else:
            print("   ❌ ML Manager не активен!")
            return

        # Генерируем сигналы
        print("\n2️⃣ ГЕНЕРАЦИЯ СИГНАЛОВ:")

        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

        for symbol in symbols:
            print(f"\n   📊 {symbol}:")

            try:
                # Генерируем сигнал
                signal = await signal_generator.generate_signal(symbol)

                if signal:
                    print("      ✅ Сигнал сгенерирован:")
                    print(f"         Тип: {signal.signal_type}")
                    print(f"         Уверенность: {signal.confidence:.2%}")
                    print(f"         Сила: {signal.strength:.4f}")
                    print(f"         Цена: ${signal.suggested_price}")

                    # Сохраняем в БД
                    await pool.execute(
                        """
                        INSERT INTO signals
                        (symbol, signal_type, strength, confidence, suggested_price,
                         strategy_name, created_at, extra_data)
                        VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7)
                    """,
                        signal.symbol,
                        signal.signal_type,
                        signal.strength,
                        signal.confidence,
                        signal.suggested_price,
                        "AI_Signal_Test",
                        "{}",
                    )
                    print("      ✅ Сигнал сохранен в БД")
                else:
                    print("      ❌ Сигнал не сгенерирован (возможно NEUTRAL)")

            except Exception as e:
                print(f"      ❌ Ошибка: {e}")

        # Проверяем периодическую генерацию
        print("\n3️⃣ ЗАПУСК ПЕРИОДИЧЕСКОЙ ГЕНЕРАЦИИ:")

        # Запускаем задачу генерации на 30 секунд
        print("   ⏱️ Мониторинг в течение 30 секунд...")

        generate_task = asyncio.create_task(signal_generator._generate_signals_loop())

        # Ждем 30 секунд
        await asyncio.sleep(30)

        # Останавливаем
        signal_generator._running = False
        generate_task.cancel()

        # Проверяем результаты
        print("\n4️⃣ РЕЗУЛЬТАТЫ:")

        signals = await pool.fetch(
            """
            SELECT
                symbol,
                signal_type,
                confidence,
                created_at
            FROM signals
            WHERE created_at > NOW() - INTERVAL '5 minutes'
                AND strategy_name LIKE '%AI%'
            ORDER BY created_at DESC
            LIMIT 10
        """
        )

        if signals:
            print(f"   ✅ Найдено {len(signals)} сигналов за последние 5 минут:")
            for sig in signals:
                print(
                    f"      {sig['symbol']} - {sig['signal_type']} "
                    f"({sig['confidence']:.0%}) в {sig['created_at'].strftime('%H:%M:%S')}"
                )
        else:
            print("   ❌ Нет сигналов за последние 5 минут")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(test_signals())
