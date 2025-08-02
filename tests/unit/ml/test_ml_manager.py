"""
Unit тесты для MLManager - менеджера ML моделей
"""

import asyncio
import pickle
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from ml.ml_manager import MLManager


@pytest.mark.unit
@pytest.mark.ml
class TestMLManager:
    """Тесты для класса MLManager"""

    @pytest.fixture
    def mock_config(self):
        """Mock конфигурация для тестов"""
        return {
            "ml": {
                "enabled": True,
                "model_directory": "models/saved",
                "data_directory": "data/ml",
                "model_cache_size": 3,
                "preload_models": ["BTCUSDT", "ETHUSDT"],
                "device": "cpu",
                "memory_limit_mb": 1024,
                "model_timeout": 30.0,
            }
        }

    @pytest.fixture
    def temp_model_dir(self, tmp_path):
        """Создание временной директории с моделями"""
        model_dir = tmp_path / "models" / "saved"
        model_dir.mkdir(parents=True)

        # Создаем фиктивные файлы моделей
        for symbol in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
            # Model file
            model_data = {
                "state_dict": {},
                "config": {"input_size": 240, "output_size": 20, "context_window": 96},
                "metadata": {
                    "symbol": symbol,
                    "version": "1.0.0",
                    "training_date": "2024-01-01",
                },
            }
            torch.save(model_data, model_dir / f"model_{symbol}.pth")

            # Scaler file
            scaler_data = {"mean": np.zeros(240), "std": np.ones(240)}
            with open(model_dir / f"scaler_{symbol}.pkl", "wb") as f:
                pickle.dump(scaler_data, f)

        return model_dir

    @pytest.fixture
    def ml_manager(self, mock_config, temp_model_dir):
        """Создание экземпляра MLManager с mock конфигурацией"""
        mock_config["ml"]["model_directory"] = str(temp_model_dir)

        with patch("ml.ml_manager.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_config.return_value = mock_config
            manager = MLManager()
            return manager

    @pytest.mark.asyncio
    async def test_initialization(self, ml_manager):
        """Тест инициализации MLManager"""
        await ml_manager.initialize()

        assert ml_manager._initialized
        assert ml_manager.device == torch.device("cpu")
        assert len(ml_manager._model_cache) == 0
        assert ml_manager._cache_size == 3
        assert ml_manager._memory_limit == 1024

    @pytest.mark.asyncio
    async def test_preload_models(self, ml_manager, temp_model_dir):
        """Тест предзагрузки моделей"""
        # Mock загрузку моделей
        with patch.object(ml_manager, "_load_single_model") as mock_load:
            mock_load.return_value = (MagicMock(), MagicMock())

            await ml_manager.initialize()

            # Проверяем, что модели из preload_models были загружены
            assert mock_load.call_count == 2
            mock_load.assert_any_call("BTCUSDT")
            mock_load.assert_any_call("ETHUSDT")

    @pytest.mark.asyncio
    async def test_load_model_success(self, ml_manager):
        """Тест успешной загрузки модели"""
        await ml_manager.initialize()

        with patch.object(ml_manager, "_load_single_model") as mock_load:
            mock_model = MagicMock()
            mock_scaler = MagicMock()
            mock_load.return_value = (mock_model, mock_scaler)

            result = await ml_manager.load_model("BTCUSDT")

            assert result is True
            assert "BTCUSDT" in ml_manager._model_cache
            assert ml_manager._model_cache["BTCUSDT"]["model"] == mock_model
            assert ml_manager._model_cache["BTCUSDT"]["scaler"] == mock_scaler

    @pytest.mark.asyncio
    async def test_load_model_not_found(self, ml_manager):
        """Тест загрузки несуществующей модели"""
        await ml_manager.initialize()

        with patch.object(ml_manager, "_load_single_model") as mock_load:
            mock_load.side_effect = FileNotFoundError("Model not found")

            result = await ml_manager.load_model("UNKNOWN")

            assert result is False
            assert "UNKNOWN" not in ml_manager._model_cache

    @pytest.mark.asyncio
    async def test_get_model_from_cache(self, ml_manager):
        """Тест получения модели из кеша"""
        await ml_manager.initialize()

        # Загружаем модель в кеш
        mock_model = MagicMock()
        mock_scaler = MagicMock()
        ml_manager._model_cache["BTCUSDT"] = {
            "model": mock_model,
            "scaler": mock_scaler,
            "last_used": asyncio.get_event_loop().time(),
        }

        model, scaler = await ml_manager.get_model("BTCUSDT")

        assert model == mock_model
        assert scaler == mock_scaler

    @pytest.mark.asyncio
    async def test_get_model_load_on_demand(self, ml_manager):
        """Тест загрузки модели по требованию"""
        await ml_manager.initialize()

        with patch.object(ml_manager, "_load_single_model") as mock_load:
            mock_model = MagicMock()
            mock_scaler = MagicMock()
            mock_load.return_value = (mock_model, mock_scaler)

            model, scaler = await ml_manager.get_model("ETHUSDT")

            assert model == mock_model
            assert scaler == mock_scaler
            assert "ETHUSDT" in ml_manager._model_cache

    @pytest.mark.asyncio
    async def test_cache_eviction(self, ml_manager):
        """Тест вытеснения из кеша при превышении размера"""
        await ml_manager.initialize()
        ml_manager._cache_size = 2  # Уменьшаем размер кеша для теста

        # Загружаем 3 модели при размере кеша 2
        for i, symbol in enumerate(["BTC", "ETH", "BNB"]):
            ml_manager._model_cache[symbol] = {
                "model": MagicMock(),
                "scaler": MagicMock(),
                "last_used": i,  # Разное время использования
            }

            if len(ml_manager._model_cache) > ml_manager._cache_size:
                # Вызываем вытеснение
                await ml_manager._evict_least_used()

        # Проверяем, что остались только 2 последние модели
        assert len(ml_manager._model_cache) == 2
        assert "BTC" not in ml_manager._model_cache  # Самая старая удалена
        assert "ETH" in ml_manager._model_cache
        assert "BNB" in ml_manager._model_cache

    @pytest.mark.asyncio
    async def test_unload_model(self, ml_manager):
        """Тест выгрузки модели из памяти"""
        await ml_manager.initialize()

        # Загружаем модель
        ml_manager._model_cache["BTCUSDT"] = {
            "model": MagicMock(),
            "scaler": MagicMock(),
            "last_used": asyncio.get_event_loop().time(),
        }

        # Выгружаем модель
        await ml_manager.unload_model("BTCUSDT")

        assert "BTCUSDT" not in ml_manager._model_cache

    @pytest.mark.asyncio
    async def test_unload_all_models(self, ml_manager):
        """Тест выгрузки всех моделей"""
        await ml_manager.initialize()

        # Загружаем несколько моделей
        for symbol in ["BTC", "ETH", "BNB"]:
            ml_manager._model_cache[symbol] = {
                "model": MagicMock(),
                "scaler": MagicMock(),
                "last_used": asyncio.get_event_loop().time(),
            }

        # Выгружаем все
        await ml_manager.unload_all()

        assert len(ml_manager._model_cache) == 0

    @pytest.mark.asyncio
    async def test_memory_management(self, ml_manager):
        """Тест управления памятью"""
        await ml_manager.initialize()

        with patch("ml.ml_manager.psutil") as mock_psutil:
            # Mock использование памяти
            mock_process = MagicMock()
            mock_process.memory_info.return_value.rss = 500 * 1024 * 1024  # 500 MB
            mock_psutil.Process.return_value = mock_process

            # Проверяем память
            memory_mb = await ml_manager.check_memory_usage()

            assert memory_mb == 500
            assert await ml_manager.is_memory_available() is True

            # Превышаем лимит
            mock_process.memory_info.return_value.rss = 1500 * 1024 * 1024  # 1500 MB

            assert await ml_manager.is_memory_available() is False

    @pytest.mark.asyncio
    async def test_get_loaded_models(self, ml_manager):
        """Тест получения списка загруженных моделей"""
        await ml_manager.initialize()

        # Загружаем модели
        for symbol in ["BTC", "ETH"]:
            ml_manager._model_cache[symbol] = {
                "model": MagicMock(),
                "scaler": MagicMock(),
                "last_used": asyncio.get_event_loop().time(),
            }

        loaded = await ml_manager.get_loaded_models()

        assert len(loaded) == 2
        assert "BTC" in loaded
        assert "ETH" in loaded

    @pytest.mark.asyncio
    async def test_get_model_info(self, ml_manager):
        """Тест получения информации о модели"""
        await ml_manager.initialize()

        # Mock модель с метаданными
        mock_model = MagicMock()
        mock_model.metadata = {
            "version": "1.0.0",
            "training_date": "2024-01-01",
            "accuracy": 0.75,
        }

        ml_manager._model_cache["BTCUSDT"] = {
            "model": mock_model,
            "scaler": MagicMock(),
            "last_used": asyncio.get_event_loop().time(),
            "load_time": 1.5,
        }

        info = await ml_manager.get_model_info("BTCUSDT")

        assert info is not None
        assert info["loaded"] is True
        assert info["version"] == "1.0.0"
        assert info["load_time"] == 1.5
        assert "last_used" in info

    @pytest.mark.asyncio
    async def test_model_prediction(self, ml_manager):
        """Тест предсказания модели"""
        await ml_manager.initialize()

        # Mock модель
        mock_model = MagicMock()
        mock_output = torch.randn(1, 20)
        mock_model.return_value = mock_output

        mock_scaler = MagicMock()
        mock_scaler.transform.return_value = np.random.randn(96, 240)

        ml_manager._model_cache["BTCUSDT"] = {
            "model": mock_model,
            "scaler": mock_scaler,
            "last_used": asyncio.get_event_loop().time(),
        }

        # Создаем тестовые данные
        features = np.random.randn(96, 240)

        # Выполняем предсказание
        with patch.object(ml_manager, "predict") as mock_predict:
            mock_predict.return_value = mock_output.numpy()

            result = await mock_predict("BTCUSDT", features)

            assert result is not None
            assert result.shape == (1, 20)

    @pytest.mark.asyncio
    async def test_shutdown(self, ml_manager):
        """Тест корректного завершения работы"""
        await ml_manager.initialize()

        # Загружаем модели
        for symbol in ["BTC", "ETH"]:
            ml_manager._model_cache[symbol] = {
                "model": MagicMock(),
                "scaler": MagicMock(),
                "last_used": asyncio.get_event_loop().time(),
            }

        # Shutdown
        await ml_manager.shutdown()

        assert len(ml_manager._model_cache) == 0
        assert not ml_manager._initialized

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_model_loading(self, ml_manager):
        """Тест конкурентной загрузки моделей"""
        await ml_manager.initialize()

        with patch.object(ml_manager, "_load_single_model") as mock_load:
            # Имитируем долгую загрузку
            async def slow_load(symbol):
                await asyncio.sleep(0.1)
                return (MagicMock(), MagicMock())

            mock_load.side_effect = slow_load

            # Запускаем несколько загрузок одновременно
            tasks = [
                ml_manager.load_model("BTC"),
                ml_manager.load_model("ETH"),
                ml_manager.load_model("BNB"),
            ]

            results = await asyncio.gather(*tasks)

            assert all(results)
            assert len(ml_manager._model_cache) == 3

    @pytest.mark.asyncio
    async def test_model_timeout(self, ml_manager):
        """Тест таймаута загрузки модели"""
        await ml_manager.initialize()
        ml_manager._model_timeout = 0.1  # Короткий таймаут для теста

        with patch.object(ml_manager, "_load_single_model") as mock_load:
            # Имитируем очень долгую загрузку
            async def very_slow_load(symbol):
                await asyncio.sleep(1.0)
                return (MagicMock(), MagicMock())

            mock_load.side_effect = very_slow_load

            # Должен произойти таймаут
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    ml_manager.load_model("SLOW"), timeout=ml_manager._model_timeout
                )

    def test_get_model_path(self, ml_manager):
        """Тест получения пути к файлу модели"""
        model_path = ml_manager._get_model_path("BTCUSDT")

        assert isinstance(model_path, Path)
        assert "BTCUSDT" in str(model_path)
        assert model_path.suffix == ".pth"

    def test_get_scaler_path(self, ml_manager):
        """Тест получения пути к файлу scaler"""
        scaler_path = ml_manager._get_scaler_path("BTCUSDT")

        assert isinstance(scaler_path, Path)
        assert "BTCUSDT" in str(scaler_path)
        assert scaler_path.suffix == ".pkl"

    @pytest.mark.asyncio
    async def test_error_handling_corrupted_model(self, ml_manager, temp_model_dir):
        """Тест обработки ошибок при загрузке поврежденной модели"""
        # Создаем поврежденный файл модели
        corrupted_path = temp_model_dir / "model_CORRUPTED.pth"
        with open(corrupted_path, "wb") as f:
            f.write(b"corrupted data")

        result = await ml_manager.load_model("CORRUPTED")

        assert result is False
        assert "CORRUPTED" not in ml_manager._model_cache

    @pytest.mark.asyncio
    async def test_model_statistics(self, ml_manager):
        """Тест сбора статистики использования моделей"""
        await ml_manager.initialize()

        # Загружаем и используем модели
        for symbol in ["BTC", "ETH", "BNB"]:
            ml_manager._model_cache[symbol] = {
                "model": MagicMock(),
                "scaler": MagicMock(),
                "last_used": asyncio.get_event_loop().time(),
                "usage_count": 0,
            }

        # Имитируем использование
        for _ in range(5):
            await ml_manager.get_model("BTC")
            ml_manager._model_cache["BTC"]["usage_count"] += 1

        for _ in range(3):
            await ml_manager.get_model("ETH")
            ml_manager._model_cache["ETH"]["usage_count"] += 1

        # Получаем статистику
        stats = await ml_manager.get_statistics()

        assert stats["total_models_loaded"] == 3
        assert stats["cache_size"] == 3
        assert stats["most_used_model"] == "BTC"
