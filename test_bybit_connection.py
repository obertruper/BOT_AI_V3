#!/usr/bin/env python3
"""
Тест подключения к Bybit API
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_bybit_connection():
    """Тест подключения к Bybit"""

    print("=" * 60)
    print("ТЕСТ ПОДКЛЮЧЕНИЯ К BYBIT API")
    print("=" * 60)

    try:
        # Проверяем переменные окружения напрямую
        print("\n1. Проверка переменных окружения...")
        api_key = os.getenv("BYBIT_API_KEY", "")
        api_secret = os.getenv("BYBIT_API_SECRET", "")
        testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"

        print(f"   API Key: {'Установлен' if api_key else 'НЕ НАЙДЕН'}")
        print(f"   API Secret: {'Установлен' if api_secret else 'НЕ НАЙДЕН'}")
        print(f"   Testnet: {testnet}")

        if not api_key or not api_secret:
            print("❌ API ключи не настроены")
            print("   Для тестирования создайте файл .env с переменными:")
            print("   BYBIT_API_KEY=your_api_key")
            print("   BYBIT_API_SECRET=your_api_secret")
            print("   BYBIT_TESTNET=true  # для тестнета")
            return

        # Создаем Bybit клиент
        print("\n2. Создание Bybit клиента...")
        from exchanges.factory import ExchangeFactory

        factory = ExchangeFactory()

        try:
            bybit_client = factory.create_client("bybit", api_key, api_secret)
            print("✅ Bybit клиент создан успешно")
        except Exception as e:
            print(f"❌ Ошибка создания клиента: {e}")
            print("\nПопробуем создать тестнет клиент...")

            # Пробуем тестнет
            os.environ["BYBIT_TESTNET"] = "true"

            try:
                bybit_client = factory.create_client("bybit", api_key, api_secret)
                print("✅ Bybit testnet клиент создан")
            except Exception as e2:
                print(f"❌ Ошибка создания testnet клиента: {e2}")
                return

        # Тестируем базовые методы
        print("\n3. Тестирование базовых методов...")

        # Получение информации об аккаунте
        try:
            account_info = await bybit_client.get_account_info()
            print("✅ Информация об аккаунте получена")
            print(f"   Тип аккаунта: {account_info.get('account_type', 'Неизвестно')}")
        except Exception as e:
            print(f"❌ Ошибка получения информации об аккаунте: {e}")

        # Получение балансов
        try:
            balances = await bybit_client.get_balances()
            print("✅ Балансы получены")

            # Показываем ненулевые балансы
            non_zero_balances = {k: v for k, v in balances.items() if float(v) > 0}
            if non_zero_balances:
                print("   Ненулевые балансы:")
                for currency, balance in list(non_zero_balances.items())[:5]:
                    print(f"     {currency}: {balance}")
            else:
                print("   Все балансы равны нулю")

        except Exception as e:
            print(f"❌ Ошибка получения балансов: {e}")

        # Получение рыночных данных
        print("\n4. Тестирование рыночных данных...")
        try:
            ticker = await bybit_client.get_ticker("BTCUSDT")
            print("✅ Ticker BTCUSDT получен")
            print(f"   Цена: {ticker.get('last', 'N/A')}")
            print(f"   Объем: {ticker.get('volume', 'N/A')}")
        except Exception as e:
            print(f"❌ Ошибка получения ticker: {e}")

        # Получение OHLCV данных
        try:
            ohlcv = await bybit_client.fetch_ohlcv("BTCUSDT", "15m", limit=5)
            print("✅ OHLCV данные получены")
            print(f"   Количество свечей: {len(ohlcv)}")
            if ohlcv:
                last_candle = ohlcv[-1]
                print(f"   Последняя свеча: {last_candle}")
        except Exception as e:
            print(f"❌ Ошибка получения OHLCV: {e}")

        # Проверка позиций
        print("\n5. Проверка позиций...")
        try:
            positions = await bybit_client.get_positions()
            print("✅ Позиции получены")

            active_positions = [p for p in positions if float(p.get("size", 0)) != 0]
            if active_positions:
                print(f"   Активных позиций: {len(active_positions)}")
                for pos in active_positions[:3]:
                    print(
                        f"     {pos.get('symbol')}: {pos.get('size')} @ {pos.get('entry_price')}"
                    )
            else:
                print("   Нет активных позиций")

        except Exception as e:
            print(f"❌ Ошибка получения позиций: {e}")

        # Проверка position mode
        print("\n6. Проверка position mode...")
        try:
            # Получаем текущий режим позиций
            position_mode = await bybit_client.get_position_mode()
            print(f"✅ Position mode: {position_mode}")

            # Если не hedge mode, пытаемся переключить
            if position_mode != "hedge":
                print("   Переключение в hedge mode...")
                await bybit_client.set_position_mode("hedge")
                print("✅ Position mode переключен на hedge")
            else:
                print("✅ Position mode уже hedge")

        except Exception as e:
            print(f"❌ Ошибка работы с position mode: {e}")

        print("\n✅ Тест Bybit API завершен успешно!")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_bybit_connection())
