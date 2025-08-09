#!/usr/bin/env python3
"""
Полный тест торгового потока BOT_AI_V3
Тестирует весь цикл от ML сигналов до исполнения ордеров на Bybit
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Безопасные параметры для тестирования
TEST_CONFIG = {
    "max_position_size_usdt": 10,  # Максимум $10 на позицию
    "max_positions": 2,  # Максимум 2 позиции одновременно
    "stop_loss_percent": 2,  # 2% стоп-лосс
    "take_profit_percent": 3,  # 3% тейк-профит
    "test_symbols": ["BTCUSDT", "ETHUSDT"],  # Только основные пары
    "dry_run": True,  # Начинаем с dry-run режима
}


class FullTradingFlowTest:
    def __init__(self):
        self.orchestrator = None
        self.exchange_client = None
        self.ml_signal_count = 0
        self.order_count = 0
        self.trade_count = 0
        self.pnl = Decimal("0")

    async def check_prerequisites(self):
        """Проверка всех предварительных условий"""
        logger.info("=" * 80)
        logger.info("🔍 ПРОВЕРКА ПРЕДВАРИТЕЛЬНЫХ УСЛОВИЙ")
        logger.info("=" * 80)

        checks_passed = True

        # 1. Проверка переменных окружения
        logger.info("\n1️⃣ Проверка API ключей...")
        api_key = os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("BYBIT_API_SECRET")

        if not api_key or not api_secret:
            logger.error("❌ API ключи Bybit не найдены в .env")
            return False

        logger.info("✅ API ключи найдены")

        # 2. Проверка PostgreSQL
        logger.info("\n2️⃣ Проверка PostgreSQL...")
        try:
            import subprocess

            result = subprocess.run(
                [
                    "psql",
                    "-p",
                    "5555",
                    "-U",
                    "obertruper",
                    "-d",
                    "bot_trading_v3",
                    "-c",
                    "SELECT 1;",
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "PGPASSWORD": os.getenv("PGPASSWORD", "")},
            )

            if result.returncode == 0:
                logger.info("✅ PostgreSQL доступен на порту 5555")
            else:
                logger.error("❌ PostgreSQL недоступен")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка проверки PostgreSQL: {e}")
            return False

        # 3. Проверка Python модулей
        logger.info("\n3️⃣ Проверка зависимостей...")
        try:
            import ccxt
            import numpy
            import pandas
            import torch

            logger.info("✅ Все необходимые модули установлены")
        except ImportError as e:
            logger.error(f"❌ Отсутствуют модули: {e}")
            return False

        return checks_passed

    async def test_bybit_connection(self):
        """Тестирование подключения к Bybit"""
        logger.info("\n" + "=" * 80)
        logger.info("🔗 ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ К BYBIT")
        logger.info("=" * 80)

        try:
            from exchanges.factory import ExchangeFactory

            factory = ExchangeFactory()
            self.exchange_client = factory.create_client(
                "bybit", os.getenv("BYBIT_API_KEY"), os.getenv("BYBIT_API_SECRET")
            )

            # Подключение
            connected = await self.exchange_client.connect()
            if not connected:
                logger.error("❌ Не удалось подключиться к Bybit")
                return False

            logger.info("✅ Подключение к Bybit успешно")

            # Проверка баланса
            logger.info("\n💰 Проверка баланса...")
            balances = await self.exchange_client.get_balances()

            usdt_balance = balances.get("USDT", 0)
            logger.info(f"   USDT баланс: ${usdt_balance}")

            if float(usdt_balance) < TEST_CONFIG["max_position_size_usdt"]:
                logger.warning(
                    f"⚠️ Недостаточно USDT для теста (нужно минимум ${TEST_CONFIG['max_position_size_usdt']})"
                )

            # Проверка рыночных данных
            logger.info("\n📊 Проверка рыночных данных...")
            for symbol in TEST_CONFIG["test_symbols"]:
                ticker = await self.exchange_client.get_ticker(symbol)
                logger.info(f"   {symbol}: ${ticker.last_price}")

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка при тестировании Bybit: {e}")
            return False

    async def initialize_trading_system(self):
        """Инициализация торговой системы"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 ИНИЦИАЛИЗАЦИЯ ТОРГОВОЙ СИСТЕМЫ")
        logger.info("=" * 80)

        try:
            from core.config.config_manager import ConfigManager
            from core.system.orchestrator import SystemOrchestrator

            # Создаем конфигурацию для теста
            config_manager = ConfigManager()
            config = config_manager.get_config()

            # Применяем тестовые параметры
            config["risk_management"]["position"]["max_position_size"] = (
                TEST_CONFIG["max_position_size_usdt"] / 100000
            )  # В процентах от капитала
            config["risk_management"]["position"]["default_stop_loss"] = (
                TEST_CONFIG["stop_loss_percent"] / 100
            )
            config["risk_management"]["position"]["default_take_profit"] = (
                TEST_CONFIG["take_profit_percent"] / 100
            )
            config["risk_management"]["global"]["max_open_positions"] = TEST_CONFIG[
                "max_positions"
            ]

            # Ограничиваем символы для теста
            config["ml"]["symbols"] = TEST_CONFIG["test_symbols"]

            # Создаем оркестратор
            self.orchestrator = SystemOrchestrator()

            # Инициализация
            logger.info("🔄 Инициализация компонентов...")
            await self.orchestrator.initialize()

            # Проверяем статус компонентов
            status = await self.orchestrator.get_system_status()
            logger.info("\n📊 Статус компонентов:")
            for component, is_ready in status.items():
                status_icon = "✅" if is_ready else "❌"
                logger.info(f"   {status_icon} {component}")

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации системы: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def start_ml_signal_generation(self):
        """Запуск ML генерации сигналов"""
        logger.info("\n" + "=" * 80)
        logger.info("🤖 ЗАПУСК ML ГЕНЕРАЦИИ СИГНАЛОВ")
        logger.info("=" * 80)

        try:
            # Запускаем систему
            await self.orchestrator.start()
            logger.info("✅ Торговая система запущена")

            # Ждем первых сигналов
            logger.info("\n⏳ Ожидание ML сигналов...")
            logger.info("   (ML генерирует сигналы каждую минуту)")

            # Мониторим сигналы в течение 3 минут
            start_time = datetime.now()
            monitoring_duration = 180  # 3 минуты

            while (datetime.now() - start_time).total_seconds() < monitoring_duration:
                # Получаем статистику
                if hasattr(self.orchestrator, "trading_engine"):
                    metrics = self.orchestrator.trading_engine.get_metrics()

                    if metrics.signals_processed > self.ml_signal_count:
                        new_signals = metrics.signals_processed - self.ml_signal_count
                        self.ml_signal_count = metrics.signals_processed
                        logger.info(f"\n🎯 Новых ML сигналов: {new_signals}")
                        logger.info(f"   Всего обработано: {self.ml_signal_count}")

                    if metrics.orders_executed > self.order_count:
                        new_orders = metrics.orders_executed - self.order_count
                        self.order_count = metrics.orders_executed
                        logger.info(f"\n📝 Новых ордеров: {new_orders}")
                        logger.info(f"   Всего исполнено: {self.order_count}")

                await asyncio.sleep(10)  # Проверяем каждые 10 секунд

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка при генерации сигналов: {e}")
            return False

    async def monitor_trades(self):
        """Мониторинг исполненных сделок"""
        logger.info("\n" + "=" * 80)
        logger.info("📈 МОНИТОРИНГ ТОРГОВЛИ")
        logger.info("=" * 80)

        try:
            # Получаем активные позиции
            if self.exchange_client:
                positions = await self.exchange_client.get_positions()

                active_positions = [
                    p for p in positions if float(p.get("size", 0)) != 0
                ]

                if active_positions:
                    logger.info(f"\n💼 Активные позиции ({len(active_positions)}):")
                    for pos in active_positions:
                        symbol = pos.get("symbol")
                        size = pos.get("size")
                        entry_price = pos.get("entry_price")
                        unrealized_pnl = pos.get("unrealized_pnl", 0)

                        logger.info(f"   {symbol}: {size} @ ${entry_price}")
                        logger.info(f"   Нереализованный PnL: ${unrealized_pnl}")
                else:
                    logger.info("\n💤 Нет активных позиций")

            # Получаем последние ордера из БД
            from sqlalchemy import desc, select

            from database.connections import get_async_db
            from database.models.base_models import Order

            async with get_async_db() as db:
                result = await db.execute(
                    select(Order).order_by(desc(Order.created_at)).limit(5)
                )
                recent_orders = result.scalars().all()

                if recent_orders:
                    logger.info(f"\n📋 Последние ордера ({len(recent_orders)}):")
                    for order in recent_orders:
                        logger.info(
                            f"   {order.symbol} {order.side.value} "
                            f"{order.quantity} @ {order.price or 'MARKET'} "
                            f"- {order.status.value}"
                        )

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка мониторинга: {e}")
            return False

    async def run_full_test(self):
        """Запуск полного теста"""
        logger.info("\n" + "=" * 80)
        logger.info("🎯 ЗАПУСК ПОЛНОГО ТЕСТА ТОРГОВЛИ")
        logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        logger.info("\n⚙️ Параметры теста:")
        logger.info(f"   Режим: {'DRY RUN' if TEST_CONFIG['dry_run'] else 'LIVE'}")
        logger.info(
            f"   Макс. размер позиции: ${TEST_CONFIG['max_position_size_usdt']}"
        )
        logger.info(f"   Макс. позиций: {TEST_CONFIG['max_positions']}")
        logger.info(f"   Stop Loss: {TEST_CONFIG['stop_loss_percent']}%")
        logger.info(f"   Take Profit: {TEST_CONFIG['take_profit_percent']}%")
        logger.info(f"   Символы: {', '.join(TEST_CONFIG['test_symbols'])}")

        # 1. Проверка предварительных условий
        if not await self.check_prerequisites():
            logger.error("\n❌ Предварительные проверки не пройдены!")
            return

        # 2. Тест подключения к Bybit
        if not await self.test_bybit_connection():
            logger.error("\n❌ Не удалось подключиться к Bybit!")
            return

        # 3. Инициализация торговой системы
        if not await self.initialize_trading_system():
            logger.error("\n❌ Не удалось инициализировать систему!")
            return

        # 4. Запуск ML генерации сигналов
        if not await self.start_ml_signal_generation():
            logger.error("\n❌ Ошибка при генерации сигналов!")
            return

        # 5. Мониторинг торговли
        logger.info("\n🔄 Продолжение мониторинга...")
        logger.info("   (Нажмите Ctrl+C для остановки)")

        try:
            while True:
                await self.monitor_trades()
                await asyncio.sleep(30)  # Обновляем каждые 30 секунд

        except KeyboardInterrupt:
            logger.info("\n⏹️ Остановка по запросу пользователя...")

        # 6. Остановка системы
        if self.orchestrator:
            await self.orchestrator.stop()
            logger.info("✅ Система остановлена")

        # 7. Финальный отчет
        logger.info("\n" + "=" * 80)
        logger.info("📊 ИТОГОВЫЙ ОТЧЕТ")
        logger.info("=" * 80)
        logger.info(f"🎯 ML сигналов обработано: {self.ml_signal_count}")
        logger.info(f"📝 Ордеров исполнено: {self.order_count}")
        logger.info(f"💰 Итоговый PnL: ${self.pnl}")
        logger.info("\n✅ Тест завершен успешно!")


async def main():
    """Основная функция"""
    test = FullTradingFlowTest()

    # Проверяем аргументы командной строки
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # Автоматический режим для тестирования
        TEST_CONFIG["dry_run"] = True
        logger.info("🤖 Автоматический запуск в режиме DRY RUN")
    else:
        # Интерактивный режим
        print("\n" + "=" * 60)
        print("🎯 BOT_AI_V3 - Полный тест торговли")
        print("=" * 60)
        print("\nВыберите режим запуска:")
        print("1. DRY RUN (без реальных ордеров)")
        print("2. LIVE (реальная торговля с минимальными суммами)")
        print("3. Выход")

        try:
            choice = input("\nВаш выбор (1-3): ").strip()
        except EOFError:
            # Если нет интерактивного ввода, используем DRY RUN
            logger.info("📋 Нет интерактивного ввода, используем DRY RUN режим")
            choice = "1"

        if choice == "1":
            TEST_CONFIG["dry_run"] = True
            logger.info("✅ Выбран режим DRY RUN")
        elif choice == "2":
            TEST_CONFIG["dry_run"] = False
            logger.warning("⚠️ ВНИМАНИЕ: Будут созданы РЕАЛЬНЫЕ ордера!")
            try:
                confirm = input("Вы уверены? (yes/no): ").strip().lower()
                if confirm != "yes":
                    logger.info("❌ Отменено пользователем")
                    return
            except EOFError:
                logger.info("❌ Требуется подтверждение в интерактивном режиме")
                return
        else:
            logger.info("👋 Выход")
            return

    await test.run_full_test()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Завершение работы")
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
