#!/usr/bin/env python3
"""
Скрипт для создания config.pkl файла для ML модели
Этот файл необходим для корректной работы PatchTSTStrategy
"""

import pickle
from pathlib import Path

import yaml


def create_model_config():
    """Создание конфигурационного файла для модели"""

    # Загружаем ML конфигурацию
    config_path = Path("config/ml/ml_config.yaml")
    with open(config_path, "r") as f:
        ml_config = yaml.safe_load(f)

    # Базовая конфигурация модели (адаптированная из LLM TRANSFORM)
    model_config = {
        "model": ml_config["model"],
        "loss": ml_config["loss"],
        "features": ml_config["features"],
        "version": "4.0",
        "created_at": "2025-07-28",
        "description": "UnifiedPatchTST model for crypto trading",
        # Добавляем имена выходных переменных
        "output_names": [
            # A. Базовые возвраты (0-3)
            "future_return_15m",
            "future_return_1h",
            "future_return_4h",
            "future_return_12h",
            # B. Направление движения (4-7)
            "direction_15m",
            "direction_1h",
            "direction_4h",
            "direction_12h",
            # C. Достижение уровней прибыли LONG (8-11)
            "long_will_reach_1pct_4h",
            "long_will_reach_2pct_4h",
            "long_will_reach_3pct_12h",
            "long_will_reach_5pct_12h",
            # D. Достижение уровней прибыли SHORT (12-15)
            "short_will_reach_1pct_4h",
            "short_will_reach_2pct_4h",
            "short_will_reach_3pct_12h",
            "short_will_reach_5pct_12h",
            # E. Риск-метрики (16-19)
            "max_drawdown_1h",
            "max_rally_1h",
            "max_drawdown_4h",
            "max_rally_4h",
        ],
        # Статистика модели
        "metrics": {
            "f1_score": 0.414,
            "win_rate": 0.466,
            "training_samples": 1000000,  # Примерное количество
        },
    }

    # Сохраняем конфигурацию
    output_path = Path("models/saved/config.pkl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        pickle.dump(model_config, f)

    print(f"✅ Конфигурация модели сохранена в: {output_path}")

    # Также сохраняем в читаемом формате
    yaml_path = Path("models/saved/config.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(model_config, f, default_flow_style=False)

    print(f"✅ Конфигурация также сохранена в YAML: {yaml_path}")

    # Выводим информацию
    print("\n📊 Информация о модели:")
    print(f"- Входов: {model_config['model']['input_size']}")
    print(f"- Выходов: {model_config['model']['output_size']}")
    print(f"- Контекстное окно: {model_config['model']['context_window']} (24 часа)")
    print(f"- F1 Score: {model_config['metrics']['f1_score']}")
    print(f"- Win Rate: {model_config['metrics']['win_rate']:.1%}")

    return model_config


if __name__ == "__main__":
    create_model_config()
