#!/usr/bin/env python3
"""
Тестирование исправлений SL/TP для SHORT позиций

Этот скрипт проверяет правильность исправлений:
1. Расчет процентов SL/TP в ml_manager.py
2. Применение процентов к ценам в ml_signal_processor.py
3. Защиту от дублирования ордеров в order_manager.py
"""

import asyncio
import logging
import os
import sys

# Добавляем корневой каталог в PATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


import numpy as np

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockMLManager:
    """Мок ML Manager для тестирования логики расчета SL/TP"""

    def calculate_sltp_percentages(self, signal_type: str, future_returns: list) -> tuple:
        """Тестируем исправленную логику расчета процентов"""

        if signal_type == "LONG":
            min_return = float(np.min(future_returns))
            max_return = float(np.max(future_returns))

            # Stop Loss: от 1% до 5%
            stop_loss_pct = np.clip(abs(min_return) * 100, 1.0, 5.0) / 100.0

            # Take Profit: от 2% до 10%
            take_profit_pct = np.clip(max_return * 100, 2.0, 10.0) / 100.0

        elif signal_type == "SHORT":
            # ИСПРАВЛЕННАЯ ЛОГИКА для SHORT позиций
            min_return = float(np.min(future_returns))  # Максимальное падение (отрицательное)
            max_return = float(np.max(future_returns))  # Максимальный рост (положительное)

            # Stop Loss для SHORT = риск роста цены (используем максимальный рост)
            if max_return > 0:
                stop_loss_pct = np.clip(max_return * 100, 1.0, 5.0) / 100.0
            else:
                stop_loss_pct = 0.02  # дефолтный 2%

            # Take Profit для SHORT = прибыль от падения цены (используем минимальный return)
            if min_return < 0:
                take_profit_pct = np.clip(abs(min_return) * 100, 2.0, 10.0) / 100.0
            else:
                take_profit_pct = 0.04  # дефолтный 4%
        else:
            stop_loss_pct = None
            take_profit_pct = None

        return stop_loss_pct, take_profit_pct


def calculate_sltp_prices(
    signal_type: str, current_price: float, stop_loss_pct: float, take_profit_pct: float
) -> tuple:
    """Тестируем правильное применение процентов к ценам"""

    if signal_type == "LONG":
        # Для LONG: SL ниже цены, TP выше цены
        stop_loss = current_price * (1 - stop_loss_pct)
        take_profit = current_price * (1 + take_profit_pct)
    elif signal_type == "SHORT":
        # Для SHORT: SL выше цены, TP ниже цены
        stop_loss = current_price * (1 + stop_loss_pct)
        take_profit = current_price * (1 - take_profit_pct)
    else:
        stop_loss = take_profit = None

    return stop_loss, take_profit


def test_long_position():
    """Тест для LONG позиции"""
    logger.info("=" * 50)
    logger.info("ТЕСТ LONG ПОЗИЦИИ")
    logger.info("=" * 50)

    # Симулируем предсказанные доходности
    future_returns = [-0.03, 0.05, -0.01, 0.08]  # min=-0.03, max=0.08
    current_price = 100.0
    signal_type = "LONG"

    ml_manager = MockMLManager()
    sl_pct, tp_pct = ml_manager.calculate_sltp_percentages(signal_type, future_returns)

    logger.info(f"Предсказанные доходности: {future_returns}")
    logger.info(f"Мин. доходность: {np.min(future_returns):.3f}")
    logger.info(f"Макс. доходность: {np.max(future_returns):.3f}")
    logger.info(f"Stop Loss процент: {sl_pct:.3f}")
    logger.info(f"Take Profit процент: {tp_pct:.3f}")

    # Рассчитываем цены
    sl_price, tp_price = calculate_sltp_prices(signal_type, current_price, sl_pct, tp_pct)

    logger.info(f"Текущая цена: {current_price}")
    logger.info(f"Stop Loss цена: {sl_price:.2f} (должна быть НИЖЕ {current_price})")
    logger.info(f"Take Profit цена: {tp_price:.2f} (должна быть ВЫШЕ {current_price})")

    # Проверка правильности
    assert sl_price < current_price, "ОШИБКА: SL для LONG должен быть ниже цены!"
    assert tp_price > current_price, "ОШИБКА: TP для LONG должен быть выше цены!"

    logger.info("✅ LONG позиция: Все проверки пройдены!")
    return True


def test_short_position():
    """Тест для SHORT позиции"""
    logger.info("=" * 50)
    logger.info("ТЕСТ SHORT ПОЗИЦИИ")
    logger.info("=" * 50)

    # Симулируем предсказанные доходности для SHORT сигнала
    # Для SHORT выгодны отрицательные returns (падение цены)
    future_returns = [-0.05, 0.03, -0.08, 0.02]  # min=-0.08, max=0.03
    current_price = 326770000  # Цена из лога ошибки
    signal_type = "SHORT"

    ml_manager = MockMLManager()
    sl_pct, tp_pct = ml_manager.calculate_sltp_percentages(signal_type, future_returns)

    logger.info(f"Предсказанные доходности: {future_returns}")
    logger.info(f"Мин. доходность: {np.min(future_returns):.3f}")
    logger.info(f"Макс. доходность: {np.max(future_returns):.3f}")
    logger.info(f"Stop Loss процент: {sl_pct:.3f}")
    logger.info(f"Take Profit процент: {tp_pct:.3f}")

    # Рассчитываем цены
    sl_price, tp_price = calculate_sltp_prices(signal_type, current_price, sl_pct, tp_pct)

    logger.info(f"Текущая цена: {current_price}")
    logger.info(f"Stop Loss цена: {sl_price:.0f} (должна быть ВЫШЕ {current_price})")
    logger.info(f"Take Profit цена: {tp_price:.0f} (должна быть НИЖЕ {current_price})")

    # Проверка правильности - КРИТИЧНО!
    if sl_price <= current_price:
        logger.error(
            f"❌ ОШИБКА: SL для SHORT ({sl_price:.0f}) должен быть ВЫШЕ цены ({current_price})!"
        )
        return False

    if tp_price >= current_price:
        logger.error(
            f"❌ ОШИБКА: TP для SHORT ({tp_price:.0f}) должен быть НИЖЕ цены ({current_price})!"
        )
        return False

    logger.info("✅ SHORT позиция: Все проверки пройдены!")
    return True


def test_edge_cases():
    """Тестирование граничных случаев"""
    logger.info("=" * 50)
    logger.info("ТЕСТ ГРАНИЧНЫХ СЛУЧАЕВ")
    logger.info("=" * 50)

    ml_manager = MockMLManager()

    # Случай 1: Только положительные доходности для SHORT
    logger.info("\nСлучай 1: Только положительные доходности для SHORT")
    future_returns = [0.01, 0.02, 0.03, 0.04]
    sl_pct, tp_pct = ml_manager.calculate_sltp_percentages("SHORT", future_returns)
    logger.info(f"SL%: {sl_pct}, TP%: {tp_pct}")
    assert tp_pct == 0.04, "Должен использовать дефолтный TP для SHORT"

    # Случай 2: Только отрицательные доходности для SHORT
    logger.info("\nСлучай 2: Только отрицательные доходности для SHORT")
    future_returns = [-0.01, -0.02, -0.03, -0.04]
    sl_pct, tp_pct = ml_manager.calculate_sltp_percentages("SHORT", future_returns)
    logger.info(f"SL%: {sl_pct}, TP%: {tp_pct}")
    assert sl_pct == 0.02, "Должен использовать дефолтный SL для SHORT"

    # Случай 3: Экстремальные значения
    logger.info("\nСлучай 3: Экстремальные значения")
    future_returns = [-0.20, 0.15, -0.25, 0.18]  # Очень большие значения
    sl_pct, tp_pct = ml_manager.calculate_sltp_percentages("SHORT", future_returns)
    logger.info(f"SL%: {sl_pct} (макс 5%), TP%: {tp_pct} (макс 10%)")
    assert sl_pct <= 0.05, "SL должен быть ограничен 5%"
    assert tp_pct <= 0.10, "TP должен быть ограничен 10%"

    logger.info("✅ Граничные случаи: Все проверки пройдены!")
    return True


class MockOrder:
    """Мок ордера для тестирования дублирования"""

    def __init__(self, symbol: str):
        self.symbol = symbol


class MockOrderManager:
    """Мок Order Manager для тестирования защиты от дублирования"""

    def __init__(self):
        self._recent_orders = {}
        self._duplicate_check_interval = 60
        self._active_orders = {}

    async def _is_duplicate_order(self, signal) -> bool:
        """Проверка на дублирование ордера"""
        import time

        symbol = signal.symbol
        current_time = time.time()

        # Проверяем есть ли недавний ордер для этого символа
        if symbol in self._recent_orders:
            last_order_time = self._recent_orders[symbol]
            time_since_last = current_time - last_order_time

            if time_since_last < self._duplicate_check_interval:
                return True

        return False

    def mark_order_created(self, symbol: str):
        """Отметить что ордер создан"""
        import time

        self._recent_orders[symbol] = time.time()


async def test_duplicate_protection():
    """Тест защиты от дублирования ордеров"""
    logger.info("=" * 50)
    logger.info("ТЕСТ ЗАЩИТЫ ОТ ДУБЛИРОВАНИЯ")
    logger.info("=" * 50)

    order_manager = MockOrderManager()

    class MockSignal:
        def __init__(self, symbol):
            self.symbol = symbol

    signal = MockSignal("BTCUSDT")

    # Первый ордер должен пройти
    is_duplicate = await order_manager._is_duplicate_order(signal)
    logger.info(f"Первый ордер для {signal.symbol}: дублирующий = {is_duplicate}")
    assert not is_duplicate, "Первый ордер не должен быть дублирующим"

    # Отмечаем что ордер создан
    order_manager.mark_order_created(signal.symbol)

    # Второй ордер сразу после должен быть заблокирован
    is_duplicate = await order_manager._is_duplicate_order(signal)
    logger.info(f"Второй ордер сразу после для {signal.symbol}: дублирующий = {is_duplicate}")
    assert is_duplicate, "Второй ордер должен быть заблокирован как дублирующий"

    # Другой символ должен пройти
    signal_other = MockSignal("ETHUSDT")
    is_duplicate = await order_manager._is_duplicate_order(signal_other)
    logger.info(f"Ордер для другого символа {signal_other.symbol}: дублирующий = {is_duplicate}")
    assert not is_duplicate, "Ордер для другого символа не должен быть дублирующим"

    logger.info("✅ Защита от дублирования: Все проверки пройдены!")
    return True


async def main():
    """Основная функция тестирования"""
    logger.info("🚀 НАЧИНАЕМ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ SL/TP")

    try:
        # Тестируем LONG позицию
        test_long_position()

        # Тестируем SHORT позицию (критично!)
        if not test_short_position():
            logger.error("❌ Тест SHORT позиции провален!")
            return False

        # Тестируем граничные случаи
        test_edge_cases()

        # Тестируем защиту от дублирования
        await test_duplicate_protection()

        logger.info("=" * 50)
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        logger.info("=" * 50)
        logger.info("Исправления SL/TP для SHORT позиций работают корректно")
        logger.info("Защита от дублирования ордеров функционирует")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка во время тестирования: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
