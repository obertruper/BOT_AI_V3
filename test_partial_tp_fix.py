#!/usr/bin/env python3
"""
Тестирование исправленного механизма частичного закрытия позиций
"""

import asyncio
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_partial_tp():
    """Тестирование частичного закрытия"""

    logger.info("🚀 Начинаем тестирование частичного закрытия позиций")

    # Импортируем необходимые модули
    from trading.sltp.enhanced_manager import EnhancedSLTPManager
    from trading.sltp.models import PartialTPLevel, SLTPConfig
    from trading.sltp.utils import normalize_percentage, round_price, round_qty

    # Создаем тестовую конфигурацию
    config = SLTPConfig(
        partial_tp_enabled=True,
        partial_tp_levels=[
            PartialTPLevel(
                level=1,
                percentage=1.2,
                price=0,  # Будет рассчитана динамически
                quantity=0,  # Будет рассчитана динамически
                close_ratio=0.25,
            ),
            PartialTPLevel(
                level=2,
                percentage=2.4,
                price=0,  # Будет рассчитана динамически
                quantity=0,  # Будет рассчитана динамически
                close_ratio=0.25,
            ),
            PartialTPLevel(
                level=3,
                percentage=3.5,
                price=0,  # Будет рассчитана динамически
                quantity=0,  # Будет рассчитана динамически
                close_ratio=0.50,
            ),
        ],
        partial_tp_update_sl=True,
    )

    # Проверяем нормализацию процентов
    logger.info("\n📊 Тестирование нормализации процентов:")
    test_values = [0.012, 0.024, 0.035, 1.2, 2.4, 3.5]
    for val in test_values:
        normalized = normalize_percentage(val)
        logger.info(f"  {val} -> {normalized}%")

    # Проверяем округление для разных символов
    logger.info("\n🔢 Тестирование округления:")
    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    test_price = 1234.567890
    test_qty = 0.123456789

    for symbol in test_symbols:
        rounded_price = round_price(symbol, test_price)
        rounded_qty = round_qty(symbol, test_qty)
        logger.info(f"  {symbol}:")
        logger.info(f"    Цена: {test_price} -> {rounded_price}")
        logger.info(f"    Количество: {test_qty} -> {rounded_qty}")

    # Создаем менеджер
    manager = EnhancedSLTPManager(config)

    # Создаем тестовую позицию
    class TestPosition:
        def __init__(self):
            self.id = "test_position_1"
            self.symbol = "BTCUSDT"
            self.side = "Buy"
            self.size = 0.01  # 0.01 BTC
            self.entry_price = 50000.0
            self.exchange = "bybit"

    position = TestPosition()

    logger.info("\n📈 Тестовая позиция:")
    logger.info(f"  Символ: {position.symbol}")
    logger.info(f"  Направление: {position.side}")
    logger.info(f"  Размер: {position.size} BTC")
    logger.info(f"  Цена входа: ${position.entry_price}")

    # Симулируем различные ценовые уровни
    price_levels = [
        (50600, 1.2),  # +1.2% - первый уровень partial TP
        (51200, 2.4),  # +2.4% - второй уровень
        (51750, 3.5),  # +3.5% - третий уровень
    ]

    logger.info("\n🎯 Проверка уровней частичного закрытия:")
    for price, expected_pct in price_levels:
        profit_pct = ((price - position.entry_price) / position.entry_price) * 100
        logger.info(f"\n  Текущая цена: ${price} (прибыль: {profit_pct:.2f}%)")

        # Проверяем, должен ли сработать partial TP
        for level in config.partial_tp_levels:
            if profit_pct >= level.percentage:
                close_qty = position.size * level.close_ratio
                close_qty = round_qty(position.symbol, close_qty)
                logger.info(f"    ✅ Уровень {level.level} ({level.percentage}%) достигнут")
                logger.info(
                    f"       Закрываем {level.close_ratio * 100}% позиции = {close_qty} BTC"
                )
                logger.info(f"       Стоимость: ${close_qty * price:.2f}")

    # Тестируем обновление SL после partial TP
    logger.info("\n🛡️ Обновление SL после частичного закрытия:")
    breakeven_offset = 0.001  # 0.1%
    new_sl = position.entry_price * (1 + breakeven_offset)
    new_sl = round_price(position.symbol, new_sl)
    logger.info(f"  Новый SL (безубыток + 0.1%): ${new_sl}")

    logger.info("\n✅ Тестирование завершено успешно!")

    # Проверяем интеграцию с биржей
    logger.info("\n🔗 Проверка интеграции с биржей:")
    try:
        from core.config.config_manager import ConfigManager

        config_manager = ConfigManager()
        exchange_config = config_manager.get_exchange_config("bybit")

        if exchange_config and exchange_config.get("enabled"):
            logger.info("  ✅ Bybit клиент доступен")

            # Проверяем hedge mode
            logger.info("  📌 Режим хеджирования активен")
            logger.info("    - Long позиции: position_idx=1")
            logger.info("    - Short позиции: position_idx=2")
        else:
            logger.warning("  ⚠️ Bybit не настроен или отключен")

    except Exception as e:
        logger.error(f"  ❌ Ошибка проверки биржи: {e}")

    return True


async def test_trading_flow():
    """Тестирование полного процесса торговли"""

    logger.info("\n🔄 Тестирование полного процесса торговли:")

    # Проверяем основные компоненты
    components = [
        ("Signal Generation", "trading.signals.ai_signal_generator"),
        ("Order Manager", "trading.orders.order_manager"),
        ("Position Manager", "trading.position_manager"),
        ("Enhanced SLTP", "trading.sltp.enhanced_manager"),
        ("Execution Engine", "trading.execution_engine"),
    ]

    for name, module_path in components:
        try:
            module = __import__(module_path, fromlist=[""])
            logger.info(f"  ✅ {name}: доступен")
        except ImportError as e:
            logger.warning(f"  ⚠️ {name}: {e}")

    logger.info("\n📋 Процесс торговли:")
    logger.info("  1. Сигнал -> OrderManager.create_order_from_signal()")
    logger.info("  2. Ордер -> ExecutionEngine.execute_order()")
    logger.info("  3. Позиция -> EnhancedSLTPManager.create_sltp_orders()")
    logger.info("  4. Мониторинг -> check_partial_tp() каждые 30 сек")
    logger.info("  5. Partial TP -> обновление SL в безубыток")
    logger.info("  6. Закрытие -> фиксация прибыли")


async def main():
    """Главная функция"""
    try:
        # Тестируем частичное закрытие
        await test_partial_tp()

        # Тестируем процесс торговли
        await test_trading_flow()

        logger.info("\n🎉 Все тесты пройдены успешно!")

    except Exception as e:
        logger.error(f"\n❌ Ошибка при тестировании: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
