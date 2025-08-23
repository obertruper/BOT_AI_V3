#!/usr/bin/env python3
"""
Тесты для системы адаптеров ML моделей.
Проверяет базовую функциональность и интеграцию.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest
import torch

from ml.adapters.base import (
    BaseModelAdapter,
    RiskLevel,
    RiskMetrics,
    SignalDirection,
    TimeframePrediction,
    UnifiedPrediction,
)
from ml.adapters.factory import ModelAdapterFactory
from ml.adapters.patchtst import PatchTSTAdapter


class TestUnifiedPrediction:
    """Тесты для UnifiedPrediction dataclass"""
    
    def test_unified_prediction_creation(self):
        """Тест создания UnifiedPrediction"""
        # Создаем тестовые данные
        risk_metrics = RiskMetrics(
            max_drawdown_1h=0.01,
            max_rally_1h=0.02,
            max_drawdown_4h=0.03,
            max_rally_4h=0.04,
            avg_risk=0.025,
            risk_level=RiskLevel.LOW
        )
        
        tf_prediction = TimeframePrediction(
            timeframe="1h",
            direction=SignalDirection.LONG,
            confidence=0.8,
            expected_return=0.015,
            direction_probabilities={"LONG": 0.7, "SHORT": 0.2, "NEUTRAL": 0.1}
        )
        
        prediction = UnifiedPrediction(
            signal_type="LONG",
            confidence=0.75,
            signal_strength=0.8,
            timeframe_predictions={"1h": tf_prediction},
            primary_direction="LONG",
            primary_confidence=0.75,
            primary_returns={"1h": 0.015},
            risk_level="LOW",
            risk_metrics=risk_metrics,
            stop_loss_pct=0.01,
            take_profit_pct=0.02
        )
        
        assert prediction.signal_type == "LONG"
        assert prediction.confidence == 0.75
        assert prediction.risk_level == "LOW"
    
    def test_unified_prediction_to_dict(self):
        """Тест конвертации UnifiedPrediction в словарь"""
        risk_metrics = RiskMetrics(
            max_drawdown_1h=0.01,
            max_rally_1h=0.02,
            max_drawdown_4h=0.03,
            max_rally_4h=0.04,
            avg_risk=0.025,
            risk_level=RiskLevel.MEDIUM
        )
        
        # Создаем предсказания для всех таймфреймов
        timeframe_predictions = {}
        for tf in ["15m", "1h", "4h", "12h"]:
            timeframe_predictions[tf] = TimeframePrediction(
                timeframe=tf,
                direction=SignalDirection.LONG,
                confidence=0.7,
                expected_return=0.01,
                direction_probabilities={"LONG": 0.6, "SHORT": 0.3, "NEUTRAL": 0.1}
            )
        
        prediction = UnifiedPrediction(
            signal_type="LONG",
            confidence=0.75,
            signal_strength=0.8,
            timeframe_predictions=timeframe_predictions,
            primary_direction="LONG",
            primary_confidence=0.75,
            primary_returns={"15m": 0.01, "1h": 0.02, "4h": 0.03, "12h": 0.04},
            risk_level="MEDIUM",
            risk_metrics=risk_metrics
        )
        
        result = prediction.to_dict()
        
        # Проверяем основные поля
        assert result["signal_type"] == "LONG"
        assert result["confidence"] == 0.75
        assert result["risk_level"] == "MEDIUM"
        
        # Проверяем legacy поля для совместимости
        assert "returns_15m" in result
        assert "direction_15m" in result
        assert "confidence_15m" in result


class TestModelAdapterFactory:
    """Тесты для фабрики адаптеров"""
    
    def test_factory_create_adapter(self):
        """Тест создания адаптера через фабрику"""
        config = {
            "model_file": "test_model.pth",
            "device": "cpu"
        }
        
        adapter = ModelAdapterFactory.create_adapter("PatchTST", config)
        assert isinstance(adapter, PatchTSTAdapter)
    
    def test_factory_unknown_type(self):
        """Тест создания адаптера неизвестного типа"""
        config = {"device": "cpu"}
        
        with pytest.raises(ValueError, match="Unknown model type"):
            ModelAdapterFactory.create_adapter("UnknownModel", config)
    
    def test_factory_get_available_types(self):
        """Тест получения списка доступных типов"""
        types = ModelAdapterFactory.get_available_types()
        assert "PatchTST" in types
        assert "UnifiedPatchTST" in types
        assert "patchtst" in types
    
    def test_factory_create_from_config(self):
        """Тест создания адаптера из конфигурации"""
        # Новый формат конфигурации
        config = {
            "ml": {
                "enabled": True,
                "active_model": "patchtst",
                "models": {
                    "patchtst": {
                        "enabled": True,
                        "type": "PatchTST",
                        "model_file": "model.pth",
                        "device": "cpu"
                    }
                }
            }
        }
        
        adapter = ModelAdapterFactory.create_from_config(config)
        assert isinstance(adapter, PatchTSTAdapter)
    
    def test_factory_legacy_config(self):
        """Тест создания адаптера из legacy конфигурации"""
        config = {
            "ml": {
                "enabled": True,
                "model": {
                    "name": "UnifiedPatchTST",
                    "device": "cpu"
                }
            }
        }
        
        adapter = ModelAdapterFactory.create_from_config(config)
        assert isinstance(adapter, PatchTSTAdapter)
    
    def test_factory_disabled_ml(self):
        """Тест когда ML отключен в конфигурации"""
        config = {
            "ml": {
                "enabled": False
            }
        }
        
        adapter = ModelAdapterFactory.create_from_config(config)
        assert adapter is None


class TestPatchTSTAdapter:
    """Тесты для PatchTST адаптера"""
    
    @pytest.fixture
    def adapter(self):
        """Создает тестовый адаптер"""
        config = {
            "model_file": "test_model.pth",
            "scaler_file": "test_scaler.pkl",
            "device": "cpu"
        }
        return PatchTSTAdapter(config)
    
    def test_adapter_initialization(self, adapter):
        """Тест инициализации адаптера"""
        assert adapter.context_length == 96
        assert adapter.num_features == 240
        assert adapter.num_targets == 20
        assert not adapter.is_initialized()
    
    @patch('ml.adapters.patchtst.torch.load')
    @patch('ml.adapters.patchtst.create_unified_model')
    @patch('ml.adapters.patchtst.pickle.load')
    @patch('ml.adapters.patchtst.FeatureEngineer')
    @patch('ml.adapters.patchtst.SignalQualityAnalyzer')
    async def test_adapter_load(self, mock_analyzer, mock_fe, mock_pickle, mock_create_model, mock_torch_load, adapter):
        """Тест загрузки компонентов адаптера"""
        # Настраиваем моки
        mock_model = MagicMock()
        mock_create_model.return_value = mock_model
        mock_torch_load.return_value = {"model_state_dict": {}}
        
        # Мокаем Path.exists
        with patch.object(Path, 'exists', return_value=True):
            with patch('builtins.open', create=True):
                await adapter.load()
        
        assert adapter.model is not None
        assert adapter.scaler is not None
        assert adapter.feature_engineer is not None
        assert adapter.quality_analyzer is not None
    
    def test_adapter_validate_input(self, adapter):
        """Тест валидации входных данных"""
        # Валидные данные
        valid_array = np.random.randn(96, 240)
        assert adapter.validate_input(valid_array)
        
        valid_df = pd.DataFrame(np.random.randn(100, 5), columns=['open', 'high', 'low', 'close', 'volume'])
        assert adapter.validate_input(valid_df)
        
        # Невалидные данные
        assert not adapter.validate_input(None)
        assert not adapter.validate_input(np.array([]))
        assert not adapter.validate_input(pd.DataFrame())
    
    @patch('ml.adapters.patchtst.torch.load')
    @patch('ml.adapters.patchtst.create_unified_model')
    async def test_adapter_predict_with_array(self, mock_create_model, mock_torch_load, adapter):
        """Тест предсказания с numpy array"""
        # Настраиваем моки
        mock_model = MagicMock()
        mock_output = torch.randn(1, 20)
        mock_model.return_value = mock_output
        mock_create_model.return_value = mock_model
        mock_torch_load.return_value = {"model_state_dict": {}}
        
        adapter.model = mock_model
        adapter.scaler = MagicMock()
        adapter.scaler.transform = lambda x: x
        adapter._initialized = True
        
        # Тестовые данные
        test_data = np.random.randn(96, 240)
        
        # Предсказание
        result = await adapter.predict(test_data)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (20,)
    
    def test_adapter_interpret_outputs(self, adapter):
        """Тест интерпретации выходов модели"""
        # Мокаем quality analyzer
        mock_analyzer = MagicMock()
        mock_filter_result = MagicMock()
        mock_filter_result.passed = True
        mock_filter_result.signal_type = "LONG"
        mock_filter_result.strategy_used.value = "moderate"
        mock_filter_result.rejection_reasons = []
        
        mock_quality_metrics = MagicMock()
        mock_quality_metrics.quality_score = 0.7
        mock_quality_metrics.agreement_score = 0.8
        mock_quality_metrics.confidence_score = 0.75
        mock_filter_result.quality_metrics = mock_quality_metrics
        
        mock_analyzer.analyze_signal_quality.return_value = mock_filter_result
        adapter.quality_analyzer = mock_analyzer
        
        # Тестовые выходы модели
        raw_outputs = np.array([
            # Future returns (0-3)
            0.01, 0.02, 0.03, 0.04,
            # Direction logits (4-15) - 4 таймфрейма × 3 класса
            2.0, 0.5, 0.1,  # 15m
            2.5, 0.3, 0.2,  # 1h
            3.0, 0.2, 0.1,  # 4h
            2.8, 0.4, 0.2,  # 12h
            # Risk metrics (16-19)
            0.02, 0.03, 0.04, 0.05
        ])
        
        # Интерпретация
        result = adapter.interpret_outputs(raw_outputs, symbol="BTCUSDT", current_price=50000)
        
        assert isinstance(result, UnifiedPrediction)
        assert result.signal_type == "LONG"
        assert result.model_name == "UnifiedPatchTST"
        assert "15m" in result.timeframe_predictions
        assert result.risk_metrics is not None
    
    def test_adapter_get_model_info(self, adapter):
        """Тест получения информации о модели"""
        info = adapter.get_model_info()
        
        assert info["model_type"] == "UnifiedPatchTST"
        assert info["context_length"] == 96
        assert info["num_features"] == 240
        assert info["num_targets"] == 20
        assert "device" in info
        assert "initialized" in info


class TestBaseModelAdapter:
    """Тесты для базового класса адаптера"""
    
    def test_abstract_methods(self):
        """Тест что базовый класс требует реализации абстрактных методов"""
        config = {"device": "cpu"}
        
        # Нельзя создать экземпляр абстрактного класса
        with pytest.raises(TypeError):
            BaseModelAdapter(config)
    
    def test_device_setup(self):
        """Тест настройки устройства"""
        # Создаем конкретную реализацию для тестирования
        class TestAdapter(BaseModelAdapter):
            async def load(self): pass
            async def predict(self, data, **kwargs): return np.array([])
            def interpret_outputs(self, raw_outputs, **kwargs): return None
            def get_model_info(self): return {}
        
        # CPU device
        adapter = TestAdapter({"device": "cpu"})
        assert adapter.device.type == "cpu"
        
        # Auto device (будет CPU в тестах без CUDA)
        adapter = TestAdapter({"device": "auto"})
        assert adapter.device.type == "cpu"


@pytest.mark.asyncio
class TestAsyncIntegration:
    """Тесты асинхронной интеграции"""
    
    async def test_adapter_initialize(self):
        """Тест полной инициализации адаптера"""
        config = {
            "model_file": "test_model.pth",
            "scaler_file": "test_scaler.pkl",
            "device": "cpu"
        }
        
        adapter = PatchTSTAdapter(config)
        
        # Мокаем load
        adapter.load = AsyncMock()
        
        await adapter.initialize()
        
        assert adapter.is_initialized()
        adapter.load.assert_called_once()
    
    async def test_adapter_update_model(self):
        """Тест обновления модели"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Создаем временные файлы
            old_model = Path(tmpdir) / "old_model.pth"
            new_model = Path(tmpdir) / "new_model.pth"
            old_model.touch()
            new_model.touch()
            
            config = {
                "model_file": str(old_model),
                "device": "cpu"
            }
            
            adapter = PatchTSTAdapter(config)
            adapter.model_path = old_model
            
            # Мокаем load
            adapter.load = AsyncMock()
            
            await adapter.update_model(str(new_model))
            
            # Проверяем что файл обновлен
            assert adapter.model_path.exists()
            adapter.load.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])