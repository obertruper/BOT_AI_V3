#!/usr/bin/env python3
"""
Базовые классы и интерфейсы для адаптеров ML моделей.
Обеспечивает абстракцию между моделями и торговой системой.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
import pandas as pd
import torch

from core.logger import setup_logger

logger = setup_logger(__name__)


class SignalDirection(Enum):
    """Направления торговых сигналов"""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class RiskLevel(Enum):
    """Уровни риска"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class RiskMetrics:
    """Метрики риска для торгового сигнала"""
    max_drawdown_1h: float
    max_rally_1h: float
    max_drawdown_4h: float
    max_rally_4h: float
    avg_risk: float
    risk_level: RiskLevel
    
    def to_dict(self) -> dict[str, Any]:
        """Конвертирует в словарь для сериализации"""
        return {
            "max_drawdown_1h": self.max_drawdown_1h,
            "max_rally_1h": self.max_rally_1h,
            "max_drawdown_4h": self.max_drawdown_4h,
            "max_rally_4h": self.max_rally_4h,
            "avg_risk": self.avg_risk,
            "risk_level": self.risk_level.value,
        }


@dataclass
class TimeframePrediction:
    """Предсказание для отдельного таймфрейма"""
    timeframe: str  # "15m", "1h", "4h", "12h"
    direction: SignalDirection
    confidence: float  # 0.0-1.0
    expected_return: float  # Ожидаемая доходность
    direction_probabilities: dict[str, float]  # {"LONG": 0.6, "SHORT": 0.3, "NEUTRAL": 0.1}
    
    def to_dict(self) -> dict[str, Any]:
        """Конвертирует в словарь"""
        return {
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "confidence": self.confidence,
            "expected_return": self.expected_return,
            "direction_probabilities": self.direction_probabilities,
        }


@dataclass
class UnifiedPrediction:
    """
    Унифицированный формат предсказания модели.
    Обеспечивает единый интерфейс независимо от архитектуры модели.
    """
    # Основные параметры сигнала
    signal_type: str  # LONG/SHORT/NEUTRAL
    confidence: float  # Общая уверенность (0.0-1.0)
    signal_strength: float  # Сила сигнала (0.0-1.0)
    
    # Предсказания по таймфреймам
    timeframe_predictions: dict[str, TimeframePrediction]
    primary_direction: str  # Основное направление
    primary_confidence: float  # Уверенность в основном направлении
    primary_returns: dict[str, float]  # {"15m": 0.01, "1h": 0.02, ...}
    
    # Риск-метрики
    risk_level: str  # LOW/MEDIUM/HIGH  
    risk_metrics: RiskMetrics
    
    # Уровни для торговли (проценты)
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    
    # Качество сигнала
    quality_score: float = 0.0
    agreement_score: float = 0.0
    filter_passed: bool = False
    filter_strategy: str = "moderate"
    rejection_reasons: list[str] = field(default_factory=list)
    
    # Метаданные
    model_name: str = "unknown"
    model_version: str = "1.0"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    raw_outputs: Optional[dict[str, Any]] = None
    
    # Совместимость с legacy системой
    is_duplicate: bool = False
    success_probability: float = 0.5
    
    def to_dict(self) -> dict[str, Any]:
        """
        Конвертирует в словарь для совместимости с существующим кодом.
        Сохраняет обратную совместимость с текущим форматом.
        """
        # Базовые поля для совместимости
        result = {
            # Основные поля
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "signal_strength": self.signal_strength,
            "signal_confidence": self.confidence,  # Для совместимости
            "success_probability": self.success_probability,
            
            # SL/TP
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            
            # Риск
            "risk_level": self.risk_level,
            "risk_score": self.risk_metrics.avg_risk if self.risk_metrics else 0.0,
            "max_drawdown": self.risk_metrics.max_drawdown_1h if self.risk_metrics else 0.0,
            "max_rally": self.risk_metrics.max_rally_1h if self.risk_metrics else 0.0,
            
            # Детализированные предсказания (legacy формат)
            "returns_15m": self.primary_returns.get("15m", 0.0),
            "returns_1h": self.primary_returns.get("1h", 0.0),
            "returns_4h": self.primary_returns.get("4h", 0.0),
            "returns_12h": self.primary_returns.get("12h", 0.0),
            
            # Направления по таймфреймам
            "direction_15m": self._get_tf_direction("15m"),
            "direction_1h": self._get_tf_direction("1h"),
            "direction_4h": self._get_tf_direction("4h"),
            "direction_12h": self._get_tf_direction("12h"),
            
            # Уверенность по таймфреймам
            "confidence_15m": self._get_tf_confidence("15m"),
            "confidence_1h": self._get_tf_confidence("1h"),
            "confidence_4h": self._get_tf_confidence("4h"),
            "confidence_12h": self._get_tf_confidence("12h"),
            
            # Метрики качества
            "quality_score": self.quality_score,
            "agreement_score": self.agreement_score,
            "filter_strategy": self.filter_strategy,
            "passed_quality_filters": self.filter_passed,
            "rejection_reasons": self.rejection_reasons,
            
            # Дополнительно
            "primary_timeframe": "4h",
            "primary_direction": self.primary_direction,
            "primary_confidence": self.primary_confidence,
            
            # Nested структуры для совместимости
            "predictions": {
                "returns_15m": self.primary_returns.get("15m", 0.0),
                "returns_1h": self.primary_returns.get("1h", 0.0),
                "returns_4h": self.primary_returns.get("4h", 0.0),
                "returns_12h": self.primary_returns.get("12h", 0.0),
                "direction_score": 0.0,  # Будет заполнено адаптером
                "directions_by_timeframe": self._get_directions_array(),
                "direction_probabilities": self._get_probabilities_array(),
            },
            
            "timestamp": self.timestamp.isoformat(),
            "is_duplicate": self.is_duplicate,
        }
        
        return result
    
    def _get_tf_direction(self, timeframe: str) -> str:
        """Получает направление для таймфрейма"""
        if timeframe in self.timeframe_predictions:
            return self.timeframe_predictions[timeframe].direction.value
        return "NEUTRAL"
    
    def _get_tf_confidence(self, timeframe: str) -> float:
        """Получает уверенность для таймфрейма"""
        if timeframe in self.timeframe_predictions:
            return self.timeframe_predictions[timeframe].confidence
        return 0.0
    
    def _get_directions_array(self) -> list[int]:
        """Возвращает массив направлений для совместимости"""
        timeframes = ["15m", "1h", "4h", "12h"]
        directions = []
        for tf in timeframes:
            if tf in self.timeframe_predictions:
                direction = self.timeframe_predictions[tf].direction
                if direction == SignalDirection.LONG:
                    directions.append(0)
                elif direction == SignalDirection.SHORT:
                    directions.append(1)
                else:
                    directions.append(2)
            else:
                directions.append(2)  # NEUTRAL по умолчанию
        return directions
    
    def _get_probabilities_array(self) -> list[list[float]]:
        """Возвращает массив вероятностей для совместимости"""
        timeframes = ["15m", "1h", "4h", "12h"]
        probabilities = []
        for tf in timeframes:
            if tf in self.timeframe_predictions:
                probs = self.timeframe_predictions[tf].direction_probabilities
                probabilities.append([
                    probs.get("LONG", 0.33),
                    probs.get("SHORT", 0.33),
                    probs.get("NEUTRAL", 0.34),
                ])
            else:
                probabilities.append([0.33, 0.33, 0.34])
        return probabilities


class BaseModelAdapter(ABC):
    """
    Базовый класс для адаптеров ML моделей.
    Определяет единый интерфейс для всех типов моделей.
    """
    
    def __init__(self, config: dict[str, Any]):
        """
        Инициализация адаптера.
        
        Args:
            config: Конфигурация модели
        """
        self.config = config
        self.model = None
        self.device = self._setup_device(config)
        self.model_name = config.get("name", "UnknownModel")
        self.model_type = config.get("type", self.model_name)  # Для обратной совместимости
        self.model_version = config.get("version", "1.0")
        self._initialized = False
        
        # Пути к файлам модели
        base_dir = Path(__file__).parent.parent.parent  # Корень проекта
        model_dir = base_dir / config.get("model_directory", "models/saved")
        self.model_path = model_dir / config.get("model_file", "model.pth")
        self.scaler_path = model_dir / config.get("scaler_file", "scaler.pkl")
        
        logger.info(f"Initialized {self.model_name} adapter, device: {self.device}")
    
    def _setup_device(self, config: dict[str, Any]) -> torch.device:
        """Настройка устройства для вычислений"""
        device_config = config.get("device", "auto")
        
        if device_config == "auto":
            if torch.cuda.is_available():
                device = torch.device("cuda:0")
                logger.info(f"Using CUDA device: {torch.cuda.get_device_name(0)}")
            else:
                device = torch.device("cpu")
                logger.info("CUDA not available, using CPU")
        else:
            device = torch.device(device_config)
            
        return device
    
    @abstractmethod
    async def load(self) -> None:
        """
        Загружает модель и необходимые компоненты.
        Должен быть реализован в наследниках.
        """
        pass
    
    @abstractmethod
    async def predict(self, data: Union[np.ndarray, pd.DataFrame], **kwargs) -> np.ndarray:
        """
        Делает предсказание на основе входных данных.
        
        Args:
            data: Входные данные (numpy array или DataFrame)
            **kwargs: Дополнительные параметры
            
        Returns:
            Сырые выходы модели в виде numpy array
        """
        pass
    
    @abstractmethod
    def interpret_outputs(
        self, 
        raw_outputs: np.ndarray,
        symbol: Optional[str] = None,
        current_price: Optional[float] = None,
        **kwargs
    ) -> UnifiedPrediction:
        """
        Интерпретирует сырые выходы модели в унифицированный формат.
        
        Args:
            raw_outputs: Сырые выходы модели
            symbol: Торговый символ (опционально)
            current_price: Текущая цена (опционально)
            **kwargs: Дополнительные параметры
            
        Returns:
            UnifiedPrediction объект с интерпретированными предсказаниями
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """
        Возвращает информацию о модели.
        
        Returns:
            Словарь с метаданными модели
        """
        pass
    
    async def initialize(self) -> None:
        """
        Полная инициализация адаптера.
        Вызывает load() и выполняет дополнительную настройку.
        """
        if self._initialized:
            logger.warning(f"{self.model_name} adapter already initialized")
            return
            
        try:
            await self.load()
            self._initialized = True
            logger.info(f"✅ {self.model_name} adapter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize {self.model_name} adapter: {e}")
            raise
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирован ли адаптер"""
        return self._initialized
    
    async def update_model(self, new_model_path: str) -> None:
        """
        Обновляет модель на новую версию.
        
        Args:
            new_model_path: Путь к новой модели
        """
        try:
            # Сохраняем резервную копию
            backup_path = self.model_path.with_suffix(".pth.backup")
            if self.model_path.exists():
                self.model_path.rename(backup_path)
            
            # Копируем новую модель
            Path(new_model_path).rename(self.model_path)
            
            # Перезагружаем
            await self.load()
            
            logger.info(f"Model updated successfully from {new_model_path}")
            
        except Exception as e:
            logger.error(f"Error updating model: {e}")
            # Восстанавливаем резервную копию
            if backup_path.exists():
                backup_path.rename(self.model_path)
            raise
    
    def validate_input(self, data: Union[np.ndarray, pd.DataFrame]) -> bool:
        """
        Валидирует входные данные.
        
        Args:
            data: Входные данные для валидации
            
        Returns:
            True если данные валидны
        """
        if data is None:
            logger.error("Input data is None")
            return False
            
        if isinstance(data, pd.DataFrame):
            if data.empty:
                logger.error("Input DataFrame is empty")
                return False
        elif isinstance(data, np.ndarray):
            if data.size == 0:
                logger.error("Input array is empty")
                return False
        else:
            logger.error(f"Unsupported data type: {type(data)}")
            return False
            
        return True
    
    def get_required_features(self) -> list[str]:
        """
        Возвращает список требуемых признаков для модели.
        Может быть переопределен в наследниках.
        
        Returns:
            Список названий признаков
        """
        return []
    
    def get_supported_timeframes(self) -> list[str]:
        """
        Возвращает поддерживаемые таймфреймы.
        
        Returns:
            Список таймфреймов
        """
        return ["15m", "1h", "4h", "12h"]
    
    def __repr__(self) -> str:
        """Строковое представление адаптера"""
        return f"{self.__class__.__name__}(model={self.model_name}, version={self.model_version}, device={self.device})"