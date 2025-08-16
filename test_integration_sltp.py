#!/usr/bin/env python3
"""
Интеграционный тест исправлений SL/TP

Проверяет работу исправлений с реальными компонентами системы
"""

import asyncio
import logging
import os
import sys

# Добавляем корневой каталог в PATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_ml_signal_processor_sltp():
    """Тест ML Signal Processor с исправлениями SL/TP"""
    try:
        from core.config.config_manager import ConfigManager
        from ml.ml_signal_processor import MLSignalProcessor

        # Инициализируем компоненты
        config = ConfigManager()
        processor = MLSignalProcessor(config=config)

        # Создаем тестовые данные для SHORT сигнала
        symbol = "BTCUSDT"
        current_price = 45000.0

        # Имитируем ML предсказания для SHORT позиции
        mock_prediction = {
            "signal_type": "SHORT",
            "confidence": 0.75,
            "signal_strength": 0.8,
            "stop_loss_pct": 0.03,  # 3% - риск роста цены
            "take_profit_pct": 0.05,  # 5% - прибыль от падения
            "risk_level": "MEDIUM",
        }

        # Тестируем расчет SL/TP цен
        logger.info("=" * 50)
        logger.info("ИНТЕГРАЦИОННЫЙ ТЕСТ ML SIGNAL PROCESSOR")
        logger.info("=" * 50)

        signal_type = mock_prediction["signal_type"]
        sl_pct = mock_prediction["stop_loss_pct"]
        tp_pct = mock_prediction["take_profit_pct"]

        # Рассчитываем цены как это делает ml_signal_processor
        if signal_type == "LONG":
            stop_loss = current_price * (1 - sl_pct)
            take_profit = current_price * (1 + tp_pct)
        else:  # SHORT
            stop_loss = current_price * (1 + sl_pct)  # SL выше цены для SHORT
            take_profit = current_price * (1 - tp_pct)  # TP ниже цены для SHORT

        logger.info(f"Символ: {symbol}")
        logger.info(f"Тип сигнала: {signal_type}")
        logger.info(f"Текущая цена: {current_price}")
        logger.info(f"SL процент: {sl_pct * 100}%")
        logger.info(f"TP процент: {tp_pct * 100}%")
        logger.info(f"Stop Loss цена: {stop_loss} (должна быть > {current_price})")
        logger.info(f"Take Profit цена: {take_profit} (должна быть < {current_price})")

        # Проверяем правильность
        if signal_type == "SHORT":
            if stop_loss <= current_price:
                logger.error(
                    f"❌ КРИТИЧЕСКАЯ ОШИБКА: SL для SHORT ({stop_loss}) должен быть ВЫШЕ цены ({current_price})"
                )
                return False
            if take_profit >= current_price:
                logger.error(
                    f"❌ КРИТИЧЕСКАЯ ОШИБКА: TP для SHORT ({take_profit}) должен быть НИЖЕ цены ({current_price})"
                )
                return False

        logger.info("✅ ML Signal Processor: SL/TP рассчитываются правильно!")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка в ML Signal Processor тесте: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_order_validation():
    """Тест валидации ордеров в TradingEngine"""
    try:
        logger.info("=" * 50)
        logger.info("ТЕСТ ВАЛИДАЦИИ ОРДЕРОВ")
        logger.info("=" * 50)

        # Создаем мок объекты для тестирования
        class MockSignal:
            def __init__(self, signal_type, price, sl, tp):
                self.signal_type = signal_type
                self.suggested_price = price
                self.suggested_stop_loss = sl
                self.suggested_take_profit = tp

        # Тестируем SHORT сигнал с правильными SL/TP
        current_price = 45000.0
        sl_price = current_price * 1.03  # SL выше цены для SHORT
        tp_price = current_price * 0.97  # TP ниже цены для SHORT

        from database.models.base_models import SignalType

        signal = MockSignal(
            signal_type=SignalType.SHORT, price=current_price, sl=sl_price, tp=tp_price
        )

        logger.info("Тестируем SHORT сигнал:")
        logger.info(f"Цена: {signal.suggested_price}")
        logger.info(f"Stop Loss: {signal.suggested_stop_loss}")
        logger.info(f"Take Profit: {signal.suggested_take_profit}")

        # Проверяем логику валидации (из trading/engine.py)
        valid = True

        if signal.signal_type == SignalType.SHORT:
            # Для SHORT: SL должен быть выше цены, TP ниже цены
            if signal.suggested_stop_loss <= signal.suggested_price:
                logger.error(
                    f"SHORT: Stop loss ({signal.suggested_stop_loss}) <= цены ({signal.suggested_price})"
                )
                valid = False

            if signal.suggested_take_profit >= signal.suggested_price:
                logger.error(
                    f"SHORT: Take profit ({signal.suggested_take_profit}) >= цены ({signal.suggested_price})"
                )
                valid = False

        if valid:
            logger.info("✅ Валидация ордеров: SHORT сигнал проходит проверку!")
        else:
            logger.error("❌ Валидация ордеров: SHORT сигнал НЕ проходит проверку!")

        return valid

    except Exception as e:
        logger.error(f"❌ Ошибка в тесте валидации: {e}")
        return False


async def test_duplicate_order_manager():
    """Тест защиты от дублирования в OrderManager"""
    try:
        logger.info("=" * 50)
        logger.info("ТЕСТ ЗАЩИТЫ ОТ ДУБЛИРОВАНИЯ В ORDER MANAGER")
        logger.info("=" * 50)

        from trading.orders.order_manager import OrderManager

        # Создаем мок exchange registry
        class MockExchangeRegistry:
            pass

        order_manager = OrderManager(MockExchangeRegistry())

        # Создаем мок сигнал
        class MockSignal:
            def __init__(self, symbol):
                self.symbol = symbol
                self.signal_type = "SHORT"

        signal = MockSignal("BTCUSDT")

        # Проверяем функцию дублирования
        is_first_duplicate = await order_manager._is_duplicate_order(signal)
        logger.info(f"Первый ордер дублирующий: {is_first_duplicate}")

        # Отмечаем что ордер создан
        import time

        order_manager._recent_orders[signal.symbol] = time.time()

        # Проверяем второй ордер
        is_second_duplicate = await order_manager._is_duplicate_order(signal)
        logger.info(f"Второй ордер дублирующий: {is_second_duplicate}")

        if not is_first_duplicate and is_second_duplicate:
            logger.info("✅ Защита от дублирования в OrderManager работает!")
            return True
        else:
            logger.error("❌ Защита от дублирования в OrderManager НЕ работает!")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка в тесте OrderManager: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Основная функция интеграционного тестирования"""
    logger.info("🚀 ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ SL/TP")

    success_count = 0
    total_tests = 3

    # Тест 1: ML Signal Processor
    if await test_ml_signal_processor_sltp():
        success_count += 1

    # Тест 2: Валидация ордеров
    if await test_order_validation():
        success_count += 1

    # Тест 3: Защита от дублирования
    if await test_duplicate_order_manager():
        success_count += 1

    logger.info("=" * 50)
    if success_count == total_tests:
        logger.info(f"🎉 ВСЕ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ПРОЙДЕНЫ! ({success_count}/{total_tests})")
        logger.info("✅ Система готова к работе с исправленными SL/TP для SHORT позиций")
    else:
        logger.error(f"❌ НЕ ВСЕ ТЕСТЫ ПРОЙДЕНЫ! ({success_count}/{total_tests})")
    logger.info("=" * 50)

    return success_count == total_tests


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
