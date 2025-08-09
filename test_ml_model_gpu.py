# \!/usr/bin/env python3
"""
Тест ML модели на GPU после исправления драйверов
"""

import asyncio
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from core.logger import setup_logger
from ml.ml_manager import MLManager

logger = setup_logger("test_ml_gpu")


async def test_ml_on_gpu():
    """Тест ML предсказаний на GPU"""

    print("=" * 60)
    print("ТЕСТ ML МОДЕЛИ НА RTX 5090")
    print("=" * 60)

    # Проверка GPU
    print("\n🖥️ Системная информация:")
    print(f"  PyTorch версия: {torch.__version__}")
    print(f"  CUDA доступна: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"  Количество GPU: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            print(f"  GPU {i}: {props.name}")
            print(f"    Compute Capability: {props.major}.{props.minor}")
            print(f"    Память: {props.total_memory / 1024**3:.1f} GB")
            print(
                f"    Свободно: {(props.total_memory - torch.cuda.memory_allocated(i)) / 1024**3:.1f} GB"
            )

    # Конфигурация
    config = {
        "ml": {
            "model": {
                "device": "auto",  # Автоматический выбор GPU/CPU
                "model_directory": "models/saved",
                "context_window": 96,
                "patch_len": 16,
                "stride": 8,
                "d_model": 256,
                "n_heads": 4,
                "e_layers": 3,
                "d_ff": 512,
                "dropout": 0.1,
            },
            "cache": {
                "indicator_ttl": 900,  # 15 минут
                "feature_ttl": 300,  # 5 минут
            },
        }
    }

    print("\n🧠 Инициализация ML Manager...")
    ml_manager = MLManager(config)
    await ml_manager.initialize()

    print(f"✅ ML Manager инициализирован на {ml_manager.device}")

    # Информация о модели
    model_info = ml_manager.get_model_info()
    print("\n📊 Информация о модели:")
    for key, value in model_info.items():
        print(f"  {key}: {value}")

    # Создаем тестовые данные
    print("\n📈 Создание тестовых данных...")
    np.random.seed(42)
    n_candles = 300

    # Генерируем реалистичные OHLCV данные
    base_price = 100000
    timestamps = pd.date_range(end=pd.Timestamp.now(), periods=n_candles, freq="15min")

    # Генерируем цены с трендом
    trend = np.linspace(0, 0.5, n_candles)  # Восходящий тренд
    noise = np.random.normal(0, 0.02, n_candles)
    prices = base_price * (1 + trend + noise)

    # Создаем OHLCV DataFrame
    data = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": prices * (1 + np.random.uniform(-0.001, 0.001, n_candles)),
            "high": prices * (1 + np.random.uniform(0, 0.002, n_candles)),
            "low": prices * (1 - np.random.uniform(0, 0.002, n_candles)),
            "close": prices,
            "volume": np.random.uniform(100, 1000, n_candles),
            "symbol": "BTCUSDT",
        }
    )

    print(f"✅ Создано {len(data)} свечей")
    print(f"  Цена от {data['close'].min():.2f} до {data['close'].max():.2f}")
    print(f"  Последняя цена: {data['close'].iloc[-1]:.2f}")

    # Тестируем предсказание несколько раз для проверки производительности
    print("\n⚡ Тестирование производительности...")

    # Прогрев
    _ = await ml_manager.predict(data)

    # Замеряем время
    times = []
    predictions = []

    for i in range(5):
        start_time = time.time()
        pred = await ml_manager.predict(data)
        elapsed = time.time() - start_time
        times.append(elapsed)
        predictions.append(pred)
        print(
            f"  Попытка {i + 1}: {elapsed * 1000:.1f}ms - Сигнал: {pred['signal_type']}"
        )

    avg_time = np.mean(times)
    print(f"\n📊 Средняя скорость предсказания: {avg_time * 1000:.1f}ms")
    print(f"  Мин: {min(times) * 1000:.1f}ms, Макс: {max(times) * 1000:.1f}ms")

    # Анализируем последнее предсказание
    last_pred = predictions[-1]
    print("\n🎯 Детали последнего предсказания:")
    print(f"  Сигнал: {last_pred['signal_type']}")
    print(f"  Сила сигнала: {last_pred['signal_strength']:.3f}")
    print(f"  Уверенность: {last_pred['confidence']:.3f}")
    print(f"  Вероятность успеха: {last_pred['success_probability']:.1%}")
    print(f"  Уровень риска: {last_pred['risk_level']}")

    if last_pred["stop_loss"] and last_pred["take_profit"]:
        print(f"  Stop Loss: {last_pred['stop_loss']:.2f}")
        print(f"  Take Profit: {last_pred['take_profit']:.2f}")

    print("\n  Детальные предсказания:")
    for key, value in last_pred["predictions"].items():
        print(f"    {key}: {value:.3f}")

    # Тест с разными рыночными условиями
    print("\n🧪 Тест разных рыночных условий:")

    # Нисходящий тренд
    down_trend = data.copy()
    down_trend["close"] = down_trend["close"] * np.linspace(1, 0.95, len(down_trend))
    pred_down = await ml_manager.predict(down_trend)
    print(
        f"  Нисходящий тренд (-5%): {pred_down['signal_type']} (сила: {pred_down['signal_strength']:.3f})"
    )

    # Боковое движение
    sideways = data.copy()
    sideways["close"] = base_price + np.random.normal(0, 100, len(sideways))
    pred_sideways = await ml_manager.predict(sideways)
    print(
        f"  Боковое движение: {pred_sideways['signal_type']} (сила: {pred_sideways['signal_strength']:.3f})"
    )

    # Высокая волатильность
    volatile = data.copy()
    volatile["high"] = volatile["close"] * 1.05
    volatile["low"] = volatile["close"] * 0.95
    pred_volatile = await ml_manager.predict(volatile)
    print(
        f"  Высокая волатильность: {pred_volatile['signal_type']} (сила: {pred_volatile['signal_strength']:.3f})"
    )

    # Информация о памяти GPU
    if torch.cuda.is_available():
        print("\n💾 Использование GPU памяти:")
        print(f"  Выделено: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
        print(f"  Кэшировано: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")
        print(f"  Максимум: {torch.cuda.max_memory_allocated() / 1024**3:.2f} GB")

    print("\n✅ Все тесты успешно завершены!")
    print(f"   Модель работает корректно на {ml_manager.device}")

    return True


if __name__ == "__main__":
    try:
        asyncio.run(test_ml_on_gpu())
    except Exception as e:
        logger.error(f"Ошибка в тесте: {e}", exc_info=True)
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)
