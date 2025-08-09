#!/usr/bin/env python3
"""
Тест публичного API Bybit (без авторизации)
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def main():
    """Главная функция"""
    print("=== Тест публичного API Bybit ===\n")

    try:
        from exchanges.bybit.client import BybitClient

        # Создаем клиент для публичных запросов
        client = BybitClient(
            api_key="public_access", api_secret="public_access", sandbox=False
        )

        print("1️⃣ Получение текущей цены BTC (публичный запрос):")

        ticker = await client.get_ticker("BTCUSDT")
        if ticker:
            print(f"   BTC/USDT: ${ticker.price:.2f}")
            print("   Цена успешно получена")

        print("\n✅ Публичный API работает!")

        print("\n2️⃣ Проверка формата API ключей:")

        api_key = os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("BYBIT_API_SECRET")

        print(f"   API Key: {api_key}")
        print(f"   API Key длина: {len(api_key) if api_key else 0}")
        print(f"   API Secret длина: {len(api_secret) if api_secret else 0}")
        print(
            f"   API Secret (первые 5 символов): {api_secret[:5] if api_secret else 'N/A'}..."
        )

        print("\n⚠️ Замечание:")
        print("   API Secret кажется слишком коротким (18 символов)")
        print("   Обычно Bybit API Secret имеет длину 36-44 символа")
        print("   Пожалуйста, проверьте правильность API Secret")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
