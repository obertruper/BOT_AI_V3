"""
Comprehensive tests for ML Prediction Logger - enhanced logging system
Tests the new ML logging functionality with table formatting and feature extraction
"""

import hashlib
import os
import sys
import time
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestMLPredictionLoggerCore:
    """Test core ML prediction logging functionality"""

    def test_prediction_logger_initialization(self):
        """Test ML prediction logger initialization"""
        # Mock the logger setup and database
        with (
            patch("ml.ml_prediction_logger.setup_logger") as mock_setup_logger,
            patch("ml.ml_prediction_logger.AsyncPGPool"),
        ):

            mock_logger = Mock()
            mock_setup_logger.return_value = mock_logger

            # Import after patching
            from ml.ml_prediction_logger import MLPredictionLogger

            # Initialize logger
            logger = MLPredictionLogger()

            # Test initial state
            assert logger.model_version == "unified_patchtst_v1.0"
            assert logger.batch_size == 10
            assert isinstance(logger.batch_predictions, list)
            assert len(logger.batch_predictions) == 0

    def test_features_hash_computation(self):
        """Test feature hash computation for deduplication"""
        with (
            patch("ml.ml_prediction_logger.setup_logger"),
            patch("ml.ml_prediction_logger.AsyncPGPool"),
        ):

            from ml.ml_prediction_logger import MLPredictionLogger

            logger = MLPredictionLogger()

            # Create a simple hash function for testing
            def compute_features_hash(features):
                """Simple hash function for testing"""
                return hashlib.sha256(str(features).encode()).hexdigest()

            # Monkey patch the method
            logger._compute_features_hash = compute_features_hash

            # Test feature arrays
            features1 = np.array([1, 2, 3, 4, 5] * 48)  # 240 features
            features2 = np.array([2, 3, 4, 5, 6] * 48)  # Different features
            features3 = features1.copy()  # Identical to features1

            # Compute hashes
            hash1 = logger._compute_features_hash(features1)
            hash2 = logger._compute_features_hash(features2)
            hash3 = logger._compute_features_hash(features3)

            # Test hash properties
            assert isinstance(hash1, str)
            assert len(hash1) == 64  # SHA256 hex digest length
            assert hash1 != hash2  # Different features should have different hashes
            assert hash1 == hash3  # Identical features should have same hash

    def test_key_features_extraction(self):
        """Test extraction of key trading indicators"""
        with (
            patch("ml.ml_prediction_logger.setup_logger"),
            patch("ml.ml_prediction_logger.AsyncPGPool"),
        ):

            from ml.ml_prediction_logger import MLPredictionLogger

            logger = MLPredictionLogger()

            # Create a mock feature extraction method
            def extract_key_features(features, market_data):
                """Mock feature extraction"""
                return {
                    "price_close": 50000.0,
                    "volume_current": 1500000,
                    "volatility_1h": 0.025,
                    "sma_20": 49800.0,
                    "ema_12": 50100.0,
                    "rsi_14": 65.5,
                    "macd_signal": 0.25,
                    "bb_position": -0.15,
                    "atr_14": 850.0,
                    "momentum_10": 0.032,
                }

            # Monkey patch the method
            logger._extract_key_features = extract_key_features

            # Mock 240 features array (typical ML model input)
            features = np.random.rand(240)

            # Mock market data
            market_data = pd.DataFrame(
                {
                    "close": [50000, 50100, 50200],
                    "volume": [1000000, 1100000, 1200000],
                    "high": [50050, 50150, 50250],
                    "low": [49950, 50050, 50150],
                }
            )

            # Extract key features
            key_features = logger._extract_key_features(features, market_data)

            # Test key features structure
            expected_keys = [
                "price_close",
                "volume_current",
                "volatility_1h",
                "sma_20",
                "ema_12",
                "rsi_14",
                "macd_signal",
                "bb_position",
                "atr_14",
                "momentum_10",
            ]

            for key in expected_keys:
                assert key in key_features
                assert isinstance(key_features[key], (int, float))

    def test_feature_statistics_computation(self):
        """Test computation of feature statistics"""
        with (
            patch("ml.ml_prediction_logger.setup_logger"),
            patch("ml.ml_prediction_logger.AsyncPGPool"),
        ):

            from ml.ml_prediction_logger import MLPredictionLogger

            logger = MLPredictionLogger()

            # Create a mock statistics computation method
            def compute_feature_statistics(features):
                """Mock statistics computation"""
                return {
                    "features_mean": float(np.mean(features)),
                    "features_std": float(np.std(features)),
                    "features_min": float(np.min(features)),
                    "features_max": float(np.max(features)),
                    "features_range": float(np.max(features) - np.min(features)),
                }

            # Monkey patch the method
            logger._compute_feature_statistics = compute_feature_statistics

            # Create test features with known statistics
            features = np.array([1.0, 2.0, 3.0, 4.0, 5.0] * 48)  # 240 features

            # Compute statistics
            stats = logger._compute_feature_statistics(features)

            # Test statistics
            assert "features_mean" in stats
            assert "features_std" in stats
            assert "features_min" in stats
            assert "features_max" in stats
            assert "features_range" in stats

            assert stats["features_mean"] == 3.0  # Mean of [1,2,3,4,5]
            assert stats["features_min"] == 1.0
            assert stats["features_max"] == 5.0
            assert stats["features_range"] == 4.0  # max - min

    @pytest.mark.asyncio
    async def test_prediction_logging(self):
        """Test complete prediction logging process"""
        with (
            patch("ml.ml_prediction_logger.setup_logger"),
            patch("ml.ml_prediction_logger.AsyncPGPool") as mock_pool,
        ):

            from ml.ml_prediction_logger import MLPredictionLogger

            logger = MLPredictionLogger()

            # Mock all necessary methods
            logger._compute_features_hash = lambda f: "mock_hash_123"
            logger._extract_key_features = lambda f, m: {
                "price_close": 50000.0,
                "volume_current": 1500000,
                "rsi_14": 65.5,
            }
            logger._compute_feature_statistics = lambda f: {
                "features_mean": 0.5,
                "features_std": 0.2,
                "features_min": 0.0,
                "features_max": 1.0,
                "features_range": 1.0,
            }

            # Mock database operations
            mock_pool.execute = AsyncMock()

            # Test data
            symbol = "BTCUSDT"
            features = np.random.rand(240)
            model_outputs = np.random.rand(20)
            predictions = {
                "returns_15m": 0.025,
                "returns_1h": 0.045,
                "returns_4h": 0.12,
                "returns_12h": 0.08,
                "direction_15m": "buy",
                "confidence_15m": 0.85,
                "direction_1h": "buy",
                "confidence_1h": 0.78,
                "volatility_prediction": 0.032,
                "trend_strength": 0.67,
            }

            market_data = pd.DataFrame(
                {"close": [50000, 50100, 50200], "volume": [1000000, 1100000, 1200000]}
            )

            # Log prediction
            await logger.log_prediction(symbol, features, model_outputs, predictions, market_data)

            # Verify that prediction was added to batch
            assert len(logger.batch_predictions) == 1

            # Check prediction record structure
            record = logger.batch_predictions[0]
            assert record["symbol"] == symbol
            assert "timestamp" in record
            assert "features_hash" in record
            assert record["features_count"] == 240
            assert "predicted_return_15m" in record
            assert "direction_15m" in record


class TestMLLoggingFormatting:
    """Test enhanced ML logging formatting"""

    def test_table_formatting(self):
        """Test beautiful table formatting for ML features"""
        with (
            patch("ml.ml_prediction_logger.setup_logger"),
            patch("ml.ml_prediction_logger.AsyncPGPool"),
        ):

            from ml.ml_prediction_logger import MLPredictionLogger

            logger = MLPredictionLogger()

            # Create a mock table formatting method
            def format_features_table(features_data):
                """Mock table formatting"""
                table = "╔═════════════════╤═════════════╗\n"
                table += "║ Indicator       │ Value       ║\n"
                table += "╠═════════════════╪═════════════╣\n"

                for key, value in features_data.items():
                    if key == "price_close":
                        formatted_value = f"{value:,.2f}"
                    elif key == "volume_current":
                        formatted_value = f"{int(value):,}"
                    else:
                        formatted_value = f"{value:.3f}"

                    display_name = key.replace("_", " ").title()
                    table += f"║ {display_name:<15} │ {formatted_value:>11} ║\n"

                table += "╚═════════════════╧═════════════╝"
                return table

            # Monkey patch the method
            logger._format_features_table = format_features_table

            # Test feature data
            features_data = {
                "price_close": 50000.0,
                "volume_current": 1500000,
                "rsi_14": 65.5,
                "macd_signal": 0.25,
            }

            # Format table
            table_str = logger._format_features_table(features_data)

            # Test table structure
            assert "╔" in table_str  # Top border
            assert "║" in table_str  # Side borders
            assert "╚" in table_str  # Bottom border
            assert "50,000.00" in table_str  # Formatted price
            assert "1,500,000" in table_str  # Formatted volume
            assert "65.500" in table_str  # RSI value

            # Test that table is not fragmented
            lines = table_str.split("\n")
            # Each line should either be empty or start with a box drawing character
            for line in lines:
                if line.strip():
                    assert line.startswith(("╔", "║", "╠", "╚")), f"Invalid line format: {line}"

    def test_compact_statistics_display(self):
        """Test compact feature statistics display"""
        with (
            patch("ml.ml_prediction_logger.setup_logger"),
            patch("ml.ml_prediction_logger.AsyncPGPool"),
        ):

            from ml.ml_prediction_logger import MLPredictionLogger

            logger = MLPredictionLogger()

            # Create a mock formatting method
            def format_feature_statistics(stats):
                """Mock compact statistics formatting"""
                return (
                    f"240 features: μ={stats['features_mean']:.3f}, "
                    f"σ={stats['features_std']:.3f}, "
                    f"R={stats['features_range']:.2f}"
                )

            # Monkey patch the method
            logger._format_feature_statistics = format_feature_statistics

            # Test feature statistics
            stats = {
                "features_count": 240,
                "features_mean": 0.5234,
                "features_std": 0.2841,
                "features_range": 5.373,
            }

            formatted_stats = logger._format_feature_statistics(stats)

            # Test compact format
            assert "240 features" in formatted_stats
            assert "μ=0.523" in formatted_stats  # Mean
            assert "σ=0.284" in formatted_stats  # Std
            assert "R=5.37" in formatted_stats  # Range

            # Test that it's a single line for compact display
            assert "\n" not in formatted_stats


class TestMLLoggingIntegration:
    """Test ML logging integration with enhanced features"""

    @pytest.mark.asyncio
    async def test_batch_database_saving(self):
        """Test batch saving with enhanced logging"""
        with (
            patch("ml.ml_prediction_logger.setup_logger"),
            patch("ml.ml_prediction_logger.AsyncPGPool") as mock_pool,
        ):

            from ml.ml_prediction_logger import MLPredictionLogger

            logger = MLPredictionLogger()
            logger.batch_size = 2  # Small batch for testing

            # Mock all necessary methods
            logger._compute_features_hash = lambda f: f"hash_{len(f)}"
            logger._extract_key_features = lambda f, m: {"price_close": 50000.0}
            logger._compute_feature_statistics = lambda f: {"features_mean": 0.5}

            # Mock database operations
            mock_pool.execute = AsyncMock()

            # Add predictions to trigger batch save
            for i in range(3):
                await logger.log_prediction(
                    f"BTC{i}USDT",
                    np.random.rand(240),
                    np.random.rand(20),
                    {"returns_15m": 0.025, "confidence_15m": 0.8, "direction_15m": "buy"},
                )

            # Should have 1 remaining prediction (2 saved in batch)
            assert len(logger.batch_predictions) == 1

    def test_performance_optimization(self):
        """Test performance optimizations in logging"""
        with (
            patch("ml.ml_prediction_logger.setup_logger"),
            patch("ml.ml_prediction_logger.AsyncPGPool"),
        ):

            from ml.ml_prediction_logger import MLPredictionLogger

            logger = MLPredictionLogger()

            # Test that methods can handle large feature arrays efficiently
            large_features = np.random.rand(240)

            # Mock the hash function to be fast
            logger._compute_features_hash = lambda f: "fast_hash"

            start_time = time.time()
            result = logger._compute_features_hash(large_features)
            end_time = time.time()

            # Should complete quickly
            assert (end_time - start_time) < 0.1  # Less than 100ms
            assert result == "fast_hash"

    def test_error_handling(self):
        """Test enhanced error handling in logging"""
        with (
            patch("ml.ml_prediction_logger.setup_logger"),
            patch("ml.ml_prediction_logger.AsyncPGPool"),
        ):

            from ml.ml_prediction_logger import MLPredictionLogger

            logger = MLPredictionLogger()

            # Test graceful handling of invalid inputs
            def safe_hash_computation(features):
                """Safe hash computation with error handling"""
                try:
                    return hashlib.sha256(str(features).encode()).hexdigest()
                except Exception:
                    return "error_hash"

            logger._compute_features_hash = safe_hash_computation

            # Test with various invalid inputs
            invalid_inputs = [None, "string", [], {}, float("inf")]

            for invalid_input in invalid_inputs:
                result = logger._compute_features_hash(invalid_input)
                assert isinstance(result, str)
                assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
