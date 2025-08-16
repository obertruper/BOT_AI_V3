"""
Глобальные pytest fixtures для всех тестов
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
import torch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connections import Base


# Настройка event loop для async тестов
@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для всей сессии тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Database fixtures
@pytest.fixture(scope="session")
def test_database_engine():
    """Создание тестовой базы данных SQLite в памяти"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(test_database_engine):
    """Создание сессии базы данных для каждого теста"""
    SessionLocal = sessionmaker(bind=test_database_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


# ML fixtures
@pytest.fixture
def mock_ml_model():
    """Mock ML модель для тестирования"""
    model = MagicMock()
    model.eval = MagicMock()
    model.train = MagicMock()

    # Mock forward pass
    def mock_forward(x):
        batch_size = x.shape[0] if hasattr(x, "shape") else 1
        return torch.randn(batch_size, 20)  # 20 outputs

    model.forward = mock_forward
    model.__call__ = mock_forward

    return model


@pytest.fixture
def sample_ohlcv_data():
    """Тестовые OHLCV данные"""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="15min")

    data = {
        "datetime": dates,
        "timestamp": [int(d.timestamp() * 1000) for d in dates],
        "open": np.random.uniform(49000, 51000, 100),
        "high": np.random.uniform(50000, 52000, 100),
        "low": np.random.uniform(48000, 50000, 100),
        "close": np.random.uniform(49000, 51000, 100),
        "volume": np.random.uniform(100, 1000, 100),
        "symbol": "BTCUSDT",
    }

    df = pd.DataFrame(data)

    # Корректируем OHLC
    df["high"] = df[["open", "close", "high"]].max(axis=1)
    df["low"] = df[["open", "close", "low"]].min(axis=1)
    df["turnover"] = df["close"] * df["volume"]

    return df


@pytest.fixture
def sample_ml_features():
    """Тестовые ML признаки (240 features)"""
    return np.random.randn(96, 240)


@pytest.fixture
def sample_ml_predictions():
    """Тестовые предсказания модели (20 outputs)"""
    predictions = np.zeros(20)

    # Future returns (индексы 0-3)
    predictions[0:4] = np.random.uniform(-0.02, 0.02, 4)

    # Directions (индексы 4-7) - 0=LONG, 1=SHORT, 2=FLAT
    predictions[4:8] = np.random.randint(0, 3, 4)

    # Long probabilities (индексы 8-11)
    predictions[8:12] = np.random.uniform(0.3, 0.9, 4)

    # Short probabilities (индексы 12-15)
    predictions[12:16] = np.random.uniform(0.3, 0.9, 4)

    # Risk metrics (индексы 16-19)
    predictions[16:20] = np.random.uniform(0.005, 0.03, 4)

    return predictions


# Exchange fixtures
@pytest.fixture
def mock_exchange():
    """Mock биржа для тестирования"""
    exchange = MagicMock()
    exchange.name = "test_exchange"
    exchange.get_balance = MagicMock(return_value={"USDT": 10000.0})
    exchange.get_ticker = MagicMock(return_value={"last": 50000.0})
    exchange.place_order = MagicMock(return_value={"id": "test_order_123"})
    exchange.cancel_order = MagicMock(return_value=True)
    exchange.get_order_status = MagicMock(return_value={"status": "filled"})

    return exchange


# Configuration fixtures
@pytest.fixture
def test_config():
    """Тестовая конфигурация"""
    return {
        "system": {"environment": "test", "debug": True, "log_level": "DEBUG"},
        "trading": {
            "default_leverage": 1,
            "max_position_size": 1000,
            "risk_limit_percentage": 2,
            "default_stop_loss_pct": 0.02,
            "default_take_profit_pct": 0.04,
        },
        "ml": {
            "enabled": True,
            "model_directory": "tests/fixtures/models",
            "data_directory": "tests/fixtures/data",
            "device": "cpu",
            "signal_weight": 0.7,
            "min_confidence": 0.6,
        },
        "database": {
            "host": "localhost",
            "port": 5555,
            "name": "test_bot_trading",
            "user": "test_user",
        },
        "exchanges": {
            "bybit": {
                "api_key": "test_key",
                "api_secret": "test_secret",
                "testnet": True,
            }
        },
    }


# Async fixtures
@pytest.fixture
async def async_mock_db_session():
    """Async mock сессия БД"""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.execute = MagicMock()
    session.query = MagicMock()

    # Async context manager
    async def async_enter():
        return session

    async def async_exit(*args):
        pass

    session.__aenter__ = async_enter
    session.__aexit__ = async_exit

    return session


# Market data fixtures
@pytest.fixture
def market_snapshot():
    """Снимок рыночных данных"""
    return {
        "symbol": "BTCUSDT",
        "last_price": 50000.0,
        "bid": 49999.0,
        "ask": 50001.0,
        "volume_24h": 1000000.0,
        "high_24h": 51000.0,
        "low_24h": 49000.0,
        "timestamp": datetime.utcnow(),
    }


# Signal fixtures
@pytest.fixture
def sample_signal():
    """Пример торгового сигнала"""
    from database.models import Signal, SignalType

    return Signal(
        symbol="BTCUSDT",
        exchange="binance",
        signal_type=SignalType.LONG,
        strength=0.8,
        confidence=0.75,
        stop_loss=49000.0,
        take_profit=51000.0,
        entry_price=50000.0,
        metadata={
            "source": "ml_model",
            "model_version": "1.0.0",
            "features_count": 240,
        },
    )


# Performance fixtures
@pytest.fixture
def performance_timer():
    """Таймер для измерения производительности"""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, *args):
            self.elapsed = time.time() - self.start_time

    return Timer


# Test data generators
@pytest.fixture
def generate_random_candles():
    """Генератор случайных свечей"""

    def _generate(count=100, symbol="BTCUSDT"):
        candles = []
        base_price = 50000.0

        for i in range(count):
            open_price = base_price + np.random.randn() * 100
            close_price = open_price + np.random.randn() * 50
            high_price = max(open_price, close_price) + abs(np.random.randn() * 20)
            low_price = min(open_price, close_price) - abs(np.random.randn() * 20)

            candles.append(
                {
                    "timestamp": datetime.utcnow().timestamp() + i * 900,  # 15 min intervals
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": abs(np.random.randn() * 1000) + 100,
                    "symbol": symbol,
                }
            )

            base_price = close_price

        return candles

    return _generate


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_test_files(request):
    """Автоматическая очистка временных файлов после тестов"""
    test_files = []

    def add_test_file(filepath):
        test_files.append(filepath)

    request.addfinalizer(lambda: [Path(f).unlink(missing_ok=True) for f in test_files])

    return add_test_file


# Mock fixtures for external services
@pytest.fixture
def mock_redis():
    """Mock Redis клиент"""
    redis = MagicMock()
    redis.get = MagicMock(return_value=None)
    redis.set = MagicMock(return_value=True)
    redis.delete = MagicMock(return_value=1)
    redis.exists = MagicMock(return_value=False)
    redis.expire = MagicMock(return_value=True)

    return redis


@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram бот"""
    bot = MagicMock()
    bot.send_message = MagicMock()
    bot.send_photo = MagicMock()
    bot.answer_callback_query = MagicMock()

    return bot


# Environment setup
@pytest.fixture(autouse=True)
def setup_test_env():
    """Настройка тестового окружения"""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["PYTHONPATH"] = str(Path(__file__).parent.parent)

    yield

    # Cleanup
    if "ENVIRONMENT" in os.environ:
        del os.environ["ENVIRONMENT"]
