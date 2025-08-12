#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор тестовых торговых сигналов для проверки SL/TP
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def generate_signal(
    signal_type: str = "LONG", symbol: str = "SOLUSDT", exchange: str = "bybit"
):
    """
    Генерация тестового торгового сигнала

    Args:
        signal_type: "LONG" или "SHORT"
        symbol: Торговый символ (по умолчанию SOLUSDT)
        exchange: Биржа (по умолчанию bybit)
    """
    try:
        logger.info(f"🎯 Генерация тестового {signal_type} сигнала для {symbol}")

        # Инициализация БД
        from sqlalchemy import select

        from database.connections import get_async_db
        from database.models.base_models import SignalType
        from database.models.signal import Signal

        # Получаем текущую цену из БД или используем фиксированную
        async with get_async_db() as db:
            # Пытаемся получить последнюю цену из market_data
            from database.models import RawMarketData

            query = (
                select(RawMarketData)
                .where(RawMarketData.symbol == symbol)
                .order_by(RawMarketData.timestamp.desc())
                .limit(1)
            )

            result = await db.execute(query)
            last_data = result.scalar_one_or_none()

            if last_data and last_data.close:
                current_price = float(last_data.close)
                logger.info(f"💰 Используем цену из БД: {current_price}")
            else:
                # Фиксированные цены для популярных монет
                default_prices = {
                    "SOLUSDT": 160.0,
                    "BTCUSDT": 50000.0,
                    "ETHUSDT": 3000.0,
                    "BNBUSDT": 400.0,
                    "XRPUSDT": 0.6,
                    "ADAUSDT": 0.5,
                    "DOGEUSDT": 0.08,
                    "MATICUSDT": 0.8,
                    "DOTUSDT": 6.0,
                    "AVAXUSDT": 35.0,
                }
                current_price = default_prices.get(symbol, 100.0)
                logger.info(f"💰 Используем фиксированную цену: {current_price}")

            # Определяем размер позиции для минимального объема $5 на Bybit
            min_order_value = 5.0  # Минимальный объем в USDT

            # Рассчитываем минимальное количество для $5
            min_quantity = min_order_value / current_price

            # Определяем размер позиции с учетом минимума
            if current_price > 10000:  # BTC
                quantity = max(0.001, min_quantity)
            elif current_price > 1000:  # ETH
                quantity = max(0.01, min_quantity)
            elif current_price > 100:  # SOL, BNB
                quantity = max(0.1, min_quantity)
            elif current_price > 10:  # DOT, AVAX
                quantity = max(1.0, min_quantity)
            elif current_price > 1:  # ADA, MATIC
                quantity = max(10.0, min_quantity)
            else:  # DOGE, XRP
                quantity = max(100.0, min_quantity)

            # Округляем до разумного количества знаков
            if quantity < 1:
                quantity = round(quantity, 4)
            elif quantity < 10:
                quantity = round(quantity, 2)
            else:
                quantity = round(quantity, 0)

            # Проверяем итоговый объем
            order_value = quantity * current_price
            logger.info(
                f"💵 Объем позиции: {order_value:.2f} USDT (минимум: {min_order_value} USDT)"
            )

            # Расчет SL/TP в зависимости от типа сигнала
            if signal_type.upper() == "LONG":
                signal_type_enum = SignalType.LONG
                stop_loss = current_price * 0.98  # -2%
                take_profit = current_price * 1.04  # +4%
                side_text = "покупка"
            else:  # SHORT
                signal_type_enum = SignalType.SHORT
                stop_loss = current_price * 1.02  # +2% (для шорта SL выше)
                take_profit = current_price * 0.96  # -4% (для шорта TP ниже)
                side_text = "продажа"

            # Создаем сигнал
            test_signal = Signal(
                strategy_name="manual_test_signal",
                symbol=symbol,
                exchange=exchange,
                signal_type=signal_type_enum,
                strength=0.85,  # Сильный сигнал
                confidence=0.90,  # Высокая уверенность
                suggested_price=current_price,
                suggested_quantity=quantity,
                suggested_stop_loss=stop_loss,
                suggested_take_profit=take_profit,
                metadata={
                    "test": True,
                    "manual": True,
                    "stop_loss_pct": 0.02,
                    "take_profit_pct": 0.04,
                    "trailing_stop": True,
                    "partial_tp_levels": [0.01, 0.02, 0.03, 0.04],  # 1%, 2%, 3%, 4%
                    "partial_tp_percentages": [
                        0.25,
                        0.25,
                        0.25,
                        0.25,
                    ],  # По 25% на каждом уровне
                    "profit_protection": {
                        "enabled": True,
                        "activation_profit": 0.015,  # Активация при +1.5%
                        "protection_level": 0.008,  # Защита 0.8% прибыли
                    },
                    "description": f"Тестовый {signal_type} сигнал для {symbol}",
                },
            )

            # Сохраняем в БД
            db.add(test_signal)
            await db.commit()
            await db.refresh(test_signal)

            logger.info("✅ Сигнал успешно создан!")
            logger.info("📊 Детали сигнала:")
            logger.info(f"   ID: {test_signal.id}")
            logger.info(f"   Тип: {signal_type} ({side_text})")
            logger.info(f"   Символ: {symbol}")
            logger.info(f"   Биржа: {exchange}")
            logger.info(f"   Цена входа: {current_price}")
            logger.info(f"   Количество: {quantity}")
            logger.info(
                f"   Stop Loss: {stop_loss} ({'-2%' if signal_type == 'LONG' else '+2%'})"
            )
            logger.info(
                f"   Take Profit: {take_profit} ({'+4%' if signal_type == 'LONG' else '-4%'})"
            )
            logger.info("   Трейлинг стоп: ✅")
            logger.info("   Частичные TP: 25% на +1%, +2%, +3%, +4%")
            logger.info("   Защита прибыли: ✅ (активация при +1.5%)")

            logger.info(
                "\n🚀 Сигнал отправлен в систему и будет обработан автоматически!"
            )
            logger.info(
                "💡 Используйте ./monitor_signals.sh для отслеживания обработки"
            )

            return test_signal

    except Exception as e:
        logger.error(f"❌ Ошибка генерации сигнала: {e}")
        import traceback

        traceback.print_exc()
        return None


async def main():
    """Главная функция"""
    import argparse

    parser = argparse.ArgumentParser(description="Генератор тестовых торговых сигналов")
    parser.add_argument(
        "--type",
        choices=["LONG", "SHORT", "long", "short"],
        default="LONG",
        help="Тип сигнала: LONG или SHORT",
    )
    parser.add_argument(
        "--symbol", default="SOLUSDT", help="Торговый символ (по умолчанию SOLUSDT)"
    )
    parser.add_argument(
        "--exchange", default="bybit", help="Биржа (по умолчанию bybit)"
    )

    args = parser.parse_args()

    # Приводим тип к верхнему регистру
    signal_type = args.type.upper()

    # Генерируем сигнал
    signal = await generate_signal(
        signal_type=signal_type,
        symbol=args.symbol.upper(),
        exchange=args.exchange.lower(),
    )

    if signal:
        logger.info("\n✅ Готово! Сигнал создан и будет обработан системой.")
    else:
        logger.error("\n❌ Не удалось создать сигнал.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
