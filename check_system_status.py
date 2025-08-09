#!/usr/bin/env python3
"""
Быстрая проверка статуса системы
"""

import asyncio
import sys
from pathlib import Path

import aiohttp

sys.path.append(str(Path(__file__).parent))

from database.connections.postgres import AsyncPGPool


async def check_status():
    """Проверяет статус системы."""

    print("🔍 ПРОВЕРКА СТАТУСА СИСТЕМЫ\n")

    # 1. API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8080/api/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ API: {data.get('status', 'unknown')}")
                    if "components" in data:
                        active = [k for k, v in data["components"].items() if v]
                        inactive = [k for k, v in data["components"].items() if not v]
                        if active:
                            print(f"   Активны: {', '.join(active)}")
                        if inactive:
                            print(f"   Не активны: {', '.join(inactive)}")
                else:
                    print(f"❌ API недоступен (код {resp.status})")
    except Exception as e:
        print(f"❌ API недоступен: {e}")

    # 2. База данных
    try:
        result = await AsyncPGPool.fetchval("SELECT 1")
        print("✅ PostgreSQL: подключен")
    except Exception as e:
        print(f"❌ PostgreSQL: {e}")

    # 3. Последние сигналы
    recent_signals = await AsyncPGPool.fetchrow(
        """
        SELECT COUNT(*) as count, MAX(created_at) as last_time
        FROM signals
        WHERE created_at > NOW() - INTERVAL '5 minutes'
    """
    )

    if recent_signals and recent_signals["count"] > 0:
        print(f"✅ Сигналы: {recent_signals['count']} за 5 минут")
    else:
        print("❌ Сигналы: нет активности")

    # 4. ML активность
    ml_activity = await AsyncPGPool.fetchrow(
        """
        SELECT COUNT(*) as count, MAX(created_at) as last_time
        FROM processed_market_data
        WHERE created_at > NOW() - INTERVAL '5 minutes'
    """
    )

    if ml_activity and ml_activity["count"] > 0:
        print(f"✅ ML: {ml_activity['count']} предсказаний за 5 минут")
    else:
        print("❌ ML: нет активности")

    # 5. Ордера
    orders = await AsyncPGPool.fetchrow(
        """
        SELECT COUNT(*) as count
        FROM orders
        WHERE created_at > NOW() - INTERVAL '1 hour'
    """
    )

    if orders and orders["count"] > 0:
        print(f"✅ Ордера: {orders['count']} за час")
    else:
        print("❌ Ордера: нет за последний час")

    print("\n" + "=" * 40)


if __name__ == "__main__":
    asyncio.run(check_status())
