#!/usr/bin/env python3
"""
Тестирование синглтона BybitClient
Проверяем что используется единственный экземпляр с правильными настройками
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from exchanges.bybit import get_bybit_client
from exchanges.bybit.singleton_client import BybitClientSingleton
from core.logger import setup_logger
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logger = setup_logger("singleton_test")


async def test_singleton():
    """Тестирование синглтона"""
    
    logger.info("=" * 60)
    logger.info("🧪 Тестирование синглтона BybitClient")
    logger.info("=" * 60)
    
    # Получаем ключи из окружения
    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")
    
    logger.info("\n1️⃣ Создаём первый экземпляр клиента")
    client1 = get_bybit_client(api_key, api_secret)
    logger.info(f"   Client1 ID: {id(client1)}")
    logger.info(f"   Hedge mode: {client1.hedge_mode}")
    logger.info(f"   Default leverage: {client1.default_leverage}")
    
    logger.info("\n2️⃣ Создаём второй экземпляр клиента")
    client2 = get_bybit_client()  # Без параметров
    logger.info(f"   Client2 ID: {id(client2)}")
    logger.info(f"   Hedge mode: {client2.hedge_mode}")
    logger.info(f"   Default leverage: {client2.default_leverage}")
    
    logger.info("\n3️⃣ Проверяем что это один и тот же объект")
    if client1 is client2:
        logger.info("   ✅ Синглтон работает! Оба клиента - один объект")
    else:
        logger.error("   ❌ Ошибка! Созданы разные объекты")
        
    logger.info("\n4️⃣ Пробуем создать с другими ключами")
    client3 = get_bybit_client("other_key", "other_secret")
    logger.info(f"   Client3 ID: {id(client3)}")
    
    if client1 is client3:
        logger.info("   ✅ Синглтон защищён! Использует существующий экземпляр")
    else:
        logger.error("   ❌ Ошибка! Создан новый объект с другими ключами")
        
    logger.info("\n5️⃣ Проверяем настройки hedge mode")
    logger.info(f"   Hedge mode из ENV: {os.getenv('BYBIT_HEDGE_MODE', 'not set')}")
    logger.info(f"   Hedge mode в клиенте: {client1.hedge_mode}")
    
    if client1.hedge_mode:
        logger.info("   ✅ Hedge mode включён правильно!")
    else:
        logger.warning("   ⚠️ Hedge mode отключён, проверьте .env")
        
    logger.info("\n6️⃣ Тестируем создание через фабрику бирж")
    from exchanges.factory import ExchangeFactory, ExchangeType
    
    factory = ExchangeFactory()
    exchange = factory.create_client(
        ExchangeType.BYBIT,
        api_key=api_key,
        api_secret=api_secret,
        sandbox=False
    )
    
    # У BybitExchange есть атрибут client
    if hasattr(exchange, 'client'):
        factory_client = exchange.client
        logger.info(f"   Factory client ID: {id(factory_client)}")
        
        if factory_client is client1:
            logger.info("   ✅ Фабрика использует синглтон!")
        else:
            logger.warning("   ⚠️ Фабрика создала новый экземпляр")
    
    logger.info("\n7️⃣ Проверяем работу API с синглтоном")
    try:
        # Тестовый запрос к API
        response = await client1._make_request(
            "GET",
            "/v5/market/time",
            auth=False
        )
        
        if response.get("retCode") == 0:
            server_time = response.get("result", {}).get("timeSecond")
            logger.info(f"   ✅ API работает! Server time: {server_time}")
        else:
            logger.error(f"   ❌ API ошибка: {response.get('retMsg')}")
            
    except Exception as e:
        logger.error(f"   ❌ Ошибка API запроса: {e}")
        
    logger.info("\n" + "=" * 60)
    logger.info("📊 Итоги тестирования:")
    logger.info("=" * 60)
    
    # Итоговая проверка
    all_same = (client1 is client2 is client3)
    hedge_enabled = client1.hedge_mode
    
    if all_same and hedge_enabled:
        logger.info("✅ Все тесты пройдены успешно!")
        logger.info("   - Синглтон работает корректно")
        logger.info("   - Hedge mode включён")
        logger.info("   - Используется единая конфигурация")
    else:
        logger.warning("⚠️ Есть проблемы:")
        if not all_same:
            logger.warning("   - Синглтон не работает правильно")
        if not hedge_enabled:
            logger.warning("   - Hedge mode отключён")
            
    # Закрываем сессию
    if hasattr(client1, 'session') and client1.session:
        await client1.session.close()
        logger.info("\n✅ Сессия закрыта")


async def main():
    """Главная функция"""
    try:
        await test_singleton()
    except Exception as e:
        logger.error(f"Ошибка теста: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())