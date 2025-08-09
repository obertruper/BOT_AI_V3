#!/usr/bin/env python3
"""
Финальная проверка ML системы после всех исправлений
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from ml.ml_manager import MLManager

logger = setup_logger("final_check")


async def final_check():
    """Финальная проверка ML системы."""

    print("🏁 ФИНАЛЬНАЯ ПРОВЕРКА ML СИСТЕМЫ\n")

    # 1. Проверка базы данных
    print("1️⃣ Проверка последних сигналов в БД...")

    # Получаем сигналы за последний час
    query = """
    SELECT
        id,
        symbol,
        signal_type,
        strength,
        confidence,
        created_at,
        extra_data
    FROM signals
    WHERE created_at > NOW() - INTERVAL '1 hour'
    ORDER BY created_at DESC
    LIMIT 20
    """

    signals = await AsyncPGPool.fetch(query)

    if signals:
        signal_types = {}
        for sig in signals:
            sig_type = sig["signal_type"]
            signal_types[sig_type] = signal_types.get(sig_type, 0) + 1

        print(f"✅ Найдено {len(signals)} сигналов за последний час")
        print(f"   Распределение: {signal_types}")

        # Проверка разнообразия
        if len(signal_types) > 1:
            print("   ✅ Разнообразие сигналов подтверждено!")
        else:
            print("   ⚠️  Все сигналы одного типа")
    else:
        print("❌ Нет сигналов за последний час")

    # 2. Тест ML предсказания
    print("\n2️⃣ Тестирование ML предсказаний...")

    config = {"ml": {"model": {"device": "cuda"}, "model_directory": "models/saved"}}

    ml_manager = MLManager(config)
    await ml_manager.initialize()

    # Загружаем тестовые данные
    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    predictions_summary = []

    for symbol in test_symbols:
        query = f"""
        SELECT * FROM raw_market_data
        WHERE symbol = '{symbol}'
        ORDER BY datetime DESC
        LIMIT 100
        """

        raw_data = await AsyncPGPool.fetch(query)

        if len(raw_data) >= 96:
            import pandas as pd

            df_data = [dict(row) for row in raw_data]
            df = pd.DataFrame(df_data)

            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            df = df.sort_values("datetime")

            try:
                prediction = await ml_manager.predict(df)

                directions = prediction.get("predictions", {}).get(
                    "directions_by_timeframe", []
                )

                predictions_summary.append(
                    {
                        "symbol": symbol,
                        "signal_type": prediction["signal_type"],
                        "confidence": prediction["confidence"],
                        "directions": directions,
                    }
                )

                print(f"\n   {symbol}:")
                print(f"   Signal: {prediction['signal_type']}")
                print(f"   Confidence: {prediction['confidence']:.1%}")
                print(f"   Directions: {directions}")

            except Exception as e:
                logger.error(f"Ошибка предсказания для {symbol}: {e}")

    # Анализ результатов
    if predictions_summary:
        unique_signals = set(p["signal_type"] for p in predictions_summary)
        all_directions = []
        for p in predictions_summary:
            all_directions.extend(p.get("directions", []))

        unique_directions = set(all_directions)

        print("\n📊 Итоги тестирования:")
        print(
            f"   Уникальных типов сигналов: {len(unique_signals)} ({list(unique_signals)})"
        )
        print(
            f"   Уникальных направлений: {len(unique_directions)} ({list(unique_directions)})"
        )

        if len(unique_signals) > 1 and len(unique_directions) > 1:
            print("   ✅ ML система работает корректно - предсказания разнообразны!")
        else:
            print("   ⚠️  Предсказания недостаточно разнообразны")

    # 3. Проверка процессов
    print("\n3️⃣ Проверка запущенных процессов...")

    import subprocess

    result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    processes = result.stdout

    required_processes = ["unified_launcher", "main.py", "web/launcher.py"]
    found_processes = []

    for proc in required_processes:
        if proc in processes and "grep" not in processes:
            found_processes.append(proc)

    print(f"   Найдено процессов: {len(found_processes)}/{len(required_processes)}")
    for proc in found_processes:
        print(f"   ✅ {proc}")

    missing = set(required_processes) - set(found_processes)
    for proc in missing:
        print(f"   ❌ {proc}")

    # 4. Итоговый вердикт
    print("\n" + "=" * 60)
    print("🏁 ИТОГОВЫЙ ВЕРДИКТ:")
    print("=" * 60)

    issues = []

    if not signals:
        issues.append("Нет новых сигналов в БД")
    elif len(signal_types) == 1:
        issues.append("Все сигналы одного типа")

    if len(unique_signals) == 1:
        issues.append("ML предсказания не разнообразны")

    if len(found_processes) < len(required_processes):
        issues.append("Не все процессы запущены")

    if not issues:
        print("✅ ВСЕ СИСТЕМЫ РАБОТАЮТ КОРРЕКТНО!")
        print("✅ ML предсказания разнообразны")
        print("✅ Исправление интерпретации direction outputs успешно!")
    else:
        print("⚠️  Обнаружены проблемы:")
        for issue in issues:
            print(f"   - {issue}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(final_check())
