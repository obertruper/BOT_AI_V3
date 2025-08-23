#!/usr/bin/env python3
"""
Адаптер для PatchTST модели.
Инкапсулирует логику загрузки, предсказания и интерпретации для PatchTST архитектуры.
"""

import os
import pickle
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
import pandas as pd
import torch

from core.logger import setup_logger
from ml.adapters.base import (
    BaseModelAdapter,
    RiskLevel,
    RiskMetrics,
    SignalDirection,
    TimeframePrediction,
    UnifiedPrediction,
)
from ml.logic.feature_engineering_production import (
    ProductionFeatureEngineer as FeatureEngineer,
)
from ml.logic.patchtst_model import create_unified_model
from ml.logic.signal_quality_analyzer import SignalQualityAnalyzer

logger = setup_logger(__name__)


class PatchTSTAdapter(BaseModelAdapter):
    """
    Адаптер для UnifiedPatchTST модели.
    Перенос логики из MLManager с сохранением полной функциональности.
    """
    
    def __init__(self, config: dict[str, Any]):
        """
        Инициализация PatchTST адаптера.
        
        Args:
            config: Конфигурация модели
        """
        super().__init__(config)
        
        # Специфичные для PatchTST параметры
        self.context_length = 96  # 24 часа при 15-минутных свечах
        self.num_features = 240  # Модель обучена на 240 признаках
        self.num_targets = 20  # Модель выдает 20 выходов
        
        # Компоненты
        self.scaler = None
        self.feature_engineer = None
        self.quality_analyzer = None
        
        # Оптимизации
        self.use_torch_compile = not os.environ.get("TORCH_COMPILE_DISABLE", "").lower() in ("1", "true")
        
        logger.info(f"PatchTSTAdapter initialized with context_length={self.context_length}, "
                   f"num_features={self.num_features}, device={self.device}")
    
    async def load(self) -> None:
        """Загружает модель PatchTST и необходимые компоненты"""
        try:
            # Загружаем модель
            await self._load_model()
            
            # Загружаем scaler
            await self._load_scaler()
            
            # Инициализируем feature engineer
            self.feature_engineer = FeatureEngineer(self.config)
            
            # Инициализируем анализатор качества
            self.quality_analyzer = SignalQualityAnalyzer(self.config)
            
            logger.info("✅ PatchTST components loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading PatchTST components: {e}")
            raise
    
    async def _load_model(self):
        """Загружает модель PatchTST"""
        try:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Model file not found: {self.model_path}")
            
            # Создаем экземпляр модели
            model_config = {
                "model": {
                    "input_size": self.num_features,
                    "output_size": self.num_targets,
                    "context_window": self.context_length,
                    "patch_len": 16,
                    "stride": 8,
                    "d_model": 256,
                    "n_heads": 4,
                    "e_layers": 3,
                    "d_ff": 512,
                    "dropout": 0.1,
                    "temperature_scaling": True,
                    "temperature": 2.0,
                }
            }
            self.model = create_unified_model(model_config)
            
            # Загружаем веса
            checkpoint = torch.load(self.model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint["model_state_dict"])
            
            # Перемещаем на устройство
            self.model.to(self.device)
            self.model.eval()
            
            # Применяем torch.compile если доступно
            if self.use_torch_compile:
                try:
                    logger.info("🚀 Applying torch.compile optimization...")
                    self.model = torch.compile(
                        self.model,
                        mode="max-autotune",
                        fullgraph=False,
                        dynamic=False,
                    )
                    
                    # Warm-up
                    with torch.no_grad():
                        warmup_input = torch.randn(1, self.context_length, self.num_features).to(self.device)
                        _ = self.model(warmup_input)
                    
                    logger.info("✅ torch.compile optimization applied successfully")
                    
                except Exception as e:
                    logger.warning(f"Could not apply torch.compile: {e}")
            
            logger.info(f"Model loaded from {self.model_path}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    async def _load_scaler(self):
        """Загружает scaler для нормализации данных"""
        try:
            if not self.scaler_path.exists():
                raise FileNotFoundError(f"Scaler file not found: {self.scaler_path}")
            
            with open(self.scaler_path, "rb") as f:
                self.scaler = pickle.load(f)
            
            logger.info(f"Scaler loaded from {self.scaler_path}")
            
        except Exception as e:
            logger.error(f"Error loading scaler: {e}")
            raise
    
    async def predict(self, data: Union[np.ndarray, pd.DataFrame], **kwargs) -> np.ndarray:
        """
        Делает предсказание на основе входных данных.
        
        Args:
            data: Входные данные (numpy array с признаками или DataFrame с OHLCV)
            **kwargs: Дополнительные параметры
            
        Returns:
            Сырые выходы модели (20 значений)
        """
        if not self._initialized:
            raise ValueError("Adapter not initialized. Call initialize() first.")
        
        if not self.validate_input(data):
            raise ValueError("Invalid input data")
        
        # Обработка входных данных
        if isinstance(data, np.ndarray):
            # Уже готовые признаки
            features = self._prepare_features_from_array(data)
        else:
            # DataFrame с OHLCV - генерируем признаки
            features = self._prepare_features_from_dataframe(data)
        
        # Нормализация
        features_scaled = self.scaler.transform(features)
        
        # Фильтрация zero variance features
        features_scaled = self._handle_zero_variance(features_scaled)
        
        # Преобразуем в тензор
        x = torch.FloatTensor(features_scaled).unsqueeze(0).to(self.device)
        
        # Предсказание
        with torch.no_grad():
            outputs = self.model(x)
        
        # Возвращаем numpy array
        return outputs.cpu().numpy()[0]
    
    def _prepare_features_from_array(self, data: np.ndarray) -> np.ndarray:
        """Подготавливает признаки из numpy array"""
        # Обрабатываем 3D массивы
        if data.ndim == 3:
            if data.shape[0] == 1:
                data = data.squeeze(0)
            else:
                raise ValueError(f"Expected single batch, got batch_size={data.shape[0]}")
        
        # Проверяем размерность
        if data.shape[0] != self.context_length or data.shape[1] != self.num_features:
            raise ValueError(
                f"Expected shape ({self.context_length}, {self.num_features}), got {data.shape}"
            )
        
        return data
    
    def _prepare_features_from_dataframe(self, df: pd.DataFrame) -> np.ndarray:
        """Генерирует признаки из DataFrame с OHLCV"""
        # Проверяем количество данных
        if len(df) < self.context_length:
            raise ValueError(f"Need at least {self.context_length} candles, got {len(df)}")
        
        # Добавляем symbol если отсутствует
        if "symbol" not in df.columns:
            df = df.copy()
            df["symbol"] = "UNKNOWN"
        
        # Генерируем признаки
        features_result = self.feature_engineer.create_features(df)
        
        # Извлекаем числовые признаки
        if isinstance(features_result, pd.DataFrame):
            numeric_cols = features_result.select_dtypes(include=[np.number]).columns
            feature_cols = [
                col for col in numeric_cols
                if not col.startswith(("future_", "direction_", "profit_"))
                and col not in ["id", "timestamp", "datetime", "symbol"]
            ]
            features_array = features_result[feature_cols].values
            
            # Подгоняем количество признаков
            if features_array.shape[1] != self.num_features:
                if features_array.shape[1] > self.num_features:
                    features_array = features_array[:, :self.num_features]
                else:
                    padding = np.zeros((features_array.shape[0], self.num_features - features_array.shape[1]))
                    features_array = np.hstack([features_array, padding])
        else:
            features_array = features_result
        
        # Берем последние context_length строк
        if len(features_array) >= self.context_length:
            features = features_array[-self.context_length:]
        else:
            # Padding если недостаточно данных
            padding_size = self.context_length - len(features_array)
            padding = np.zeros((padding_size, features_array.shape[1]))
            features = np.vstack([padding, features_array])
        
        return features
    
    def _handle_zero_variance(self, features: np.ndarray) -> np.ndarray:
        """Обработка признаков с нулевой дисперсией"""
        feature_stds = features.std(axis=0)
        zero_variance_mask = feature_stds < 1e-6
        zero_variance_count = zero_variance_mask.sum()
        
        if zero_variance_count > 0:
            logger.debug(f"Found {zero_variance_count} zero variance features, adding noise")
            for i, is_zero_var in enumerate(zero_variance_mask):
                if is_zero_var:
                    noise = np.random.normal(0, 1e-4, features.shape[0])
                    features[:, i] = features[:, i] + noise
        
        return features
    
    def interpret_outputs(
        self,
        raw_outputs: np.ndarray,
        symbol: Optional[str] = None,
        current_price: Optional[float] = None,
        **kwargs
    ) -> UnifiedPrediction:
        """
        Интерпретирует выходы PatchTST модели в унифицированный формат.
        Перенос логики из MLManager._interpret_predictions.
        
        Args:
            raw_outputs: 20 выходов модели
            symbol: Торговый символ
            current_price: Текущая цена
            
        Returns:
            UnifiedPrediction с интерпретированными данными
        """
        # Структура выходов:
        # 0-3: future returns (15m, 1h, 4h, 12h)
        # 4-15: direction logits (12 values = 3 classes × 4 timeframes)
        # 16-19: risk metrics
        
        future_returns = raw_outputs[0:4]
        direction_logits = raw_outputs[4:16]
        risk_metrics_raw = raw_outputs[16:20]
        
        # Интерпретация направлений
        direction_logits_reshaped = direction_logits.reshape(4, 3)  # 4 таймфрейма × 3 класса
        
        timeframes = ["15m", "1h", "4h", "12h"]
        timeframe_predictions = {}
        directions = []
        direction_probs = []
        
        for i, (tf, logits) in enumerate(zip(timeframes, direction_logits_reshaped)):
            # Softmax для вероятностей
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / exp_logits.sum()
            direction_probs.append(probs)
            
            # Определяем направление
            direction_class = np.argmax(probs)
            directions.append(direction_class)
            
            # Маппинг классов
            if direction_class == 0:
                direction = SignalDirection.LONG
            elif direction_class == 1:
                direction = SignalDirection.SHORT
            else:
                direction = SignalDirection.NEUTRAL
            
            # Создаем предсказание для таймфрейма
            timeframe_predictions[tf] = TimeframePrediction(
                timeframe=tf,
                direction=direction,
                confidence=float(np.max(probs)),
                expected_return=float(future_returns[i]),
                direction_probabilities={
                    "LONG": float(probs[0]),
                    "SHORT": float(probs[1]),
                    "NEUTRAL": float(probs[2]),
                }
            )
        
        directions = np.array(directions)
        
        # Анализ качества сигнала
        weighted_direction = np.sum(directions * np.array([0.4, 0.3, 0.2, 0.1]))
        
        filter_result = self.quality_analyzer.analyze_signal_quality(
            directions=directions,
            direction_probs=direction_probs,
            future_returns=future_returns,
            risk_metrics=risk_metrics_raw,
            weighted_direction=weighted_direction,
        )
        
        # Определяем основные параметры
        if not filter_result.passed:
            signal_type = "NEUTRAL"
            signal_strength = 0.25
            confidence = 0.25
            stop_loss_pct = None
            take_profit_pct = None
        else:
            signal_type = filter_result.signal_type
            metrics = filter_result.quality_metrics
            signal_strength = metrics.agreement_score
            confidence = metrics.confidence_score
            
            # Расчет SL/TP для торговых сигналов
            if signal_type in ["LONG", "SHORT"]:
                base_sl = 0.01  # 1%
                base_tp = 0.02  # 2%
                
                quality_multiplier = 0.8 + (metrics.quality_score * 0.4)
                
                stop_loss_pct = base_sl * quality_multiplier
                take_profit_pct = base_tp * quality_multiplier
                
                # Корректировка на волатильность
                volatility = np.std(future_returns[:2])
                if volatility > 0.01:
                    stop_loss_pct *= 1.2
                    take_profit_pct *= 1.2
                
                # Ограничения
                stop_loss_pct = np.clip(stop_loss_pct, 0.005, 0.025)
                take_profit_pct = np.clip(take_profit_pct, 0.01, 0.05)
            else:
                stop_loss_pct = None
                take_profit_pct = None
        
        # Определяем уровень риска
        avg_risk = float(np.mean(risk_metrics_raw))
        if avg_risk < 0.3:
            risk_level = RiskLevel.LOW
        elif avg_risk < 0.7:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.HIGH
        
        # Создаем объект риск-метрик
        risk_metrics = RiskMetrics(
            max_drawdown_1h=float(risk_metrics_raw[0]),
            max_rally_1h=float(risk_metrics_raw[1]),
            max_drawdown_4h=float(risk_metrics_raw[2]),
            max_rally_4h=float(risk_metrics_raw[3]),
            avg_risk=avg_risk,
            risk_level=risk_level
        )
        
        # Определяем основное направление
        direction_counts = {0: 0, 1: 0, 2: 0}
        for d in directions:
            direction_counts[d] += 1
        
        primary_direction_idx = max(direction_counts, key=direction_counts.get)
        primary_direction_map = {0: "LONG", 1: "SHORT", 2: "NEUTRAL"}
        primary_direction = primary_direction_map[primary_direction_idx]
        
        # Собираем возвраты по таймфреймам
        primary_returns = {
            "15m": float(future_returns[0]),
            "1h": float(future_returns[1]),
            "4h": float(future_returns[2]),
            "12h": float(future_returns[3]),
        }
        
        # Создаем унифицированное предсказание
        unified_prediction = UnifiedPrediction(
            # Основные параметры
            signal_type=signal_type,
            confidence=float(confidence),
            signal_strength=float(signal_strength),
            
            # Предсказания по таймфреймам
            timeframe_predictions=timeframe_predictions,
            primary_direction=primary_direction,
            primary_confidence=float(confidence),
            primary_returns=primary_returns,
            
            # Риск
            risk_level=risk_level.value,
            risk_metrics=risk_metrics,
            
            # SL/TP
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            
            # Качество
            quality_score=filter_result.quality_metrics.quality_score if filter_result.passed else 0.0,
            agreement_score=filter_result.quality_metrics.agreement_score if filter_result.passed else 0.0,
            filter_passed=filter_result.passed,
            filter_strategy=filter_result.strategy_used.value,
            rejection_reasons=filter_result.rejection_reasons,
            
            # Метаданные
            model_name="UnifiedPatchTST",
            model_version="2.0",
            timestamp=datetime.now(UTC),
            
            # Совместимость
            success_probability=float(confidence),
            
            # Сырые данные для отладки
            raw_outputs={
                "future_returns": future_returns.tolist(),
                "direction_logits": direction_logits.tolist(),
                "risk_metrics": risk_metrics_raw.tolist(),
                "weighted_direction": float(weighted_direction),
            }
        )
        
        logger.info(f"PatchTST interpretation complete: {signal_type} signal with confidence {confidence:.2f}")
        
        return unified_prediction
    
    def get_model_info(self) -> dict[str, Any]:
        """Возвращает информацию о модели"""
        return {
            "model_type": "UnifiedPatchTST",
            "model_name": self.model_name,
            "model_version": self.model_version,
            "model_path": str(self.model_path),
            "context_length": self.context_length,
            "num_features": self.num_features,
            "num_targets": self.num_targets,
            "device": str(self.device),
            "model_loaded": self.model is not None,
            "scaler_loaded": self.scaler is not None,
            "torch_compile_enabled": self.use_torch_compile,
            "initialized": self._initialized,
        }
    
    def switch_filtering_strategy(self, strategy: str) -> bool:
        """
        Переключение стратегии фильтрации сигналов.
        
        Args:
            strategy: Название стратегии (conservative/moderate/aggressive)
            
        Returns:
            True если успешно переключено
        """
        if self.quality_analyzer and self.quality_analyzer.switch_strategy(strategy):
            logger.info(f"✅ Filtering strategy switched to: {strategy}")
            return True
        else:
            logger.error(f"❌ Failed to switch strategy to: {strategy}")
            return False
    
    def get_filtering_statistics(self) -> dict[str, Any]:
        """Получение статистики работы системы фильтрации"""
        if self.quality_analyzer:
            return self.quality_analyzer.get_strategy_statistics()
        return {}
    
    def get_available_strategies(self) -> list[str]:
        """Получение списка доступных стратегий фильтрации"""
        return ["conservative", "moderate", "aggressive"]
    
    def get_current_strategy_config(self) -> dict[str, Any]:
        """Получение конфигурации текущей стратегии"""
        if self.quality_analyzer:
            return {
                "active_strategy": self.quality_analyzer.active_strategy.value,
                "strategy_params": self.quality_analyzer.strategy_params,
                "timeframe_weights": self.quality_analyzer.timeframe_weights.tolist(),
                "quality_weights": self.quality_analyzer.quality_weights,
            }
        return {}