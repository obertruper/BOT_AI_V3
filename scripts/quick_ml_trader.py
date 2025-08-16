#!/usr/bin/env python3
"""
Упрощенный скрипт для быстрого запуска ML трейдера
Использует минимальную конфигурацию для демонстрации
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.config_manager import ConfigManager
from core.traders.trader_factory import TraderFactory
from core.traders.trader_manager import TraderManager
from strategies.ml_strategy.patchtst_strategy import PatchTSTStrategy

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def quick_start():
    """Быстрый запуск ML трейдера"""

    logger.info("🚀 Быстрый запуск ML трейдера...")

    # Создаем минимальную конфигурацию
    config_manager = ConfigManager()

    # Создаем фабрику и менеджер трейдеров
    trader_factory = TraderFactory(config_manager)
    trader_manager = TraderManager(config_manager, trader_factory)

    # Регистрируем PatchTST стратегию
    trader_factory.register_strategy("patchtst_strategy", PatchTSTStrategy)
    logger.info("✅ ML стратегия зарегистрирована")

    # Инициализируем менеджер
    await trader_manager.initialize()
    await trader_manager.start()
    logger.info("✅ Менеджер трейдеров запущен")

    # Создаем конфигурацию трейдера
    trader_id = f"ml_demo_{datetime.now().strftime('%H%M%S')}"
    trader_config = {
        "trader_id": trader_id,
        "enabled": True,
        "exchange": "bybit",
        "exchange_config": {
            "api_key": "demo_key",
            "api_secret": "demo_secret",
            "testnet": True,
            "market_type": "spot",
        },
        "strategy": "patchtst_strategy",
        "strategy_config": {
            "name": "PatchTST_Demo",
            "symbol": "BTC/USDT",
            "exchange": "bybit",
            "timeframe": "15m",
            "parameters": {
                "model_path": "models/saved/best_model_20250728_215703.pth",
                "scaler_path": "models/saved/data_scaler.pkl",
                "config_path": "models/saved/config.pkl",
                "min_confidence": 0.5,
                "min_profit_probability": 0.6,
            },
        },
    }

    # Сохраняем конфигурацию
    config_manager.set_trader_config(trader_id, trader_config)

    # Создаем и запускаем трейдера
    try:
        await trader_manager.create_trader(trader_id)
        await trader_manager.start_trader(trader_id)
        logger.info(f"✅ ML трейдер {trader_id} запущен")

        # Работаем 2 минуты
        logger.info("⏳ Мониторинг работы трейдера (2 минуты)...")
        await asyncio.sleep(120)

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

    finally:
        # Останавливаем трейдера
        logger.info("🛑 Остановка трейдера...")
        await trader_manager.stop_trader(trader_id)
        await trader_manager.stop()
        logger.info("✅ Работа завершена")


if __name__ == "__main__":
    print("=" * 50)
    print("🤖 ДЕМО ЗАПУСК ML ТРЕЙДЕРА")
    print("=" * 50)
    print("Это упрощенная демонстрация работы ML стратегии.")
    print("Для полноценной работы используйте create_ml_trader.py")
    print("=" * 50)

    asyncio.run(quick_start())
