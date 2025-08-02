#!/usr/bin/env python3
"""
Скрипт для создания и запуска тестового трейдера с ML стратегией PatchTST

Этот скрипт:
1. Подключается к запущенному SystemOrchestrator
2. Создает трейдера с ML стратегией patchtst_strategy
3. Настраивает его для работы с парой BTC/USDT на бирже Bybit
4. Запускает трейдера в тестовом режиме
5. Показывает статус и первые сигналы
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from core.config.config_manager import get_global_config_manager
from core.system.orchestrator import SystemOrchestrator
from core.traders.trader_factory import get_global_trader_factory
from database.models import Signal
from strategies.ml_strategy.patchtst_strategy import PatchTSTStrategy

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MLTraderCreator:
    """Класс для создания и управления ML трейдером"""

    def __init__(self):
        self.config_manager = get_global_config_manager()
        self.orchestrator = None
        self.trader_id = f"ml_trader_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    async def initialize_system(self) -> None:
        """Инициализация системы и оркестратора"""
        logger.info("🚀 Инициализация системы...")

        # Создаем оркестратор
        self.orchestrator = SystemOrchestrator(self.config_manager)

        # Инициализируем оркестратор
        await self.orchestrator.initialize()

        # Запускаем оркестратор
        await self.orchestrator.start()

        logger.info("✅ Система инициализирована и запущена")

    async def register_ml_strategy(self) -> None:
        """Регистрация PatchTST стратегии в фабрике"""
        logger.info("📝 Регистрация ML стратегии...")

        # Получаем фабрику трейдеров
        trader_factory = get_global_trader_factory()

        # Регистрируем PatchTST стратегию
        trader_factory.register_strategy("patchtst_strategy", PatchTSTStrategy)

        logger.info("✅ ML стратегия зарегистрирована")

    async def create_trader_config(self) -> Dict[str, Any]:
        """Создание конфигурации для ML трейдера"""
        config = {
            "trader_id": self.trader_id,
            "enabled": True,
            "exchange": "bybit",
            "exchange_config": {
                "api_key": self.config_manager.get_config(
                    "exchanges.bybit.api_key", ""
                ),
                "api_secret": self.config_manager.get_config(
                    "exchanges.bybit.api_secret", ""
                ),
                "testnet": True,  # Используем testnet для безопасности
                "market_type": "spot",
            },
            "strategy": "patchtst_strategy",
            "strategy_config": {
                "name": "PatchTST_ML",
                "symbol": "BTC/USDT",
                "exchange": "bybit",
                "timeframe": "15m",
                "parameters": {
                    # Пути к моделям
                    "model_path": "models/saved/best_model_20250728_215703.pth",
                    "scaler_path": "models/saved/data_scaler.pkl",
                    "config_path": "models/saved/config.pkl",
                    # Параметры торговли
                    "min_confidence": 0.6,
                    "min_profit_probability": 0.65,
                    "max_risk_threshold": 0.03,
                    "position_sizing_mode": "kelly",
                    # Веса для разных таймфреймов
                    "timeframe_weights": {"15m": 0.3, "1h": 0.3, "4h": 0.3, "12h": 0.1},
                    # Дополнительные параметры
                    "kelly_safety_factor": 0.25,
                    "fixed_risk_pct": 0.02,
                    "min_position_pct": 0.01,
                    "max_position_pct": 0.1,
                    "risk_multiplier": 1.5,
                    "min_risk_reward_ratio": 2.0,
                },
            },
            "risk_management": {
                "type": "basic",
                "max_position_size": 0.1,  # 10% от баланса
                "max_daily_loss": 0.05,  # 5% максимальный дневной убыток
                "max_open_positions": 1,  # Одна позиция за раз
                "stop_loss_percentage": 0.02,  # 2% стоп-лосс
            },
        }

        return config

    async def create_ml_trader(self) -> None:
        """Создание и запуск ML трейдера"""
        logger.info(f"🤖 Создание ML трейдера {self.trader_id}...")

        # Создаем конфигурацию трейдера
        trader_config = await self.create_trader_config()

        # Сохраняем конфигурацию
        self.config_manager.set_trader_config(self.trader_id, trader_config)

        # Создаем трейдера через менеджер
        trader_manager = self.orchestrator.trader_manager

        # Создаем и запускаем трейдера
        await trader_manager.create_trader(self.trader_id)
        await trader_manager.start_trader(self.trader_id)

        logger.info(f"✅ ML трейдер {self.trader_id} создан и запущен")

    async def monitor_trader(self, duration_seconds: int = 300) -> None:
        """Мониторинг работы трейдера"""
        logger.info(f"📊 Мониторинг трейдера в течение {duration_seconds} секунд...")

        start_time = datetime.now()
        signal_count = 0

        while (datetime.now() - start_time).seconds < duration_seconds:
            try:
                # Получаем статус трейдера
                trader_manager = self.orchestrator.trader_manager
                trader_context = trader_manager._traders.get(self.trader_id)

                if trader_context:
                    # Проверяем состояние
                    logger.info(f"Статус трейдера: {trader_context.state}")

                    # Получаем метрики если доступны
                    if hasattr(trader_context, "strategy") and trader_context.strategy:
                        metrics = trader_context.strategy.get_metrics()
                        logger.info(f"Метрики стратегии: {metrics}")

                    # Проверяем новые сигналы
                    from database.connections import AsyncSessionLocal

                    async with AsyncSessionLocal() as db:
                        query = (
                            select(Signal)
                            .where(Signal.created_at > start_time)
                            .order_by(Signal.created_at.desc())
                            .limit(10)
                        )
                        result = await db.execute(query)
                        signals = result.scalars().all()

                        if signals:
                            new_signals = len(signals) - signal_count
                            if new_signals > 0:
                                signal_count = len(signals)
                                logger.info(f"🎯 Новых сигналов: {new_signals}")

                                for signal in signals[:new_signals]:
                                    logger.info(
                                        f"  - {signal.signal_type.value} @ {signal.created_at} | "
                                        f"Уверенность: {signal.confidence:.2%} | "
                                        f"Сила: {signal.strength:.2f}"
                                    )

                # Пауза перед следующей проверкой
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Ошибка при мониторинге: {e}")

        logger.info("✅ Мониторинг завершен")

    async def stop_trader(self) -> None:
        """Остановка трейдера и системы"""
        logger.info("🛑 Остановка трейдера...")

        if self.orchestrator and self.orchestrator.trader_manager:
            # Останавливаем трейдера
            await self.orchestrator.trader_manager.stop_trader(self.trader_id)

            # Удаляем трейдера
            await self.orchestrator.trader_manager.remove_trader(self.trader_id)

        logger.info("✅ Трейдер остановлен")

    async def cleanup(self) -> None:
        """Очистка ресурсов"""
        logger.info("🧹 Очистка ресурсов...")

        if self.orchestrator:
            await self.orchestrator.stop()

        logger.info("✅ Очистка завершена")


async def check_prerequisites() -> bool:
    """Проверка предварительных условий"""
    logger.info("🔍 Проверка предварительных условий...")

    # Проверяем наличие файлов модели
    model_files = {
        "model": Path("models/saved/best_model_20250728_215703.pth"),
        "scaler": Path("models/saved/data_scaler.pkl"),
        "config": Path("models/saved/config.pkl"),
    }

    all_exist = True
    for name, path in model_files.items():
        if path.exists():
            logger.info(f"✅ {name}: {path}")
        else:
            logger.error(f"❌ {name} не найден: {path}")
            all_exist = False

    if not all_exist:
        logger.error("❌ Необходимые файлы модели отсутствуют!")
        logger.info(
            "Скопируйте файлы из проекта LLM TRANSFORM или запустите prepare_model_config.py"
        )
        return False

    # Проверяем подключение к БД
    try:
        from database.connections import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
        logger.info("✅ Подключение к БД успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        return False

    return True


async def main():
    """Основная функция"""
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК ML ТРЕЙДЕРА С СТРАТЕГИЕЙ PatchTST")
    logger.info("=" * 60)

    # Проверяем предварительные условия
    if not await check_prerequisites():
        return

    creator = MLTraderCreator()

    try:
        # Инициализируем систему
        await creator.initialize_system()

        # Регистрируем ML стратегию
        await creator.register_ml_strategy()

        # Создаем и запускаем трейдера
        await creator.create_ml_trader()

        # Мониторим работу трейдера
        await creator.monitor_trader(duration_seconds=300)  # 5 минут

    except KeyboardInterrupt:
        logger.info("⚠️ Получен сигнал прерывания")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)

    finally:
        # Останавливаем трейдера
        await creator.stop_trader()

        # Очищаем ресурсы
        await creator.cleanup()

        logger.info("=" * 60)
        logger.info("✅ РАБОТА ЗАВЕРШЕНА")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
