#!/usr/bin/env python3
"""
Система адаптеров для ML моделей в BOT_AI_V3.
Обеспечивает унифицированный интерфейс для работы с различными архитектурами моделей.
"""

from ml.adapters.base import (
    BaseModelAdapter,
    RiskMetrics,
    TimeframePrediction,
    UnifiedPrediction,
)
from ml.adapters.factory import ModelAdapterFactory
from ml.adapters.patchtst import PatchTSTAdapter

# Регистрируем адаптеры при импорте
ModelAdapterFactory.register_adapter("PatchTST", PatchTSTAdapter)
ModelAdapterFactory.register_adapter("PatchTSTAdapter", PatchTSTAdapter)
ModelAdapterFactory.register_adapter("UnifiedPatchTST", PatchTSTAdapter)
ModelAdapterFactory.register_adapter("patchtst", PatchTSTAdapter)

__all__ = [
    "BaseModelAdapter",
    "UnifiedPrediction",
    "TimeframePrediction",
    "RiskMetrics",
    "PatchTSTAdapter",
    "ModelAdapterFactory",
]