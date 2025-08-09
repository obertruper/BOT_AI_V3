#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностический скрипт для отладки ML inference проблемы
Проверяет все этапы ML pipeline от загрузки модели до получения предсказания
"""

import asyncio
import logging
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

# Настройка логирования для детального отслеживания
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from ml.logic.feature_engineering import FeatureEngineer
from ml.logic.patchtst_model import create_unified_model


async def debug_ml_inference():
    """Полная диагностика ML inference pipeline"""

    print("🔍 === ДИАГНОСТИКА ML INFERENCE PIPELINE ===")

    try:
        # Конфигурация модели
        model_config = {
            "model": {
                "input_size": 240,
                "output_size": 20,
                "context_window": 96,
                "patch_len": 16,
                "stride": 8,
                "d_model": 256,
                "n_heads": 4,
                "e_layers": 3,
                "d_ff": 512,
                "dropout": 0.1,
                "temperature_scaling": True,
                "temperature": 2.0,
            }
        }

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🖥️  Устройство: {device}")

        # === 1. ПРОВЕРКА ЗАГРУЗКИ МОДЕЛИ ===
        print("\n1️⃣ === ЗАГРУЗКА МОДЕЛИ ===")

        model_path = Path("models/saved/best_model_20250728_215703.pth")
        if not model_path.exists():
            model_path = Path("ml/models/saved/best_model.pth")

        print(f"📁 Путь к модели: {model_path}")
        print(f"✅ Модель существует: {model_path.exists()}")

        if model_path.exists():
            # Загружаем checkpoint для анализа
            checkpoint = torch.load(model_path, map_location=device)
            print(f"📊 Ключи в checkpoint: {list(checkpoint.keys())}")

            if "model_state_dict" in checkpoint:
                state_dict = checkpoint["model_state_dict"]
                print(f"🔢 Количество параметров в модели: {len(state_dict)}")

                # Печатаем несколько ключей для проверки структуры
                print("🗝️ Первые 10 ключей модели:")
                for i, key in enumerate(list(state_dict.keys())[:10]):
                    print(f"   {i + 1}. {key}: {state_dict[key].shape}")

        # Создаем модель
        print("\n🏗️ Создание модели...")
        model = create_unified_model(model_config)
        model.to(device)

        # Загружаем веса
        if model_path.exists():
            checkpoint = torch.load(model_path, map_location=device)
            model.load_state_dict(checkpoint["model_state_dict"])
            print("✅ Веса модели загружены")

        model.eval()
        print(f"🎯 Модель в режиме eval: {not model.training}")

        # === 2. ПРОВЕРКА SCALER ===
        print("\n2️⃣ === ЗАГРУЗКА SCALER ===")

        scaler_path = Path("models/saved/data_scaler.pkl")
        if not scaler_path.exists():
            scaler_path = Path("ml/models/saved/data_scaler.pkl")

        print(f"📁 Путь к scaler: {scaler_path}")
        print(f"✅ Scaler существует: {scaler_path.exists()}")

        scaler = None
        if scaler_path.exists():
            with open(scaler_path, "rb") as f:
                scaler = pickle.load(f)
            print(f"📊 Тип scaler: {type(scaler)}")
            if hasattr(scaler, "n_features_in_"):
                print(f"🔢 Количество признаков в scaler: {scaler.n_features_in_}")

        # === 3. ГЕНЕРАЦИЯ ТЕСТОВЫХ ДАННЫХ ===
        print("\n3️⃣ === ГЕНЕРАЦИЯ ТЕСТОВЫХ ДАННЫХ ===")

        # Создаем тестовые OHLCV данные (как будто получены с биржи)
        dates = pd.date_range(start="2024-01-01", periods=200, freq="15min")
        base_price = 50000.0

        # Генерируем реалистичные OHLCV данные
        np.random.seed(42)  # Для воспроизводимости
        price_changes = np.random.normal(0, 0.01, len(dates))  # 1% волатильность

        prices = [base_price]
        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)

        # Создаем OHLCV с реалистичной вариацией
        test_data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            high = close * (1 + abs(np.random.normal(0, 0.005)))  # Высота свечи
            low = close * (1 - abs(np.random.normal(0, 0.005)))  # Низ свечи
            open_price = (
                prices[i - 1] if i > 0 else close
            )  # Открытие = предыдущее закрытие
            volume = np.random.uniform(100, 1000)  # Случайный объем

            test_data.append(
                {
                    "datetime": date,
                    "open": open_price,
                    "high": max(high, close, open_price),
                    "low": min(low, close, open_price),
                    "close": close,
                    "volume": volume,
                    "symbol": "BTCUSDT",
                }
            )

        test_df = pd.DataFrame(test_data)
        print(f"📊 Сгенерировано {len(test_df)} тестовых записей OHLCV")
        print(
            f"📈 Диапазон цен: {test_df['close'].min():.2f} - {test_df['close'].max():.2f}"
        )
        print("📋 Первые 3 записи:")
        print(test_df.head(3)[["datetime", "open", "high", "low", "close", "volume"]])

        # === 4. FEATURE ENGINEERING ===
        print("\n4️⃣ === FEATURE ENGINEERING ===")

        feature_engineer = FeatureEngineer()
        print("🔧 FeatureEngineer создан")

        # Берем последние 120 записей для генерации признаков (больше чем context_window=96)
        recent_data = test_df.tail(120).copy()
        print(
            f"📊 Используем последние {len(recent_data)} записей для feature engineering"
        )

        # Генерируем признаки
        try:
            features_array = feature_engineer.create_features(recent_data)
            print("✅ Feature engineering успешно выполнен")
            print(f"🔢 Размер массива признаков: {features_array.shape}")
            print("📊 Статистика признаков:")
            print(f"   Min: {features_array.min():.6f}")
            print(f"   Max: {features_array.max():.6f}")
            print(f"   Mean: {features_array.mean():.6f}")
            print(f"   Std: {features_array.std():.6f}")
            print(f"   NaN count: {np.isnan(features_array).sum()}")
            print(f"   Inf count: {np.isinf(features_array).sum()}")

            # Проверяем есть ли проблемные значения
            if np.isnan(features_array).any():
                print("⚠️  ОБНАРУЖЕНЫ NaN значения!")
            if np.isinf(features_array).any():
                print("⚠️  ОБНАРУЖЕНЫ Inf значения!")

            # Берем последние context_window строк для модели
            context_window = 96
            if len(features_array) >= context_window:
                model_input = features_array[-context_window:]
                print(f"🎯 Входные данные для модели: {model_input.shape}")
            else:
                print(
                    f"❌ Недостаточно данных! Нужно {context_window}, есть {len(features_array)}"
                )
                return

        except Exception as e:
            print(f"❌ Ошибка в feature engineering: {e}")
            import traceback

            traceback.print_exc()
            return

        # === 5. НОРМАЛИЗАЦИЯ ДАННЫХ ===
        print("\n5️⃣ === НОРМАЛИЗАЦИЯ ДАННЫХ ===")

        if scaler:
            print("🔄 Применяем scaler...")
            try:
                features_scaled = scaler.transform(model_input)
                print("✅ Нормализация успешна")
                print("📊 Статистика после нормализации:")
                print(f"   Min: {features_scaled.min():.6f}")
                print(f"   Max: {features_scaled.max():.6f}")
                print(f"   Mean: {features_scaled.mean():.6f}")
                print(f"   Std: {features_scaled.std():.6f}")

                # Проверяем диапазон после нормализации
                if abs(features_scaled.mean()) > 1.0:
                    print(
                        "⚠️  Подозрительно большое среднее значение после нормализации!"
                    )
                if features_scaled.std() > 5.0:
                    print(
                        "⚠️  Подозрительно большая стандартное отклонение после нормализации!"
                    )

            except Exception as e:
                print(f"❌ Ошибка нормализации: {e}")
                features_scaled = model_input
        else:
            print("⚠️  Scaler не найден, используем сырые признаки")
            features_scaled = model_input

        # === 6. INFERENCE МОДЕЛИ ===
        print("\n6️⃣ === INFERENCE МОДЕЛИ ===")

        print("🔄 Подготовка тензора для модели...")
        x_tensor = torch.FloatTensor(features_scaled).unsqueeze(0).to(device)
        print(f"📊 Размер входного тензора: {x_tensor.shape}")
        print(f"🖥️  Устройство тензора: {x_tensor.device}")
        print("📊 Статистика входного тензора:")
        print(f"   Min: {x_tensor.min().item():.6f}")
        print(f"   Max: {x_tensor.max().item():.6f}")
        print(f"   Mean: {x_tensor.mean().item():.6f}")
        print(f"   Std: {x_tensor.std().item():.6f}")

        print("🧠 Запуск inference...")
        try:
            with torch.no_grad():
                outputs = model(x_tensor)

            print("✅ Inference выполнен успешно")
            print(f"📊 Размер выходного тензора: {outputs.shape}")

            # Конвертируем в numpy для анализа
            outputs_np = outputs.cpu().numpy()[0]
            print("📊 Выходные данные модели (20 значений):")
            for i, value in enumerate(outputs_np):
                print(f"   Выход {i:2d}: {value:8.6f}")

            print("\n📊 Статистика выходов:")
            print(f"   Min: {outputs_np.min():.6f}")
            print(f"   Max: {outputs_np.max():.6f}")
            print(f"   Mean: {outputs_np.mean():.6f}")
            print(f"   Std: {outputs_np.std():.6f}")
            print(f"   Уникальных значений: {len(np.unique(np.round(outputs_np, 6)))}")

            # === ДИАГНОСТИКА ПРОБЛЕМЫ ===
            print("\n🔍 === ДИАГНОСТИКА ПРОБЛЕМЫ ===")

            # Проверяем разнообразие выходов
            unique_outputs = len(np.unique(np.round(outputs_np, 3)))
            print(f"🎯 Уникальных значений (с точностью до 3 знаков): {unique_outputs}")

            if unique_outputs < 5:
                print(
                    "🚨 ПРОБЛЕМА: Слишком мало уникальных выходов - модель дает одинаковые предсказания!"
                )

                # Дополнительная диагностика
                print("\n🔍 Дополнительная диагностика:")

                # Проверяем веса модели
                total_params = sum(p.numel() for p in model.parameters())
                print(f"📊 Общее количество параметров модели: {total_params:,}")

                # Проверяем есть ли градиенты (не должно быть в eval режиме)
                requires_grad = sum(p.requires_grad for p in model.parameters())
                print(f"🎯 Параметров требующих градиентов: {requires_grad}")

                # Проверяем первый слой
                first_layer = None
                for name, module in model.named_modules():
                    if isinstance(module, torch.nn.Linear):
                        first_layer = module
                        break

                if first_layer:
                    print(f"🔧 Первый линейный слой: {first_layer}")
                    print(
                        f"   Веса: min={first_layer.weight.min():.6f}, max={first_layer.weight.max():.6f}"
                    )
                    if first_layer.bias is not None:
                        print(
                            f"   Биасы: min={first_layer.bias.min():.6f}, max={first_layer.bias.max():.6f}"
                        )

                # Проверяем различия в разных прогонах
                print("\n🔄 Тестируем стабильность модели...")
                outputs_list = []
                for i in range(3):
                    with torch.no_grad():
                        test_output = model(x_tensor)
                    outputs_list.append(test_output.cpu().numpy()[0])
                    print(f"   Прогон {i + 1}: {test_output.cpu().numpy()[0][:5]}...")

                # Проверяем идентичность результатов
                all_same = all(
                    np.allclose(outputs_list[0], out, atol=1e-8)
                    for out in outputs_list[1:]
                )
                print(f"🎯 Все результаты идентичны: {all_same}")

                if all_same:
                    print("✅ Модель детерминистична (нормально)")
                else:
                    print(
                        "⚠️  Модель дает разные результаты (возможно проблема с dropout/batch_norm)"
                    )

            else:
                print("✅ Выходы модели разнообразны - это хорошо")

            # === ИНТЕРПРЕТАЦИЯ РЕЗУЛЬТАТОВ ===
            print("\n7️⃣ === ИНТЕРПРЕТАЦИЯ РЕЗУЛЬТАТОВ ===")

            # Структура выходов согласно модели:
            future_returns = outputs_np[0:4]
            future_directions = outputs_np[4:8]
            long_levels = outputs_np[8:12]
            short_levels = outputs_np[12:16]
            risk_metrics = outputs_np[16:20]

            print("📊 Разбор по группам выходов:")
            print(f"   Future returns (0-3):    {future_returns}")
            print(f"   Future directions (4-7):  {future_directions}")
            print(f"   Long levels (8-11):       {long_levels}")
            print(f"   Short levels (12-15):     {short_levels}")
            print(f"   Risk metrics (16-19):     {risk_metrics}")

            # Проверим логику интерпретации как в MLManager
            weights = np.array([0.4, 0.3, 0.2, 0.1])
            weighted_direction = np.sum(future_directions * weights)
            signal_strength = abs(weighted_direction)

            if weighted_direction > 0.05:
                signal_type = "BUY"
            elif weighted_direction < -0.05:
                signal_type = "SELL"
            else:
                signal_type = "NEUTRAL"

            print("\n🎯 Результат интерпретации:")
            print(f"   Взвешенное направление: {weighted_direction:.6f}")
            print(f"   Сила сигнала: {signal_strength:.6f}")
            print(f"   Тип сигнала: {signal_type}")

            # Если получили одинаковые значения - выводим их
            if unique_outputs < 5:
                print("\n🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА:")
                print(f"   Модель всегда дает сигнал: {signal_type}")
                print(f"   Силу сигнала: {signal_strength:.6f}")
                print("   Это объясняет почему все предсказания одинаковы!")

                # Рекомендации по исправлению
                print("\n💡 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
                print("   1. Проверить правильность загрузки весов модели")
                print("   2. Проверить нормализацию входных данных")
                print("   3. Проверить архитектуру модели на совместимость")
                print("   4. Возможно модель переобучена или не обучена")
                print("   5. Проверить что используется правильный checkpoint")

        except Exception as e:
            print(f"❌ Ошибка inference: {e}")
            import traceback

            traceback.print_exc()
            return

        print("\n🎉 === ДИАГНОСТИКА ЗАВЕРШЕНА ===")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_ml_inference())
