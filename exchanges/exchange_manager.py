"""
Exchange Manager для управления экземплярами бирж
"""

import asyncio
from typing import Any

from core.logger import setup_logger
from exchanges.factory import ExchangeFactory, ExchangeType


class ExchangeManager:
    """Менеджер для управления экземплярами бирж"""

    def __init__(self, config: dict[str, Any]):
        """
        Инициализация менеджера бирж

        Args:
            config: Конфигурация бирж из system.yaml
        """
        self.logger = setup_logger("exchange_manager")
        self.config = config
        self.exchanges: dict[str, Any] = {}
        self._initialized = False

    async def initialize(self):
        """Инициализация всех настроенных бирж"""
        if self._initialized:
            return

        self.logger.info("🔄 Инициализация Exchange Manager...")

        # Получаем конфигурацию бирж
        exchanges_config = self.config.get("exchanges", {})

        for exchange_name, exchange_config in exchanges_config.items():
            if not exchange_config.get("enabled", False):
                self.logger.info(f"⏭️ Биржа {exchange_name} отключена")
                continue

            try:
                # Создаем экземпляр фабрики и используем ее для создания биржи
                factory = ExchangeFactory()

                # Подготавливаем креденшалы - сначала пробуем из ENV, потом из конфига
                import os

                env_key_name = f"{exchange_name.upper()}_API_KEY"
                env_secret_name = f"{exchange_name.upper()}_API_SECRET"
                env_testnet_name = f"{exchange_name.upper()}_TESTNET"

                api_key = os.getenv(env_key_name) or exchange_config.get("api_key", "")
                api_secret = os.getenv(env_secret_name) or exchange_config.get("api_secret", "")
                testnet = os.getenv(
                    env_testnet_name, "false"
                ).lower() == "true" or exchange_config.get("testnet", False)

                # Проверяем наличие API ключей
                if not api_key or not api_secret:
                    self.logger.warning(f"⚠️ Нет API ключей для биржи {exchange_name}")
                    self.logger.debug(f"   Проверялись: {env_key_name}, {env_secret_name}")
                    continue

                self.logger.info(f"✅ Найдены API ключи для {exchange_name}")
                self.logger.debug(f"   API Key: {api_key[:10]}..." if api_key else "NONE")
                self.logger.debug(f"   Testnet: {testnet}")

                # Преобразуем строку в ExchangeType
                try:
                    exchange_type = ExchangeType(exchange_name)
                except ValueError:
                    self.logger.warning(f"Неподдерживаемый тип биржи: {exchange_name}")
                    continue

                # Создаем клиента через фабрику
                exchange = factory.create_client(
                    exchange_type=exchange_type,
                    api_key=api_key,
                    api_secret=api_secret,
                    sandbox=testnet,
                )

                # Инициализируем биржу
                if hasattr(exchange, "initialize"):
                    await exchange.initialize()

                self.exchanges[exchange_name] = exchange
                self.logger.info(f"✅ Биржа {exchange_name} инициализирована")

            except Exception as e:
                self.logger.error(f"❌ Ошибка инициализации биржи {exchange_name}: {e}")

        self._initialized = True
        self.logger.info(f"✅ Exchange Manager инициализирован с {len(self.exchanges)} биржами")

    async def get_exchange(self, exchange_name: str):
        """
        Получение экземпляра биржи

        Args:
            exchange_name: Название биржи

        Returns:
            Экземпляр биржи или None
        """
        if not self._initialized:
            await self.initialize()

        return self.exchanges.get(exchange_name)

    async def get_available_exchanges(self) -> list[str]:
        """Получение списка доступных бирж"""
        if not self._initialized:
            await self.initialize()

        return list(self.exchanges.keys())

    async def health_check(self) -> bool:
        """Проверка здоровья менеджера бирж"""
        try:
            if not self._initialized:
                await self.initialize()

            # Проверяем что есть хотя бы одна биржа
            if not self.exchanges:
                self.logger.warning("Нет инициализированных бирж")
                return False

            # Проверяем каждую биржу
            for exchange_name, exchange in self.exchanges.items():
                if hasattr(exchange, "health_check"):
                    try:
                        result = await exchange.health_check()
                        if not result:
                            self.logger.warning(f"Health check failed для биржи {exchange_name}")
                    except Exception as e:
                        self.logger.error(f"Ошибка health check для {exchange_name}: {e}")

            return True

        except Exception as e:
            self.logger.error(f"Ошибка health check ExchangeManager: {e}")
            return False

    async def get_positions(self, exchange_name: str, symbol: str | None = None) -> list:
        """Получить позиции с конкретной биржи

        Args:
            exchange_name: Название биржи
            symbol: Символ для фильтрации (опционально)

        Returns:
            Список позиций с биржи
        """
        try:
            exchange = await self.get_exchange(exchange_name)
            if exchange and hasattr(exchange, "get_positions"):
                return await exchange.get_positions(symbol)
            else:
                self.logger.warning(f"Биржа {exchange_name} не поддерживает get_positions")
                return []
        except Exception as e:
            self.logger.error(f"Ошибка получения позиций с {exchange_name}: {e}")
            return []

    async def close(self):
        """Закрытие всех соединений с биржами"""
        self.logger.info("🔄 Закрытие Exchange Manager...")

        close_tasks = []
        for exchange_name, exchange in self.exchanges.items():
            if hasattr(exchange, "close"):
                self.logger.info(f"  → Закрытие {exchange_name}...")
                close_tasks.append(exchange.close())

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        self.exchanges.clear()
        self._initialized = False
        self.logger.info("✅ Exchange Manager закрыт")
