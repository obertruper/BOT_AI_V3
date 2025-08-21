"""
PatchTST модель для BOT Trading v3
Адаптированная версия унифицированной модели для многозадачного обучения

Архитектура:
- Input: 240 признаков (OHLCV + технические индикаторы)
- Context window: 96 (24 часа при 15-минутных свечах)
- Output: 20 целевых переменных:
  - 4 future returns (15m, 1h, 4h, 12h)
  - 4 directions (15m, 1h, 4h, 12h)
  - 8 level targets (4 long, 4 short)
  - 4 risk metrics (drawdown/rally для 1h, 4h)
"""

import logging
import math

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class PositionalEncoding(nn.Module):
    """Позиционное кодирование для Transformer"""

    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        # Изменено: формат [batch, seq_len, d_model] для совместимости
        pe = pe.unsqueeze(0)  # [1, max_len, d_model]

        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (batch, seq_len, d_model)"""
        # Адаптация под batch_first=True
        return x + self.pe[:, : x.size(1), :]


class RevIN(nn.Module):
    """Reversible Instance Normalization для временных рядов"""

    def __init__(self, num_features: int, eps: float = 1e-5, affine: bool = True):
        super().__init__()
        self.num_features = num_features
        self.eps = eps
        self.affine = affine

        if self.affine:
            self.affine_weight = nn.Parameter(torch.ones(num_features))
            self.affine_bias = nn.Parameter(torch.zeros(num_features))

    def forward(self, x: torch.Tensor, mode: str = "norm") -> torch.Tensor:
        """
        x: [Batch, Length, Features]
        mode: 'norm' для нормализации, 'denorm' для денормализации
        """
        if mode == "norm":
            self.mean = x.mean(dim=1, keepdim=True)
            self.std = torch.sqrt(x.var(dim=1, keepdim=True) + self.eps)
            x = (x - self.mean) / self.std

            if self.affine:
                x = x * self.affine_weight + self.affine_bias

        elif mode == "denorm":
            if self.affine:
                x = (x - self.affine_bias) / self.affine_weight

            x = x * self.std + self.mean

        return x


class EncoderLayer(nn.Module):
    """Слой энкодера с multi-head attention"""

    def __init__(
        self,
        d_model: int,
        n_heads: int,
        d_ff: int,
        dropout: float = 0.1,
        activation: str = "gelu",
    ):
        super().__init__()

        # Multi-head attention
        self.self_attention = nn.MultiheadAttention(
            embed_dim=d_model, num_heads=n_heads, dropout=dropout, batch_first=True
        )

        # Feed forward
        self.ff = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU() if activation == "gelu" else nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
        )

        # Normalization
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)

        # Dropout
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: [Batch, Length, Features]"""
        # Self attention with residual
        attn_out, _ = self.self_attention(x, x, x)
        x = x + self.dropout1(attn_out)
        x = self.norm1(x)

        # Feed forward with residual
        ff_out = self.ff(x)
        x = x + self.dropout2(ff_out)
        x = self.norm2(x)

        return x


class PatchTSTEncoder(nn.Module):
    """Encoder для PatchTST с остаточными соединениями"""

    def __init__(
        self,
        e_layers: int = 3,
        d_model: int = 256,
        n_heads: int = 4,
        d_ff: int = 512,
        dropout: float = 0.1,
        activation: str = "gelu",
    ):
        super().__init__()

        self.e_layers = e_layers
        self.d_model = d_model

        # Encoder layers
        self.encoder_layers = nn.ModuleList(
            [
                EncoderLayer(
                    d_model=d_model,
                    n_heads=n_heads,
                    d_ff=d_ff,
                    dropout=dropout,
                    activation=activation,
                )
                for _ in range(e_layers)
            ]
        )

        self.norm = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: [Batch, Length, Features]"""
        # Encoder
        for encoder_layer in self.encoder_layers:
            x = encoder_layer(x)

        x = self.norm(x)

        return x


class UnifiedPatchTSTForTrading(nn.Module):
    """
    Единая модель PatchTST для торговли

    Архитектура:
    1. Общий энкодер для извлечения признаков
    2. Многозадачные головы для разных типов предсказаний
    3. 20 выходных переменных для комплексного анализа рынка
    """

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        model_config = config.get("model", {})

        # Базовые параметры
        self.n_features = model_config.get("input_size", 240)
        self.context_window = model_config.get("context_window", 96)
        self.patch_len = model_config.get("patch_len", 16)
        self.stride = model_config.get("stride", 8)

        # Параметры трансформера
        self.d_model = model_config.get("d_model", 256)
        self.n_heads = model_config.get("n_heads", 4)
        self.e_layers = model_config.get("e_layers", 3)
        self.d_ff = model_config.get("d_ff", 512)
        self.dropout = model_config.get("dropout", 0.1)
        self.activation = model_config.get("activation", "gelu")

        # Количество выходов
        self.n_outputs = model_config.get("output_size", 20)

        # Нормализация
        self.revin = RevIN(num_features=self.n_features, eps=1e-5, affine=True)

        # Патч эмбеддинги
        self.patch_embedding = nn.Conv1d(
            in_channels=self.n_features,
            out_channels=self.d_model,
            kernel_size=self.patch_len,
            stride=self.stride,
            padding=0,
            bias=False,
        )

        # Позиционное кодирование
        self.n_patches = (self.context_window - self.patch_len) // self.stride + 1
        self.positional_encoding = PositionalEncoding(d_model=self.d_model, max_len=self.n_patches)

        # Основной энкодер
        self.encoder = PatchTSTEncoder(
            e_layers=self.e_layers,
            d_model=self.d_model,
            n_heads=self.n_heads,
            d_ff=self.d_ff,
            dropout=self.dropout,
            activation=self.activation,
        )

        # Многозадачные выходные слои

        # 1. Future returns (регрессия) - 4 выхода [0-3]
        self.future_returns_head = nn.Sequential(
            nn.Linear(self.d_model, self.d_model // 2),
            nn.ReLU(),
            nn.Dropout(self.dropout),
            nn.Linear(self.d_model // 2, 4),
            nn.Tanh(),  # Ограничиваем выходы для стабильности
        )

        # 2. Направления движения (классификация 3 класса) - 4 выхода [4-7]
        self.direction_head = nn.Sequential(
            nn.Linear(self.d_model, self.d_model // 2),
            nn.ReLU(),
            nn.Dropout(self.dropout),
            nn.Linear(self.d_model // 2, 4 * 3),  # 4 таймфрейма x 3 класса
        )

        # 3. Достижение уровней LONG (бинарная классификация) - 4 выхода [8-11]
        self.long_levels_head = nn.Sequential(
            nn.Linear(self.d_model, self.d_model // 2),
            nn.ReLU(),
            nn.Dropout(self.dropout),
            nn.Linear(self.d_model // 2, 4),
        )

        # 4. Достижение уровней SHORT (бинарная классификация) - 4 выхода [12-15]
        self.short_levels_head = nn.Sequential(
            nn.Linear(self.d_model, self.d_model // 2),
            nn.ReLU(),
            nn.Dropout(self.dropout),
            nn.Linear(self.d_model // 2, 4),
        )

        # 5. Риск-метрики (регрессия) - 4 выхода [16-19]
        self.risk_metrics_head = nn.Sequential(
            nn.Linear(self.d_model, self.d_model // 2),
            nn.ReLU(),
            nn.Dropout(self.dropout),
            nn.Linear(self.d_model // 2, 4),
        )

        # 6. Confidence head (для совместимости со старой моделью)
        self.confidence_head = nn.Sequential(
            nn.Linear(self.d_model, self.d_model // 2),
            nn.ReLU(),
            nn.Dropout(self.dropout),
            nn.Linear(self.d_model // 2, 4),
        )

        # Финальный слой для объединения
        self.output_projection = nn.Linear(self.d_model, self.d_model)

        # Layer normalization
        self.ln = nn.LayerNorm(self.d_model)

        # Temperature scaling для калибровки
        if model_config.get("temperature_scaling", False):
            temp_value = model_config.get("temperature", 2.0)
            self.temperature = nn.Parameter(torch.ones(1) * temp_value)
        else:
            self.temperature = None

        # Инициализация весов
        self._init_weights()

    def _init_weights(self):
        """Инициализация весов модели"""
        for name, module in self.named_modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight, gain=0.5)
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0)

            elif isinstance(module, nn.Conv1d):
                nn.init.kaiming_normal_(module.weight, mode="fan_in", nonlinearity="leaky_relu")
                with torch.no_grad():
                    module.weight.mul_(0.7)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass

        Args:
            x: (batch_size, seq_len, n_features)

        Returns:
            output: (batch_size, n_outputs) - все целевые переменные
        """
        batch_size = x.shape[0]

        # Нормализация
        x = self.revin(x, "norm")

        # Перестановка для Conv1d: (B, L, C) -> (B, C, L)
        x = x.transpose(1, 2)

        # Создание патчей
        x = self.patch_embedding(x)  # (B, d_model, n_patches)
        x = x.transpose(1, 2)  # (B, n_patches, d_model)

        # Позиционное кодирование
        x = self.positional_encoding(x)

        # Трансформер энкодер
        x = self.encoder(x)  # (B, n_patches, d_model)

        # Глобальное представление (среднее по патчам)
        x_global = x.mean(dim=1)  # (B, d_model)

        # Нормализация
        x_global = self.ln(x_global)

        # Проекция
        x_projected = self.output_projection(x_global)

        # Многозадачные предсказания
        future_returns = self.future_returns_head(x_projected)  # (B, 4)

        # Direction head - логиты для 3 классов на каждый таймфрейм
        direction_logits = self.direction_head(x_projected)  # (B, 12)
        direction_logits_reshaped = direction_logits.view(batch_size, 4, 3)  # (B, 4, 3)

        # Temperature scaling если включено
        if self.temperature is not None:
            direction_logits_reshaped = direction_logits_reshaped / self.temperature

        # Риск-метрики
        risk_metrics = self.risk_metrics_head(x_projected)  # (B, 4)

        # Объединяем все выходы - возвращаем ЛОГИТЫ для правильной интерпретации в ml_manager
        # Reshape логитов для правильной структуры вывода
        # direction_logits_reshaped имеет форму (B, 4, 3) - нужно развернуть в (B, 12)
        direction_logits_flat = direction_logits_reshaped.reshape(batch_size, -1)  # (B, 12)
        
        outputs = torch.cat(
            [
                future_returns,  # 0-3: future returns (4 значения)
                direction_logits_flat,  # 4-15: direction logits (12 значений: 4 таймфрейма x 3 класса)
                risk_metrics,  # 16-19: risk metrics (4 значения)
            ],
            dim=1,
        )

        # Клиппинг для стабильности
        outputs = torch.clamp(outputs, min=-10.0, max=10.0)

        # Сохраняем логиты для loss функции
        outputs._direction_logits = direction_logits_reshaped

        return outputs

    def get_output_names(self) -> list[str]:
        """Возвращает имена всех выходов"""
        return [
            # Future returns (0-3)
            "future_return_15m",
            "future_return_1h",
            "future_return_4h",
            "future_return_12h",
            # Direction logits (4-15: 4 таймфрейма x 3 логита)
            "direction_15m_long_logit",
            "direction_15m_short_logit",
            "direction_15m_neutral_logit",
            "direction_1h_long_logit",
            "direction_1h_short_logit",
            "direction_1h_neutral_logit",
            "direction_4h_long_logit",
            "direction_4h_short_logit",
            "direction_4h_neutral_logit",
            "direction_12h_long_logit",
            "direction_12h_short_logit",
            "direction_12h_neutral_logit",
            # Risk metrics (16-19)
            "max_drawdown_1h",
            "max_rally_1h",
            "max_drawdown_4h",
            "max_rally_4h",
        ]


class DirectionalMultiTaskLoss(nn.Module):
    """
    Гибридная loss функция для multi-task learning
    Комбинирует MSE для регрессии, CrossEntropy для классификации и BCE для бинарных задач
    """

    def __init__(self, config: dict):
        super().__init__()
        self.config = config

        # Веса для разных типов задач
        task_weights = config.get("loss", {}).get("task_weights", {})
        self.future_returns_weight = task_weights.get("future_returns", 1.0)
        self.directions_weight = task_weights.get("directions", 3.0)
        self.long_levels_weight = task_weights.get("long_levels", 1.0)
        self.short_levels_weight = task_weights.get("short_levels", 1.0)
        self.risk_metrics_weight = task_weights.get("risk_metrics", 0.5)

        # Параметры для direction focus
        self.large_move_weight = config.get("loss", {}).get("large_move_weight", 5.0)
        self.min_movement_threshold = config.get("loss", {}).get("large_move_threshold", 0.003)

        # Loss функции
        self.mse_loss = nn.MSELoss(reduction="none")
        self.bce_with_logits_loss = nn.BCEWithLogitsLoss(reduction="none")

        # Веса классов для борьбы с дисбалансом
        config_weights = config.get("loss", {}).get("class_weights", [1.3, 1.3, 0.7])
        self.class_weights = torch.tensor(config_weights)

        # CrossEntropy с весами
        self.cross_entropy_loss = nn.CrossEntropyLoss(
            weight=(self.class_weights.cuda() if torch.cuda.is_available() else self.class_weights),
            reduction="none",
        )

        # Focal Loss параметры
        self.focal_alpha = config.get("loss", {}).get("focal_alpha", 0.25)
        self.focal_gamma = config.get("loss", {}).get("focal_gamma", 2.0)

        # Штраф за неправильное направление
        self.wrong_direction_penalty = config.get("loss", {}).get("wrong_direction_penalty", 3.0)

    def focal_loss(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """Focal Loss для борьбы с несбалансированными классами"""
        ce_loss = F.cross_entropy(
            logits,
            targets,
            weight=self.class_weights.to(logits.device),
            reduction="none",
        )
        pt = torch.exp(-ce_loss)
        focal_loss = self.focal_alpha * (1 - pt) ** self.focal_gamma * ce_loss
        return focal_loss

    def forward(self, outputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Вычисление multi-task loss

        Args:
            outputs: (batch_size, 20) - выходы модели
            targets: (batch_size, 20) - целевые значения

        Returns:
            loss: скаляр
        """
        losses = []

        # 1. Future Returns Loss (индексы 0-3)
        future_returns_pred = outputs[:, 0:4]
        future_returns_target = targets[:, 0:4] / 100.0  # Конвертируем из % в доли

        abs_returns = torch.abs(future_returns_target)
        large_move_mask = abs_returns > self.min_movement_threshold

        mse_loss = self.mse_loss(future_returns_pred, future_returns_target)

        movement_weights = torch.ones_like(mse_loss)
        movement_weights[large_move_mask] = self.large_move_weight

        future_returns_loss = (mse_loss * movement_weights).mean()
        losses.append(future_returns_loss * self.future_returns_weight)

        # 2. Direction Loss (индексы 4-7)
        if hasattr(outputs, "_direction_logits"):
            direction_logits = outputs._direction_logits  # (batch_size, 4, 3)
            direction_targets = targets[:, 4:8].long()  # (batch_size, 4)

            direction_loss = 0
            for i in range(4):
                focal_loss_val = self.focal_loss(direction_logits[:, i, :], direction_targets[:, i])

                pred_classes = torch.argmax(direction_logits[:, i, :], dim=-1)
                true_classes = direction_targets[:, i]

                wrong_direction_penalty = (
                    ((pred_classes == 0) & (true_classes == 1))
                    | ((pred_classes == 1) & (true_classes == 0))
                ).float() * self.wrong_direction_penalty

                timeframe_loss = focal_loss_val + wrong_direction_penalty
                direction_loss += timeframe_loss.mean()

            direction_loss = direction_loss / 4
            losses.append(direction_loss * self.directions_weight)

        # 3. Long Levels Loss (индексы 8-11)
        long_levels_pred = outputs[:, 8:12]
        long_levels_target = targets[:, 8:12]
        long_levels_loss = self.bce_with_logits_loss(long_levels_pred, long_levels_target).mean()
        losses.append(long_levels_loss * self.long_levels_weight)

        # 4. Short Levels Loss (индексы 12-15)
        short_levels_pred = outputs[:, 12:16]
        short_levels_target = targets[:, 12:16]
        short_levels_loss = self.bce_with_logits_loss(short_levels_pred, short_levels_target).mean()
        losses.append(short_levels_loss * self.short_levels_weight)

        # 5. Risk Metrics Loss (индексы 16-19)
        risk_metrics_pred = outputs[:, 16:20]
        risk_metrics_target = targets[:, 16:20] / 100.0  # Нормализуем если в процентах
        risk_metrics_loss = self.mse_loss(risk_metrics_pred, risk_metrics_target).mean()
        losses.append(risk_metrics_loss * self.risk_metrics_weight)

        total_loss = sum(losses)

        return total_loss


def create_unified_model(config: dict) -> UnifiedPatchTSTForTrading:
    """Создание унифицированной модели"""
    return UnifiedPatchTSTForTrading(config)


def load_model_safe(
    model: UnifiedPatchTSTForTrading, checkpoint_path: str, device: str = "cpu"
) -> UnifiedPatchTSTForTrading:
    """
    Безопасная загрузка модели с обработкой несовместимостей

    Args:
        model: Инициализированная модель
        checkpoint_path: Путь к чекпоинту
        device: Устройство для загрузки

    Returns:
        Модель с загруженными весами
    """
    checkpoint = torch.load(checkpoint_path, map_location=device)

    if "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
    else:
        state_dict = checkpoint

    # Обработка несовместимостей размерностей
    model_state = model.state_dict()
    compatible_state_dict = {}
    incompatible_keys = []

    for key, value in state_dict.items():
        if key in model_state:
            if model_state[key].shape == value.shape:
                compatible_state_dict[key] = value
            else:
                # Специальная обработка для positional_encoding
                if (
                    "positional_encoding.pe" in key
                    and value.shape[0] == 1
                    and value.shape[2] == model_state[key].shape[2]
                ):
                    # Преобразуем [1, seq, d_model] в текущий формат
                    compatible_state_dict[key] = value
                else:
                    incompatible_keys.append(
                        (key, f"expected {model_state[key].shape}, got {value.shape}")
                    )
                    logger.warning(
                        f"Skipping {key} due to shape mismatch: expected {model_state[key].shape}, got {value.shape}"
                    )
        else:
            if not any(
                skip in key for skip in ["confidence_head"]
            ):  # Игнорируем confidence_head если не используется
                incompatible_keys.append((key, "key not found in model"))

    # Проверяем отсутствующие ключи
    missing_keys = set(model_state.keys()) - set(compatible_state_dict.keys())
    for key in missing_keys:
        if "confidence_head" not in key:  # Не предупреждаем о confidence_head
            logger.warning(f"Missing key in checkpoint: {key}")

    # Загружаем совместимые веса
    model.load_state_dict(compatible_state_dict, strict=False)

    if incompatible_keys:
        logger.info(f"Loaded model with {len(incompatible_keys)} incompatible keys")
        for key, reason in incompatible_keys[:5]:  # Показываем первые 5
            logger.debug(f"  - {key}: {reason}")

    logger.info(f"Successfully loaded {len(compatible_state_dict)} out of {len(state_dict)} keys")

    return model


# Экспорт для совместимости
UnifiedPatchTST = UnifiedPatchTSTForTrading

__all__ = [
    "DirectionalMultiTaskLoss",
    "UnifiedPatchTST",
    "UnifiedPatchTSTForTrading",
    "create_unified_model",
    "load_model_safe",
]
