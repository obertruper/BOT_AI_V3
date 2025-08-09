#!/usr/bin/env python3
"""
Диагностический скрипт для анализа ML предсказаний
Проверяет почему модель выдает только NEUTRAL сигналы
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import torch

# Добавляем корневую папку в путь
sys.path.append(str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from ml.ml_manager import MLManager

logger = setup_logger(__name__)


async def diagnose_ml_predictions():
    """Диагностика ML предсказаний"""
    try:
        logger.info("🔍 Начинаем диагностику ML предсказаний...")

        # Инициализация
        config_manager = ConfigManager()
        ml_manager = MLManager(config_manager._config)
        data_loader = DataLoader(config_manager)

        # Инициализируем ML Manager
        await ml_manager.initialize()

        # Проверяем состояние модели
        logger.info(f"Модель инициализирована: {ml_manager.model is not None}")
        logger.info(f"Устройство: {ml_manager.device}")

        if ml_manager.model is not None:
            logger.info(f"Модель в режиме eval: {not ml_manager.model.training}")

        # Загружаем данные для одного символа
        symbol = "BTCUSDT"
        logger.info(f"Загружаем данные для {symbol}...")

        ohlcv_data = await data_loader.get_data_for_ml(symbol, limit=500)

        if ohlcv_data is None or len(ohlcv_data) < 240:
            logger.error(
                f"Недостаточно данных для {symbol}: {len(ohlcv_data) if ohlcv_data is not None else 0}"
            )
            return

        logger.info(f"Загружено {len(ohlcv_data)} свечей для {symbol}")
        logger.info(f"Последняя цена: {ohlcv_data['close'].iloc[-1]}")
        logger.info(
            f"Временной диапазон: {ohlcv_data.index[0]} - {ohlcv_data.index[-1]}"
        )

        # Генерируем предсказание
        logger.info("Генерируем предсказание...")
        prediction = await ml_manager.predict(ohlcv_data)

        if not prediction:
            logger.error("Предсказание не было сгенерировано")
            return

        # Анализируем предсказание
        logger.info("=" * 60)
        logger.info("📊 ДЕТАЛЬНЫЙ АНАЛИЗ ПРЕДСКАЗАНИЯ")
        logger.info("=" * 60)

        for key, value in prediction.items():
            logger.info(f"{key}: {value}")

        # Получаем сырые выходы модели для дополнительного анализа
        logger.info("\n🔬 АНАЛИЗ СЫРЫХ ДАННЫХ МОДЕЛИ:")

        # Делаем сырой inference для проверки
        from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

        indicator_calc = RealTimeIndicatorCalculator(config=config_manager._config)
        features_array, metadata = await indicator_calc.prepare_ml_input(
            symbol, ohlcv_data
        )

        logger.info(f"Размер входных данных: {features_array.shape}")

        if ml_manager.model is not None:
            ml_manager.model.eval()
            with torch.no_grad():
                # Конвертируем в тензор
                input_tensor = torch.FloatTensor(features_array).to(ml_manager.device)

                # Получаем сырые выходы
                raw_outputs = ml_manager.model(input_tensor)
                raw_outputs_np = raw_outputs.cpu().numpy().flatten()

                logger.info(f"Сырые выходы модели (первые 10): {raw_outputs_np[:10]}")
                logger.info(f"Сырые выходы модели (все 20): {raw_outputs_np}")

                # Анализируем конкретные компоненты
                future_returns = raw_outputs_np[0:4]
                future_directions = raw_outputs_np[4:8]
                level_targets = raw_outputs_np[8:16]
                risk_metrics = raw_outputs_np[16:20]

                logger.info(f"Future returns: {future_returns}")
                logger.info(f"Future directions: {future_directions}")
                logger.info(f"Level targets: {level_targets}")
                logger.info(f"Risk metrics: {risk_metrics}")

                # Проверяем статистику модели
                logger.info("Средние значения по компонентам:")
                logger.info(f"  Returns mean: {np.mean(future_returns):.6f}")
                logger.info(f"  Directions mean: {np.mean(future_directions):.6f}")
                logger.info(f"  Levels mean: {np.mean(level_targets):.6f}")
                logger.info(f"  Risk mean: {np.mean(risk_metrics):.6f}")

        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка диагностики: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(diagnose_ml_predictions())
