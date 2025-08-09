#!/usr/bin/env python3
"""
Простой тест ML системы
"""

import asyncio

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.signal_scheduler import SignalScheduler

logger = setup_logger(__name__)


async def main():
    """Запускаем планировщик сигналов"""

    logger.info("\n" + "=" * 80)
    logger.info("🤖 BOT_AI_V3 - Запуск ML торговли")
    logger.info("=" * 80 + "\n")

    config_manager = ConfigManager()
    scheduler = SignalScheduler(config_manager)

    try:
        # Инициализация
        await scheduler.initialize()

        # Запуск
        await scheduler.start()

        # Мониторим 2 минуты чтобы увидеть результаты
        logger.info("⏱️ Мониторинг сигналов в течение 2 минут...")

        for i in range(4):  # 4 раза по 30 секунд
            await asyncio.sleep(30)

            # Получаем статус
            status = await scheduler.get_status()

            logger.info(f"\n📊 Статус после {(i + 1) * 30} секунд:")

            # Показываем последние сигналы
            signals_count = 0
            for symbol, data in status["symbols"].items():
                if data.get("last_signal") and data["last_signal"].get("signal"):
                    signals_count += 1
                    sig = data["last_signal"]["signal"]
                    logger.info(
                        f"   {symbol}: {sig.signal_type.value} (conf: {sig.confidence:.1%})"
                    )

            if signals_count == 0:
                logger.info("   Пока нет сигналов...")
            else:
                logger.info(f"   Всего сгенерировано сигналов: {signals_count}")

    except KeyboardInterrupt:
        logger.info("\n⏹️ Остановка...")
    finally:
        await scheduler.stop()
        logger.info("✅ Завершено")


if __name__ == "__main__":
    asyncio.run(main())
