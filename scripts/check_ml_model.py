#!/usr/bin/env python3
"""
Скрипт для проверки готовности ML модели к работе
"""

import pickle
import sys
from datetime import datetime
from pathlib import Path

import torch

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.logic.patchtst_model import UnifiedPatchTSTForTrading


def check_model_files():
    """Проверка наличия всех необходимых файлов"""
    print("🔍 Проверка файлов модели...")

    required_files = {
        "model": Path("models/saved/best_model_20250728_215703.pth"),
        "scaler": Path("models/saved/data_scaler.pkl"),
        "config": Path("models/saved/config.pkl"),
    }

    all_exist = True
    file_info = {}

    for name, path in required_files.items():
        if path.exists():
            size = path.stat().st_size / (1024 * 1024)  # MB
            file_info[name] = {
                "path": str(path),
                "size_mb": round(size, 2),
                "exists": True,
            }
            print(f"✅ {name}: {path} ({size:.2f} MB)")
        else:
            file_info[name] = {"path": str(path), "exists": False}
            print(f"❌ {name}: {path} - НЕ НАЙДЕН")
            all_exist = False

    return all_exist, file_info


def check_model_loading():
    """Проверка загрузки модели"""
    print("\n📦 Проверка загрузки модели...")

    try:
        # Загружаем конфигурацию
        with open("models/saved/config.pkl", "rb") as f:
            config = pickle.load(f)
        print("✅ Конфигурация загружена")

        # Создаем модель
        model = UnifiedPatchTSTForTrading(config)
        print("✅ Модель создана")

        # Загружаем веса
        device = torch.device("cpu")  # Используем CPU для совместимости
        checkpoint = torch.load("models/saved/best_model_20250728_215703.pth", map_location=device)

        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            model.load_state_dict(checkpoint)

        model.to(device)
        model.eval()
        print(f"✅ Веса модели загружены на {device}")

        # Информация о модели
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

        print("\n📊 Информация о модели:")
        print(f"- Всего параметров: {total_params:,}")
        print(f"- Обучаемых параметров: {trainable_params:,}")
        print(f"- Устройство: {device}")
        print(f"- Входов: {config['model']['input_size']}")
        print(f"- Выходов: {config['model']['output_size']}")

        return True, model, config

    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        return False, None, None


def check_scaler():
    """Проверка загрузки scaler"""
    print("\n🔧 Проверка scaler...")

    try:
        with open("models/saved/data_scaler.pkl", "rb") as f:
            scaler = pickle.load(f)

        print("✅ Scaler загружен")
        print(f"- Тип: {type(scaler).__name__}")

        if hasattr(scaler, "mean_"):
            print(f"- Количество признаков: {len(scaler.mean_)}")

        return True, scaler

    except Exception as e:
        print(f"❌ Ошибка загрузки scaler: {e}")
        return False, None


def test_inference(model, config, scaler):
    """Тестовый запуск инференса"""
    print("\n🚀 Тестовый запуск инференса...")

    try:
        import numpy as np

        # Создаем тестовые данные
        batch_size = 1
        seq_len = 96  # context_window
        input_size = config["model"]["input_size"]

        # Генерируем случайные данные
        test_data = np.random.randn(seq_len, input_size)

        # Нормализуем
        if scaler:
            test_data = scaler.transform(test_data)

        # Конвертируем в тензор
        device = next(model.parameters()).device
        test_tensor = torch.FloatTensor(test_data).unsqueeze(0).to(device)

        print(f"- Входные данные: {test_tensor.shape}")

        # Запускаем инференс
        start_time = datetime.now()
        with torch.no_grad():
            output = model(test_tensor)
        inference_time = (datetime.now() - start_time).total_seconds() * 1000

        print("✅ Инференс успешен")
        print(f"- Выходные данные: {output.shape}")
        print(f"- Время инференса: {inference_time:.2f} мс")

        # Проверяем выходы
        output_np = output.cpu().numpy()[0]
        print("\n📈 Примеры предсказаний:")
        print(f"- Future return 15m: {output_np[0]:.4f}")
        print(f"- Direction 15m: {output_np[4]:.0f}")
        print(f"- Long probability 1%: {1 / (1 + np.exp(-output_np[8])):.2%}")
        print(f"- Max drawdown 1h: {output_np[16]:.4f}")

        return True

    except Exception as e:
        print(f"❌ Ошибка инференса: {e}")
        return False


def main():
    """Основная функция"""
    print("=" * 60)
    print("🔍 ПРОВЕРКА ГОТОВНОСТИ ML МОДЕЛИ")
    print("=" * 60)

    # Проверка файлов
    files_ok, file_info = check_model_files()
    if not files_ok:
        print("\n❌ Не все файлы модели найдены!")
        print("Скопируйте недостающие файлы из проекта LLM TRANSFORM")
        return

    # Проверка загрузки модели
    model_ok, model, config = check_model_loading()
    if not model_ok:
        return

    # Проверка scaler
    scaler_ok, scaler = check_scaler()
    if not scaler_ok:
        return

    # Тестовый инференс
    if model and config:
        inference_ok = test_inference(model, config, scaler)

    # Итоговый результат
    print("\n" + "=" * 60)
    if files_ok and model_ok and scaler_ok and inference_ok:
        print("✅ ML МОДЕЛЬ ГОТОВА К РАБОТЕ!")
        print("\nТеперь вы можете запустить:")
        print("python scripts/create_ml_trader.py")
    else:
        print("❌ ML модель не готова к работе")
        print("Исправьте указанные выше проблемы")
    print("=" * 60)


if __name__ == "__main__":
    main()
