#!/usr/bin/env python3
"""
Проверка генерации ML сигналов и создания ордеров
"""

import asyncio
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


async def check_ml_signals():
    """Проверка ML сигналов в БД"""
    print("=" * 60)
    print("🔍 ПРОВЕРКА ML СИГНАЛОВ И ОРДЕРОВ")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    try:
        from sqlalchemy import desc, func, select

        from database.connections import get_async_db
        from database.models.base_models import Order, Trade
        from database.models.signal import Signal

        async with get_async_db() as db:
            # 1. Проверка сигналов
            print("\n📊 СИГНАЛЫ:")

            # Общее количество
            signal_count = await db.scalar(select(func.count(Signal.id)))
            print(f"Всего сигналов в БД: {signal_count or 0}")

            # Последние 10 сигналов
            result = await db.execute(
                select(Signal).order_by(desc(Signal.created_at)).limit(10)
            )
            recent_signals = result.scalars().all()

            if recent_signals:
                print("\nПоследние сигналы:")
                for sig in recent_signals[:5]:
                    strength_str = f"{sig.strength:.2f}" if sig.strength else "N/A"
                    confidence_str = (
                        f"{sig.confidence:.0f}%" if sig.confidence else "N/A"
                    )
                    print(
                        f"  {sig.created_at.strftime('%H:%M:%S')} | "
                        f"{sig.symbol} | {sig.signal_type.value} | "
                        f"Сила: {strength_str} | "
                        f"Уверенность: {confidence_str}"
                    )
            else:
                print("❌ Нет сигналов в БД")

            # 2. Проверка ордеров
            print("\n📋 ОРДЕРА:")

            # Общее количество
            order_count = await db.scalar(select(func.count(Order.id)))
            print(f"Всего ордеров в БД: {order_count or 0}")

            # Последние ордера
            result = await db.execute(
                select(Order).order_by(desc(Order.created_at)).limit(10)
            )
            recent_orders = result.scalars().all()

            if recent_orders:
                print("\nПоследние ордера:")
                for order in recent_orders[:5]:
                    print(
                        f"  {order.created_at.strftime('%H:%M:%S')} | "
                        f"{order.symbol} | {order.side.value} | "
                        f"{order.quantity} @ {order.price or 'MARKET'} | "
                        f"Статус: {order.status.value}"
                    )
            else:
                print("❌ Нет ордеров в БД")

            # 3. Проверка сделок
            print("\n💰 СДЕЛКИ:")

            # Общее количество
            trade_count = await db.scalar(select(func.count(Trade.id)))
            print(f"Всего сделок в БД: {trade_count or 0}")

            # Последние сделки
            result = await db.execute(
                select(Trade).order_by(desc(Trade.created_at)).limit(5)
            )
            recent_trades = result.scalars().all()

            if recent_trades:
                print("\nПоследние сделки:")
                for trade in recent_trades:
                    pnl_str = (
                        f"+${trade.pnl:.2f}"
                        if trade.pnl > 0
                        else f"-${abs(trade.pnl):.2f}"
                        if trade.pnl
                        else "N/A"
                    )
                    print(
                        f"  {trade.created_at.strftime('%H:%M:%S')} | "
                        f"{trade.symbol} | {trade.side.value} | "
                        f"{trade.quantity} @ {trade.price} | "
                        f"PnL: {pnl_str}"
                    )
            else:
                print("❌ Нет сделок в БД")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


async def test_ml_signal_generation():
    """Тест генерации одного ML сигнала"""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТ ГЕНЕРАЦИИ ML СИГНАЛА")
    print("=" * 60)

    try:
        from core.config.config_manager import ConfigManager
        from ml.ml_manager import MLManager
        from ml.ml_signal_processor import MLSignalProcessor

        # Инициализация
        print("\n🔄 Инициализация ML компонентов...")
        config_manager = ConfigManager()
        config = config_manager.get_config()

        ml_manager = MLManager(config)
        await ml_manager.initialize()
        print("✅ ML Manager инициализирован")

        ml_signal_processor = MLSignalProcessor(
            ml_manager=ml_manager, config=config, config_manager=config_manager
        )
        await ml_signal_processor.initialize()
        print("✅ ML Signal Processor инициализирован")

        # Генерация сигнала
        print("\n🎯 Генерация сигнала для BTCUSDT...")
        signal = await ml_signal_processor.process_realtime_signal(
            symbol="BTCUSDT", exchange="bybit"
        )

        if signal:
            print("✅ Сигнал сгенерирован!")
            print(f"   Тип: {signal.signal_type.value}")
            print(f"   Уверенность: {signal.confidence:.1f}%")
            print(f"   Стратегия: {signal.strategy_name}")
            if signal.entry_price:
                print(f"   Цена входа: ${signal.entry_price:.2f}")
            if signal.stop_loss:
                print(f"   Stop Loss: ${signal.stop_loss:.2f}")
            if signal.take_profit:
                print(f"   Take Profit: ${signal.take_profit:.2f}")
        else:
            print("⚠️ Сигнал не сгенерирован")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Основная функция"""
    # Проверка сигналов в БД
    await check_ml_signals()

    # Опционально: тест генерации нового сигнала
    print("\n" + "-" * 60)
    response = input("\nСгенерировать тестовый ML сигнал? (y/N): ")
    if response.lower() == "y":
        await test_ml_signal_generation()

    print("\n✅ Проверка завершена")


if __name__ == "__main__":
    asyncio.run(main())
