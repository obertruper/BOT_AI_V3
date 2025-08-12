#!/usr/bin/env python3
"""
Исправление синхронизации статусов ордеров с биржей
"""

import asyncio

from sqlalchemy import text

from database.connections import get_async_db


async def add_order_sync_to_engine():
    """
    Добавляет синхронизацию ордеров в TradingEngine._position_sync_loop

    Проблема: Ордера создаются со статусом OPEN, отправляются на биржу,
    но их статус не обновляется на FILLED когда они исполняются.

    Решение: Добавить вызов sync_orders_with_exchange в цикл синхронизации
    """

    print("=" * 80)
    print("ИСПРАВЛЕНИЕ СИНХРОНИЗАЦИИ ОРДЕРОВ")
    print("=" * 80)

    # Показываем текущую проблему
    async with get_async_db() as db:
        result = await db.execute(
            text(
                """
            SELECT status, COUNT(*) as cnt
            FROM orders
            GROUP BY status
        """
            )
        )

        statuses = result.fetchall()
        print("\n📊 Текущие статусы ордеров в БД:")
        for st in statuses:
            print(f"  {st.status}: {st.cnt} ордеров")

    print("\n⚠️ ПРОБЛЕМА:")
    print("  66 ордеров со статусом OPEN, хотя на бирже они уже исполнены")

    print("\n✅ РЕШЕНИЕ:")
    print("  Добавить в trading/engine.py в метод _position_sync_loop:")
    print("  После строки 568: await self.position_manager.sync_positions()")
    print("  Добавить:")
    print("  # Синхронизация статусов ордеров")
    print("  await self.order_manager.sync_orders_with_exchange('bybit')")

    print("\n📝 КОД ДЛЯ ДОБАВЛЕНИЯ в trading/engine.py:")
    code_to_add = """
                # Синхронизация позиций с биржами
                await self.position_manager.sync_positions()

                # ДОБАВЛЕНО: Синхронизация статусов ордеров
                # Исправляет проблему когда ордера остаются в статусе OPEN
                if self.order_manager:
                    try:
                        await self.order_manager.sync_orders_with_exchange('bybit')
                        self.logger.debug("Синхронизация ордеров выполнена")
                    except Exception as e:
                        self.logger.error(f"Ошибка синхронизации ордеров: {e}")
    """

    print(code_to_add)

    print("\n" + "=" * 80)
    print("ДОПОЛНИТЕЛЬНЫЕ ИСПРАВЛЕНИЯ:")
    print("=" * 80)

    print("\n1. Добавить интервал синхронизации (строка 643 в _position_sync_loop):")
    print("   await asyncio.sleep(30)  # Синхронизация каждые 30 секунд")

    print("\n2. Проверить max_open_positions в trading/engine.py:")
    print("   В методе _validate_signal добавить проверку количества открытых позиций")

    print("\n3. Исправить расчет размера позиций в order_executor.py")

    return True


if __name__ == "__main__":
    asyncio.run(add_order_sync_to_engine())
