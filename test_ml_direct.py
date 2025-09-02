#!/usr/bin/env python3
"""
Прямой тест логики MLManager без полной инициализации
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from core.logger import setup_logger
from ml.ml_manager import MLManager
from ml.adapters.patchtst import PatchTSTAdapter
from ml.adapters.base import UnifiedPrediction

logger = setup_logger(__name__)

async def test_predict_logic():
    """Тест логики predict с мокированным адаптером"""
    try:
        logger.info("🧪 Тестирование логики MLManager.predict...")
        
        # Создаем простой конфиг
        config = {
            'ml': {
                'enabled': True,
                'model_type': 'patchtst',
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
        
        # Создаем MLManager с мокированным адаптером
        ml_manager = MLManager(config)
        ml_manager.use_adapter = True
        
        # Создаем мокированный адаптер
        mock_adapter = AsyncMock(spec=PatchTSTAdapter)
        
        # Настраиваем мок
        mock_adapter.validate_input.return_value = True
        
        # Мокируем predict - возвращает numpy array (как реальный адаптер)
        mock_raw_output = np.random.randn(20).astype(np.float32)
        mock_adapter.predict.return_value = mock_raw_output
        
        # Мокируем interpret_outputs - возвращает UnifiedPrediction
        mock_unified = MagicMock()
        mock_unified.to_dict.return_value = {
            "signal_type": "LONG",
            "confidence": 0.75,
            "signal_strength": 0.8,
            "primary_direction": "LONG",
            "primary_confidence": 0.75,
            "risk_level": "MEDIUM"
        }
        mock_adapter.interpret_outputs.return_value = mock_unified
        
        # Устанавливаем мок
        ml_manager.adapter = mock_adapter
        
        # Создаем тестовые данные (numpy array - готовые признаки)
        features_array = np.random.randn(100, 240).astype(np.float32)
        
        # Тестируем predict
        logger.info("📊 Вызываем predict с numpy array...")
        result = await ml_manager.predict(
            features_array, 
            symbol="BTCUSDT", 
            current_price=50000.0
        )
        
        logger.info(f"Результат типа: {type(result)}")
        
        # Проверяем что получили dict
        if isinstance(result, dict):
            logger.info("✅ Получили dict как ожидалось")
            logger.info(f"   Ключи результата: {list(result.keys())}")
            
            # Проверяем основные поля
            expected_fields = ["signal_type", "confidence", "signal_strength"]
            found_fields = [field for field in expected_fields if field in result]
            
            if len(found_fields) >= 2:
                logger.info("✅ Основные поля присутствуют")
                
                # Проверяем что адаптер был вызван правильно
                mock_adapter.predict.assert_called_once()
                mock_adapter.interpret_outputs.assert_called_once()
                
                call_args = mock_adapter.interpret_outputs.call_args
                assert call_args[0][0] is mock_raw_output, "Raw outputs должны передаваться"
                assert call_args[1]['symbol'] == "BTCUSDT", "Symbol должен передаваться"
                assert call_args[1]['current_price'] == 50000.0, "Current price должна передаваться"
                
                logger.info("✅ Адаптер вызван с правильными параметрами")
                return True
            else:
                logger.warning("⚠️ Не хватает основных полей")
                return False
        else:
            logger.error(f"❌ Получили неожиданный тип: {type(result)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка в тесте: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    import asyncio
    print("Запускаем тест...")
    success = asyncio.run(test_predict_logic())
    print(f"Результат теста: {success}")
    if success:
        print("🎉 Логика MLManager работает корректно!")
        logger.info("🎉 Логика MLManager работает корректно!")
    else:
        print("⚠️ Требуются исправления")
        logger.warning("⚠️ Требуются исправления")