"""
Unit тесты для PatchTST модели
"""

import pytest
import torch

from ml.logic.patchtst_model import (
    DirectionalMultiTaskLoss,
    EncoderLayer,
    PositionalEncoding,
    RevIN,
    UnifiedPatchTSTForTrading,
    create_unified_model,
)


@pytest.mark.unit
@pytest.mark.ml
class TestPatchTSTComponents:
    """Тесты компонентов модели"""

    def test_revin(self):
        """Тест Reversible Instance Normalization"""
        revin = RevIN(num_features=10)
        x = torch.randn(32, 100, 10)

        # Нормализация
        x_norm = revin(x, mode="norm")
        assert x_norm.shape == x.shape

        # Денормализация
        x_denorm = revin(x_norm, mode="denorm")
        assert torch.allclose(x, x_denorm, atol=1e-5)

    def test_positional_encoding(self):
        """Тест позиционного кодирования"""
        pe = PositionalEncoding(d_model=256, max_len=100)
        x = torch.randn(50, 32, 256)  # seq_len, batch, d_model

        x_encoded = pe(x)
        assert x_encoded.shape == x.shape

    def test_encoder_layer(self):
        """Тест слоя энкодера"""
        encoder = EncoderLayer(d_model=256, n_heads=4, d_ff=512, dropout=0.1)

        x = torch.randn(32, 50, 256)
        output = encoder(x)
        assert output.shape == x.shape


@pytest.mark.unit
@pytest.mark.ml
class TestUnifiedPatchTST:
    """Тесты основной модели"""

    @pytest.fixture
    def config(self):
        """Базовая конфигурация для тестов"""
        return {
            "model": {
                "input_size": 240,
                "output_size": 20,
                "context_window": 96,
                "patch_len": 16,
                "stride": 8,
                "d_model": 256,
                "n_heads": 4,
                "e_layers": 3,
                "d_ff": 512,
                "dropout": 0.1,
                "direction_confidence_threshold": 0.5,
            }
        }

    def test_model_creation(self, config):
        """Тест создания модели"""
        model = create_unified_model(config)
        assert isinstance(model, UnifiedPatchTSTForTrading)
        assert model.n_features == 240
        assert model.n_outputs == 20

    def test_forward_pass(self, config):
        """Тест forward pass"""
        model = create_unified_model(config)
        model.eval()

        batch_size = 16
        x = torch.randn(batch_size, 96, 240)

        with torch.no_grad():
            outputs = model(x)

        assert outputs.shape == (batch_size, 20)
        assert hasattr(outputs, "_direction_logits")
        assert outputs._direction_logits.shape == (batch_size, 4, 3)

    def test_output_names(self, config):
        """Тест имен выходов"""
        model = create_unified_model(config)
        names = model.get_output_names()

        assert len(names) == 20
        assert names[0:4] == [
            "future_return_15m",
            "future_return_1h",
            "future_return_4h",
            "future_return_12h",
        ]
        assert names[4:8] == [
            "direction_15m",
            "direction_1h",
            "direction_4h",
            "direction_12h",
        ]

    def test_temperature_scaling(self):
        """Тест temperature scaling"""
        config = {
            "model": {
                "input_size": 240,
                "output_size": 20,
                "context_window": 96,
                "patch_len": 16,
                "stride": 8,
                "temperature_scaling": True,
                "temperature": 2.0,
            }
        }

        model = create_unified_model(config)
        assert model.temperature is not None
        assert model.temperature.item() == 2.0

    def test_confidence_threshold(self, config):
        """Тест порога уверенности"""
        config["model"]["direction_confidence_threshold"] = 0.8
        model = create_unified_model(config)
        model.eval()

        x = torch.randn(10, 96, 240)

        with torch.no_grad():
            outputs = model(x)

        # Проверяем, что направления корректно обрабатываются
        directions = outputs[:, 4:8]
        assert torch.all((directions >= 0) & (directions <= 2))


@pytest.mark.unit
@pytest.mark.ml
class TestDirectionalMultiTaskLoss:
    """Тесты loss функции"""

    @pytest.fixture
    def loss_config(self):
        """Конфигурация для loss"""
        return {
            "loss": {
                "task_weights": {
                    "future_returns": 1.0,
                    "directions": 3.0,
                    "long_levels": 1.0,
                    "short_levels": 1.0,
                    "risk_metrics": 0.5,
                },
                "class_weights": [1.3, 1.3, 0.7],
                "large_move_weight": 5.0,
                "large_move_threshold": 0.003,
                "focal_alpha": 0.25,
                "focal_gamma": 2.0,
                "wrong_direction_penalty": 3.0,
            }
        }

    def test_loss_creation(self, loss_config):
        """Тест создания loss функции"""
        criterion = DirectionalMultiTaskLoss(loss_config)
        assert criterion.future_returns_weight == 1.0
        assert criterion.directions_weight == 3.0

    def test_loss_computation(self, loss_config):
        """Тест вычисления loss"""
        criterion = DirectionalMultiTaskLoss(loss_config)

        batch_size = 8
        outputs = torch.randn(batch_size, 20)
        targets = torch.zeros(batch_size, 20)

        # Создаем фейковые логиты для направлений
        outputs._direction_logits = torch.randn(batch_size, 4, 3)

        # Future returns
        targets[:, 0:4] = torch.randn(batch_size, 4) * 2
        # Directions
        targets[:, 4:8] = torch.randint(0, 3, (batch_size, 4)).float()
        # Binary targets
        targets[:, 8:16] = torch.randint(0, 2, (batch_size, 8)).float()
        # Risk metrics
        targets[:, 16:20] = torch.abs(torch.randn(batch_size, 4)) * 5

        loss = criterion(outputs, targets)

        assert isinstance(loss, torch.Tensor)
        assert loss.ndim == 0  # Скаляр
        assert loss.item() > 0

    def test_focal_loss(self, loss_config):
        """Тест focal loss"""
        criterion = DirectionalMultiTaskLoss(loss_config)

        logits = torch.randn(32, 3)
        targets = torch.randint(0, 3, (32,))

        focal_loss = criterion.focal_loss(logits, targets)
        assert focal_loss.shape == (32,)


@pytest.mark.unit
@pytest.mark.ml
@pytest.mark.slow
class TestIntegration:
    """Интеграционные тесты"""

    def test_full_training_step(self):
        """Тест полного шага обучения"""
        config = {
            "model": {
                "input_size": 240,
                "output_size": 20,
                "context_window": 96,
                "patch_len": 16,
                "stride": 8,
                "d_model": 128,  # Меньше для теста
                "n_heads": 2,
                "e_layers": 2,
                "d_ff": 256,
                "dropout": 0.1,
            },
            "loss": {
                "task_weights": {
                    "future_returns": 1.0,
                    "directions": 3.0,
                    "long_levels": 1.0,
                    "short_levels": 1.0,
                    "risk_metrics": 0.5,
                },
                "class_weights": [1.0, 1.0, 1.0],
            },
        }

        model = create_unified_model(config)
        criterion = DirectionalMultiTaskLoss(config)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

        # Данные
        batch_size = 4
        inputs = torch.randn(batch_size, 96, 240)
        targets = torch.zeros(batch_size, 20)
        targets[:, 4:8] = torch.randint(0, 3, (batch_size, 4)).float()

        # Training step
        model.train()
        optimizer.zero_grad()

        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        assert loss.item() > 0

        # Проверяем, что градиенты прошли для основных параметров
        # Некоторые параметры могут не иметь градиентов (например, frozen слои)
        params_with_grad = sum(1 for p in model.parameters() if p.grad is not None)
        total_params = sum(1 for p in model.parameters() if p.requires_grad)

        # Должны быть градиенты хотя бы у 80% параметров
        assert params_with_grad / total_params > 0.8, (
            f"Only {params_with_grad}/{total_params} params have gradients"
        )
