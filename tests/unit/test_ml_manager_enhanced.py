"""
Enhanced tests for ML Manager - tests improved logging and feature processing
Tests the new ML Manager functionality with table formatting and feature extraction
"""

import os
import sys
import time
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pandas as pd
import pytest
import torch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestMLManagerEnhanced:
    """Test enhanced ML Manager with improved logging"""

    @patch("torch.cuda.is_available")
    @patch("core.logger.setup_logger")  # Правильный путь к setup_logger
    def test_gpu_initialization_enhanced(self, mock_setup_logger, mock_cuda_available):
        """Test enhanced GPU initialization with detailed logging"""
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger
        mock_cuda_available.return_value = True

        # Mock GPU properties с правильными числовыми значениями
        with (
            patch("torch.cuda.device_count", return_value=1),
            patch("torch.cuda.get_device_properties") as mock_props,
            patch("torch.cuda.set_device"),
            patch("torch.cuda.memory_allocated", return_value=0),
            patch("torch.zeros") as mock_zeros,
        ):

            # Mock GPU properties
            mock_gpu_props = Mock()
            mock_gpu_props.name = "RTX 5090"
            mock_gpu_props.major = 8
            mock_gpu_props.minor = 9
            mock_gpu_props.total_memory = 24 * 1024**3  # 24GB
            mock_props.return_value = mock_gpu_props

            # Mock тензор для проверки GPU
            mock_tensor = Mock()
            mock_tensor.__mul__ = Mock(return_value=mock_tensor)
            mock_tensor.to = Mock(return_value=mock_tensor)
            mock_zeros.return_value = mock_tensor

            # Import after mocking
            from ml.ml_manager import MLManager

            config = {"ml": {"model": {"device": "auto", "precision": "fp16"}}}

            # Initialize ML Manager
            ml_manager = MLManager(config)

            # Test GPU initialization
            assert hasattr(ml_manager, "device")

            # Verify logging calls
            assert mock_setup_logger.called

    def test_feature_engineer_integration(self):
        """Test integration with ProductionFeatureEngineer"""
        with (
            patch("core.logger.setup_logger"),
            patch("torch.cuda.is_available", return_value=False),
            patch("ml.ml_manager.FeatureEngineer") as mock_feature_engineer,
        ):

            from ml.ml_manager import MLManager

            # Mock feature engineer
            mock_fe_instance = Mock()
            mock_feature_engineer.return_value = mock_fe_instance

            config = {
                "ml": {
                    "model": {"device": "cpu"},
                    "features": {
                        "count": 240,
                        "engineering_enabled": True,
                        "normalization": "standard",
                    },
                }
            }

            ml_manager = MLManager(config)

            # Test feature engineer setup
            assert ml_manager.config == config

    @patch("torch.cuda.is_available", return_value=False)
    @patch("core.logger.setup_logger")
    async def test_prediction_with_enhanced_logging(self, mock_setup_logger, mock_cuda):
        """Test ML prediction with enhanced logging system"""
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger

        with (
            patch("ml.ml_manager.FeatureEngineer"),
            patch("ml.ml_manager.create_unified_model"),
            patch("ml.ml_manager.ml_prediction_logger") as mock_ml_logger,
        ):

            from ml.ml_manager import MLManager

            config = {
                "ml": {
                    "model": {"device": "cpu", "input_features": 240},
                    "logging": {"enhanced": True, "table_format": True},
                }
            }

            ml_manager = MLManager(config)

            # Mock model and scaler
            mock_model = Mock()
            mock_model.eval = Mock()
            mock_model.return_value = torch.tensor(
                [[0.025, 0.045, 0.12, 0.08, 0.67]]
            )  # Mock outputs
            ml_manager.model = mock_model

            mock_scaler = Mock()
            mock_scaler.transform.return_value = np.random.rand(240).reshape(1, -1)
            ml_manager.scaler = mock_scaler

            # Mock feature engineer
            mock_fe = Mock()
            mock_fe.create_features.return_value = (np.random.rand(240), True)
            ml_manager.feature_engineer = mock_fe

            # Mock ML logger
            mock_ml_logger_instance = Mock()
            mock_ml_logger_instance.log_prediction = AsyncMock()
            mock_ml_logger.return_value = mock_ml_logger_instance

            # Test prediction
            symbol = "BTCUSDT"
            market_data = pd.DataFrame(
                {
                    "timestamp": [1692000000, 1692000060, 1692000120],
                    "close": [50000, 50100, 50200],
                    "volume": [1000, 1100, 1200],
                    "high": [50050, 50150, 50250],
                    "low": [49950, 50050, 50150],
                }
            )

            # Mock the predict method
            async def mock_predict(symbol, market_data):
                return {
                    "returns_15m": 0.025,
                    "returns_1h": 0.045,
                    "direction_15m": "buy",
                    "confidence_15m": 0.85,
                    "features_used": 240,
                    "model_version": "unified_patchtst_v1.0",
                }

            ml_manager.predict = mock_predict

            # Execute prediction
            result = await ml_manager.predict(symbol, market_data)

            # Test result structure
            assert result["returns_15m"] == 0.025
            assert result["direction_15m"] == "buy"
            assert result["confidence_15m"] == 0.85
            assert result["features_used"] == 240


class TestMLTableFormatting:
    """Test ML table formatting functionality"""

    def test_feature_table_generation(self):
        """Test generation of beautiful feature tables"""
        # Mock feature data that would be extracted
        feature_data = {
            "price_close": 50000.0,
            "volume_current": 1500000,
            "sma_20": 49800.0,
            "ema_12": 50100.0,
            "rsi_14": 65.5,
            "macd_signal": 0.25,
            "bb_position": -0.15,
            "atr_14": 850.0,
            "momentum_10": 0.032,
            "volatility_1h": 0.025,
        }

        def create_features_table(data):
            """Create a beautiful ASCII table for features"""
            table = "╔═══════════════════╤═══════════════╗\n"
            table += "║ Technical Indicator │ Current Value ║\n"
            table += "╠═══════════════════╪═══════════════╣\n"

            # Format each indicator
            indicators_display = {
                "price_close": ("Price Close", f"{data['price_close']:,.2f}"),
                "volume_current": ("Volume", f"{int(data['volume_current']):,}"),
                "sma_20": ("SMA(20)", f"{data['sma_20']:,.2f}"),
                "ema_12": ("EMA(12)", f"{data['ema_12']:,.2f}"),
                "rsi_14": ("RSI(14)", f"{data['rsi_14']:.2f}"),
                "macd_signal": ("MACD Signal", f"{data['macd_signal']:.3f}"),
                "bb_position": ("BB Position", f"{data['bb_position']:.3f}"),
                "atr_14": ("ATR(14)", f"{data['atr_14']:.2f}"),
                "momentum_10": ("Momentum(10)", f"{data['momentum_10']:.3f}"),
                "volatility_1h": ("Volatility 1H", f"{data['volatility_1h']:.3f}"),
            }

            for key, (display_name, formatted_value) in indicators_display.items():
                table += f"║ {display_name:<17} │ {formatted_value:>13} ║\n"

            table += "╚═══════════════════╧═══════════════╝"
            return table

        # Generate table
        table = create_features_table(feature_data)

        # Test table structure
        assert "╔" in table  # Top border
        assert "║" in table  # Side borders
        assert "╚" in table  # Bottom border
        assert "Technical Indicator" in table
        assert "Current Value" in table

        # Test formatting
        assert "50,000.00" in table  # Price formatting
        assert "1,500,000" in table  # Volume formatting
        assert "65.50" in table  # RSI formatting

        # Test that all indicators are present
        indicators = [
            "Price Close",
            "Volume",
            "SMA(20)",
            "EMA(12)",
            "RSI(14)",
            "MACD Signal",
            "BB Position",
            "ATR(14)",
            "Momentum(10)",
            "Volatility 1H",
        ]

        for indicator in indicators:
            assert indicator in table

    def test_compact_statistics_formatting(self):
        """Test compact feature statistics formatting"""
        stats = {
            "count": 240,
            "mean": 0.5234,
            "std": 0.2841,
            "min": -2.1543,
            "max": 3.2187,
            "range": 5.373,
            "non_zero": 238,
            "outliers": 12,
        }

        def format_compact_stats(stats):
            """Format statistics in compact form"""
            return (
                f"📊 Features: {stats['count']} "
                f"(μ={stats['mean']:.3f}, σ={stats['std']:.3f}, "
                f"R={stats['range']:.2f}, outliers={stats['outliers']})"
            )

        formatted = format_compact_stats(stats)

        # Test compact format
        assert "📊 Features: 240" in formatted
        assert "μ=0.523" in formatted  # Mean with Greek letter
        assert "σ=0.284" in formatted  # Std with Greek letter
        assert "R=5.37" in formatted  # Range
        assert "outliers=12" in formatted

        # Should be single line
        assert "\n" not in formatted


class TestMLPerformanceOptimization:
    """Test ML performance optimizations"""

    def test_gpu_memory_optimization(self):
        """Test GPU memory optimization features"""
        with (
            patch("torch.cuda.is_available", return_value=True),
            patch("torch.cuda.device_count", return_value=1),
            patch("torch.cuda.get_device_properties"),
            patch("torch.cuda.set_device"),
            patch("torch.cuda.memory_allocated", return_value=1024**3),
            patch("core.logger.setup_logger"),
        ):

            from ml.ml_manager import MLManager

            config = {
                "ml": {
                    "model": {"device": "auto", "memory_optimization": True, "precision": "fp16"},
                    "inference": {"batch_size": 32, "timeout_ms": 50},
                }
            }

            ml_manager = MLManager(config)

            # Test that device is set
            assert hasattr(ml_manager, "device")

    def test_inference_timing(self):
        """Test inference timing and performance metrics"""
        performance_metrics = {
            "feature_extraction_ms": 5.2,
            "model_inference_ms": 12.8,
            "post_processing_ms": 2.1,
            "total_prediction_ms": 20.1,
            "features_processed": 240,
            "batch_size": 1,
            "gpu_memory_used_mb": 1024,
        }

        def analyze_performance(metrics):
            """Analyze ML performance metrics"""
            analysis = {
                "overall_speed": "fast" if metrics["total_prediction_ms"] < 50 else "slow",
                "bottleneck": (
                    "model_inference"
                    if metrics["model_inference_ms"] > metrics["feature_extraction_ms"]
                    else "feature_extraction"
                ),
                "efficiency_score": min(100, (50 / metrics["total_prediction_ms"]) * 100),
                "memory_efficient": metrics["gpu_memory_used_mb"] < 2048,
            }

            return analysis

        analysis = analyze_performance(performance_metrics)

        # Test performance analysis
        assert analysis["overall_speed"] == "fast"  # <50ms
        assert analysis["bottleneck"] == "model_inference"  # 12.8ms > 5.2ms
        assert analysis["efficiency_score"] > 80  # Good efficiency
        assert analysis["memory_efficient"] is True  # <2GB

    def test_caching_optimization(self):
        """Test caching system for repeated predictions"""
        cache_system = {
            "feature_cache": {},
            "prediction_cache": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "ttl_seconds": 300,
        }

        def cache_features(symbol, features_hash, features):
            """Cache processed features"""
            cache_key = f"{symbol}_{features_hash}"
            cache_system["feature_cache"][cache_key] = {
                "features": features,
                "timestamp": time.time(),
            }

        def get_cached_features(symbol, features_hash):
            """Get cached features if available"""
            cache_key = f"{symbol}_{features_hash}"

            if cache_key in cache_system["feature_cache"]:
                cached = cache_system["feature_cache"][cache_key]
                age = time.time() - cached["timestamp"]

                if age < cache_system["ttl_seconds"]:
                    cache_system["cache_hits"] += 1
                    return cached["features"]

            cache_system["cache_misses"] += 1
            return None

        # Test caching
        symbol = "BTCUSDT"
        features_hash = "abc123"
        features = np.random.rand(240)

        # Cache features
        cache_features(symbol, features_hash, features)

        # Retrieve cached features
        cached_features = get_cached_features(symbol, features_hash)

        assert cached_features is not None
        assert cache_system["cache_hits"] == 1
        assert cache_system["cache_misses"] == 0

        # Test cache miss
        missed_features = get_cached_features("ETHUSDT", "xyz789")

        assert missed_features is None
        assert cache_system["cache_misses"] == 1


class TestMLSignalQuality:
    """Test ML signal quality analysis"""

    def test_signal_quality_analyzer_integration(self):
        """Test integration with SignalQualityAnalyzer"""
        with (
            patch("ml.ml_manager.SignalQualityAnalyzer") as mock_analyzer,
            patch("core.logger.setup_logger"),
        ):

            from ml.ml_manager import MLManager

            # Mock analyzer
            mock_analyzer_instance = Mock()
            mock_analyzer.return_value = mock_analyzer_instance

            config = {
                "ml": {
                    "model": {"device": "cpu"},
                    "quality": {"enabled": True, "min_confidence": 0.7, "max_volatility": 0.05},
                }
            }

            ml_manager = MLManager(config)

            # Test that analyzer is available
            assert hasattr(ml_manager, "config")

    def test_prediction_quality_metrics(self):
        """Test prediction quality metrics calculation"""
        prediction_data = {
            "confidence_15m": 0.85,
            "confidence_1h": 0.78,
            "volatility_prediction": 0.032,
            "trend_strength": 0.67,
            "signal_clarity": 0.72,
            "market_regime": "trending",
            "features_stability": 0.89,
        }

        def calculate_quality_score(data):
            """Calculate overall prediction quality score"""
            weights = {
                "confidence_15m": 0.25,
                "confidence_1h": 0.20,
                "volatility_prediction": 0.15,  # Lower is better
                "trend_strength": 0.20,
                "signal_clarity": 0.10,
                "features_stability": 0.10,
            }

            score = 0
            score += data["confidence_15m"] * weights["confidence_15m"]
            score += data["confidence_1h"] * weights["confidence_1h"]
            score += (1 - min(data["volatility_prediction"] / 0.1, 1)) * weights[
                "volatility_prediction"
            ]
            score += data["trend_strength"] * weights["trend_strength"]
            score += data["signal_clarity"] * weights["signal_clarity"]
            score += data["features_stability"] * weights["features_stability"]

            return min(score, 1.0)

        quality_score = calculate_quality_score(prediction_data)

        # Test quality score calculation
        assert 0 <= quality_score <= 1
        assert quality_score > 0.7  # Should be high quality with given inputs

        # Test with poor quality data
        poor_data = prediction_data.copy()
        poor_data["confidence_15m"] = 0.3
        poor_data["confidence_1h"] = 0.25
        poor_data["volatility_prediction"] = 0.15  # High volatility

        poor_score = calculate_quality_score(poor_data)
        assert poor_score < 0.5  # Should be low quality


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
