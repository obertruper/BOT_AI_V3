"""
Unit тесты для MLSignalProcessor - процессора ML сигналов
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from database.models.base_models import SignalType
from database.models.signal import Signal
from ml.ml_signal_processor import MLSignalProcessor


@pytest.mark.unit
@pytest.mark.ml
class TestMLSignalProcessor:
    """Тесты для класса MLSignalProcessor"""

    @pytest.fixture
    def mock_config(self):
        """Mock конфигурация для тестов"""
        return {
            "ml": {
                "signal_weight": 0.7,
                "min_confidence": 0.6,
                "signal_expiry_minutes": 15,
                "batch_processing": True,
                "max_batch_size": 10,
            },
            "trading": {
                "default_stop_loss_pct": 0.02,
                "default_take_profit_pct": 0.04,
                "risk_reward_ratio": 2.0,
            },
        }

    @pytest.fixture
    def signal_processor(self, mock_config, mock_ml_manager):
        """Создание экземпляра MLSignalProcessor"""
        # MLSignalProcessor принимает ml_manager и config
        processor = MLSignalProcessor(mock_ml_manager, mock_config)
        return processor

    @pytest.fixture
    def mock_ml_manager(self):
        """Mock MLManager"""
        manager = MagicMock()
        manager.get_model = AsyncMock()
        manager.predict = AsyncMock()
        return manager

    @pytest.fixture
    def sample_features(self):
        """Тестовые признаки для модели"""
        return np.random.randn(96, 240)

    @pytest.fixture
    def sample_predictions(self):
        """Тестовые предсказания модели"""
        predictions = np.zeros(20)
        # Future returns
        predictions[0:4] = [0.002, 0.005, 0.01, 0.015]
        # Directions (0=LONG, 1=SHORT, 2=FLAT)
        predictions[4:8] = [0, 0, 0, 2]
        # Long probabilities
        predictions[8:12] = [0.7, 0.8, 0.75, 0.65]
        # Short probabilities
        predictions[12:16] = [0.2, 0.15, 0.2, 0.3]
        # Risk metrics
        predictions[16:20] = [0.01, 0.015, 0.012, 0.008]
        return predictions

    @pytest.mark.asyncio
    async def test_initialization(self, signal_processor):
        """Тест инициализации процессора"""
        # Проверяем, что процессор правильно инициализирован
        assert signal_processor.ml_manager is not None
        assert signal_processor.config is not None
        assert signal_processor.min_confidence == 0.6  # из mock_config
        assert signal_processor.min_signal_strength == 0.3
        assert signal_processor.risk_tolerance == "MEDIUM"
        assert signal_processor.cache_ttl == 60

    @pytest.mark.asyncio
    async def test_process_single_signal(
        self, signal_processor, mock_ml_manager, sample_features, sample_predictions
    ):
        """Тест обработки одиночного сигнала"""
        await signal_processor.initialize()
        signal_processor._ml_manager = mock_ml_manager

        # Mock предсказание модели
        mock_ml_manager.predict.return_value = sample_predictions

        # Обрабатываем сигнал
        signal = await signal_processor.process_signal(
            symbol="BTCUSDT", features=sample_features, current_price=50000.0
        )

        assert signal is not None
        assert isinstance(signal, Signal)
        assert signal.symbol == "BTCUSDT"
        assert signal.signal_type == SignalType.LONG
        assert signal.confidence >= 0.6
        assert signal.stop_loss < 50000.0
        assert signal.take_profit > 50000.0

    @pytest.mark.asyncio
    async def test_process_batch_signals(self, signal_processor, mock_ml_manager):
        """Тест пакетной обработки сигналов"""
        await signal_processor.initialize()
        signal_processor._ml_manager = mock_ml_manager

        # Подготовка данных для нескольких символов
        batch_data = []
        for i, symbol in enumerate(["BTCUSDT", "ETHUSDT", "BNBUSDT"]):
            batch_data.append(
                {
                    "symbol": symbol,
                    "features": np.random.randn(96, 240),
                    "current_price": 50000.0 - i * 1000,
                }
            )

        # Mock предсказания для каждого символа
        predictions = []
        for i in range(3):
            pred = np.zeros(20)
            pred[4:8] = [0, 0, 1, 2]  # Разные направления
            pred[8:12] = [0.7 - i * 0.1] * 4  # Разная уверенность
            predictions.append(pred)

        mock_ml_manager.predict.side_effect = predictions

        # Обрабатываем пакет
        signals = await signal_processor.process_batch(batch_data)

        assert len(signals) <= 3  # Некоторые могут быть отфильтрованы
        for signal in signals:
            assert isinstance(signal, Signal)
            assert signal.confidence >= 0.6

    @pytest.mark.asyncio
    async def test_signal_validation(self, signal_processor):
        """Тест валидации сигналов"""
        await signal_processor.initialize()

        # Валидный сигнал
        valid_signal = Signal(
            symbol="BTCUSDT",
            signal_type=SignalType.LONG,
            confidence=0.8,
            strength=0.7,
            stop_loss=49000.0,
            take_profit=51000.0,
            entry_price=50000.0,
        )

        assert await signal_processor.validate_signal(valid_signal) is True

        # Невалидный сигнал - низкая уверенность
        invalid_signal = Signal(
            symbol="BTCUSDT",
            signal_type=SignalType.LONG,
            confidence=0.4,
            strength=0.7,
            stop_loss=49000.0,
            take_profit=51000.0,
        )

        assert await signal_processor.validate_signal(invalid_signal) is False

    @pytest.mark.asyncio
    async def test_convert_predictions_to_signal(self, signal_processor, sample_predictions):
        """Тест конвертации предсказаний модели в сигнал"""
        await signal_processor.initialize()

        signal = await signal_processor._convert_predictions_to_signal(
            symbol="BTCUSDT", predictions=sample_predictions, current_price=50000.0
        )

        assert signal is not None
        assert signal.metadata is not None
        assert "ml_predictions" in signal.metadata
        assert "future_returns" in signal.metadata["ml_predictions"]
        assert "directions" in signal.metadata["ml_predictions"]
        assert "profit_probabilities" in signal.metadata["ml_predictions"]
        assert "risk_metrics" in signal.metadata["ml_predictions"]

    @pytest.mark.asyncio
    async def test_calculate_signal_strength(self, signal_processor):
        """Тест расчета силы сигнала"""
        await signal_processor.initialize()

        # Высокая сила сигнала
        strength = await signal_processor._calculate_signal_strength(
            confidence=0.9,
            direction_agreement=0.8,
            profit_probability=0.85,
            risk_level=0.01,
        )

        assert 0.7 <= strength <= 1.0

        # Низкая сила сигнала
        strength = await signal_processor._calculate_signal_strength(
            confidence=0.5,
            direction_agreement=0.5,
            profit_probability=0.4,
            risk_level=0.05,
        )

        assert 0.0 <= strength <= 0.5

    @pytest.mark.asyncio
    async def test_determine_signal_type(self, signal_processor):
        """Тест определения типа сигнала"""
        await signal_processor.initialize()

        # LONG сигнал
        directions = np.array([0, 0, 0, 2])  # 3 LONG, 1 FLAT
        signal_type = await signal_processor._determine_signal_type(directions)
        assert signal_type == SignalType.LONG

        # SHORT сигнал
        directions = np.array([1, 1, 1, 0])  # 3 SHORT, 1 LONG
        signal_type = await signal_processor._determine_signal_type(directions)
        assert signal_type == SignalType.SHORT

        # Нет сигнала (FLAT)
        directions = np.array([2, 2, 2, 2])  # Все FLAT
        signal_type = await signal_processor._determine_signal_type(directions)
        assert signal_type is None

    @pytest.mark.asyncio
    async def test_calculate_risk_levels(self, signal_processor):
        """Тест расчета уровней риска"""
        await signal_processor.initialize()

        # LONG позиция
        stop_loss, take_profit = await signal_processor._calculate_risk_levels(
            signal_type=SignalType.LONG,
            current_price=50000.0,
            risk_metrics=np.array([0.01, 0.015, 0.012, 0.008]),
            profit_probabilities=np.array([0.7, 0.8, 0.6, 0.5]),
        )

        assert stop_loss < 50000.0
        assert take_profit > 50000.0
        assert (take_profit - 50000.0) >= 2 * (50000.0 - stop_loss)  # RR >= 2

        # SHORT позиция
        stop_loss, take_profit = await signal_processor._calculate_risk_levels(
            signal_type=SignalType.SHORT,
            current_price=50000.0,
            risk_metrics=np.array([0.01, 0.015, 0.012, 0.008]),
            profit_probabilities=np.array([0.7, 0.8, 0.6, 0.5]),
        )

        assert stop_loss > 50000.0
        assert take_profit < 50000.0
        assert (50000.0 - take_profit) >= 2 * (stop_loss - 50000.0)  # RR >= 2

    @pytest.mark.asyncio
    async def test_signal_expiry(self, signal_processor):
        """Тест истечения срока действия сигнала"""
        await signal_processor.initialize()

        # Создаем сигнал
        signal = Signal(
            symbol="BTCUSDT",
            signal_type=SignalType.LONG,
            confidence=0.8,
            created_at=datetime.utcnow(),
        )

        # Проверяем срок действия
        expires_at = await signal_processor._calculate_expiry(signal)

        assert expires_at > signal.created_at
        assert (expires_at - signal.created_at).total_seconds() == 15 * 60  # 15 минут

    @pytest.mark.asyncio
    async def test_save_signal_to_database(self, signal_processor):
        """Тест сохранения сигнала в базу данных"""
        await signal_processor.initialize()

        with patch("ml.ml_signal_processor.get_async_db") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            signal = Signal(
                symbol="BTCUSDT",
                signal_type=SignalType.LONG,
                confidence=0.8,
                strength=0.7,
            )

            saved = await signal_processor.save_signal(signal)

            assert saved is True
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_filter_weak_signals(self, signal_processor):
        """Тест фильтрации слабых сигналов"""
        await signal_processor.initialize()

        signals = [
            Signal(symbol="BTC", confidence=0.8, strength=0.7),
            Signal(symbol="ETH", confidence=0.5, strength=0.6),  # Будет отфильтрован
            Signal(symbol="BNB", confidence=0.7, strength=0.8),
            Signal(symbol="ADA", confidence=0.4, strength=0.9),  # Будет отфильтрован
        ]

        filtered = await signal_processor.filter_signals(signals)

        assert len(filtered) == 2
        assert all(s.confidence >= 0.6 for s in filtered)

    @pytest.mark.asyncio
    async def test_signal_aggregation(self, signal_processor):
        """Тест агрегации множественных сигналов"""
        await signal_processor.initialize()

        # Несколько сигналов для одного символа
        signals = []
        for i in range(3):
            signals.append(
                {
                    "symbol": "BTCUSDT",
                    "signal_type": SignalType.LONG,
                    "confidence": 0.7 + i * 0.05,
                    "strength": 0.6 + i * 0.1,
                    "timestamp": datetime.utcnow() - timedelta(minutes=i),
                }
            )

        # Агрегируем сигналы
        aggregated = await signal_processor.aggregate_signals(signals)

        assert aggregated is not None
        assert aggregated["symbol"] == "BTCUSDT"
        assert aggregated["aggregated_confidence"] > 0.7
        assert aggregated["signal_count"] == 3

    @pytest.mark.asyncio
    async def test_handle_model_error(self, signal_processor, mock_ml_manager):
        """Тест обработки ошибок модели"""
        await signal_processor.initialize()
        signal_processor._ml_manager = mock_ml_manager

        # Mock ошибку предсказания
        mock_ml_manager.predict.side_effect = RuntimeError("Model error")

        # Должен вернуть None при ошибке
        signal = await signal_processor.process_signal(
            symbol="BTCUSDT", features=np.random.randn(96, 240), current_price=50000.0
        )

        assert signal is None

    @pytest.mark.asyncio
    async def test_performance_metrics(self, signal_processor):
        """Тест сбора метрик производительности"""
        await signal_processor.initialize()

        # Обновляем статистику
        signal_processor._stats["total_signals_processed"] = 100
        signal_processor._stats["valid_signals_generated"] = 75
        signal_processor._stats["signals_saved"] = 70
        signal_processor._stats["processing_errors"] = 5

        metrics = await signal_processor.get_metrics()

        assert metrics["total_processed"] == 100
        assert metrics["success_rate"] == 0.75
        assert metrics["save_rate"] == 0.70
        assert metrics["error_rate"] == 0.05

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, signal_processor, mock_ml_manager):
        """Тест конкурентной обработки сигналов"""
        await signal_processor.initialize()
        signal_processor._ml_manager = mock_ml_manager

        # Mock предсказания
        mock_ml_manager.predict.return_value = np.random.randn(20)

        # Создаем множество задач
        tasks = []
        for i in range(10):
            task = signal_processor.process_signal(
                symbol=f"SYMBOL{i}",
                features=np.random.randn(96, 240),
                current_price=50000.0 + i * 100,
            )
            tasks.append(task)

        # Выполняем конкурентно
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Проверяем результаты
        successful = [r for r in results if isinstance(r, (Signal, type(None)))]
        assert len(successful) == 10

    @pytest.mark.asyncio
    async def test_signal_priority_queue(self, signal_processor):
        """Тест приоритетной очереди сигналов"""
        await signal_processor.initialize()

        # Создаем сигналы с разным приоритетом
        high_priority = {"symbol": "BTCUSDT", "confidence": 0.95, "priority": "high"}

        low_priority = {"symbol": "ALTCOIN", "confidence": 0.65, "priority": "low"}

        # Добавляем в очередь
        await signal_processor.queue_signal(low_priority)
        await signal_processor.queue_signal(high_priority)

        # Обрабатываем очередь
        processed = await signal_processor.process_queue()

        # Первым должен быть обработан high priority
        assert processed[0]["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_signal_caching(self, signal_processor):
        """Тест кеширования сигналов"""
        await signal_processor.initialize()

        # Включаем кеширование
        signal_processor._enable_cache = True
        signal_processor._cache_ttl = 60  # 60 секунд

        # Первый вызов - генерация сигнала
        with patch.object(signal_processor, "_generate_signal") as mock_generate:
            mock_signal = Signal(symbol="BTCUSDT", confidence=0.8)
            mock_generate.return_value = mock_signal

            signal1 = await signal_processor.get_or_generate_signal("BTCUSDT", {})
            assert mock_generate.call_count == 1

            # Второй вызов - из кеша
            signal2 = await signal_processor.get_or_generate_signal("BTCUSDT", {})
            assert mock_generate.call_count == 1  # Не увеличился
            assert signal1 == signal2

    @pytest.mark.asyncio
    async def test_shutdown(self, signal_processor):
        """Тест корректного завершения работы"""
        await signal_processor.initialize()

        # Добавляем незавершенные задачи
        signal_processor._pending_tasks = [asyncio.create_task(asyncio.sleep(10))]

        # Shutdown должен отменить все задачи
        await signal_processor.shutdown()

        assert not signal_processor._initialized
        assert all(task.cancelled() for task in signal_processor._pending_tasks)
