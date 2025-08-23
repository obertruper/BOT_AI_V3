#!/usr/bin/env python3
"""
Integration tests for component interaction.

Tests integration between ConfigManager, ML adapters, TransactionManager,
and their interaction with the system orchestrator.
"""

import pytest
import asyncio
import tempfile
import yaml
import pickle
import torch
import numpy as np
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from core.config.config_manager import ConfigManager
from core.config.models import RootConfig
from ml.adapters.factory import ModelAdapterFactory
from ml.adapters.base import BaseModelAdapter
from database.connections.transaction_manager import TransactionManager, UnitOfWork


class TestConfigManagerMLAdapterIntegration:
    """Test integration between ConfigManager and ML adapters."""
    
    @pytest.fixture
    def temp_config_with_ml(self):
        """Create temporary configuration with ML settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create config with ML settings
            config_data = {
                'ml': {
                    'enabled': True,
                    'use_adapters': True,
                    'active_model': 'patchtst',
                    'models': {
                        'patchtst': {
                            'enabled': True,
                            'type': 'PatchTST',
                            'adapter_class': 'PatchTST',
                            'model_file': 'test_model.pth',
                            'scaler_file': 'test_scaler.pkl',
                            'device': 'cpu'
                        }
                    }
                }
            }
            
            config_file = temp_path / 'config.yaml'
            with open(config_file, 'w') as f:
                yaml.safe_dump(config_data, f)
            
            yield temp_path / 'config.yaml'
    
    def test_config_ml_adapter_creation(self, temp_config_with_ml):
        """Test creating ML adapter from configuration."""
        # Load configuration
        config_manager = ConfigManager(str(temp_config_with_ml))
        config = config_manager.get_config()
        
        assert isinstance(config, RootConfig)
        assert config.ml.enabled
        assert config.ml.use_adapters
        assert config.ml.active_model == 'patchtst'
        
        # Create adapter from config
        config_dict = config.model_dump() if hasattr(config, 'model_dump') else config.dict()
        adapter = ModelAdapterFactory.create_from_config(config_dict)
        
        assert adapter is not None
        assert isinstance(adapter, BaseModelAdapter)
    
    def test_config_validation_with_ml_settings(self, temp_config_with_ml):
        """Test configuration validation with ML settings."""
        config_manager = ConfigManager(str(temp_config_with_ml))
        config = config_manager.get_config()
        
        # Validate consistency
        warnings = config.validate_consistency()
        
        # Should have warning about missing ML model file
        ml_warnings = [w for w in warnings if 'ML' in w or 'model' in w.lower()]
        assert len(ml_warnings) > 0  # Expected since model file doesn't exist
    
    @pytest.mark.asyncio
    async def test_config_update_affects_ml_adapter(self, temp_config_with_ml):
        """Test that configuration updates affect ML adapter creation."""
        config_manager = ConfigManager(str(temp_config_with_ml))
        
        # Create adapter with original config
        original_config = config_manager.get_config()
        config_dict = original_config.model_dump() if hasattr(original_config, 'model_dump') else original_config.dict()
        adapter1 = ModelAdapterFactory.create_from_config(config_dict)
        assert adapter1 is not None
        
        # Update config to disable ML
        config_manager.update_system_config({
            'ml': {
                'enabled': False
            }
        })
        
        # Create adapter with updated config
        updated_config = config_manager.get_config()
        config_dict = updated_config.model_dump() if hasattr(updated_config, 'model_dump') else updated_config.dict()
        adapter2 = ModelAdapterFactory.create_from_config(config_dict)
        
        assert adapter2 is None  # Should be None because ML is disabled


class TestTransactionManagerConfigIntegration:
    """Test integration between TransactionManager and configuration."""
    
    @pytest.fixture
    def temp_config_with_db(self):
        """Create temporary configuration with database settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config_data = {
                'database': {
                    'host': '127.0.0.1',
                    'port': 5555,
                    'name': 'test_db',
                    'user': 'test_user',
                    'pool': {
                        'min_connections': 5,
                        'max_connections': 20,
                        'connection_timeout': 30,
                        'idle_timeout': 300
                    }
                }
            }
            
            config_file = temp_path / 'config.yaml'
            with open(config_file, 'w') as f:
                yaml.safe_dump(config_data, f)
            
            yield temp_path / 'config.yaml'
    
    def test_config_provides_database_settings(self, temp_config_with_db):
        """Test that configuration provides database connection settings."""
        config_manager = ConfigManager(str(temp_config_with_db))
        config = config_manager.get_config()
        
        assert config.database.host == '127.0.0.1'
        assert config.database.port == 5555
        assert config.database.name == 'test_db'
        assert config.database.pool.min_connections == 5
        assert config.database.pool.max_connections == 20
    
    def test_transaction_manager_from_config(self, temp_config_with_db):
        """Test creating TransactionManager using configuration settings."""
        config_manager = ConfigManager(str(temp_config_with_db))
        config = config_manager.get_config()
        
        # Mock connection pool creation
        mock_pool = MagicMock()
        
        # Create TransactionManager with config-based pool
        transaction_manager = TransactionManager(mock_pool)
        
        assert transaction_manager is not None
        assert transaction_manager.pool == mock_pool


class TestFullSystemIntegration:
    """Test full system integration scenarios."""
    
    @pytest.fixture
    def complete_config(self):
        """Create complete system configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config_data = {
                'system': {
                    'name': 'IntegrationTest',
                    'version': '3.0.0',
                    'environment': 'testing'
                },
                'database': {
                    'host': '127.0.0.1',
                    'port': 5555,
                    'name': 'integration_test',
                    'pool': {
                        'min_connections': 2,
                        'max_connections': 10
                    }
                },
                'ml': {
                    'enabled': True,
                    'use_adapters': True,
                    'active_model': 'patchtst',
                    'models': {
                        'patchtst': {
                            'enabled': True,
                            'type': 'PatchTST',
                            'model_file': 'test_model.pth',
                            'device': 'cpu'
                        }
                    }
                },
                'trading': {
                    'hedge_mode': True,
                    'orders': {
                        'default_leverage': 5
                    }
                }
            }
            
            config_file = temp_path / 'config.yaml'
            with open(config_file, 'w') as f:
                yaml.safe_dump(config_data, f)
            
            yield temp_path / 'config.yaml'
    
    def test_config_loading_and_validation(self, complete_config):
        """Test loading and validation of complete configuration."""
        config_manager = ConfigManager(str(complete_config))
        config = config_manager.get_config()
        
        # Verify all sections loaded correctly
        assert isinstance(config, RootConfig)
        assert config.system.name == 'IntegrationTest'
        assert config.database.port == 5555
        assert config.ml.enabled
        assert config.trading.orders.default_leverage == 5
        
        # Validate consistency
        warnings = config.validate_consistency()
        # Should have some warnings about missing ML model files
        assert isinstance(warnings, list)
    
    def test_component_creation_from_config(self, complete_config):
        """Test creating all components from configuration."""
        config_manager = ConfigManager(str(complete_config))
        config = config_manager.get_config()
        config_dict = config.model_dump() if hasattr(config, 'model_dump') else config.dict()
        
        # Create ML adapter
        ml_adapter = ModelAdapterFactory.create_from_config(config_dict)
        assert ml_adapter is not None
        
        # Create TransactionManager (with mock pool)
        mock_pool = MagicMock()
        transaction_manager = TransactionManager(mock_pool)
        assert transaction_manager is not None
        
        # Verify configuration consistency
        system_config = config_manager.get_system_config()
        assert system_config.name == 'IntegrationTest'
    
    @pytest.mark.asyncio
    async def test_async_component_initialization(self, complete_config):
        """Test asynchronous initialization of components."""
        config_manager = ConfigManager(str(complete_config))
        
        # Initialize config manager
        await config_manager.initialize()
        assert config_manager._is_initialized
        
        # Get configuration
        config = config_manager.get_config()
        config_dict = config.model_dump() if hasattr(config, 'model_dump') else config.dict()
        
        # Create and initialize ML adapter
        ml_adapter = ModelAdapterFactory.create_from_config(config_dict)
        if ml_adapter:
            # Mock dependencies for successful load
            with patch('ml.logic.patchtst_model.UnifiedPatchTST'):
                with patch('pickle.load'):
                    with patch('pathlib.Path.exists', return_value=True):
                        success = await ml_adapter.load_model()
                        # May fail due to missing files, but should not crash
                        assert isinstance(success, bool)
    
    def test_configuration_error_handling(self):
        """Test configuration error handling in integration scenario."""
        # Test with invalid config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_config_path = f.name
        
        config_manager = ConfigManager(invalid_config_path)
        
        with pytest.raises(Exception):  # Should raise some configuration error
            config_manager.get_config()
        
        # Cleanup
        Path(invalid_config_path).unlink()


class TestMLAdapterTransactionIntegration:
    """Test integration between ML adapters and transaction management."""
    
    @pytest.mark.asyncio
    async def test_ml_prediction_with_transaction(self):
        """Test ML prediction within a transaction context."""
        # Mock transaction manager
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value = mock_conn
        
        transaction_manager = TransactionManager(mock_pool)
        
        # Mock ML adapter
        config = {
            'model_file': 'test_model.pth',
            'device': 'cpu'
        }
        
        with patch('ml.logic.patchtst_model.UnifiedPatchTST'):
            with patch('pickle.load'):
                adapter = ModelAdapterFactory.create_adapter('PatchTST', config)
                
                # Test prediction within transaction
                async def prediction_operation(conn):
                    """Simulate ML prediction and database storage operation."""
                    # Mock prediction
                    test_data = np.random.randn(240, 10)
                    with patch.object(adapter, 'predict') as mock_predict:
                        mock_predict.return_value = {
                            'predictions': np.array([0.6, 0.4]),
                            'confidence': 0.8,
                            'model_info': {'type': 'test'}
                        }
                        
                        prediction = await adapter.predict(test_data)
                        
                        # Store prediction in database (mocked)
                        await conn.execute(
                            "INSERT INTO predictions (data, confidence) VALUES ($1, $2)",
                            prediction['predictions'].tolist(),
                            prediction['confidence']
                        )
                        
                        return prediction['confidence']
                
                # Execute within transaction
                async with transaction_manager.transaction() as conn:
                    confidence = await prediction_operation(conn)
                    assert confidence == 0.8
    
    @pytest.mark.asyncio
    async def test_unit_of_work_with_ml_operations(self):
        """Test Unit of Work pattern with ML operations."""
        mock_pool = MagicMock()
        transaction_manager = TransactionManager(mock_pool)
        transaction_manager.execute_in_transaction = AsyncMock(return_value=['pred1', 'pred2'])
        
        uow = UnitOfWork(transaction_manager)
        
        # Register ML-related operations
        async def generate_prediction():
            return "pred1"
        
        async def store_prediction():
            return "pred2"
        
        uow.register_operation(generate_prediction)
        uow.register_operation(store_prediction)
        
        # Commit operations
        results = await uow.commit()
        assert results == ['pred1', 'pred2']


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""
    
    @pytest.mark.asyncio
    async def test_trading_signal_processing_workflow(self):
        """Test complete trading signal processing workflow."""
        # This would test:
        # 1. Load configuration
        # 2. Create ML adapter
        # 3. Process market data
        # 4. Generate trading signals
        # 5. Store results in database within transaction
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create configuration
            config_data = {
                'ml': {
                    'enabled': True,
                    'active_model': 'patchtst',
                    'models': {
                        'patchtst': {
                            'enabled': True,
                            'type': 'PatchTST'
                        }
                    }
                },
                'database': {'port': 5555}
            }
            
            config_file = temp_path / 'config.yaml'
            with open(config_file, 'w') as f:
                yaml.safe_dump(config_data, f)
            
            # Load configuration
            config_manager = ConfigManager(str(config_file))
            config = config_manager.get_config()
            config_dict = config.model_dump() if hasattr(config, 'model_dump') else config.dict()
            
            # Create components
            ml_adapter = ModelAdapterFactory.create_from_config(config_dict)
            mock_pool = MagicMock()
            transaction_manager = TransactionManager(mock_pool)
            
            assert ml_adapter is not None
            assert transaction_manager is not None
            
            # Simulate workflow
            with patch.object(ml_adapter, 'predict') as mock_predict:
                mock_predict.return_value = {
                    'predictions': np.array([0.7, 0.3]),
                    'confidence': 0.85,
                    'model_info': {'type': 'PatchTST'}
                }
                
                # Mock database operations
                transaction_manager.execute_in_transaction = AsyncMock(
                    return_value=['signal_generated', 'signal_stored']
                )
                
                # Execute workflow
                async def generate_signal():
                    return "signal_generated"
                
                async def store_signal():
                    return "signal_stored"
                
                results = await transaction_manager.execute_in_transaction([
                    generate_signal,
                    store_signal
                ])
                
                assert results == ['signal_generated', 'signal_stored']


if __name__ == "__main__":
    pytest.main([__file__])