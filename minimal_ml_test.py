#!/usr/bin/env python3
"""
Минимальный тест ML
"""

import asyncio
from pathlib import Path

import torch

from core.logger import setup_logger
from ml.logic.patchtst_model import create_unified_model

logger = setup_logger("minimal_test")


async def test_ml():
    """Минимальный тест модели напрямую"""
    try:
        # Создаем модель
        logger.info("Создаем модель...")
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

        model = create_unified_model(model_config)

        # Загружаем веса
        model_path = Path("models/saved/best_model_20250728_215703.pth")
        if model_path.exists():
            logger.info("Загружаем веса модели...")
            checkpoint = torch.load(model_path, map_location="cpu")
            model.load_state_dict(checkpoint["model_state_dict"])
            model.eval()
            logger.info("Модель загружена")
        else:
            logger.error(f"Файл модели не найден: {model_path}")
            return

        # Создаем случайные данные
        logger.info("Создаем тестовые данные...")
        test_input = torch.randn(1, 96, 240)  # batch_size=1, seq_len=96, features=240

        # Делаем предсказание
        logger.info("Делаем предсказание...")
        with torch.no_grad():
            outputs = model(test_input)

        outputs_np = outputs.numpy()[0]
        logger.info(f"Выходы модели: {outputs_np.shape}")
        logger.info(f"Первые 10 значений: {outputs_np[:10]}")

        # Проверяем разнообразие
        unique_vals = len(set([round(v, 1) for v in outputs_np[4:8]]))
        logger.info(f"Уникальных направлений: {unique_vals} из 4")

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_ml())
