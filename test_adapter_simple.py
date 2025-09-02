#!/usr/bin/env python3
"""
Простой тест адаптера PatchTST
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import numpy as np
from ml.adapters.patchtst import PatchTSTAdapter
from core.logger import setup_logger

logger = setup_logger(__name__)

async def test_adapter_outputs():
    """Тест того, что адаптер корректно возвращает UnifiedPrediction"""
    try:
        logger.info("🧪 Тестирование адаптера PatchTST...")
        
        # Создаем простой конфиг
        config = {
            'ml': {
                'models': {
                    'patchtst': {
                        'model_path': 'ml/models/patchtst_v4.pth',
                        'num_features': 240,
                        'context_length': 100,
                        'pred_len': 1,
                        'e_layers': 3,
                        'd_model': 128,
                        'd_ff': 256,
                        'n_heads': 8,
                        'dropout': 0.1
                    }
                }
            }
        }
        
        # Создаем адаптер
        adapter = PatchTSTAdapter(config)
        
        # Создаем тестовые данные (20 выходов модели)
        raw_outputs = np.random.randn(20).astype(np.float32)
        logger.info(f"Создали тестовые выходы: shape={raw_outputs.shape}")
        
        # Тестируем interpret_outputs
        unified_prediction = adapter.interpret_outputs(
            raw_outputs=raw_outputs,
            symbol="BTCUSDT", 
            current_price=50000.0
        )
        
        logger.info(f"Тип результата: {type(unified_prediction)}")
        
        # Проверяем что это UnifiedPrediction
        if hasattr(unified_prediction, 'to_dict'):
            logger.info("✅ Адаптер возвращает объект с методом to_dict")
            
            # Преобразуем в dict
            result_dict = unified_prediction.to_dict()
            logger.info(f"Dict содержит ключи: {list(result_dict.keys())}")
            
            # Проверяем основные поля
            expected_fields = ["signal_type", "confidence", "signal_strength"]
            found_fields = [field for field in expected_fields if field in result_dict]
            
            if len(found_fields) >= 2:
                logger.info("✅ Основные поля присутствуют")
                return True
            else:
                logger.warning("⚠️ Не хватает основных полей")
                return False
        else:
            logger.error("❌ Адаптер не возвращает объект UnifiedPrediction")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка в тесте адаптера: {e}")
        return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_adapter_outputs())
    if success:
        logger.info("🎉 Адаптер работает корректно!")
    else:
        logger.warning("⚠️ Требуются исправления")