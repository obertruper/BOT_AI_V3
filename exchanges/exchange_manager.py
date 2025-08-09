"""
Exchange Manager для управления экземплярами бирж
"""

import asyncio
from typing import Any, Dict, List

from core.logger import setup_logger
from exchanges.factory import ExchangeFactory, ExchangeType


class ExchangeManager:
    """Менеджер для управления экземплярами бирж"""

    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация менеджера бирж

        Args:
            config: Конфигурация бирж из system.yaml
        """
        self.logger = setup_logger("exchange_manager")
        self.config = config
        self.exchanges: Dict[str, Any] = {}
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

                # Подготавливаем креденшалы
                api_key = exchange_config.get("api_key", "")
                api_secret = exchange_config.get("api_secret", "")
                testnet = exchange_config.get("testnet", False)

                # Проверяем наличие API ключей
                if not api_key or not api_secret:
                    self.logger.warning(f"⚠️ Нет API ключей для биржи {exchange_name}")
                    continue

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
        self.logger.info(
            f"✅ Exchange Manager инициализирован с {len(self.exchanges)} биржами"
        )

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

    async def get_available_exchanges(self) -> List[str]:
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
                            self.logger.warning(
                                f"Health check failed для биржи {exchange_name}"
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Ошибка health check для {exchange_name}: {e}"
                        )

            return True

        except Exception as e:
            self.logger.error(f"Ошибка health check ExchangeManager: {e}")
            return False

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
