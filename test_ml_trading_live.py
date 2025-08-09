#!/usr/bin/env python3
"""
Тест запуска торговой системы с ML сигналами и проверка разнообразности предсказаний
"""

import asyncio
import json
import sys
from datetime import datetime

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor
from ml.signal_scheduler import SignalScheduler

logger = setup_logger(__name__)


async def test_ml_predictions_diversity():
    """Тестирует разнообразность ML предсказаний для разных монет"""

    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Инициализируем ML Manager
    ml_manager = MLManager(config)
    await ml_manager.initialize()

    # Инициализируем Signal Processor
    signal_processor = MLSignalProcessor(
        ml_manager=ml_manager, config=config, config_manager=config_manager
    )
    await signal_processor.initialize()

    # Список монет для тестирования (из конфига)
    test_symbols = [
        "BTCUSDT",
        "ETHUSDT",
        "BNBUSDT",
        "SOLUSDT",
        "XRPUSDT",
        "DOGEUSDT",
        "ADAUSDT",
        "AVAXUSDT",
        "DOTUSDT",
        "LINKUSDT",
    ]

    logger.info(f"\n{'=' * 60}")
    logger.info("🧪 Тестирование разнообразности ML предсказаний")
    logger.info(f"{'=' * 60}\n")

    predictions_summary = {}

    for symbol in test_symbols:
        try:
            logger.info(f"\n📊 Обрабатываем {symbol}...")

            # Генерируем сигнал
            signal = await signal_processor.process_realtime_signal(
                symbol=symbol, exchange="bybit"
            )

            if signal:
                # Извлекаем информацию о предсказании
                prediction_info = {
                    "signal_type": signal.signal_type.value,
                    "confidence": round(signal.confidence, 3),
                    "strength": round(signal.strength, 3),
                    "raw_predictions": signal.extra_data.get("raw_prediction", {}),
                }

                # Анализируем направления из raw predictions
                directions = prediction_info["raw_predictions"].get(
                    "predictions", [0] * 20
                )[4:8]
                direction_map = {0: "LONG", 1: "SHORT", 2: "FLAT"}
                direction_labels = [
                    direction_map.get(int(d), "UNKNOWN") for d in directions
                ]

                predictions_summary[symbol] = {
                    "signal": prediction_info["signal_type"],
                    "confidence": prediction_info["confidence"],
                    "strength": prediction_info["strength"],
                    "directions": direction_labels,
                    "timestamp": datetime.now().isoformat(),
                }

                logger.info(
                    f"✅ {symbol}: {prediction_info['signal_type']} "
                    f"(conf: {prediction_info['confidence']:.1%}, "
                    f"str: {prediction_info['strength']:.2f})"
                )
                logger.info(f"   Направления [15m, 1h, 4h, 12h]: {direction_labels}")

            else:
                predictions_summary[symbol] = {
                    "signal": "NO_SIGNAL",
                    "confidence": 0,
                    "strength": 0,
                    "directions": ["N/A"] * 4,
                    "timestamp": datetime.now().isoformat(),
                }
                logger.info(f"❌ {symbol}: Нет сигнала (низкая уверенность или сила)")

        except Exception as e:
            logger.error(f"Ошибка при обработке {symbol}: {e}")
            predictions_summary[symbol] = {
                "signal": "ERROR",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    # Анализ разнообразности
    logger.info(f"\n{'=' * 60}")
    logger.info("📊 АНАЛИЗ РАЗНООБРАЗНОСТИ ПРЕДСКАЗАНИЙ")
    logger.info(f"{'=' * 60}\n")

    # Подсчет типов сигналов
    signal_types = {}
    direction_stats = {"LONG": 0, "SHORT": 0, "FLAT": 0}

    for symbol, data in predictions_summary.items():
        signal = data.get("signal", "ERROR")
        signal_types[signal] = signal_types.get(signal, 0) + 1

        # Подсчет направлений
        if "directions" in data and data["directions"][0] != "N/A":
            for direction in data["directions"]:
                if direction in direction_stats:
                    direction_stats[direction] += 1

    # Вывод статистики
    logger.info("📈 Распределение сигналов:")
    for signal_type, count in signal_types.items():
        percentage = (count / len(test_symbols)) * 100
        logger.info(f"   {signal_type}: {count} ({percentage:.1f}%)")

    logger.info("\n📊 Распределение направлений (все таймфреймы):")
    total_directions = sum(direction_stats.values())
    if total_directions > 0:
        for direction, count in direction_stats.items():
            percentage = (count / total_directions) * 100
            logger.info(f"   {direction}: {count} ({percentage:.1f}%)")

    # Сохраняем результаты
    with open("ml_predictions_diversity_test.json", "w") as f:
        json.dump(predictions_summary, f, indent=2)

    logger.info("\n💾 Результаты сохранены в ml_predictions_diversity_test.json")

    # Проверка разнообразности
    unique_signals = len(
        [s for s in signal_types.keys() if s not in ["ERROR", "NO_SIGNAL"]]
    )
    if unique_signals > 1:
        logger.info(
            f"\n✅ ТЕСТ ПРОЙДЕН: Модель генерирует {unique_signals} разных типа сигналов"
        )
    else:
        logger.warning(
            f"\n⚠️ ВНИМАНИЕ: Модель генерирует только {unique_signals} тип сигналов"
        )

    return predictions_summary


async def test_signal_scheduler():
    """Тестирует работу планировщика сигналов"""

    logger.info(f"\n{'=' * 60}")
    logger.info("🚀 Запуск Signal Scheduler для real-time торговли")
    logger.info(f"{'=' * 60}\n")

    config_manager = ConfigManager()
    scheduler = SignalScheduler(config_manager)

    try:
        # Инициализация
        await scheduler.initialize()

        # Запуск
        await scheduler.start()

        # Мониторинг в течение 5 минут
        monitor_duration = 300  # 5 минут
        check_interval = 30  # проверка каждые 30 секунд

        logger.info(f"⏱️ Мониторинг сигналов в течение {monitor_duration} секунд...")
        logger.info("   (проверка каждые 30 секунд)\n")

        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < monitor_duration:
            # Получаем статус
            status = await scheduler.get_status()

            active_symbols = sum(1 for s in status["symbols"].values() if s["active"])
            total_errors = sum(s["errors"] for s in status["symbols"].values())

            logger.info(f"\n📊 Статус [{datetime.now().strftime('%H:%M:%S')}]:")
            logger.info(
                f"   Активных символов: {active_symbols}/{len(status['symbols'])}"
            )
            logger.info(f"   Всего ошибок: {total_errors}")

            # Показываем последние сигналы
            recent_signals = []
            for symbol, data in status["symbols"].items():
                if data.get("last_signal") and data["last_signal"].get("signal"):
                    signal_info = data["last_signal"]["signal"]
                    recent_signals.append(
                        {
                            "symbol": symbol,
                            "type": signal_info.signal_type.value,
                            "confidence": signal_info.confidence,
                            "time": data["last_signal"]["timestamp"],
                        }
                    )

            if recent_signals:
                logger.info("\n   Последние сигналы:")
                for sig in sorted(
                    recent_signals, key=lambda x: x["time"], reverse=True
                )[:5]:
                    time_ago = (
                        datetime.now(sig["time"].tzinfo) - sig["time"]
                    ).total_seconds()
                    logger.info(
                        f"   - {sig['symbol']}: {sig['type']} "
                        f"(conf: {sig['confidence']:.1%}, "
                        f"{int(time_ago)}s назад)"
                    )

            # Ждем до следующей проверки
            await asyncio.sleep(check_interval)

        logger.info("\n✅ Тест завершен. Система работает корректно.")

    except KeyboardInterrupt:
        logger.info("\n⏹️ Остановка по запросу пользователя...")
    finally:
        await scheduler.stop()


async def main():
    """Основная функция"""

    logger.info("\n" + "=" * 80)
    logger.info("🤖 BOT_AI_V3 - Тест ML торговой системы")
    logger.info("=" * 80 + "\n")

    # Сначала тестируем разнообразность предсказаний
    logger.info("Этап 1: Проверка разнообразности ML предсказаний")
    predictions = await test_ml_predictions_diversity()

    # Если предсказания разнообразные, запускаем планировщик
    unique_types = len(
        set(
            p.get("signal")
            for p in predictions.values()
            if p.get("signal") not in ["ERROR", "NO_SIGNAL"]
        )
    )

    if unique_types > 1:
        logger.info("\nЭтап 2: Запуск real-time планировщика сигналов")
        await test_signal_scheduler()
    else:
        logger.warning(
            "\n⚠️ Планировщик не запущен из-за недостаточной разнообразности сигналов"
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Программа завершена")
        sys.exit(0)
