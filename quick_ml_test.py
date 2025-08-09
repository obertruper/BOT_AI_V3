#!/usr/bin/env python3
"""
Быстрая проверка ML предсказаний после исправлений
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from data.data_loader import DataLoader
from ml.ml_manager_singleton import get_ml_manager


async def quick_test():
    """Быстрый тест ML предсказаний"""
    print("🚀 Быстрая проверка ML системы...")

    # Инициализация
    config_manager = ConfigManager()
    data_loader = DataLoader(config_manager)

    # Получаем ML Manager через singleton
    print("🔄 Получаем ML Manager (singleton)...")
    ml_manager = await get_ml_manager(config_manager._config)
    print(f"✅ ML Manager инициализирован на {ml_manager.device}")

    # Логируем детали GPU если используется
    if ml_manager.device.type == "cuda":
        import torch

        gpu_idx = ml_manager.device.index or 0
        props = torch.cuda.get_device_properties(gpu_idx)
        print(f"   GPU: {props.name}")
        print(f"   Memory: {props.total_memory / 1024**3:.1f}GB")
        print(f"   Compute Capability: {props.major}.{props.minor}")

    # Загружаем данные
    symbol = "BTCUSDT"
    print(f"\n📊 Загружаем данные {symbol}...")
    data = await data_loader.get_data_for_ml(symbol, limit=300)

    if data is None or len(data) < 240:
        print(f"❌ Недостаточно данных: {len(data) if data else 0}")
        return

    print(f"✅ Загружено {len(data)} свечей")
    print(f"   Последняя цена: ${data['close'].iloc[-1]:,.2f}")

    # Генерируем предсказание
    print("\n🔮 Генерируем предсказание...")
    prediction = await ml_manager.predict(data)

    if not prediction:
        print("❌ Предсказание не сгенерировано")
        return

    # Выводим результаты
    print("\n📈 РЕЗУЛЬТАТ ПРЕДСКАЗАНИЯ:")
    print(f"   Направление: {prediction['signal_type']}")
    if "weighted_direction" in prediction:
        print(f"   Сила: {prediction['weighted_direction']:.6f}")
    print(f"   Уверенность: {prediction['confidence']:.2%}")
    print(f"   Stop Loss: ${prediction['stop_loss']:,.2f}")
    print(f"   Take Profit: ${prediction['take_profit']:,.2f}")

    # Показываем все поля для диагностики
    print("\n📊 Все поля предсказания:")
    for key, value in prediction.items():
        if key not in ["signal_type", "confidence", "stop_loss", "take_profit"]:
            print(f"   {key}: {value}")

    # Проверяем разнообразие
    if prediction["signal_type"] == "NEUTRAL":
        print("\n⚠️ Предсказание NEUTRAL")
    else:
        print(f"\n✅ Предсказание разнообразное: {prediction['signal_type']}!")


if __name__ == "__main__":
    asyncio.run(quick_test())
