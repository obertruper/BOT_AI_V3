"""
Пример использования PatchTST модели в BOT Trading v3
"""

import torch

from ml.logic.patchtst_model import (
    DirectionalMultiTaskLoss,
    create_unified_model,
    load_model_safe,
)


def example_model_usage():
    """Пример создания и использования модели"""

    # Конфигурация модели
    config = {
        "model": {
            "input_size": 240,  # 240 признаков
            "output_size": 20,  # 20 выходов
            "context_window": 96,  # 24 часа при 15-мин свечах
            "patch_len": 16,  # Размер патча
            "stride": 8,  # Шаг патча
            "d_model": 256,  # Размерность модели
            "n_heads": 4,  # Количество голов attention
            "e_layers": 3,  # Количество слоев энкодера
            "d_ff": 512,  # Размерность FFN
            "dropout": 0.1,  # Dropout rate
            "activation": "gelu",  # Активация
            "temperature_scaling": True,
            "temperature": 2.0,
            "direction_confidence_threshold": 0.5,
        },
        "loss": {
            "task_weights": {
                "future_returns": 1.0,
                "directions": 3.0,  # Больший вес для направлений
                "long_levels": 1.0,
                "short_levels": 1.0,
                "risk_metrics": 0.5,
            },
            "class_weights": [1.3, 1.3, 0.7],  # LONG, SHORT, FLAT
            "large_move_weight": 5.0,
            "large_move_threshold": 0.003,
            "focal_alpha": 0.25,
            "focal_gamma": 2.0,
            "wrong_direction_penalty": 3.0,
        },
    }

    # Создание модели
    model = create_unified_model(config)

    # Создание loss функции
    criterion = DirectionalMultiTaskLoss(config)

    # Пример входных данных
    batch_size = 32
    seq_len = 96
    n_features = 240

    # Случайные данные для демонстрации
    x = torch.randn(batch_size, seq_len, n_features)

    # Forward pass
    outputs = model(x)

    print(f"Форма выходов: {outputs.shape}")  # (32, 20)
    print(f"Имена выходов: {model.get_output_names()}")

    # Пример целевых значений
    targets = torch.zeros(batch_size, 20)

    # Future returns (0-3) - в процентах
    targets[:, 0:4] = torch.randn(batch_size, 4) * 2  # ±2%

    # Directions (4-7) - классы 0, 1, 2
    targets[:, 4:8] = torch.randint(0, 3, (batch_size, 4)).float()

    # Long/Short levels (8-15) - бинарные
    targets[:, 8:16] = torch.randint(0, 2, (batch_size, 8)).float()

    # Risk metrics (16-19) - в процентах
    targets[:, 16:20] = torch.abs(torch.randn(batch_size, 4)) * 5  # 0-5%

    # Вычисление loss
    loss = criterion(outputs, targets)

    print(f"Loss: {loss.item():.4f}")

    return model, outputs, loss


def integration_example():
    """Пример интеграции с торговой системой"""

    config = {
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
        }
    }

    model = create_unified_model(config)
    model.eval()  # Режим инференса

    # Загрузка весов (если есть)
    # Старый способ (может вызвать ошибки при несовместимости):
    # model.load_state_dict(torch.load('models/saved/patchtst_model.pth'))

    # Новый безопасный способ:
    # model = load_model_safe(model, 'models/saved/best_model_20250728_215703.pth', device='cpu')

    with torch.no_grad():
        # Подготовка данных из торговой системы
        # В реальности это будут данные из market_data
        market_data = torch.randn(
            1, 96, 240
        )  # 1 пример, 96 временных шагов, 240 признаков

        # Предсказание
        predictions = model(market_data)

        # Разбор предсказаний
        pred_dict = {}
        output_names = model.get_output_names()

        for i, name in enumerate(output_names):
            pred_dict[name] = predictions[0, i].item()

        # Интерпретация результатов
        print("\n=== Предсказания модели ===")

        print("\nFuture Returns:")
        for tf in ["15m", "1h", "4h", "12h"]:
            print(f"  {tf}: {pred_dict[f'future_return_{tf}']:.4f}")

        print("\nDirections:")
        direction_map = {0: "LONG", 1: "SHORT", 2: "FLAT"}
        for tf in ["15m", "1h", "4h", "12h"]:
            direction = int(pred_dict[f"direction_{tf}"])
            print(f"  {tf}: {direction_map[direction]}")

        print("\nLong Levels (вероятности):")
        print(
            f"  1% за 4h: {torch.sigmoid(torch.tensor(pred_dict['long_will_reach_1pct_4h'])).item():.3f}"
        )
        print(
            f"  2% за 4h: {torch.sigmoid(torch.tensor(pred_dict['long_will_reach_2pct_4h'])).item():.3f}"
        )

        print("\nRisk Metrics:")
        print(f"  Max Drawdown 1h: {pred_dict['max_drawdown_1h']:.4f}")
        print(f"  Max Rally 1h: {pred_dict['max_rally_1h']:.4f}")

    return pred_dict


def test_model_loading():
    """Тестирование загрузки сохраненной модели"""
    import os

    print("=== Тестирование загрузки модели ===")

    # Путь к сохраненной модели
    model_path = "models/saved/best_model_20250728_215703.pth"

    if not os.path.exists(model_path):
        print(f"Файл модели не найден: {model_path}")
        return

    # Конфигурация для создания модели
    config = {
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
            "activation": "gelu",
            "temperature_scaling": True,
            "temperature": 2.0,
            "direction_confidence_threshold": 0.5,
        }
    }

    # Создание модели
    model = create_unified_model(config)

    # Загрузка с помощью безопасной функции
    try:
        model = load_model_safe(model, model_path, device="cpu")
        print("✓ Модель успешно загружена!")

        # Тест инференса
        model.eval()
        with torch.no_grad():
            test_input = torch.randn(1, 96, 240)
            output = model(test_input)
            print(f"✓ Инференс успешен! Форма выхода: {output.shape}")

    except Exception as e:
        print(f"✗ Ошибка при загрузке модели: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Пример использования
    print("=== Пример создания и обучения модели ===")
    model, outputs, loss = example_model_usage()

    print("\n=== Пример интеграции с торговой системой ===")
    predictions = integration_example()

    print("\n")
    test_model_loading()
