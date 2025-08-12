#!/usr/bin/env python3
"""
Запуск торговли по 10 криптовалютам с генерацией сигналов каждую минуту
Адаптация системы из BOT_AI_V2 для V3
"""

import asyncio
import logging
import os
import signal
from datetime import datetime
from typing import Dict, Optional

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/multi_crypto_trading.log"),
    ],
)
logger = logging.getLogger("MultiCryptoTrading")

from core.config.config_manager import ConfigManager
from core.shared_context import SharedContext

# Импорты из V3
from core.system.orchestrator import SystemOrchestrator
from exchanges.factory import ExchangeFactory
from risk_management.manager import RiskManager
from strategies.manager import StrategyManager
from trading.engine import TradingEngine

# Список из 10 криптовалют для торговли
CRYPTO_SYMBOLS = [
    "BTCUSDT",  # Bitcoin
    "ETHUSDT",  # Ethereum
    "BNBUSDT",  # Binance Coin
    "SOLUSDT",  # Solana
    "XRPUSDT",  # Ripple
    "ADAUSDT",  # Cardano
    "DOGEUSDT",  # Dogecoin
    "DOTUSDT",  # Polkadot
    "LINKUSDT",  # Chainlink
    "MATICUSDT",  # Polygon
]


class MultiCryptoTradingSystem:
    """Система торговли по нескольким криптовалютам"""

    def __init__(self):
        self.orchestrator: Optional[SystemOrchestrator] = None
        self.config_manager: Optional[ConfigManager] = None
        self.trading_engine: Optional[TradingEngine] = None
        self.strategy_manager: Optional[StrategyManager] = None
        self.exchange = None
        self.risk_manager: Optional[RiskManager] = None
        self.shared_context: Optional[SharedContext] = None
        self.running = False
        self.signal_generation_task = None

    async def initialize(self):
        """Инициализация системы"""
        try:
            logger.info("=" * 60)
            logger.info("  ЗАПУСК MULTI-CRYPTO TRADING SYSTEM")
            logger.info("=" * 60)

            # Инициализация конфигурации
            self.config_manager = ConfigManager()
            await self.config_manager.initialize()

            # Общий контекст
            self.shared_context = SharedContext()

            # Создание биржи (Bybit)
            exchange_config = {
                "api_key": os.getenv("BYBIT_API_KEY"),
                "api_secret": os.getenv("BYBIT_API_SECRET"),
                "testnet": os.getenv("BYBIT_TESTNET", "false").lower() == "true",
            }

            factory = ExchangeFactory()
            self.exchange = await factory.create_and_connect(
                exchange_type="bybit",
                api_key=exchange_config["api_key"],
                api_secret=exchange_config["api_secret"],
                sandbox=exchange_config.get("testnet", False),
            )
            await self.exchange.initialize()

            # Проверка баланса
            balance = await self.exchange.get_balance()
            usdt_balance = balance.get("USDT", 0)
            logger.info(f"💰 Баланс USDT: {usdt_balance:.2f}")

            # Инициализация компонентов
            self.trading_engine = TradingEngine(self.shared_context)
            self.strategy_manager = StrategyManager(self.shared_context)
            self.risk_manager = RiskManager(self.shared_context)

            # Инициализация оркестратора
            self.orchestrator = SystemOrchestrator(self.shared_context)
            await self.orchestrator.initialize()

            # Регистрация компонентов
            self.orchestrator.register_component("trading_engine", self.trading_engine)
            self.orchestrator.register_component(
                "strategy_manager", self.strategy_manager
            )
            self.orchestrator.register_component("risk_manager", self.risk_manager)
            self.orchestrator.register_component("exchange", self.exchange)

            logger.info("✅ Система инициализирована успешно")

            # Вывод информации о торговле
            logger.info("\n📊 Параметры торговли:")
            logger.info(
                f"   Биржа: Bybit {'(Testnet)' if exchange_config['testnet'] else '(Mainnet)'}"
            )
            logger.info(f"   Количество валют: {len(CRYPTO_SYMBOLS)}")
            logger.info("   Интервал сигналов: 60 секунд")
            logger.info(f"   Leverage: {os.getenv('DEFAULT_LEVERAGE', 5)}x")
            logger.info("   Risk per trade: 2%")

            logger.info("\n💹 Торговые пары:")
            for symbol in CRYPTO_SYMBOLS:
                logger.info(f"   - {symbol}")

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {str(e)}")
            return False

    async def generate_signals(self):
        """Генерация торговых сигналов каждую минуту"""
        while self.running:
            try:
                logger.info("\n" + "=" * 50)
                logger.info(
                    f"🔄 Генерация сигналов - {datetime.now().strftime('%H:%M:%S')}"
                )

                # Получаем текущие цены для всех символов
                for symbol in CRYPTO_SYMBOLS:
                    try:
                        # Получаем данные о рынке
                        ticker = await self.exchange.get_ticker(symbol)
                        if not ticker:
                            continue

                        current_price = ticker.get("last", 0)
                        logger.info(f"\n📈 {symbol}: ${current_price:.4f}")

                        # Проверяем открытые позиции
                        positions = await self.exchange.get_positions(symbol)

                        # Генерируем сигнал через стратегию
                        # Здесь можно добавить вашу стратегию или использовать индикаторы
                        signal = await self._analyze_market(symbol, ticker)

                        if signal:
                            logger.info(
                                f"   🎯 Сигнал: {signal['action']} (сила: {signal['strength']})"
                            )

                            # Проверка риск-менеджмента
                            if await self.risk_manager.can_open_position(symbol):
                                # Обработка сигнала через trading engine
                                await self.trading_engine.process_signal(signal)
                            else:
                                logger.warning("   ⚠️ Риск-менеджмент блокирует сделку")

                    except Exception as e:
                        logger.error(f"   ❌ Ошибка обработки {symbol}: {str(e)}")

                # Ждем 60 секунд до следующей генерации
                logger.info("\n⏳ Ожидание 60 секунд до следующего цикла...")
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"❌ Ошибка в цикле генерации сигналов: {str(e)}")
                await asyncio.sleep(60)

    async def _analyze_market(self, symbol: str, ticker: Dict) -> Optional[Dict]:
        """Простой анализ рынка для генерации сигналов"""
        # Это базовый пример - замените на вашу стратегию
        # Можно использовать индикаторы RSI, EMA, MACD и т.д.

        try:
            # Получаем исторические данные (свечи)
            # candles = await self.exchange.get_candles(symbol, '5m', limit=100)

            # Простая логика на основе изменения цены за 24ч
            change_24h = ticker.get("percentage", 0)

            # Генерация сигнала на основе простых условий
            if change_24h > 5:  # Рост более 5% за 24ч
                return {
                    "symbol": symbol,
                    "action": "SELL",  # Продаем на росте
                    "strength": "MEDIUM",
                    "price": ticker["last"],
                    "reason": f"Рост {change_24h:.2f}% за 24ч",
                }
            elif change_24h < -5:  # Падение более 5% за 24ч
                return {
                    "symbol": symbol,
                    "action": "BUY",  # Покупаем на падении
                    "strength": "MEDIUM",
                    "price": ticker["last"],
                    "reason": f"Падение {change_24h:.2f}% за 24ч",
                }

            return None

        except Exception as e:
            logger.error(f"Ошибка анализа {symbol}: {str(e)}")
            return None

    async def start(self):
        """Запуск системы"""
        if not await self.initialize():
            return False

        self.running = True

        try:
            # Запуск оркестратора
            await self.orchestrator.start()

            # Запуск генерации сигналов
            self.signal_generation_task = asyncio.create_task(self.generate_signals())

            logger.info("\n✅ Система запущена и работает!")
            logger.info("Нажмите Ctrl+C для остановки")

            # Ожидание завершения
            await self.signal_generation_task

        except KeyboardInterrupt:
            logger.info("\n⚠️ Получен сигнал остановки...")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {str(e)}")
        finally:
            await self.stop()

    async def stop(self):
        """Остановка системы"""
        logger.info("\n🛑 Остановка системы...")
        self.running = False

        # Отмена задачи генерации сигналов
        if self.signal_generation_task:
            self.signal_generation_task.cancel()
            try:
                await self.signal_generation_task
            except asyncio.CancelledError:
                pass

        # Остановка компонентов
        if self.orchestrator:
            await self.orchestrator.stop()

        if self.exchange:
            await self.exchange.close()

        logger.info("✅ Система остановлена")


async def main():
    """Главная функция"""
    system = MultiCryptoTradingSystem()

    # Обработка сигналов
    def signal_handler(sig, frame):
        logger.info("\nПолучен сигнал завершения")
        asyncio.create_task(system.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Запуск системы
    await system.start()


if __name__ == "__main__":
    # Создаем директорию для логов если её нет
    os.makedirs("logs", exist_ok=True)

    # Запускаем систему
    asyncio.run(main())
