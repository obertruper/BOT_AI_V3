#!/usr/bin/env python3
"""
Рабочий скрипт запуска торгового бота с ML
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"data/logs/trading_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
logger = logging.getLogger(__name__)

# Убираем лишние логи
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)


class SimpleTradingBot:
    def __init__(self):
        self.client = None
        self.ml_processor = None
        self.is_running = False
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]

    async def initialize(self):
        """Инициализация компонентов"""
        try:
            # Загружаем конфигурацию
            from dotenv import load_dotenv

            load_dotenv()

            api_key = os.getenv("BYBIT_API_KEY")
            api_secret = os.getenv("BYBIT_API_SECRET")

            if not api_key or not api_secret:
                logger.error("❌ API ключи не найдены в .env")
                return False

            # Создаем клиент биржи
            logger.info("📡 Подключение к Bybit...")
            from exchanges.bybit.client import BybitClient

            self.client = BybitClient(api_key, api_secret, sandbox=False)

            # Проверяем подключение
            if await self.client.test_connection():
                logger.info("✅ Успешно подключено к Bybit")
            else:
                logger.error("❌ Не удалось подключиться к Bybit")
                return False

            # Инициализируем ML систему
            logger.info("🧠 Инициализация ML системы...")
            from core.config.config_manager import ConfigManager
            from ml.ml_manager import MLManager
            from ml.ml_signal_processor import MLSignalProcessor

            config_manager = ConfigManager()
            ml_config = config_manager.get_ml_config()

            ml_manager = MLManager(config=ml_config)
            self.ml_processor = MLSignalProcessor(
                ml_manager=ml_manager, config={"symbols": self.symbols}
            )

            logger.info("✅ ML система инициализирована")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def get_market_data(self, symbol: str):
        """Получение рыночных данных"""
        try:
            # Получаем свечи за последние 24 часа
            end_time = datetime.now()
            start_time = end_time - timedelta(days=1)

            candles = await self.client.get_klines(
                symbol=symbol,
                interval="15",
                start_time=start_time,
                end_time=end_time,  # 15 минут
            )

            if candles and len(candles) > 0:
                logger.info(f"📊 Получено {len(candles)} свечей для {symbol}")
                return candles
            else:
                logger.warning(f"⚠️ Нет данных для {symbol}")
                return None

        except Exception as e:
            logger.error(f"❌ Ошибка получения данных {symbol}: {e}")
            return None

    async def generate_signals(self):
        """Генерация торговых сигналов"""
        while self.is_running:
            try:
                logger.info("🔄 Генерация сигналов...")

                for symbol in self.symbols:
                    # Получаем рыночные данные
                    candles = await self.get_market_data(symbol)

                    if candles:
                        # Здесь можно добавить ML предсказания
                        last_price = candles[-1].close_price
                        logger.info(f"💰 {symbol}: ${last_price}")

                        # Простая логика для примера
                        if len(candles) > 20:
                            sma20 = sum([c.close_price for c in candles[-20:]]) / 20

                            if last_price > sma20 * 1.01:  # Цена выше SMA20 на 1%
                                logger.info(
                                    f"📈 {symbol}: СИГНАЛ НА ПОКУПКУ (цена ${last_price} > SMA20 ${sma20:.2f})"
                                )
                            elif last_price < sma20 * 0.99:  # Цена ниже SMA20 на 1%
                                logger.info(
                                    f"📉 {symbol}: СИГНАЛ НА ПРОДАЖУ (цена ${last_price} < SMA20 ${sma20:.2f})"
                                )

                # Ждем минуту до следующей проверки
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"❌ Ошибка генерации сигналов: {e}")
                await asyncio.sleep(10)

    async def start(self):
        """Запуск бота"""
        logger.info("🚀 Запуск торгового бота...")

        if not await self.initialize():
            logger.error("❌ Не удалось инициализировать бота")
            return

        self.is_running = True

        logger.info("✅ Бот запущен и работает!")
        logger.info(f"📊 Отслеживаемые пары: {', '.join(self.symbols)}")
        logger.info("🛑 Для остановки нажмите Ctrl+C")

        # Запускаем генерацию сигналов
        await self.generate_signals()

    async def stop(self):
        """Остановка бота"""
        logger.info("⏸️ Остановка бота...")
        self.is_running = False


async def main():
    """Главная функция"""
    bot = SimpleTradingBot()

    # Обработчик сигналов
    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info("🛑 Получен сигнал остановки...")
        stop_event.set()
        bot.is_running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Запускаем бота
    bot_task = asyncio.create_task(bot.start())

    # Ждем сигнал остановки
    await stop_event.wait()

    # Останавливаем бота
    await bot.stop()
    bot_task.cancel()

    try:
        await bot_task
    except asyncio.CancelledError:
        pass

    logger.info("👋 Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
