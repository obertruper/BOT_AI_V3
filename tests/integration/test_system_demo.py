#!/usr/bin/env python3
"""
Демонстрация работы системы BOT_AI_V3 в тестовом режиме
Показывает весь процесс от генерации сигнала до создания ордера
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from core.config.config_manager import ConfigManager

# Импортируем компоненты системы
from core.logger import setup_logger
from core.logging.trade_logger import TradeLogger
from database.models.signal import Signal  # Правильный импорт

logger = setup_logger("test_demo")


async def create_test_signal() -> Signal:
    """Создаем тестовый сигнал для демонстрации"""

    signal = Signal(
        symbol="BTCUSDT",
        exchange="BYBIT",
        signal_type="LONG",
        entry_price=Decimal("45000"),
        stop_loss=Decimal("44100"),  # 2% стоп
        take_profit=Decimal("46350"),  # 3% профит
        confidence=Decimal("0.75"),
        strength=Decimal("0.8"),
        source="TEST_DEMO",
        metadata={
            "reason": "Демонстрация работы системы",
            "risk_reward": "1:1.5",
            "timeframe": "15m",
        },
    )

    logger.info(
        f"""
    ===== СОЗДАН ТЕСТОВЫЙ СИГНАЛ =====
    Символ: {signal.symbol}
    Тип: {signal.signal_type}
    Вход: ${signal.entry_price}
    Стоп: ${signal.stop_loss} (-2%)
    Тейк: ${signal.take_profit} (+3%)
    Уверенность: {signal.confidence}
    ==================================
    """
    )

    return signal


async def demonstrate_position_calculation():
    """Демонстрация расчета позиции по методу из V2"""

    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Параметры из конфига
    fixed_balance = Decimal(
        str(
            config.get("trading", {})
            .get("risk_management", {})
            .get("fixed_risk_balance", 500)
        )
    )
    risk_per_trade = Decimal(
        str(
            config.get("trading", {})
            .get("risk_management", {})
            .get("risk_per_trade", 0.02)
        )
    )
    leverage = Decimal(
        str(config.get("trading", {}).get("orders", {}).get("default_leverage", 5))
    )

    # Пример расчета для BTC по $45000
    entry_price = Decimal("45000")

    # Формула из V2
    position_value_usd = fixed_balance * risk_per_trade * leverage
    position_size_btc = position_value_usd / entry_price

    logger.info(
        f"""
    ===== РАСЧЕТ РАЗМЕРА ПОЗИЦИИ (МЕТОД V2) =====

    Параметры из конфига:
    - Фиксированный баланс: ${fixed_balance}
    - Риск на сделку: {risk_per_trade * 100}%
    - Плечо: {leverage}x
    - Цена входа: ${entry_price}

    Расчет:
    1. Сумма позиции = ${fixed_balance} × {risk_per_trade} × {leverage} = ${position_value_usd}
    2. Размер в BTC = ${position_value_usd} ÷ ${entry_price} = {position_size_btc:.6f} BTC

    Проверка:
    - Нотационная стоимость: {position_size_btc:.6f} BTC × ${entry_price} = ${position_size_btc * entry_price}
    - С плечом {leverage}x требуется маржа: ${position_value_usd / leverage}
    - Максимальный убыток (2% движение): ${position_value_usd * Decimal("0.02")}
    ===============================================
    """
    )

    return position_size_btc


async def demonstrate_sltp_levels():
    """Демонстрация уровней частичного закрытия из V2"""

    logger.info(
        """
    ===== СИСТЕМА ЧАСТИЧНОГО ЗАКРЫТИЯ (ИЗ V2) =====

    Take Profit уровни:
    - TP1: +1% от входа → закрыть 30% позиции
    - TP2: +2% от входа → закрыть 30% позиции
    - TP3: +3% от входа → закрыть 40% позиции

    Trailing Stop:
    - Активация: при достижении +1% прибыли
    - Шаг: 0.5% от текущей цены

    Защита прибыли:
    - При +0.5%: переместить стоп в безубыток
    - При +1%: зафиксировать 0.5% прибыли
    - При +2%: зафиксировать 1% прибыли
    - При +3%: зафиксировать 2% прибыли

    Пример для входа $45000:
    - TP1: $45,450 (+1%) → закрыть 30%
    - TP2: $45,900 (+2%) → закрыть 30%
    - TP3: $46,350 (+3%) → закрыть 40%
    - Initial SL: $44,100 (-2%)
    ================================================
    """
    )


async def demonstrate_logging_stages():
    """Демонстрация всех этапов логирования"""

    trade_logger = TradeLogger()

    # Этапы торговли с подробным логированием
    stages = [
        ("1. Получение сигнала", "Signal received from ML/Strategy"),
        ("2. Валидация сигнала", "Signal validation passed"),
        ("3. Расчет позиции", "Position size calculated: 0.001111 BTC"),
        ("4. Проверка риска", "Risk check passed: 2% of balance"),
        ("5. Создание ордера", "Market order created"),
        ("6. Отправка на биржу", "Order sent to exchange"),
        ("7. Подтверждение", "Order filled at $45,000"),
        ("8. Установка SL/TP", "Stop Loss at $44,100, Take Profit at $46,350"),
        ("9. Мониторинг позиции", "Position monitoring active"),
        ("10. Частичное закрытие", "TP1 hit: 30% closed at $45,450"),
        ("11. Обновление стопа", "Trailing stop moved to $45,225"),
        ("12. Финальное закрытие", "Position closed, profit: +$15.50"),
    ]

    logger.info(
        """
    ===== ЭТАПЫ ЛОГИРОВАНИЯ СДЕЛКИ =====

    Каждый этап полностью логируется:
    """
    )

    for stage, description in stages:
        logger.info(f"  {stage}: {description}")
        await asyncio.sleep(0.1)  # Имитация процесса

    logger.info(
        """

    Все логи сохраняются в:
    - data/logs/trading.log - основной лог
    - data/logs/trades/ - детальные логи сделок
    - PostgreSQL таблицы: trades, orders, signals
    =====================================
    """
    )


async def main():
    """Главная функция демонстрации"""

    print(
        """
    ╔══════════════════════════════════════════════════╗
    ║         BOT_AI_V3 - ДЕМОНСТРАЦИЯ СИСТЕМЫ        ║
    ║                                                  ║
    ║  Показывает работу системы без реальных API     ║
    ╚══════════════════════════════════════════════════╝
    """
    )

    await asyncio.sleep(1)

    # 1. Создаем тестовый сигнал
    signal = await create_test_signal()
    await asyncio.sleep(1)

    # 2. Демонстрируем расчет позиции
    position_size = await demonstrate_position_calculation()
    await asyncio.sleep(1)

    # 3. Показываем уровни SL/TP
    await demonstrate_sltp_levels()
    await asyncio.sleep(1)

    # 4. Демонстрируем этапы логирования
    await demonstrate_logging_stages()

    print(
        """
    ╔══════════════════════════════════════════════════╗
    ║              ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА              ║
    ║                                                  ║
    ║  Для работы с реальной торговлей необходимо:    ║
    ║  1. Получить новые API ключи Bybit              ║
    ║  2. Обновить их в файле .env                    ║
    ║  3. Запустить: python unified_launcher.py       ║
    ╚══════════════════════════════════════════════════╝
    """
    )


if __name__ == "__main__":
    asyncio.run(main())
