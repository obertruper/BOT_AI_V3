#!/usr/bin/env python3
"""
Быстрый тест торгового движка с новой конфигурацией риска
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from trading.engine import TradingEngine


async def quick_trading_test():
    """Быстрый тест создания ордера с новой конфигурацией риска"""

    print("=" * 60)
    print("БЫСТРЫЙ ТЕСТ ТОРГОВОГО ДВИЖКА")
    print("=" * 60)

    try:
        # Загружаем конфигурацию
        config_manager = ConfigManager()
        await config_manager.initialize()
        config = config_manager.get_config()

        # Инициализируем торговый движок
        trading_engine = TradingEngine(config)
        await trading_engine.initialize()

        print("✅ TradingEngine инициализирован")

        # Создаем тестовый сигнал
        test_signal = {
            "id": "test_signal_001",
            "symbol": "BTC/USDT",
            "side": "buy",
            "action": "open",
            "entry_price": 95000.0,
            "stop_loss": 94050.0,
            "take_profit": 96900.0,
            "confidence": 0.75,
            "leverage": 5,
            "strategy": "ml_test",
            "timestamp": "2025-08-19T14:00:00Z",
        }

        print("\n📊 Тестовый сигнал:")
        print(f"  Символ: {test_signal['symbol']}")
        print(f"  Сторона: {test_signal['side']}")
        print(f"  Цена входа: ${test_signal['entry_price']}")
        print(f"  Плечо: {test_signal['leverage']}x")

        # Обрабатываем сигнал
        print("\n🔄 Обработка сигнала...")
        result = await trading_engine.process_signal(test_signal)

        if result:
            print("✅ Сигнал успешно обработан")
        else:
            print("❌ Сигнал отклонен")

        print("\n📈 Проверим статистику движка...")
        stats = trading_engine.get_stats() if hasattr(trading_engine, "get_stats") else {}
        print(f"  Статистика: {stats}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()

    print("\n✅ Тест завершен")


if __name__ == "__main__":
    asyncio.run(quick_trading_test())
