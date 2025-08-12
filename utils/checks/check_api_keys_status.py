#!/usr/bin/env python3
"""
Проверка статуса API ключей Bybit
"""

import asyncio
import os
from datetime import datetime

import ccxt.async_support as ccxt
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


async def check_api_keys():
    """Проверка API ключей Bybit"""

    print("=" * 60)
    print("🔑 ПРОВЕРКА API КЛЮЧЕЙ BYBIT")
    print("=" * 60)

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    if not api_key or not api_secret:
        print("❌ API ключи не найдены в .env файле!")
        print("Добавьте в .env:")
        print("  BYBIT_API_KEY=ваш_ключ")
        print("  BYBIT_API_SECRET=ваш_секрет")
        return False

    print("✅ API ключи найдены в .env")
    print(f"   Ключ: {api_key[:8]}...{api_key[-4:]}")

    # Проверяем через ccxt
    exchange = None
    try:
        exchange = ccxt.bybit(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "linear",  # USDT perpetual
                },
            }
        )

        print("\n📊 Проверка подключения...")

        # Получаем баланс
        balance = await exchange.fetch_balance()
        usdt_balance = balance.get("USDT", {})

        print("✅ Подключение успешно!")
        print("   Баланс USDT:")
        print(f"   - Всего: ${usdt_balance.get('total', 0):.2f}")
        print(f"   - Свободно: ${usdt_balance.get('free', 0):.2f}")
        print(f"   - Используется: ${usdt_balance.get('used', 0):.2f}")

        # Проверяем открытые позиции
        print("\n📈 Проверка позиций...")
        positions = await exchange.fetch_positions()

        if positions:
            print(f"   Открытых позиций: {len(positions)}")
            for pos in positions:
                if pos["contracts"] > 0:
                    print(
                        f"   - {pos['symbol']}: {pos['side']} {pos['contracts']} контрактов"
                    )
        else:
            print("   Нет открытых позиций")

        # Проверяем API лимиты
        print("\n⚡ Проверка API статуса...")
        try:
            api_info = await exchange.private_get_v5_user_query_api()
            print("✅ API статус получен")

            if "result" in api_info:
                result = api_info["result"]
                print(f"   - Тип аккаунта: {result.get('userStatus', 'Unknown')}")
                print(f"   - ID: {result.get('uid', 'Unknown')}")

                # Проверка срока действия ключей
                if "expiredAt" in result:
                    exp_time = result["expiredAt"]
                    if exp_time and exp_time != "0":
                        exp_date = datetime.fromtimestamp(int(exp_time) / 1000)
                        now = datetime.now()
                        if exp_date < now:
                            print(f"   ❌ API ключ истек: {exp_date}")
                            print("   ⚠️  Создайте новый ключ на bybit.com")
                        else:
                            days_left = (exp_date - now).days
                            print(f"   ✅ Ключ действителен еще {days_left} дней")
                else:
                    print("   ✅ Ключ бессрочный")

        except Exception as e:
            if "expired" in str(e).lower():
                print("❌ API ключ истек!")
                print(
                    "   Создайте новый ключ на https://www.bybit.com/app/user/api-management"
                )
            elif "invalid" in str(e).lower():
                print("❌ API ключ недействителен!")
                print("   Проверьте правильность ключа и секрета")
            else:
                print(f"⚠️  Не удалось проверить статус API: {e}")

        return True

    except Exception as e:
        print(f"\n❌ Ошибка подключения: {e}")

        error_msg = str(e).lower()
        if "expired" in error_msg or "33004" in error_msg:
            print("\n🔴 API КЛЮЧ ИСТЕК!")
            print("Решение:")
            print("1. Зайдите на https://www.bybit.com")
            print("2. Перейдите в API Management")
            print("3. Создайте новый API ключ")
            print("4. Обновите .env файл:")
            print("   BYBIT_API_KEY=новый_ключ")
            print("   BYBIT_API_SECRET=новый_секрет")

        elif "invalid" in error_msg or "10003" in error_msg:
            print("\n🔴 API КЛЮЧ НЕДЕЙСТВИТЕЛЕН!")
            print("Проверьте:")
            print("1. Правильность ключа и секрета")
            print("2. Нет лишних пробелов в .env")
            print("3. Ключ активен на бирже")

        elif "not enough" in error_msg or "110007" in error_msg:
            print("\n⚠️  Недостаточно средств на балансе")
            print("Но API ключи работают!")

        return False

    finally:
        if exchange:
            await exchange.close()


async def main():
    success = await check_api_keys()

    print("\n" + "=" * 60)
    if success:
        print("✅ API КЛЮЧИ РАБОТАЮТ")
    else:
        print("❌ ПРОБЛЕМА С API КЛЮЧАМИ")
        print("\n📝 Инструкция по обновлению ключей:")
        print("1. Зайдите на bybit.com → API Management")
        print("2. Создайте новый ключ с правами:")
        print("   - Spot Trading")
        print("   - Derivatives Trading")
        print("   - Read (чтение)")
        print("3. Скопируйте ключ и секрет")
        print("4. Обновите .env файл")
        print("5. Перезапустите систему: ./stop_all.sh && ./start_with_logs.sh")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
