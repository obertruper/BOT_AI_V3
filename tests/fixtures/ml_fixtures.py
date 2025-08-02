"""
ML-специфичные fixtures и mock данные для тестирования
"""

import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler


class MLFixtures:
    """Класс с ML fixtures для тестирования"""

    @staticmethod
    def create_mock_model_files(directory: Path, symbols: List[str] = None):
        """Создание mock файлов моделей"""
        if symbols is None:
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

        directory.mkdir(parents=True, exist_ok=True)

        for symbol in symbols:
            # Создаем mock модель
            model_data = {
                "state_dict": {
                    "encoder.weight": torch.randn(256, 240),
                    "encoder.bias": torch.randn(256),
                    "decoder.weight": torch.randn(20, 256),
                    "decoder.bias": torch.randn(20),
                },
                "config": {
                    "input_size": 240,
                    "output_size": 20,
                    "context_window": 96,
                    "d_model": 256,
                    "n_heads": 4,
                    "e_layers": 3,
                },
                "metadata": {
                    "symbol": symbol,
                    "version": "1.0.0",
                    "training_date": datetime.now().isoformat(),
                    "training_metrics": {
                        "accuracy": 0.75,
                        "f1_score": 0.72,
                        "precision": 0.78,
                        "recall": 0.70,
                    },
                },
            }

            torch.save(model_data, directory / f"model_{symbol}.pth")

            # Создаем mock scaler
            scaler = StandardScaler()
            fake_data = np.random.randn(1000, 240)
            scaler.fit(fake_data)

            with open(directory / f"scaler_{symbol}.pkl", "wb") as f:
                pickle.dump(scaler, f)

    @staticmethod
    def generate_feature_data(
        n_samples: int = 96, n_features: int = 240
    ) -> pd.DataFrame:
        """Генерация данных с признаками для ML"""
        # Базовые временные метки
        timestamps = pd.date_range(end=datetime.now(), periods=n_samples, freq="15min")

        # Генерируем признаки с разными характеристиками
        features = {}

        # Технические индикаторы (нормализованные)
        for i in range(50):
            features[f"tech_indicator_{i}"] = np.random.randn(n_samples)

        # Статистические признаки
        for i in range(30):
            features[f"stat_feature_{i}"] = np.random.randn(n_samples) * 0.5

        # Микроструктурные признаки
        for i in range(40):
            features[f"microstructure_{i}"] = np.random.exponential(1.0, n_samples)

        # Паттерны (бинарные)
        for i in range(20):
            features[f"pattern_{i}"] = np.random.choice([0, 1], n_samples)

        # Временные признаки
        features["hour_sin"] = np.sin(2 * np.pi * timestamps.hour / 24)
        features["hour_cos"] = np.cos(2 * np.pi * timestamps.hour / 24)
        features["day_sin"] = np.sin(2 * np.pi * timestamps.dayofweek / 7)
        features["day_cos"] = np.cos(2 * np.pi * timestamps.dayofweek / 7)

        # Объемные признаки
        for i in range(30):
            features[f"volume_feature_{i}"] = np.random.lognormal(0, 1, n_samples)

        # ML meta-features
        for i in range(20):
            features[f"ml_meta_{i}"] = np.random.uniform(-1, 1, n_samples)

        # Оставшиеся признаки до 240
        remaining = 240 - len(features)
        for i in range(remaining):
            features[f"feature_{i}"] = np.random.randn(n_samples)

        df = pd.DataFrame(features, index=timestamps)
        return df

    @staticmethod
    def generate_model_outputs(batch_size: int = 1) -> torch.Tensor:
        """Генерация выходов модели"""
        outputs = torch.zeros(batch_size, 20)

        for i in range(batch_size):
            # Future returns (0-3)
            outputs[i, 0:4] = torch.randn(4) * 0.02

            # Directions (4-7) - дискретные значения 0, 1, 2
            outputs[i, 4:8] = torch.randint(0, 3, (4,)).float()

            # Long probabilities (8-11) - логиты
            outputs[i, 8:12] = torch.randn(4) * 2

            # Short probabilities (12-15) - логиты
            outputs[i, 12:16] = torch.randn(4) * 2

            # Risk metrics (16-19) - положительные значения
            outputs[i, 16:20] = torch.abs(torch.randn(4)) * 0.02

        return outputs

    @staticmethod
    def create_training_dataset(n_samples: int = 1000) -> Dict[str, Any]:
        """Создание тренировочного датасета"""
        # Генерируем OHLCV данные
        dates = pd.date_range(end=datetime.now(), periods=n_samples, freq="15min")

        ohlcv_data = pd.DataFrame(
            {
                "datetime": dates,
                "open": np.random.uniform(49000, 51000, n_samples),
                "high": np.random.uniform(50000, 52000, n_samples),
                "low": np.random.uniform(48000, 50000, n_samples),
                "close": np.random.uniform(49000, 51000, n_samples),
                "volume": np.random.uniform(100, 1000, n_samples),
            }
        )

        # Корректируем OHLC
        ohlcv_data["high"] = ohlcv_data[["open", "close", "high"]].max(axis=1)
        ohlcv_data["low"] = ohlcv_data[["open", "close", "low"]].min(axis=1)

        # Генерируем признаки
        features = MLFixtures.generate_feature_data(n_samples, 240)

        # Генерируем таргеты
        targets = pd.DataFrame(index=dates)

        # Future returns
        for horizon in ["15m", "1h", "4h", "12h"]:
            targets[f"future_return_{horizon}"] = np.random.randn(n_samples) * 0.02

        # Directions
        for horizon in ["15m", "1h", "4h", "12h"]:
            targets[f"direction_{horizon}"] = np.random.randint(0, 3, n_samples)

        # Long/Short levels
        for level in ["1pct_4h", "2pct_4h", "3pct_12h", "5pct_12h"]:
            targets[f"long_will_reach_{level}"] = np.random.randint(0, 2, n_samples)
            targets[f"short_will_reach_{level}"] = np.random.randint(0, 2, n_samples)

        # Risk metrics
        for horizon in ["1h", "4h"]:
            targets[f"max_drawdown_{horizon}"] = (
                np.abs(np.random.randn(n_samples)) * 0.03
            )
            targets[f"max_rally_{horizon}"] = np.abs(np.random.randn(n_samples)) * 0.03

        return {"ohlcv": ohlcv_data, "features": features, "targets": targets}

    @staticmethod
    def create_mock_ml_pipeline_data() -> Dict[str, Any]:
        """Создание данных для тестирования ML pipeline"""
        return {
            "raw_market_data": {
                "symbol": "BTCUSDT",
                "timestamp": int(datetime.now().timestamp() * 1000),
                "datetime": datetime.now(),
                "open": 50000.0,
                "high": 51000.0,
                "low": 49000.0,
                "close": 50500.0,
                "volume": 1000.0,
                "interval_minutes": 15,
            },
            "processed_features": MLFixtures.generate_feature_data(96, 240).values,
            "model_predictions": MLFixtures.generate_model_outputs(1).numpy()[0],
            "signal": {
                "symbol": "BTCUSDT",
                "signal_type": "LONG",
                "confidence": 0.75,
                "strength": 0.8,
                "stop_loss": 49500.0,
                "take_profit": 51500.0,
                "metadata": {
                    "model_version": "1.0.0",
                    "processing_time": 0.125,
                    "features_used": 240,
                },
            },
        }

    @staticmethod
    def create_backtesting_data(
        symbol: str = "BTCUSDT", days: int = 30
    ) -> pd.DataFrame:
        """Создание данных для бэктестинга"""
        # Генерируем реалистичные OHLCV данные
        n_candles = days * 24 * 4  # 15-минутные свечи
        dates = pd.date_range(end=datetime.now(), periods=n_candles, freq="15min")

        # Создаем тренд с шумом
        trend = np.linspace(50000, 52000, n_candles)
        noise = np.random.randn(n_candles) * 200
        seasonal = np.sin(np.linspace(0, 4 * np.pi, n_candles)) * 500

        base_price = trend + noise + seasonal

        data = pd.DataFrame(
            {
                "datetime": dates,
                "symbol": symbol,
                "open": base_price + np.random.randn(n_candles) * 50,
                "close": base_price + np.random.randn(n_candles) * 50,
            }
        )

        # Генерируем high/low на основе open/close
        data["high"] = data[["open", "close"]].max(axis=1) + np.abs(
            np.random.randn(n_candles) * 100
        )
        data["low"] = data[["open", "close"]].min(axis=1) - np.abs(
            np.random.randn(n_candles) * 100
        )

        # Объем с дневной сезонностью
        hour_of_day = dates.hour
        volume_profile = 1000 + 500 * np.sin(2 * np.pi * hour_of_day / 24)
        data["volume"] = volume_profile + np.random.exponential(200, n_candles)

        return data

    @staticmethod
    def create_mock_exchange_data() -> Dict[str, Any]:
        """Создание mock данных биржи"""
        return {
            "orderbook": {
                "bids": [[49999.0, 10.5], [49998.0, 15.2], [49997.0, 20.1]],
                "asks": [[50001.0, 10.3], [50002.0, 14.8], [50003.0, 19.5]],
                "timestamp": datetime.now(),
            },
            "ticker": {
                "symbol": "BTCUSDT",
                "last": 50000.0,
                "bid": 49999.0,
                "ask": 50001.0,
                "high": 51000.0,
                "low": 49000.0,
                "volume": 1500000.0,
                "timestamp": datetime.now(),
            },
            "trades": [
                {
                    "price": 50000.0,
                    "amount": 0.5,
                    "side": "buy",
                    "timestamp": datetime.now(),
                },
                {
                    "price": 49999.0,
                    "amount": 0.3,
                    "side": "sell",
                    "timestamp": datetime.now(),
                },
                {
                    "price": 50001.0,
                    "amount": 0.7,
                    "side": "buy",
                    "timestamp": datetime.now(),
                },
            ],
        }


# Функции-генераторы для быстрого создания данных
def generate_ml_batch(batch_size: int = 32, seq_len: int = 96, n_features: int = 240):
    """Быстрая генерация батча для ML модели"""
    return torch.randn(batch_size, seq_len, n_features)


def generate_signal_batch(n_signals: int = 10):
    """Генерация батча торговых сигналов"""
    from database.models import Signal, SignalType

    signals = []
    for i in range(n_signals):
        signal = Signal(
            symbol=f"SYMBOL{i}",
            signal_type=np.random.choice([SignalType.LONG, SignalType.SHORT]),
            confidence=np.random.uniform(0.6, 0.95),
            strength=np.random.uniform(0.5, 1.0),
            stop_loss=49000.0 + i * 100,
            take_profit=51000.0 + i * 100,
            metadata={"model_version": "1.0.0", "batch_index": i},
        )
        signals.append(signal)

    return signals


def create_mock_model_checkpoint(path: Path):
    """Создание mock checkpoint модели"""
    checkpoint = {
        "epoch": 100,
        "model_state_dict": {
            "layer1.weight": torch.randn(256, 240),
            "layer1.bias": torch.randn(256),
            "layer2.weight": torch.randn(128, 256),
            "layer2.bias": torch.randn(128),
            "output.weight": torch.randn(20, 128),
            "output.bias": torch.randn(20),
        },
        "optimizer_state_dict": {},
        "loss": 0.0234,
        "metrics": {
            "train_loss": 0.0234,
            "val_loss": 0.0267,
            "train_accuracy": 0.78,
            "val_accuracy": 0.75,
        },
        "config": {"input_size": 240, "output_size": 20, "context_window": 96},
    }

    torch.save(checkpoint, path)
