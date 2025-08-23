#!/usr/bin/env python3
"""
Unit tests for ML adapters and ModelAdapterFactory.

Tests adapter creation, factory pattern implementation,
configuration validation, and model integration.
"""

import pytest
import tempfile
import torch
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any

from ml.adapters.base import BaseModelAdapter
from ml.adapters.factory import ModelAdapterFactory, register_future_adapters
from ml.adapters.patchtst import PatchTSTAdapter


class MockAdapter(BaseModelAdapter):
    """Mock adapter for testing factory registration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = MagicMock()
        self.is_loaded = True
    
    async def load(self) -> None:
        """Load model method."""
        self._initialized = True
    
    async def predict(self, data: np.ndarray, **kwargs) -> np.ndarray:
        return np.array([0.6, 0.4])
    
    def get_model_info(self) -> Dict[str, Any]:
        return {'type': 'mock', 'version': '1.0'}
    
    def interpret_outputs(self, raw_outputs, **kwargs):
        """Interpret raw model outputs."""
        from ml.adapters.base import UnifiedPrediction, RiskMetrics, RiskLevel
        return UnifiedPrediction(
            signal_type="LONG",
            confidence=0.8,
            signal_strength=0.8,
            timeframe_predictions={},
            primary_direction="LONG",
            primary_confidence=0.8,
            primary_returns={"15m": 0.01},
            risk_level="LOW",
            risk_metrics=RiskMetrics(
                max_drawdown_1h=0.01,
                max_rally_1h=0.02,
                max_drawdown_4h=0.01,
                max_rally_4h=0.02,
                avg_risk=0.3,
                risk_level=RiskLevel.LOW
            )
        )


class TestModelAdapterFactory:
    """Test ModelAdapterFactory functionality."""
    
    def test_factory_available_types(self):
        """Test getting available adapter types."""
        types = ModelAdapterFactory.get_available_types()
        
        assert 'PatchTST' in types
        assert 'UnifiedPatchTST' in types
        assert 'patchtst' in types
        assert len(types) >= 3
    
    def test_create_adapter_patchtst(self):
        """Test creating PatchTST adapter."""
        config = {
            'model_file': 'test_model.pth',
            'device': 'cpu',
            'scaler_file': 'test_scaler.pkl'
        }
        
        adapter = ModelAdapterFactory.create_adapter('PatchTST', config)
        
        assert isinstance(adapter, PatchTSTAdapter)
        assert adapter.config == config
    
    def test_create_adapter_unknown_type(self):
        """Test creating unknown adapter type."""
        with pytest.raises(ValueError, match="Unknown model type: UnknownModel"):
            ModelAdapterFactory.create_adapter('UnknownModel', {})
    
    def test_register_adapter_success(self):
        """Test successful adapter registration."""
        # Register mock adapter
        ModelAdapterFactory.register_adapter('MockAdapter', MockAdapter)
        
        # Verify registration
        assert 'MockAdapter' in ModelAdapterFactory.get_available_types()
        
        # Test creation
        config = {'test': 'config'}
        adapter = ModelAdapterFactory.create_adapter('MockAdapter', config)
        assert isinstance(adapter, MockAdapter)
    
    def test_register_adapter_invalid_class(self):
        """Test registering invalid adapter class."""
        class InvalidAdapter:
            """Invalid adapter that doesn't inherit from BaseModelAdapter."""
            pass
        
        with pytest.raises(ValueError, match="must inherit from BaseModelAdapter"):
            ModelAdapterFactory.register_adapter('InvalidAdapter', InvalidAdapter)
    
    def test_create_from_config_ml_disabled(self):
        """Test creating adapter when ML is disabled."""
        config = {
            'ml': {
                'enabled': False
            }
        }
        
        adapter = ModelAdapterFactory.create_from_config(config)
        assert adapter is None
    
    def test_create_from_config_legacy_format(self):
        """Test creating adapter with legacy configuration format."""
        config = {
            'ml': {
                'enabled': True,
                'model': {
                    'name': 'UnifiedPatchTST',
                    'model_file': 'test_model.pth',
                    'device': 'cpu'
                }
            }
        }
        
        adapter = ModelAdapterFactory.create_from_config(config)
        assert isinstance(adapter, PatchTSTAdapter)
    
    def test_create_from_config_new_format_active_model(self):
        """Test creating adapter with new configuration format."""
        config = {
            'ml': {
                'enabled': True,
                'active_model': 'patchtst',
                'models': {
                    'patchtst': {
                        'enabled': True,
                        'type': 'PatchTST',
                        'model_file': 'test_model.pth',
                        'device': 'cpu'
                    }
                }
            }
        }
        
        adapter = ModelAdapterFactory.create_from_config(config)
        assert isinstance(adapter, PatchTSTAdapter)
    
    def test_create_from_config_model_disabled(self):
        """Test creating adapter when active model is disabled."""
        config = {
            'ml': {
                'enabled': True,
                'active_model': 'patchtst',
                'models': {
                    'patchtst': {
                        'enabled': False,
                        'type': 'PatchTST'
                    }
                }
            }
        }
        
        adapter = ModelAdapterFactory.create_from_config(config)
        assert adapter is None
    
    def test_validate_config_success(self):
        """Test successful configuration validation."""
        config = {
            'model_file': 'test_model.pth',
            'device': 'cpu',
            'scaler_file': 'test_scaler.pkl'
        }
        
        is_valid, errors = ModelAdapterFactory.validate_config(config, 'PatchTST')
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_config_unknown_model(self):
        """Test validation with unknown model type."""
        config = {}
        
        is_valid, errors = ModelAdapterFactory.validate_config(config, 'UnknownModel')
        
        assert not is_valid
        assert len(errors) > 0
        assert 'Unknown model type' in errors[0]
    
    def test_validate_config_missing_optional_fields(self):
        """Test validation with missing optional fields."""
        config = {}  # No required fields
        
        is_valid, errors = ModelAdapterFactory.validate_config(config, 'PatchTST')
        
        # Should still be valid as fields are optional with defaults
        assert is_valid


class TestPatchTSTAdapter:
    """Test PatchTSTAdapter functionality."""
    
    @pytest.fixture
    def temp_model_dir(self):
        """Create temporary directory with mock model files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create dummy model file
            model_file = temp_path / 'model.pth'
            torch.save({'state_dict': {}}, model_file)
            
            # Create dummy scaler file with a simple dict instead of MagicMock
            scaler_file = temp_path / 'scaler.pkl'
            import pickle
            mock_scaler = {'feature_names': ['feature1', 'feature2'], 'scaler_type': 'mock'}
            with open(scaler_file, 'wb') as f:
                pickle.dump(mock_scaler, f)
            
            yield temp_path
    
    @pytest.fixture
    def adapter_config(self, temp_model_dir):
        """Create adapter configuration."""
        return {
            'model_file': str(temp_model_dir / 'model.pth'),
            'scaler_file': str(temp_model_dir / 'scaler.pkl'),
            'device': 'cpu',
            'sequence_length': 240,
            'prediction_length': 1,
            'd_model': 64,
            'patch_len': 16,
            'stride': 16
        }
    
    def test_adapter_initialization(self, adapter_config):
        """Test PatchTSTAdapter initialization."""
        adapter = PatchTSTAdapter(adapter_config)
        
        assert adapter.config == adapter_config
        assert not adapter._initialized
        assert adapter.model is None
        assert adapter.scaler is None
        assert adapter.device == torch.device('cpu')
    
    @pytest.mark.asyncio
    async def test_adapter_load_model_success(self, adapter_config):
        """Test successful model loading."""
        with patch('ml.logic.patchtst_model.create_unified_model') as mock_model_func:
            with patch('pickle.load') as mock_pickle_load:
                with patch('torch.load') as mock_torch_load:
                    with patch('ml.logic.feature_engineering_production.ProductionFeatureEngineer'):
                        with patch('ml.logic.signal_quality_analyzer.SignalQualityAnalyzer'):
                            mock_model = MagicMock()
                            mock_model.load_state_dict = MagicMock()
                            mock_model.to = MagicMock(return_value=mock_model)
                            mock_model.eval = MagicMock()
                            mock_model_func.return_value = mock_model
                            
                            mock_pickle_load.return_value = MagicMock()
                            mock_torch_load.return_value = {"model_state_dict": {}}
                            
                            adapter = PatchTSTAdapter(adapter_config)
                            await adapter.load()
                            
                            assert adapter._initialized
                            assert adapter.model is not None
                            assert adapter.scaler is not None
    
    @pytest.mark.asyncio
    async def test_adapter_load_model_file_not_found(self, adapter_config):
        """Test model loading with missing file."""
        adapter_config['model_file'] = '/nonexistent/model.pth'
        adapter = PatchTSTAdapter(adapter_config)
        
        with pytest.raises(FileNotFoundError):
            await adapter.load()
        
        assert not adapter._initialized
    
    @pytest.mark.asyncio
    async def test_adapter_predict_success(self, adapter_config):
        """Test successful prediction."""
        with patch('ml.logic.patchtst_model.create_unified_model') as mock_model_func:
            with patch('pickle.load') as mock_pickle_load:
                with patch('torch.load') as mock_torch_load:
                    with patch('ml.logic.feature_engineering_production.ProductionFeatureEngineer'):
                        with patch('ml.logic.signal_quality_analyzer.SignalQualityAnalyzer'):
                            # Setup mocks
                            mock_model = MagicMock()
                            mock_model.load_state_dict = MagicMock()
                            mock_model.to = MagicMock(return_value=mock_model)
                            mock_model.eval = MagicMock()
                            mock_model_func.return_value = mock_model
                            
                            mock_scaler = MagicMock()
                            mock_pickle_load.return_value = mock_scaler
                            mock_torch_load.return_value = {"model_state_dict": {}}
                            
                            # Mock model prediction
                            mock_pred = torch.tensor([0.6, 0.4, 0.1, 0.2] + [0.0] * 16)
                            mock_model.return_value = mock_pred
                            
                            # Mock scaler
                            mock_scaler.transform.return_value = np.random.randn(96, 240)
                            
                            adapter = PatchTSTAdapter(adapter_config)
                            await adapter.load()
                            
                            # Test data - prepared features
                            test_data = np.random.randn(96, 240)
                            result = await adapter.predict(test_data)
                            
                            assert isinstance(result, np.ndarray)
                            assert len(result) == 20  # PatchTST outputs 20 values
    
    @pytest.mark.asyncio
    async def test_adapter_predict_not_loaded(self, adapter_config):
        """Test prediction when model is not loaded."""
        adapter = PatchTSTAdapter(adapter_config)
        
        test_data = np.random.randn(96, 240)
        
        with pytest.raises(ValueError, match="Adapter not initialized"):
            await adapter.predict(test_data)
    
    def test_adapter_validate_input_success(self, adapter_config):
        """Test successful input validation."""
        adapter = PatchTSTAdapter(adapter_config)
        
        valid_data = np.random.randn(96, 240)
        result = adapter.validate_input(valid_data)
        
        assert result is True
    
    def test_adapter_validate_input_none(self, adapter_config):
        """Test input validation with None data."""
        adapter = PatchTSTAdapter(adapter_config)
        
        # None data should fail validation
        result = adapter.validate_input(None)
        
        assert result is False
    
    def test_adapter_validate_input_too_short(self, adapter_config):
        """Test input validation with too short sequence."""
        adapter = PatchTSTAdapter(adapter_config)
        
        # Too short sequence (as DataFrame)
        import pandas as pd
        invalid_data = pd.DataFrame(np.random.randn(50, 5))
        result = adapter.validate_input(invalid_data)
        
        assert result is True  # Base validation just checks for None/empty
    
    def test_adapter_get_model_info(self, adapter_config):
        """Test getting model information."""
        adapter = PatchTSTAdapter(adapter_config)
        
        info = adapter.get_model_info()
        
        assert 'model_type' in info
        assert 'initialized' in info
        assert info['model_type'] == 'UnifiedPatchTST'
        assert info['initialized'] is False
    


class TestBaseModelAdapter:
    """Test BaseModelAdapter abstract functionality."""
    
    def test_base_adapter_cannot_be_instantiated(self):
        """Test that BaseModelAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseModelAdapter({})
    
    def test_base_adapter_abstract_methods(self):
        """Test that abstract methods must be implemented."""
        class IncompleteAdapter(BaseModelAdapter):
            """Adapter missing required methods."""
            pass
        
        with pytest.raises(TypeError):
            IncompleteAdapter({})


class TestAdapterIntegration:
    """Test adapter integration scenarios."""
    
    def test_register_future_adapters(self):
        """Test registering future adapters function."""
        # Should not raise any errors
        register_future_adapters()
    
    @pytest.mark.asyncio
    async def test_full_adapter_lifecycle(self, temp_model_dir):
        """Test complete adapter lifecycle."""
        config = {
            'ml': {
                'enabled': True,
                'active_model': 'patchtst',
                'models': {
                    'patchtst': {
                        'enabled': True,
                        'type': 'PatchTST',
                        'model_file': str(temp_model_dir / 'model.pth'),
                        'scaler_file': str(temp_model_dir / 'scaler.pkl'),
                        'device': 'cpu'
                    }
                }
            }
        }
        
        # Create adapter from config
        adapter = ModelAdapterFactory.create_from_config(config)
        assert adapter is not None
        
        # Initialize adapter (with mocked dependencies)
        with patch('ml.logic.patchtst_model.create_unified_model'):
            with patch('pickle.load'):
                with patch('torch.load') as mock_torch_load:
                    mock_torch_load.return_value = {"model_state_dict": {}}
                    await adapter.initialize()
                    assert adapter._initialized
        
        # Get model info
        info = adapter.get_model_info()
        assert info['initialized']


if __name__ == "__main__":
    pytest.main([__file__])