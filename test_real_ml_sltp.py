#!/usr/bin/env python3
"""
Тест реальных ML компонентов с исправлениями SL/TP
"""

import asyncio
import logging
import os
import sys

# Добавляем корневой каталог в PATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_ml_manager_sltp():
    """Тест MLManager с реальными данными"""
    try:
        from core.config.config_manager import ConfigManager
        from ml.ml_manager import MLManager

        config = ConfigManager()
        ml_manager = MLManager(config)

        logger.info("🔬 ТЕСТ ML MANAGER С РЕАЛЬНЫМИ ДАННЫМИ")
        logger.info("=" * 50)

        # Симулируем реальные ML предсказания
        mock_predictions = {
            "directions": [1, 1, 1, 1],  # 4 SHORT голоса
            "returns_15m": 0.02,  # +2% ожидается (плохо для SHORT)
            "returns_1h": -0.03,  # -3% ожидается (хорошо для SHORT)
            "returns_4h": 0.01,  # +1% ожидается (плохо для SHORT)
            "returns_24h": -0.05,  # -5% ожидается (хорошо для SHORT)
            "confidence": 0.75,
        }

        # Создаем future_returns
        future_returns = [
            mock_predictions["returns_15m"],
            mock_predictions["returns_1h"],
            mock_predictions["returns_4h"],
            mock_predictions["returns_24h"],
        ]

        logger.info(f"Предсказанные доходности: {future_returns}")
        logger.info(f"Мин. доходность: {min(future_returns):.3f}")
        logger.info(f"Макс. доходность: {max(future_returns):.3f}")

        # Вызываем функцию _generate_signal_with_predictions напрямую для тестирования
        result = await ml_manager._generate_signal_with_predictions(
            "BTCUSDT", mock_predictions, future_returns, 45000.0
        )

        if result:
            signal_type = result.get("signal_type")
            sl_pct = result.get("stop_loss_pct")
            tp_pct = result.get("take_profit_pct")

            logger.info(f"Тип сигнала: {signal_type}")
            logger.info(f"Stop Loss процент: {sl_pct:.3f}")
            logger.info(f"Take Profit процент: {tp_pct:.3f}")

            if signal_type == "SHORT":
                # Проверяем правильность логики для SHORT
                max_return = max(future_returns)  # 0.02 (рост цены - риск для SHORT)
                min_return = min(future_returns)  # -0.05 (падение - прибыль для SHORT)

                logger.info(
                    f"Ожидаемый SL% (на основе max_return {max_return}): {max_return * 100:.1f}%"
                )
                logger.info(
                    f"Ожидаемый TP% (на основе |min_return| {abs(min_return)}): {abs(min_return) * 100:.1f}%"
                )

                # Проверяем что проценты рассчитаны правильно
                if sl_pct and tp_pct:
                    current_price = 45000.0
                    sl_price = current_price * (1 + sl_pct)  # SL выше для SHORT
                    tp_price = current_price * (1 - tp_pct)  # TP ниже для SHORT

                    logger.info(f"Цена: {current_price}")
                    logger.info(
                        f"Stop Loss цена: {sl_price:.2f} (выше цены? {sl_price > current_price})"
                    )
                    logger.info(
                        f"Take Profit цена: {tp_price:.2f} (ниже цены? {tp_price < current_price})"
                    )

                    if sl_price > current_price and tp_price < current_price:
                        logger.info("✅ ML Manager: SL/TP для SHORT рассчитаны правильно!")
                        return True
                    else:
                        logger.error("❌ ML Manager: Неправильные SL/TP для SHORT!")
                        return False

        logger.error("❌ ML Manager: Не получен результат от _generate_signal_with_predictions")
        return False

    except Exception as e:
        logger.error(f"❌ Ошибка в ML Manager тесте: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Основная функция"""
    logger.info("🚀 ТЕСТ РЕАЛЬНЫХ ML КОМПОНЕНТОВ")

    success = await test_ml_manager_sltp()

    logger.info("=" * 50)
    if success:
        logger.info("🎉 РЕАЛЬНЫЕ ML КОМПОНЕНТЫ: Исправления работают!")
    else:
        logger.error("❌ РЕАЛЬНЫЕ ML КОМПОНЕНТЫ: Есть проблемы!")
    logger.info("=" * 50)

    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
