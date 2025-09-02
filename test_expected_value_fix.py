#!/usr/bin/env python3
"""
Тест исправления ошибки expected_value
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import numpy as np
from datetime import datetime
from ml.ml_signal_processor import MLSignalProcessor

print("Тестирование исправления expected_value...")

# Создаем тестовый pred_dict как от новой модели
pred_dict = {
    "signal_type": "LONG",
    "confidence": 0.75,
    "signal_strength": 0.8,
    "primary_returns": {
        "15m": 0.001,
        "1h": 0.002,
        "4h": 0.003,
        "12h": 0.004
    },
    "risk_level": "MEDIUM",
    "risk_metrics": {
        "max_drawdown_1h": 0.015,
        "max_drawdown_4h": 0.025,
        "volatility": 0.02
    },
    "stop_loss_pct": 0.02,
    "take_profit_pct": 0.05
}

# Создаем процессор
processor = MLSignalProcessor(ml_manager=None, config={})

# Тестируем метод
try:
    import asyncio
    
    async def test():
        result = await processor._convert_predictions_to_signal(
            symbol="BTCUSDT",
            predictions=pred_dict,
            current_price=50000.0
        )
        
        if result:
            print(f"✅ Сигнал создан успешно!")
            print(f"   Тип: {result.signal_type}")
            print(f"   Уверенность: {result.confidence:.2%}")
            if "expected_value" in result.indicators:
                print(f"   Expected Value: {result.indicators['expected_value']:.4f}")
            return True
        else:
            print("⚠️ Сигнал не создан")
            return False
    
    success = asyncio.run(test())
    
    if success:
        print("🎉 Исправление работает корректно!")
    else:
        print("❌ Требуется дополнительная проверка")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()