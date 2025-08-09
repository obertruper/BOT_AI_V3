#!/usr/bin/env python3
"""
Временное решение для включения ML сигналов
"""

import asyncio
import os
import shutil
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def enable_ml_signals():
    """Включение ML сигналов через настройку конфигурации"""

    print(f"\n🔧 ВКЛЮЧЕНИЕ ML СИГНАЛОВ - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

    try:
        # 1. Обновляем ml_config.yaml для снижения порогов
        print("\n1️⃣ ОБНОВЛЕНИЕ ML КОНФИГУРАЦИИ:")

        import yaml

        ml_config_path = "config/ml/ml_config.yaml"

        # Делаем бэкап
        shutil.copy(ml_config_path, ml_config_path + ".backup")
        print(f"   ✅ Создан бэкап: {ml_config_path}.backup")

        # Читаем конфигурацию
        with open(ml_config_path, "r") as f:
            ml_config = yaml.safe_load(f)

        # Снижаем пороги для тестирования
        old_confidence = ml_config.get("trading", {}).get(
            "min_confidence_threshold", 0.6
        )
        if "trading" not in ml_config:
            ml_config["trading"] = {}
        ml_config["trading"]["min_confidence_threshold"] = 0.3  # Снижаем до 0.3
        ml_config["trading"]["max_daily_trades"] = 100  # Увеличиваем лимит

        # Увеличиваем частоту генерации
        if "signal_generation" not in ml_config:
            ml_config["signal_generation"] = {}
        ml_config["signal_generation"]["interval_seconds"] = (
            30  # Каждые 30 сек вместо 60
        )

        # Сохраняем
        with open(ml_config_path, "w") as f:
            yaml.dump(ml_config, f, default_flow_style=False)

        print(f"   ✅ Минимальная уверенность: {old_confidence:.0%} → 30%")
        print("   ✅ Интервал генерации: 60 сек → 30 сек")

        # 2. Создаем тестовый генератор сигналов
        print("\n2️⃣ СОЗДАНИЕ ТЕСТОВОГО ГЕНЕРАТОРА:")

        test_script = '''#!/usr/bin/env python3
"""
Тестовый генератор ML сигналов
"""

import asyncio
import os
import random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

os.environ['PGPORT'] = '5555'
os.environ['PGUSER'] = 'obertruper'
os.environ['PGDATABASE'] = 'bot_trading_v3'


async def generate_test_signals():
    """Генерация тестовых ML сигналов"""
    from database.connections.postgres import AsyncPGPool

    pool = await AsyncPGPool.get_pool()

    print(f"\\n🤖 ТЕСТОВЫЙ ML ГЕНЕРАТОР ЗАПУЩЕН - {datetime.now().strftime('%H:%M:%S')}")
    print("Нажмите Ctrl+C для остановки\\n")

    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

    try:
        while True:
            # Генерируем сигнал для случайного символа
            symbol = random.choice(symbols)

            # Случайное направление (больше нейтральных для реалистичности)
            rand = random.random()
            if rand < 0.2:  # 20% LONG
                signal_type = 'LONG'
                confidence = random.uniform(0.35, 0.7)
                strength = random.uniform(0.02, 0.05)
            elif rand < 0.4:  # 20% SHORT
                signal_type = 'SHORT'
                confidence = random.uniform(0.35, 0.7)
                strength = random.uniform(0.02, 0.05)
            else:  # 60% NEUTRAL
                signal_type = 'NEUTRAL'
                confidence = random.uniform(0.25, 0.4)
                strength = random.uniform(0.001, 0.02)

            # Получаем текущую цену
            price_data = await pool.fetchrow("""
                SELECT close
                FROM raw_market_data
                WHERE symbol = $1 AND interval_minutes = 15
                ORDER BY datetime DESC
                LIMIT 1
            """, symbol)

            if price_data:
                current_price = float(price_data['close'])

                # Сохраняем сигнал
                await pool.execute("""
                    INSERT INTO signals
                    (symbol, signal_type, strength, confidence, suggested_price,
                     strategy_name, created_at, extra_data)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7)
                """,
                    symbol,
                    signal_type,
                    strength,
                    confidence,
                    current_price,
                    'ML_Test_Generator',
                    '{"test": true}'
                )

                if signal_type != 'NEUTRAL':
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"{'🟢' if signal_type == 'LONG' else '🔴'} "
                          f"{symbol}: {signal_type} (уверенность: {confidence:.0%})")

            # Ждем перед следующим сигналом
            await asyncio.sleep(random.uniform(10, 30))

    except KeyboardInterrupt:
        print("\\n⏹️ Генератор остановлен")
    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(generate_test_signals())
'''

        with open("test_signal_generator.py", "w") as f:
            f.write(test_script)

        os.chmod("test_signal_generator.py", 0o755)
        print("   ✅ Создан test_signal_generator.py")

        # 3. Инструкции
        print("\n3️⃣ ИНСТРУКЦИИ ДЛЯ ТЕСТИРОВАНИЯ:")
        print("\n   1. Перезапустите бота для применения новой конфигурации:")
        print("      python unified_launcher.py")
        print("\n   2. В отдельном терминале запустите тестовый генератор:")
        print("      python test_signal_generator.py")
        print("\n   3. Мониторьте результаты:")
        print("      python monitor_simple.py")

        print("\n⚠️  ВАЖНО: Это временное решение для тестирования!")
        print("   Для восстановления оригинальной конфигурации:")
        print("   cp config/ml/ml_config.yaml.backup config/ml/ml_config.yaml")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(enable_ml_signals())
