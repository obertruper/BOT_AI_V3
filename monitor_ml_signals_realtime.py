#!/usr/bin/env python3
"""
Мониторинг генерации ML сигналов в реальном времени
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger("signal_monitor")


async def monitor_signals():
    """Мониторит генерацию новых сигналов."""

    print("🔍 МОНИТОРИНГ ML СИГНАЛОВ В РЕАЛЬНОМ ВРЕМЕНИ\n")
    print("Нажмите Ctrl+C для остановки\n")

    last_signal_id = 0
    signal_count = {"LONG": 0, "SHORT": 0, "NEUTRAL": 0}

    # Получаем последний ID сигнала
    result = await AsyncPGPool.fetchval("SELECT MAX(id) FROM signals")
    if result:
        last_signal_id = result

    while True:
        try:
            # Проверяем новые сигналы
            query = """
            SELECT
                id,
                symbol,
                signal_type,
                strength,
                confidence,
                extra_data,
                created_at
            FROM signals
            WHERE id > $1
            ORDER BY id ASC
            """

            new_signals = await AsyncPGPool.fetch(query, last_signal_id)

            if new_signals:
                print(f"\n{'=' * 80}")
                print(f"⚡ Обнаружено {len(new_signals)} новых сигналов!")
                print(f"{'=' * 80}\n")

                for signal in new_signals:
                    last_signal_id = signal["id"]
                    signal_type = signal["signal_type"]
                    signal_count[signal_type] = signal_count.get(signal_type, 0) + 1

                    print(f"📊 Сигнал #{signal['id']}")
                    print(f"   Symbol: {signal['symbol']}")
                    print(f"   Type: {signal_type}")
                    print(f"   Strength: {signal['strength']:.3f}")
                    print(f"   Confidence: {signal['confidence']:.1%}")
                    print(f"   Time: {signal['created_at']}")

                    # Проверяем predictions в extra_data
                    if signal["extra_data"] and "predictions" in signal["extra_data"]:
                        predictions = signal["extra_data"]["predictions"]
                        if "directions_by_timeframe" in predictions:
                            print(
                                f"   Directions: {predictions['directions_by_timeframe']}"
                            )
                        if "direction_score" in predictions:
                            print(
                                f"   Direction score: {predictions['direction_score']:.3f}"
                            )

                    print("-" * 40)

                # Статистика
                total_signals = sum(signal_count.values())
                print(f"\n📈 Статистика сигналов (всего: {total_signals}):")
                for sig_type, count in signal_count.items():
                    if total_signals > 0:
                        percentage = count / total_signals * 100
                        print(f"   {sig_type}: {count} ({percentage:.1f}%)")

                # Проверка разнообразия
                unique_types = sum(1 for count in signal_count.values() if count > 0)
                if unique_types > 1:
                    print("\n✅ Разнообразие сигналов подтверждено!")
                else:
                    print("\n⚠️  Пока только один тип сигналов")

            # Проверяем также логи системы
            ml_status = await AsyncPGPool.fetchrow(
                """
                SELECT COUNT(*) as total_predictions,
                       MAX(created_at) as last_prediction
                FROM processed_market_data
                WHERE created_at > NOW() - INTERVAL '5 minutes'
            """
            )

            if ml_status and ml_status["total_predictions"] > 0:
                print(
                    f"\n🤖 ML активность: {ml_status['total_predictions']} предсказаний за 5 минут"
                )
                if ml_status["last_prediction"]:
                    time_diff = (
                        datetime.now(timezone.utc) - ml_status["last_prediction"]
                    )
                    print(
                        f"   Последнее предсказание: {time_diff.total_seconds():.0f} сек назад"
                    )

            # Ждем 10 секунд
            await asyncio.sleep(10)

        except KeyboardInterrupt:
            print("\n\n👋 Мониторинг остановлен")
            break
        except Exception as e:
            logger.error(f"Ошибка мониторинга: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(monitor_signals())
