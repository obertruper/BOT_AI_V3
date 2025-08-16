#!/usr/bin/env python3
"""
Принудительная синхронизация статусов ордеров с Bybit
"""

import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text

from database.connections import get_async_db
from exchanges.bybit.client import BybitClient

load_dotenv()


async def sync_orders():
    """Синхронизация статусов ордеров"""

    print("=" * 80)
    print("ПРИНУДИТЕЛЬНАЯ СИНХРОНИЗАЦИЯ ОРДЕРОВ С BYBIT")
    print("=" * 80)

    # Инициализируем клиент Bybit
    client = BybitClient(
        api_key=os.getenv("BYBIT_API_KEY"), api_secret=os.getenv("BYBIT_API_SECRET")
    )

    await client.connect()

    async with get_async_db() as db:
        # Получаем все OPEN ордера из БД
        result = await db.execute(
            text(
                """
            SELECT id, order_id, symbol, side, quantity, price, status
            FROM orders
            WHERE status = 'OPEN'
        """
            )
        )

        open_orders = result.fetchall()

        print(f"\n📊 Найдено {len(open_orders)} ордеров со статусом OPEN в БД")

        updated_count = 0
        filled_count = 0
        cancelled_count = 0

        for order in open_orders:
            try:
                # Запрашиваем статус ордера на бирже
                exchange_order = await client.get_order(
                    symbol=order.symbol, order_id=order.order_id
                )

                if exchange_order:
                    exchange_status = exchange_order.get("orderStatus", "").upper()

                    # Мапинг статусов Bybit на наши
                    status_map = {
                        "FILLED": "FILLED",
                        "NEW": "OPEN",
                        "PARTIALLYFILLED": "PARTIALLY_FILLED",
                        "CANCELLED": "CANCELLED",
                        "REJECTED": "REJECTED",
                        "EXPIRED": "CANCELLED",
                    }

                    new_status = status_map.get(exchange_status, "OPEN")

                    if new_status != "OPEN":
                        # Обновляем статус в БД
                        await db.execute(
                            text(
                                """
                            UPDATE orders
                            SET status = :status,
                                updated_at = NOW(),
                                filled_quantity = :filled_qty,
                                average_price = :avg_price
                            WHERE id = :id
                        """
                            ),
                            {
                                "status": new_status,
                                "filled_qty": float(exchange_order.get("cumExecQty", 0)),
                                "avg_price": float(exchange_order.get("avgPrice", 0)),
                                "id": order.id,
                            },
                        )

                        updated_count += 1
                        if new_status == "FILLED":
                            filled_count += 1
                            print(f"  ✅ {order.symbol}: OPEN → FILLED")
                        elif new_status == "CANCELLED":
                            cancelled_count += 1
                            print(f"  ❌ {order.symbol}: OPEN → CANCELLED")
                else:
                    # Ордер не найден на бирже - вероятно отменен или истек
                    await db.execute(
                        text(
                            """
                        UPDATE orders
                        SET status = 'CANCELLED',
                            updated_at = NOW()
                        WHERE id = :id
                    """
                        ),
                        {"id": order.id},
                    )

                    cancelled_count += 1
                    print(f"  ❌ {order.symbol}: OPEN → CANCELLED (не найден на бирже)")

            except Exception as e:
                print(f"  ⚠️ Ошибка проверки ордера {order.symbol}: {e}")

        # Коммитим изменения
        await db.commit()

        print("\n" + "=" * 80)
        print("РЕЗУЛЬТАТЫ СИНХРОНИЗАЦИИ:")
        print(f"  Обновлено ордеров: {updated_count}")
        print(f"  Из них FILLED: {filled_count}")
        print(f"  Из них CANCELLED: {cancelled_count}")

        # Проверяем новую статистику
        new_stats = await db.execute(
            text(
                """
            SELECT status, COUNT(*) as cnt
            FROM orders
            GROUP BY status
        """
            )
        )

        stats = new_stats.fetchall()

        print("\n📊 НОВАЯ СТАТИСТИКА ОРДЕРОВ:")
        for st in stats:
            print(f"  {st.status}: {st.cnt}")

        print("\n✅ Синхронизация завершена")


if __name__ == "__main__":
    asyncio.run(sync_orders())
