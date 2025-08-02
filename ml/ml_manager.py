#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML Manager для управления PatchTST моделью в BOT Trading v3
"""

import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import torch

from core.logger import setup_logger
from ml.logic.feature_engineering import FeatureEngineer

logger = setup_logger("ml_manager")


class MLManager:
    """
    Менеджер для управления ML моделями в торговой системе.
    Работает с PatchTST моделью для предсказания движений рынка.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация ML менеджера.

        Args:
            config: Конфигурация системы
        """
        self.config = config
        self.model = None
        self.scaler = None
        self.feature_engineer = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Пути к моделям
        self.model_path = Path("models/saved/best_model_20250728_215703.pth")
        self.scaler_path = Path("models/saved/data_scaler.pkl")

        # Параметры модели
        self.context_length = 96  # 24 часа при 15-минутных свечах
        self.num_features = 240
        self.num_targets = 20

        logger.info(f"MLManager initialized, device: {self.device}")

    async def initialize(self):
        """Инициализация и загрузка моделей"""
        try:
            # Загружаем модель
            await self._load_model()

            # Загружаем scaler
            await self._load_scaler()

            # Инициализируем feature engineer
            self.feature_engineer = FeatureEngineer()

            logger.info("ML components initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing ML components: {e}")
            raise

    async def _load_model(self):
        """Загрузка PatchTST модели"""
        try:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Model file not found: {self.model_path}")

            # Создаем экземпляр модели
            self.model = UnifiedPatchTST(
                c_in=self.num_features,
                context_len=self.context_length,
                target_dim=self.num_targets,
                patch_len=16,
                stride=8,
                max_seq_len=1024,
                n_layers=3,
                d_model=128,
                n_heads=16,
                d_k=None,
                d_v=None,
                d_ff=256,
                norm="BatchNorm",
                attn_dropout=0.0,
                dropout=0.0,
                act="gelu",
                key_padding_mask="auto",
                padding_var=None,
                attn_mask=None,
                res_attention=True,
                pre_norm=False,
                store_attn=False,
                pe="zeros",
                learn_pe=True,
                fc_dropout=0.0,
                head_dropout=0.0,
                padding_patch="end",
                pretrain_head=False,
                head_type="flatten",
                individual=False,
                revin=True,
                affine=True,
                subtract_last=False,
                verbose=False,
            )

            # Загружаем веса
            checkpoint = torch.load(self.model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint["model_state_dict"])
            self.model.to(self.device)
            self.model.eval()

            logger.info(f"Model loaded successfully from {self.model_path}")

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    async def _load_scaler(self):
        """Загрузка scaler для нормализации данных"""
        try:
            if not self.scaler_path.exists():
                raise FileNotFoundError(f"Scaler file not found: {self.scaler_path}")

            with open(self.scaler_path, "rb") as f:
                self.scaler = pickle.load(f)

            logger.info(f"Scaler loaded successfully from {self.scaler_path}")

        except Exception as e:
            logger.error(f"Error loading scaler: {e}")
            raise

    async def predict(self, ohlcv_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Делает предсказание на основе OHLCV данных.

        Args:
            ohlcv_data: DataFrame с OHLCV данными (минимум 96 свечей)

        Returns:
            Dict с предсказаниями и рекомендациями
        """
        try:
            # Проверяем количество данных
            if len(ohlcv_data) < self.context_length:
                raise ValueError(
                    f"Need at least {self.context_length} candles, got {len(ohlcv_data)}"
                )

            # Берем последние context_length свечей
            if len(ohlcv_data) > self.context_length:
                ohlcv_data = ohlcv_data.iloc[-self.context_length :]

            # Генерируем признаки
            features = self.feature_engineer.generate_features(ohlcv_data)

            # Нормализуем данные
            features_scaled = self.scaler.transform(features)

            # Преобразуем в тензор
            x = torch.FloatTensor(features_scaled).unsqueeze(0).to(self.device)

            # Делаем предсказание
            with torch.no_grad():
                outputs = self.model(x)

            # Интерпретируем результаты
            predictions = self._interpret_predictions(outputs)

            return predictions

        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            raise

    def _interpret_predictions(self, outputs: torch.Tensor) -> Dict[str, Any]:
        """
        Интерпретация выходов модели.

        Args:
            outputs: Тензор с 20 выходами модели

        Returns:
            Dict с интерпретированными предсказаниями
        """
        outputs_np = outputs.cpu().numpy()[0]

        # Структура выходов:
        # 0-3: future returns (15m, 1h, 4h, 12h)
        # 4-7: future directions
        # 8-15: level targets (цены для разных уровней)
        # 16-19: risk metrics

        future_returns = outputs_np[0:4]
        future_directions = outputs_np[4:8]
        level_targets = outputs_np[8:16]
        risk_metrics = outputs_np[16:20]

        # Определяем основной сигнал
        # Используем взвешенное среднее направлений с большим весом на ближайшие таймфреймы
        weights = np.array([0.4, 0.3, 0.2, 0.1])
        weighted_direction = np.sum(future_directions * weights)

        # Определяем силу сигнала
        signal_strength = abs(weighted_direction)

        # Определяем тип сигнала
        if weighted_direction > 0.1:
            signal_type = "BUY"
        elif weighted_direction < -0.1:
            signal_type = "SELL"
        else:
            signal_type = "NEUTRAL"

        # Рассчитываем уровни SL/TP на основе предсказанных уровней
        current_price_idx = len(level_targets) // 2

        if signal_type == "BUY":
            stop_loss = float(level_targets[max(0, current_price_idx - 2)])
            take_profit = float(
                level_targets[min(len(level_targets) - 1, current_price_idx + 3)]
            )
        elif signal_type == "SELL":
            stop_loss = float(
                level_targets[min(len(level_targets) - 1, current_price_idx + 2)]
            )
            take_profit = float(level_targets[max(0, current_price_idx - 3)])
        else:
            stop_loss = None
            take_profit = None

        # Оценка риска
        avg_risk = float(np.mean(risk_metrics))
        risk_level = "LOW" if avg_risk < 0.3 else "MEDIUM" if avg_risk < 0.7 else "HIGH"

        return {
            "signal_type": signal_type,
            "signal_strength": float(signal_strength),
            "confidence": float(
                1.0 - avg_risk
            ),  # Инвертируем риск для получения уверенности
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_level": risk_level,
            "predictions": {
                "returns_15m": float(future_returns[0]),
                "returns_1h": float(future_returns[1]),
                "returns_4h": float(future_returns[2]),
                "returns_12h": float(future_returns[3]),
                "direction_score": float(weighted_direction),
            },
            "timestamp": datetime.now().isoformat(),
        }

    async def update_model(self, new_model_path: str):
        """
        Обновление модели на новую версию.

        Args:
            new_model_path: Путь к новой модели
        """
        try:
            # Сохраняем старую модель как резервную
            backup_path = self.model_path.with_suffix(".pth.backup")
            if self.model_path.exists():
                self.model_path.rename(backup_path)

            # Копируем новую модель
            Path(new_model_path).rename(self.model_path)

            # Перезагружаем модель
            await self._load_model()

            logger.info(f"Model updated successfully from {new_model_path}")

        except Exception as e:
            logger.error(f"Error updating model: {e}")
            # Восстанавливаем старую модель
            if backup_path.exists():
                backup_path.rename(self.model_path)
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """Получение информации о модели"""
        return {
            "model_type": "UnifiedPatchTST",
            "model_path": str(self.model_path),
            "context_length": self.context_length,
            "num_features": self.num_features,
            "num_targets": self.num_targets,
            "device": str(self.device),
            "model_loaded": self.model is not None,
            "scaler_loaded": self.scaler is not None,
        }
